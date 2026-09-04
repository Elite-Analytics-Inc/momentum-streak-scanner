# momentum-streak-scanner — specification

*This file is the source of truth for the analysis. When anything changes — an input, an output
column, the dashboard's shape — this file changes first, and everything else follows from it.
`README.md` is a plain summary derived from this spec; it is regenerated when the spec changes and
never edited directly.*

## The question

Which S&P 500 stocks have closed higher every single session for days on end — and are still doing
it as of the latest close? The analysis finds every stock with an **active, unbroken run of higher
closes** ending exactly on the most recent completed session, drops any streak that has already
broken, keeps the ones at least a minimum length long, and ranks them by streak length and then by
the gain the streak produced.

## How it decides

For each stock, start at the latest close and step back one session at a time:

1. **The gatekeeper.** If the latest close is not above the previous close, the stock's active
   streak is zero. It is ignored, whatever it did before.
2. **The backward count.** If the latest close is above the previous one, that is a streak of one.
   Keep stepping back; each session whose close beat the one before adds one.
3. **The break.** The first flat or down session ends the count. The close *on* that session is
   the **base** — the price the streak is measured from.

A stock is a **winner** when its streak is at least `min_streak_days` long. Winners are ranked by
streak length (longest first), then by **streak gain** — the percentage rise from the base close to
the latest close.

Decisions taken, and why:

- **Only closed sessions count.** During US market hours the price feed already carries a row for
  today, half-finished. The loader drops it until 4:15pm New York time; a half day is not a close.
  Whoever loads the same feed into the lake must do the same.
- **Adjusted close, not raw close.** A dividend or split moves the raw close without the stock
  really falling. The adjusted series removes that, so an ex-dividend day does not break a streak by
  itself. This is what the original spec asks for ("Adj Close").
- **The scan date is the newest close in the data, not today's date.** An analysis anchored on
  `now()` finds nothing on a weekend.
- **The backward walk is done in SQL without a loop.** Every session is flagged *up* or not; a
  running count of the not-up sessions per stock gives each session a run id that changes only on a
  break. Numbering the rows within a run (minus the break itself) is the streak length as of that
  session, and the run's first row is the base. This gives a streak length for every stock on every
  day in one pass, which is what the market-backdrop page reads.
- **A stock with no close on the scan date is stale and excluded**, and counted in the overview so
  a feed gap is visible rather than silent.
- **A streak that reaches the start of the window is flagged `capped`**: it is *at least* that
  long, and the window should be widened.
- **The roster and the prices come from the live feeds, never a typed-in list.** On the laptop,
  `tools/load_market_data.py` fetches the S&P 500 roster from Wikipedia and three months of daily
  prices from Yahoo Finance (via `yfinance`), and writes them as the two input tables. It is a
  loader, not part of the analysis: the same feeds will be loaded into the lake under the same
  names, and `main.py` runs unchanged against them.
- **The loader is gentle with Yahoo Finance.** Batches of 25 symbols, a two-second pause between
  batches, growing retry waits on failure, and every finished batch cached on disk so a re-run
  resumes instead of refetching.
- **Symbols are sanitised for the feed but shown as the exchange writes them.** Wikipedia lists
  `BRK.B`; Yahoo wants `BRK-B`. The roster carries both; every output shows the exchange spelling.

## The pick score (page 5)

Four signs, each 0–100, computed for every stock on every session so the rule can be replayed:

| Sign | Weight | Definition |
| --- | --- | --- |
| accel | 30 | the last session's rise, capped at 3% = 100 |
| tide | 30 | share of the stock's sector that rose that session |
| steady | 20 | share of the streak's gain not made in its single biggest day |
| trend | 20 | the close as a share of the stock's highest close so far in the window |

Score = 0.3·accel + 0.3·tide + 0.2·steady + 0.2·trend. Picks are the top N scores among streaking
stocks on the scan date. The back-test keeps the top 20 for every past session with a next
session, records whether each rose, and the page adds up the first N.

**Decision, and the finding it rests on.** The score was designed by looking at the same weeks it
is tested on, and forty sessions is a short test, so its hit rate is flattered and noisy. On the
first run (data to 3 September 2026) the top-five picks rose the next session 40% of the time, all
streaking stocks 45.7%, and the whole index 50.2% — the rule did *worse* than random. The page
is built to show that honestly rather than to hide it: the back-test tiles sit beside the picks.

## Inputs

| Dataset | Each row is | What it provides |
| --- | --- | --- |
| `markets.daily_prices` | one stock on one closed trading session | `symbol` (Yahoo spelling), `trade_date`, `open`, `high`, `low`, `close`, `adj_close`, `volume` |
| `markets.sp500_constituents` | one current index member | `symbol` (exchange spelling), `yahoo_symbol`, `company`, `sector`, `sub_industry`, `headquarters`, `date_added`, `cik` (10-digit string, leading zeros kept), `founded` |

The price table must hold **closed sessions only** and at least as much history as the longest
streak the analysis is expected to find (the loader pulls three months).

## Parameters (what varies per run)

| Parameter | What it means | Default | Bounds |
| --- | --- | --- | --- |
| `min_streak_days` | the shortest streak worth reporting | 3 | 2–30 |
| `lookback_days` | calendar days of history considered, back from the latest close | 60 | 10–365 |

## The dashboard

Five pages, so that every page fits its screen and every control sits beside what it drives.

1. **Today's Streaks** (front page). Four headline tiles: the close the scan is as of, how many
   stocks are on a streak, the longest streak, and the best streak gain. Then the **leaderboard**
   — the spec's ranked listing — with two controls directly above it: a slider for the minimum
   streak length and a sector multi-select. Below that, two charts: stocks by streak length (the
   ladder) and streaking stocks by sector.
2. **Streaks Side By Side.** Pick a streak length; every streak of that length is drawn on one
   chart, indexed to 100 at the base close, so a steady grind and a one-day jump can be told apart.
   Three tiles for the group and a table of its members.
3. **One Stock, Up Close.** Pick any winner; its full-window price line with the active streak
   highlighted and the base marked, a green/red bar chart of daily moves, four tiles, and a
   day-by-day table of the streak.
4. **The Market Backdrop.** Breadth (share of index members up each session) and the count of
   stocks on a streak as of each session, side by side, so the reader can tell a market-wide lift
   from stock-specific momentum. Then a sector table with share, longest streak, and the sector's
   own breadth.
5. **Next-Session Picks.** Every streaking stock scored out of 100 on four signs that its run
   still had force at the close (below), the top N named as picks — N chosen from a dropdown of
   5, 10, 15 or 20 — with a stacked bar of what each score is made of and a table giving the
   reasons and warnings in words. Beside it, the **back-test**: the same rule replayed on every
   earlier day in the window, its picks checked against the next session, and the hit rate shown
   next to the whole index's rate for the same days. The page says plainly that if the picks are
   not clearly above the index, the rule has no edge.

Every page opens with a note on how to read it and a glossary of its terms; every tile, chart and
table carries an ⓘ saying what it shows and how to judge it.

## Outputs (the results the dashboard reads)

| Output | Grain | Columns |
| --- | --- | --- |
| `scan_overview` | one row | scan_date, scan_date_label, universe_size, priced_today, stale_symbols, winners, longest_streak, longest_symbol, longest_company, best_gain_pct, best_gain_symbol, share_up_today_pct, avg_gain_pct, history_sessions, min_streak_days, lookback_days |
| `active_streaks` | one row per winner, in rank order | rank, symbol, company, sector, sub_industry, streak_days, streak_gain_pct, avg_daily_gain_pct, latest_day_pct, base_date, base_close, latest_close, capped |
| `streak_ladder` | one row per streak length among winners | streak_days, label, stocks, avg_gain_pct, best_gain_pct, best_symbol |
| `sector_streaks` | one row per sector | sector, priced, winners, winners_share_pct, up_today_pct, longest_streak, avg_gain_pct |
| `price_history` | one row per winner per session in the window | symbol, company, trade_date, close, day_pct, up_pct, down_pct, streak_days_as_of, in_active_streak, streak_close, base_close |
| `streak_paths` | one row per winner per streak day, day 0 = base | symbol, company, streak_days, day_index, trade_date, close, indexed, pct_from_base |
| `daily_breadth` | one row per session in the window | trade_date, stocks_priced, stocks_up, share_up_pct, on_streak, longest_streak |
| `pick_scores` | one row per winner on the scan date, best score first | pick_rank, symbol, company, sector, streak_days, streak_gain_pct, latest_day_pct, score, accel_pts, tide_pts, steady_pts, trend_pts, sector_up_pct, biggest_day_pct, pct_of_high, recommended, why, warning |
| `pick_backtest` | one row per pick (top 20) per past session with a next session | pick_date, next_date, pick_rank, symbol, streak_days, score, next_day_pct, rose_next_day, streak_hit_pct, market_hit_pct |
| `pick_backtest_summary` | one row | days_tested, streak_hit_pct, streak_avg_next_pct, market_hit_pct, market_avg_next_pct, top_pick, top_score |

## Dependencies

The analysis itself needs the platform SDK (`tarn`) only: every output is a single SQL query on the
governed connection.

The one-time data loader (`tools/load_market_data.py`, laptop only, never part of the promoted job)
uses `yfinance` for prices, `requests` for the Wikipedia page, and `lxml` for reading its table.
They live in the `loader` dependency group and are installed only when that script is run:
`uv run --group loader python tools/load_market_data.py`.
