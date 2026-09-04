"""momentum-streak-scanner — S&P 500 stocks on an unbroken run of higher closes, right now.

**The measurement, stated plainly, because it is the whole analysis.** For each stock, walk back
from the most recent close: if it closed above the previous close, that is one streak day; keep
stepping back while each close beats the one before it. The first flat or down session ends the
count. A stock whose latest session was flat or down has a streak of zero and is ignored — as is
any streak that ended before the latest close, however impressive it was. Only *active* streaks
count.

The winners are those with at least `min_streak_days` sessions, ranked by streak length and then
by the **streak gain**: the percentage rise from the close just *before* the streak began to the
latest close. Both the floor and the history window are launch parameters.

**How the SQL does the backward walk without a loop.** Each session is flagged *up* (close above
the previous close) or not. A running count of the not-up sessions, per stock in date order, gives
every session a *run id* that only changes on a break — so each run is one break session followed
by every consecutive up session after it. Numbering the rows inside a run (minus the break itself)
is the streak length as of that day, and the run's first row is the pre-streak base: its close is
what the streak gain is measured from. The active streak is simply that number on the latest date.
The same derivation gives a streak length for every stock on every day, which is what the
market-backdrop page reads.

**The shape is the Job Definition contract.** `main.py` runs top to bottom; `parameters.json`
beside it declares what varies per run; `dashboard/` holds the pages shipped at the end.

**Every output is one governed query.** The shared derivation is a block of CTEs repeated in each
output's SQL, so each artifact is produced by a single SELECT on the governed connection.
"""

import os

import tarn

#: The deployment names its own workspace catalog; a job reads the name from the environment
#: rather than hardcoding it, so the same repo runs against any install.
CATALOG = os.environ.get("TARN_WORKSPACE_CATALOG", "lake")

#: Typed and constrained in `parameters.json`, which is also what renders the launch form.
MIN_STREAK = int(os.environ.get("TARN_PARAM_MIN_STREAK_DAYS", "3"))
LOOKBACK_DAYS = int(os.environ.get("TARN_PARAM_LOOKBACK_DAYS", "60"))

#: The shared derivation: prices in the window, each session flagged up or not, sessions grouped
#: into runs, and the streak length + base price as of every session.
#:
#: **Anchored on the newest close in the data, not on today's date.** The feed only holds closed
#: sessions (a half-finished day is not a close), so "today" is the latest date present; an
#: analysis anchored on `now()` would find nothing on a weekend.
#:
#: **Adjusted close, not raw close.** A dividend or split moves the raw close without the stock
#: really falling; the adjusted series removes that, so a streak is not broken by an ex-dividend
#: day. This is what the spec asks for ("Adj Close").
#:
#: **A session with no previous close counts as a break.** The first row of the window has nothing
#: to compare against, so a streak can never be longer than the window shows. `capped` says when
#: that happened — it means the streak is *at least* that long, and the window should be widened.
STREAKS = f"""
    roster AS (
        SELECT symbol, yahoo_symbol, company, sector, sub_industry
        FROM {CATALOG}.markets.sp500_constituents
    ),
    scan AS (
        SELECT max(trade_date) AS scan_date FROM {CATALOG}.markets.daily_prices
    ),
    prices AS (
        SELECT p.symbol AS yahoo_symbol, p.trade_date, p.adj_close AS close
        FROM {CATALOG}.markets.daily_prices p, scan
        WHERE p.adj_close IS NOT NULL
          AND p.trade_date >= scan.scan_date - INTERVAL '{LOOKBACK_DAYS}' DAY
    ),
    moves AS (
        SELECT yahoo_symbol, trade_date, close,
               lag(close) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date) AS prev_close
        FROM prices
    ),
    flagged AS (
        SELECT *,
               CASE WHEN prev_close IS NOT NULL AND close > prev_close THEN 1 ELSE 0 END AS up,
               CASE WHEN prev_close IS NOT NULL AND prev_close > 0
                    THEN 100.0 * (close / prev_close - 1) END AS day_pct
        FROM moves
    ),
    runs AS (
        -- the running count of non-up sessions: a new id at every break, so each run is one
        -- break session followed by the consecutive up sessions after it
        SELECT *,
               sum(1 - up) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date
                                 ROWS UNBOUNDED PRECEDING) AS run_id
        FROM flagged
    ),
    streaked AS (
        -- inside a run: row number minus the break itself = streak length as of that day;
        -- the run's first row is the pre-streak base the gain is measured from
        SELECT r.*,
               row_number() OVER (PARTITION BY yahoo_symbol, run_id ORDER BY trade_date) - 1
                   AS streak_days,
               first_value(close) OVER (PARTITION BY yahoo_symbol, run_id ORDER BY trade_date)
                   AS base_close,
               first_value(trade_date) OVER (PARTITION BY yahoo_symbol, run_id ORDER BY trade_date)
                   AS base_date,
               first_value(prev_close IS NULL) OVER (PARTITION BY yahoo_symbol, run_id ORDER BY trade_date)
                   AS capped
        FROM runs r
    ),
    today AS (
        -- every stock's state on the latest close; a stock with no row that day is stale
        SELECT s.*, ro.symbol, ro.company, ro.sector, ro.sub_industry,
               100.0 * (s.close / s.base_close - 1) AS streak_gain_pct
        FROM streaked s
        JOIN scan ON s.trade_date = scan.scan_date
        JOIN roster ro ON ro.yahoo_symbol = s.yahoo_symbol
    ),
    winners AS (
        SELECT t.*,
               row_number() OVER (ORDER BY streak_days DESC, streak_gain_pct DESC, symbol) AS rank
        FROM today t
        WHERE streak_days >= {MIN_STREAK}
    )
"""

#: The headline numbers. `scan_date_label` is the date as a person reads it, because every number
#: on the page is "as of" that close and the reader must never guess which day that was.
SCAN_OVERVIEW = f"""
WITH {STREAKS}
SELECT
    (SELECT scan_date FROM scan) AS scan_date,
    (SELECT strftime(scan_date, '%a %-d %b %Y') FROM scan) AS scan_date_label,
    (SELECT count(*) FROM roster) AS universe_size,
    (SELECT count(*) FROM today) AS priced_today,
    (SELECT count(*) FROM roster) - (SELECT count(*) FROM today) AS stale_symbols,
    (SELECT count(*) FROM winners) AS winners,
    (SELECT coalesce(max(streak_days), 0) FROM winners) AS longest_streak,
    (SELECT symbol FROM winners WHERE rank = 1) AS longest_symbol,
    (SELECT company FROM winners WHERE rank = 1) AS longest_company,
    (SELECT round(max(streak_gain_pct), 2) FROM winners) AS best_gain_pct,
    (SELECT symbol FROM winners ORDER BY streak_gain_pct DESC LIMIT 1) AS best_gain_symbol,
    (SELECT round(100.0 * sum(up) / greatest(1, count(*)), 1) FROM today) AS share_up_today_pct,
    (SELECT round(avg(streak_gain_pct), 2) FROM winners) AS avg_gain_pct,
    (SELECT count(DISTINCT trade_date) FROM prices) AS history_sessions,
    {MIN_STREAK}::INTEGER AS min_streak_days,
    {LOOKBACK_DAYS}::INTEGER AS lookback_days
"""

#: The leaderboard — the spec's terminal listing, as a table. Ordered by streak length, then by
#: the gain made during the streak: exactly the two-level ranking the spec asks for.
ACTIVE_STREAKS = f"""
WITH {STREAKS}
SELECT rank, symbol, company, sector, sub_industry,
       streak_days,
       round(streak_gain_pct, 2) AS streak_gain_pct,
       round(streak_gain_pct / streak_days, 2) AS avg_daily_gain_pct,
       round(day_pct, 2) AS latest_day_pct,
       base_date,
       round(base_close, 2) AS base_close,
       round(close, 2) AS latest_close,
       capped
FROM winners
ORDER BY rank
"""

#: One row per streak length — how the winners spread across 3, 4, 5… days. The tall bar is
#: always at the floor; what matters is how far the ladder reaches to the right.
STREAK_LADDER = f"""
WITH {STREAKS}
SELECT streak_days,
       streak_days || ' days' AS label,
       count(*) AS stocks,
       round(avg(streak_gain_pct), 2) AS avg_gain_pct,
       max(streak_gain_pct) AS best_gain_pct,
       arg_max(symbol, streak_gain_pct) AS best_symbol
FROM winners
GROUP BY streak_days
ORDER BY streak_days
"""

#: Where the streaks cluster. Many winners in one sector is a sector move, not stock-picking —
#: which changes what a reader should do with the list.
SECTOR_STREAKS = f"""
WITH {STREAKS}
SELECT t.sector,
       count(*) AS priced,
       count(*) FILTER (WHERE t.streak_days >= {MIN_STREAK}) AS winners,
       round(100.0 * count(*) FILTER (WHERE t.streak_days >= {MIN_STREAK}) / count(*), 1)
           AS winners_share_pct,
       round(100.0 * sum(t.up) / count(*), 1) AS up_today_pct,
       coalesce(max(t.streak_days), 0) AS longest_streak,
       round(avg(t.streak_gain_pct) FILTER (WHERE t.streak_days >= {MIN_STREAK}), 2)
           AS avg_gain_pct
FROM today t
GROUP BY t.sector
ORDER BY winners DESC, winners_share_pct DESC
"""

#: The winners' recent price paths, for the one-stock page. `streak_close` is the close only on
#: sessions inside the active streak (null elsewhere), so a chart can draw the streak as its own
#: highlighted line over the full history. `up_pct` / `down_pct` split each day's move by sign so
#: a bar chart can colour gains and losses differently.
PRICE_HISTORY = f"""
WITH {STREAKS}
SELECT w.symbol, w.company, s.trade_date,
       round(s.close, 2) AS close,
       round(s.day_pct, 2) AS day_pct,
       CASE WHEN s.day_pct > 0 THEN round(s.day_pct, 2) END AS up_pct,
       CASE WHEN s.day_pct <= 0 THEN round(s.day_pct, 2) END AS down_pct,
       s.streak_days AS streak_days_as_of,
       s.trade_date >= w.base_date AS in_active_streak,
       CASE WHEN s.trade_date >= w.base_date THEN round(s.close, 2) END AS streak_close,
       round(w.base_close, 2) AS base_close
FROM streaked s
JOIN winners w ON w.yahoo_symbol = s.yahoo_symbol
ORDER BY w.rank, s.trade_date
"""

#: The winners' streaks side by side, indexed to 100 at the pre-streak close so a $15 stock and a
#: $1,500 stock can share one chart. Day 0 is the base session; day N is the latest close.
STREAK_PATHS = f"""
WITH {STREAKS}
SELECT w.symbol, w.company, w.streak_days,
       s.streak_days AS day_index,
       s.trade_date,
       round(s.close, 2) AS close,
       round(100.0 * s.close / w.base_close, 2) AS indexed,
       round(100.0 * (s.close / w.base_close - 1), 2) AS pct_from_base
FROM streaked s
JOIN winners w ON w.yahoo_symbol = s.yahoo_symbol AND s.trade_date >= w.base_date
ORDER BY w.rank, s.trade_date
"""

#: The market backdrop, one row per session: how much of the index rose that day, and how many
#: stocks were on a qualifying streak *as of* that day. Fifty-one streaks after three broad up
#: days is the market lifting everything; fifty-one after a mixed week is stock-specific momentum.
DAILY_BREADTH = f"""
WITH {STREAKS}
SELECT trade_date,
       count(*) AS stocks_priced,
       sum(up) AS stocks_up,
       round(100.0 * sum(up) / count(*), 1) AS share_up_pct,
       count(*) FILTER (WHERE streak_days >= {MIN_STREAK}) AS on_streak,
       max(streak_days) AS longest_streak
FROM streaked
WHERE prev_close IS NOT NULL
GROUP BY trade_date
ORDER BY trade_date
"""

OUTPUTS = (
    ("scan_overview", SCAN_OVERVIEW, "the headline numbers"),
    ("active_streaks", ACTIVE_STREAKS, "the leaderboard"),
    ("streak_ladder", STREAK_LADDER, "winners by streak length"),
    ("sector_streaks", SECTOR_STREAKS, "where the streaks cluster"),
    ("price_history", PRICE_HISTORY, "the winners' recent prices"),
    ("streak_paths", STREAK_PATHS, "the streaks side by side"),
    ("daily_breadth", DAILY_BREADTH, "the market backdrop"),
)


def main() -> None:
    tarn.stage("analyse")
    tarn.log(
        f"active streaks of at least {MIN_STREAK} higher closes, over the last "
        f"{LOOKBACK_DAYS} calendar days of prices"
    )

    for index, (name, sql, what) in enumerate(OUTPUTS, start=1):
        tarn.progress(index / (len(OUTPUTS) + 1), what)
        tarn.save_artifact(name, sql)
        tarn.log(f"wrote {name} — {what}")

    tarn.stage("dashboard")
    # The repo's own `dashboard/` directory, uploaded exactly as shipped — the pages the author
    # wrote, never pages generated by the run.
    tarn.save_dashboard()
    tarn.progress(1.0, "dashboard uploaded")

    tarn.stage("done")
    tarn.conclusion(
        f"S&P 500 stocks that closed higher {MIN_STREAK} or more sessions in a row, ending on the "
        "latest close, ranked by streak length and then by the gain made during the streak. The "
        "leaderboard is the list; the backdrop page says whether the market lifted them or they "
        "rose on their own."
    )


if __name__ == "__main__":
    main()
