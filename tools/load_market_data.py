"""One-time loader: the S&P 500 roster and its recent daily prices, saved as the local lake.

This is **not** part of the analysis. The analysis (`main.py`) reads two governed tables from the
platform's lake; on the laptop those tables are the parquet files this script writes under
`data/lake/markets/`. When the same yfinance feed is loaded into the real lake under the same
names, `main.py` runs against it unchanged.

Run it from the repo root:

    uv run --group loader python tools/load_market_data.py

What it produces:

- `data/lake/markets/sp500_constituents/`  one row per index member, as Wikipedia lists them today
- `data/lake/markets/daily_prices/`         one row per stock per trading day, ~3 months back

**Being polite to Yahoo Finance is the whole design of the download.** Five hundred symbols is a
lot of requests, and Yahoo throttles clients that hammer it. So the script:

- fetches in small batches (a few dozen symbols at a time) with a pause between batches;
- retries a failed batch with a growing wait (a second, then a few, then longer) before giving up
  on it;
- caches every finished batch on disk, so a re-run after a failure resumes rather than refetches.
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
LAKE = ROOT / "data" / "lake" / "markets"
CACHE = ROOT / ".loader_cache"                    # gitignored: it never leaves the laptop

#: How much history to pull. The streak logic itself needs only weeks, but the analysis also
#: **back-tests its own pick rule**, and three months of sessions was far too short to tell a real
#: edge from noise — the first version of the pick page was judged on forty days and said nothing
#: trustworthy. Two years gives ~500 sessions and a held-out half.
PERIOD = "2y"
#: Batch shape. Twenty-five symbols per request group, two seconds between groups, is well under
#: Yahoo's tolerance and still finishes the whole index in a few minutes.
BATCH_SIZE = 25
PAUSE_BETWEEN_BATCHES = 2.0
#: Retry waits for a batch that failed (network hiccup, throttle): patient, then more patient.
RETRY_WAITS = (2, 8, 30, 90)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
#: Wikipedia refuses the default Python user agent; a plain descriptive one is what they ask for.
HEADERS = {"User-Agent": "tarn-draft momentum-streak loader (contact: analysis author)"}


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------------------------
# 1. The roster — fetched live, never hardcoded (spec §2).
# --------------------------------------------------------------------------------------------
def fetch_constituents() -> pd.DataFrame:
    log(f"fetching the S&P 500 roster from {WIKI_URL}")
    html = requests.get(WIKI_URL, headers=HEADERS, timeout=30).text
    tables = pd.read_html(io.StringIO(html))
    # The first table on the page is the current constituents; the second is the change log.
    roster = tables[0]
    roster = roster.rename(
        columns={
            "Symbol": "symbol",
            "Security": "company",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "sub_industry",
            "Headquarters Location": "headquarters",
            "Date added": "date_added",
            "CIK": "cik",
            "Founded": "founded",
        }
    )
    keep = ["symbol", "company", "sector", "sub_industry", "headquarters", "date_added", "cik", "founded"]
    roster = roster[[c for c in keep if c in roster.columns]].copy()
    # Symbol sanitisation (spec §2): Wikipedia writes BRK.B, Yahoo wants BRK-B. Keep both — the
    # exchange spelling is what a person recognises, the Yahoo spelling is what the feed keys on.
    roster["yahoo_symbol"] = roster["symbol"].str.replace(".", "-", regex=False)
    # Real-data mess, kept on purpose: the CIK is a number with leading zeros — a string, not an
    # int, or `0000320193` silently becomes `320193`. `founded` has values like "1902 (1970)".
    roster["cik"] = roster["cik"].astype("string").str.zfill(10)
    roster["founded"] = roster["founded"].astype("string")
    # Wikipedia's markup leaks into a few company names — "ResMed|" carries a stray table pipe.
    # Left in, it shows up in the dashboard exactly as scraped, which reads as a broken cell.
    roster["company"] = roster["company"].astype("string").str.strip().str.rstrip("|").str.strip()
    roster["date_added"] = pd.to_datetime(roster["date_added"], errors="coerce").dt.date
    log(f"  {len(roster)} constituents")
    return roster


# --------------------------------------------------------------------------------------------
# 2. Prices — batched, paused, retried, cached.
# --------------------------------------------------------------------------------------------
def download_batch(symbols: list[str]) -> pd.DataFrame:
    """One polite request group. Returns long-format rows: symbol, trade_date, open…volume."""
    raw = yf.download(
        symbols,
        period=PERIOD,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,   # keep both the raw close and the dividend/split-adjusted close
        actions=False,
        threads=False,       # sequential inside the batch — gentler than a burst
        progress=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError("empty response")

    frames = []
    for sym in symbols:
        try:
            one = raw[sym] if isinstance(raw.columns, pd.MultiIndex) else raw
        except KeyError:
            continue                      # symbol not in the response — delisted, renamed, or throttled
        one = one.dropna(how="all")
        if one.empty:
            continue
        cols = {c: c.lower().replace(" ", "_") for c in one.columns}
        one = one.rename(columns=cols).reset_index().rename(columns={"Date": "trade_date", "index": "trade_date"})
        one["symbol"] = sym
        frames.append(one)
    if not frames:
        raise RuntimeError("no symbol in the batch returned rows")
    out = pd.concat(frames, ignore_index=True)
    # An older yfinance may omit adj_close when auto_adjust is off on some paths; never crash on it.
    if "adj_close" not in out.columns:
        out["adj_close"] = out["close"]
    out["trade_date"] = pd.to_datetime(out["trade_date"]).dt.date
    return out[["symbol", "trade_date", "open", "high", "low", "close", "adj_close", "volume"]]


def fetch_prices(symbols: list[str]) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    batches = [symbols[i : i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]
    log(f"downloading {len(symbols)} symbols in {len(batches)} batches of {BATCH_SIZE}")
    parts = []
    for n, batch in enumerate(batches, start=1):
        cached = CACHE / f"batch_{n:03d}.parquet"
        if cached.exists():
            parts.append(pd.read_parquet(cached) if _has_parquet_reader() else duckdb.read_parquet(str(cached)).df())
            log(f"  batch {n}/{len(batches)}: from cache")
            continue
        for attempt, wait in enumerate((0,) + RETRY_WAITS):
            if wait:
                log(f"  batch {n}: retrying in {wait}s")
                time.sleep(wait)
            try:
                rows = download_batch(batch)
                _write_parquet(rows, cached)
                parts.append(rows)
                log(f"  batch {n}/{len(batches)}: {rows['symbol'].nunique()}/{len(batch)} symbols, {len(rows)} rows")
                break
            except Exception as exc:  # noqa: BLE001 — any failure is a reason to wait and retry
                log(f"  batch {n}: failed ({exc})")
        else:
            log(f"  batch {n}: giving up after {len(RETRY_WAITS)} retries — {batch}")
        time.sleep(PAUSE_BETWEEN_BATCHES)
    if not parts:
        raise SystemExit("no prices downloaded at all — check the network, then re-run")
    prices = pd.concat(parts, ignore_index=True)
    # A cached batch comes back with timestamps; a fresh one with dates. One type, always.
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.date
    return prices


# --------------------------------------------------------------------------------------------
# Parquet through DuckDB — the engine the analysis runs on, and no extra writer package.
# --------------------------------------------------------------------------------------------
def _has_parquet_reader() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.register("df", df)
    con.execute(f"COPY (SELECT * FROM df) TO '{path.as_posix()}' (FORMAT PARQUET)")
    con.close()


#: The spec counts closed sessions only. During US market hours Yahoo's daily feed already carries
#: a row for today — a half-finished session that is not a close. Drop it until the bell.
MARKET_CLOSE_ET = (16, 15)   # 4:15pm New York time: a small margin after the 4pm close


def drop_open_session(prices: pd.DataFrame) -> pd.DataFrame:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today = now_et.date()
    if (now_et.hour, now_et.minute) >= MARKET_CLOSE_ET:
        return prices
    still_open = prices["trade_date"] == today
    if still_open.any():
        log(f"  dropping {int(still_open.sum())} rows for {today}: the session has not closed yet")
    return prices[~still_open].copy()


def main() -> None:
    roster = fetch_constituents()
    prices = drop_open_session(fetch_prices(roster["yahoo_symbol"].tolist()))

    _write_parquet(roster, LAKE / "sp500_constituents" / "constituents.parquet")
    _write_parquet(prices, LAKE / "daily_prices" / "prices.parquet")

    got = prices["symbol"].nunique()
    missing = sorted(set(roster["yahoo_symbol"]) - set(prices["symbol"]))
    summary = {
        "constituents": int(len(roster)),
        "symbols_with_prices": int(got),
        "symbols_missing": missing,
        "first_trade_date": str(prices["trade_date"].min()),
        "last_trade_date": str(prices["trade_date"].max()),
        "price_rows": int(len(prices)),
    }
    (CACHE / "load_summary.json").write_text(json.dumps(summary, indent=2))
    log(json.dumps(summary, indent=2))


if __name__ == "__main__":
    sys.exit(main())
