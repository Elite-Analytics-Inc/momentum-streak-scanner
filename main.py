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
    ),
    -- ---- the other direction: how many sessions has each stock closed DOWN in a row? -----
    -- Built the same way as the up-streak, on the same rows. It exists because the analysis
    -- back-tests its own pick rule, and that test said the momentum rule loses: over two years
    -- the stocks on the longest up-runs did *worse* than the market next session, in both halves
    -- of the sample. The falling stocks were where the small edge was. An analysis that hides
    -- that to protect its own headline is worthless, so both directions are computed and both
    -- are shown.
    dn_runs AS (
        SELECT yahoo_symbol, trade_date, close, prev_close, day_pct,
               CASE WHEN prev_close IS NOT NULL AND close < prev_close THEN 1 ELSE 0 END AS down,
               sum(CASE WHEN prev_close IS NOT NULL AND close < prev_close THEN 0 ELSE 1 END)
                   OVER (PARTITION BY yahoo_symbol ORDER BY trade_date ROWS UNBOUNDED PRECEDING)
                   AS dn_run_id
        FROM flagged
    ),
    dn_streaked AS (
        SELECT *,
               row_number() OVER (PARTITION BY yahoo_symbol, dn_run_id ORDER BY trade_date) - 1
                   AS dn_streak
        FROM dn_runs
    ),
    -- every stock, every session, with the two things the reversal rule reads: how many days it
    -- has fallen in a row, and how far it has fallen over five sessions
    reversal AS (
        SELECT d.yahoo_symbol, d.trade_date, d.close, d.day_pct, d.dn_streak,
               ro.symbol, ro.company, ro.sector,
               100.0 * (d.close / nullif(lag(d.close, 5) OVER
                   (PARTITION BY d.yahoo_symbol ORDER BY d.trade_date), 0) - 1) AS r5,
               100.0 * (d.close / nullif(max(d.close) OVER
                   (PARTITION BY d.yahoo_symbol ORDER BY d.trade_date ROWS 19 PRECEDING), 0))
                   AS pct_of_hi20,
               lead(d.day_pct) OVER (PARTITION BY d.yahoo_symbol ORDER BY d.trade_date) AS fwd1
        FROM dn_streaked d
        JOIN roster ro ON ro.yahoo_symbol = d.yahoo_symbol
        WHERE d.prev_close IS NOT NULL
    ),
    -- the market's own move each session: the equal-weighted average of every member. Subtracting
    -- it is what separates "this stock rose" from "everything rose" — the difference between
    -- picking a stock and buying the index.
    mkt AS (
        SELECT trade_date,
               avg(day_pct) AS mkt_today,
               avg(fwd1) AS mkt_fwd1,
               100.0 * avg(CASE WHEN day_pct > 0 THEN 1 ELSE 0 END) AS breadth_pct
        FROM reversal
        GROUP BY trade_date
    ),
    rev AS (
        SELECT r.*, m.mkt_today, m.mkt_fwd1, m.breadth_pct,
               r.fwd1 - m.mkt_fwd1 AS excess
        FROM reversal r JOIN mkt m ON m.trade_date = r.trade_date
    ),
    -- the rule, applied on every session: among stocks down 3+ sessions, the five that have
    -- fallen furthest over five days.
    rev_ranked AS (
        SELECT *, row_number() OVER (PARTITION BY trade_date ORDER BY r5) AS bounce_rank
        FROM rev WHERE dn_streak >= 3 AND r5 IS NOT NULL
    ),
    -- ---- the pick score: four signs that a run still had force at the close -------------
    -- Computed for every stock on every session (not just the latest), so the same rule can be
    -- replayed on past days and its hit rate measured honestly. Each sign is 0-100:
    --   accel  : the last day's move, 3% or more scores 100 — a run that is speeding up
    --   tide   : share of the stock's sector that rose that day — the tide is with it
    --   steady : share of the streak's gain NOT made in its single biggest day — a climb, not a jump
    --   trend  : the close as a % of the stock's highest close so far in the window — near highs
    -- The score is a weighted sum: 30 accel + 30 tide + 20 steady + 20 trend.
    signs AS (
        SELECT s.yahoo_symbol, s.trade_date, s.close, s.day_pct, s.streak_days, s.base_close,
               ro.symbol, ro.company, ro.sector,
               100.0 * (s.close / s.base_close - 1) AS gain_pct,
               max(s.day_pct) OVER (PARTITION BY s.yahoo_symbol, s.run_id ORDER BY s.trade_date
                                    ROWS UNBOUNDED PRECEDING) AS biggest_day_pct,
               max(s.close) OVER (PARTITION BY s.yahoo_symbol ORDER BY s.trade_date
                                  ROWS UNBOUNDED PRECEDING) AS high_so_far,
               100.0 * avg(s.up) OVER (PARTITION BY ro.sector, s.trade_date) AS sector_up_pct
        FROM streaked s
        JOIN roster ro ON ro.yahoo_symbol = s.yahoo_symbol
        WHERE s.prev_close IS NOT NULL
    ),
    scored AS (
        SELECT *,
               least(100, greatest(0, 100.0 * day_pct / 3.0)) AS accel,
               sector_up_pct AS tide,
               least(100, greatest(0, CASE WHEN gain_pct > 0
                    THEN 100.0 * (1 - biggest_day_pct / gain_pct) ELSE 0 END)) AS steady,
               least(100, greatest(0, 100.0 * close / high_so_far)) AS trend
        FROM signs
        WHERE streak_days >= {MIN_STREAK}
    ),
    candidates AS (
        SELECT *,
               0.3 * accel + 0.3 * tide + 0.2 * steady + 0.2 * trend AS score,
               row_number() OVER (PARTITION BY trade_date
                                  ORDER BY 0.3 * accel + 0.3 * tide + 0.2 * steady + 0.2 * trend DESC,
                                           streak_days DESC, symbol) AS pick_rank
        FROM scored
    ),
    -- what actually happened the session after: the back-test's answer key
    next_day AS (
        SELECT yahoo_symbol, trade_date,
               lead(trade_date) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date) AS next_date,
               lead(day_pct) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date) AS next_day_pct
        FROM streaked
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

#: Today's picks: every winner scored, best first, with the reasons and the warnings spelled out
#: in words so the table explains itself. `pick_rank` 1-5 is the recommendation.
PICK_SCORES = f"""
WITH {STREAKS}
SELECT c.pick_rank, c.symbol, c.company, c.sector, c.streak_days,
       round(c.gain_pct, 2) AS streak_gain_pct,
       round(c.day_pct, 2) AS latest_day_pct,
       round(c.score, 1) AS score,
       round(0.3 * c.accel, 1) AS accel_pts,
       round(0.3 * c.tide, 1) AS tide_pts,
       round(0.2 * c.steady, 1) AS steady_pts,
       round(0.2 * c.trend, 1) AS trend_pts,
       round(c.sector_up_pct, 1) AS sector_up_pct,
       round(c.biggest_day_pct, 2) AS biggest_day_pct,
       round(100.0 * c.close / c.high_so_far, 1) AS pct_of_high,
       c.pick_rank <= 5 AS recommended,
       concat_ws('; ',
           CASE WHEN c.day_pct >= 2 THEN 'strong last day' END,
           CASE WHEN c.tide >= 75 THEN 'sector tide with it' END,
           CASE WHEN c.steady >= 60 THEN 'steady climb' END,
           CASE WHEN c.trend >= 98 THEN 'at its high' END) AS why,
       concat_ws('; ',
           CASE WHEN c.day_pct < 0.5 THEN 'fading' END,
           CASE WHEN c.tide < 35 THEN 'against its sector' END,
           CASE WHEN c.steady < 40 THEN 'one-day jump' END,
           CASE WHEN c.trend < 85 THEN 'bounce from a fall' END) AS warning
FROM candidates c
JOIN scan ON c.trade_date = scan.scan_date
ORDER BY c.pick_rank
"""

#: The back-test, one row per pick per past session: apply the same rule as of that day, keep its
#: top twenty, and record what each did the next session. The dashboard chooses how many of the
#: twenty count as "the picks" (five, ten, fifteen, twenty) and adds them up itself. Two baselines
#: ride on every row — the share of all streaking stocks that rose next day, and the share of the
#: whole index — because the question is not "did the picks rise" but "did they rise more often
#: than not picking".
PICK_BACKTEST = f"""
WITH {STREAKS},
    picks AS (
        SELECT c.trade_date, c.pick_rank, c.symbol, c.score, c.streak_days,
               n.next_date, n.next_day_pct
        FROM candidates c
        JOIN next_day n ON n.yahoo_symbol = c.yahoo_symbol AND n.trade_date = c.trade_date
        WHERE c.pick_rank <= 20 AND n.next_day_pct IS NOT NULL
    ),
    streak_base AS (
        SELECT c.trade_date,
               100.0 * count(*) FILTER (WHERE n.next_day_pct > 0) / count(*) AS streak_hit_pct
        FROM candidates c
        JOIN next_day n ON n.yahoo_symbol = c.yahoo_symbol AND n.trade_date = c.trade_date
        WHERE n.next_day_pct IS NOT NULL
        GROUP BY c.trade_date
    ),
    market_base AS (
        SELECT trade_date,
               100.0 * count(*) FILTER (WHERE next_day_pct > 0) / count(*) AS market_hit_pct
        FROM next_day
        WHERE next_day_pct IS NOT NULL
        GROUP BY trade_date
    )
SELECT p.trade_date AS pick_date, p.next_date, p.pick_rank, p.symbol, p.streak_days,
       round(p.score, 1) AS score,
       round(p.next_day_pct, 2) AS next_day_pct,
       p.next_day_pct > 0 AS rose_next_day,
       round(sb.streak_hit_pct, 1) AS streak_hit_pct,
       round(mb.market_hit_pct, 1) AS market_hit_pct
FROM picks p
JOIN streak_base sb ON sb.trade_date = p.trade_date
JOIN market_base mb ON mb.trade_date = p.trade_date
ORDER BY p.trade_date, p.pick_rank
"""

#: The back-test's baselines in one row: how often any streaking stock, and any index member,
#: rose the next session over the same days — the bar the picks have to clear.
PICK_BACKTEST_SUMMARY = f"""
WITH {STREAKS},
    streakers AS (
        SELECT c.trade_date, n.next_day_pct
        FROM candidates c
        JOIN next_day n ON n.yahoo_symbol = c.yahoo_symbol AND n.trade_date = c.trade_date
        WHERE n.next_day_pct IS NOT NULL
    ),
    market AS (
        SELECT trade_date, next_day_pct FROM next_day WHERE next_day_pct IS NOT NULL
    )
SELECT
    (SELECT count(DISTINCT trade_date) FROM streakers) AS days_tested,
    (SELECT round(100.0 * count(*) FILTER (WHERE next_day_pct > 0) / greatest(1, count(*)), 1)
     FROM streakers) AS streak_hit_pct,
    (SELECT round(avg(next_day_pct), 2) FROM streakers) AS streak_avg_next_pct,
    (SELECT round(100.0 * count(*) FILTER (WHERE next_day_pct > 0) / greatest(1, count(*)), 1)
     FROM market) AS market_hit_pct,
    (SELECT round(avg(next_day_pct), 2) FROM market) AS market_avg_next_pct,
    (SELECT symbol FROM candidates c JOIN scan ON c.trade_date = scan.scan_date
     WHERE pick_rank = 1) AS top_pick,
    (SELECT round(score, 1) FROM candidates c JOIN scan ON c.trade_date = scan.scan_date
     WHERE pick_rank = 1) AS top_score
"""

#: ---------------------------------------------------------------------------------------------
#: **The evidence block reads the WHOLE price history, not the analysis window.**
#:
#: This distinction cost a wrong answer once already. `STREAKS` deliberately trims to
#: `lookback_days` — that is right for "what is on a streak today". It is *wrong* for judging a
#: rule: sixty days is about forty sessions, and forty sessions of a five-stock rule is two
#: hundred observations whose average is noise. The first version of the pick page was judged on
#: exactly that and reported an edge that did not exist.
#:
#: So the evidence queries below build the same features over every session in the table, and the
#: sample is split in half: a rule may be chosen on the first half, and the second half is the
#: only honest report of how it does.
HISTORY = f"""
    roster AS (
        SELECT symbol, yahoo_symbol, company, sector, sub_industry
        FROM {CATALOG}.markets.sp500_constituents
    ),
    scan AS (
        SELECT max(trade_date) AS scan_date FROM {CATALOG}.markets.daily_prices
    ),
    all_prices AS (
        SELECT p.symbol AS yahoo_symbol, p.trade_date, p.adj_close AS close
        FROM {CATALOG}.markets.daily_prices p
        WHERE p.adj_close IS NOT NULL
    ),
    all_moves AS (
        SELECT yahoo_symbol, trade_date, close,
               lag(close) OVER w AS prev_close,
               lag(close, 5) OVER w AS close_5_ago,
               max(close) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date ROWS 19 PRECEDING)
                   AS hi20
        FROM all_prices
        WINDOW w AS (PARTITION BY yahoo_symbol ORDER BY trade_date)
    ),
    all_flagged AS (
        SELECT *,
               CASE WHEN prev_close IS NOT NULL AND close > prev_close THEN 1 ELSE 0 END AS up,
               CASE WHEN prev_close IS NOT NULL AND close < prev_close THEN 1 ELSE 0 END AS down,
               CASE WHEN prev_close IS NOT NULL AND prev_close > 0
                    THEN 100.0 * (close / prev_close - 1) END AS day_pct
        FROM all_moves
    ),
    all_runs AS (
        SELECT *,
               sum(1 - up) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date
                                 ROWS UNBOUNDED PRECEDING) AS up_run_id,
               sum(1 - down) OVER (PARTITION BY yahoo_symbol ORDER BY trade_date
                                   ROWS UNBOUNDED PRECEDING) AS dn_run_id
        FROM all_flagged
    ),
    all_streaked AS (
        SELECT *,
               row_number() OVER (PARTITION BY yahoo_symbol, up_run_id ORDER BY trade_date) - 1
                   AS up_streak,
               row_number() OVER (PARTITION BY yahoo_symbol, dn_run_id ORDER BY trade_date) - 1
                   AS dn_streak,
               first_value(close) OVER (PARTITION BY yahoo_symbol, up_run_id ORDER BY trade_date)
                   AS up_base_close
        FROM all_runs
    ),
    hist AS (
        SELECT a.yahoo_symbol, a.trade_date, a.close, a.day_pct, a.up_streak, a.dn_streak,
               ro.symbol, ro.company, ro.sector,
               100.0 * (a.close / nullif(a.close_5_ago, 0) - 1) AS r5,
               100.0 * a.close / nullif(a.hi20, 0) AS pct_of_hi20,
               100.0 * (a.close / nullif(a.up_base_close, 0) - 1) AS up_gain_pct,
               lead(a.day_pct) OVER (PARTITION BY a.yahoo_symbol ORDER BY a.trade_date) AS fwd1
        FROM all_streaked a
        JOIN roster ro ON ro.yahoo_symbol = a.yahoo_symbol
        WHERE a.prev_close IS NOT NULL
    ),
    hist_mkt AS (
        -- the market's own move: the equal-weighted average of every member that session
        SELECT trade_date, avg(day_pct) AS mkt_today, avg(fwd1) AS mkt_fwd1,
               100.0 * avg(CASE WHEN day_pct > 0 THEN 1 ELSE 0 END) AS breadth_pct
        FROM hist GROUP BY trade_date
    ),
    h AS (
        SELECT x.*, m.mkt_today, m.mkt_fwd1, m.breadth_pct, x.fwd1 - m.mkt_fwd1 AS excess
        FROM hist x JOIN hist_mkt m ON m.trade_date = x.trade_date
    ),
    halves AS (
        SELECT min(trade_date) + ((max(trade_date) - min(trade_date)) / 2)::INTEGER AS mid
        FROM h WHERE fwd1 IS NOT NULL
    ),
    h_bounce AS (
        SELECT *, row_number() OVER (PARTITION BY trade_date ORDER BY r5) AS bounce_rank
        FROM h WHERE dn_streak >= 3 AND r5 IS NOT NULL
    ),
    h_momentum AS (
        SELECT *, row_number() OVER (PARTITION BY trade_date ORDER BY up_gain_pct DESC) AS mom_rank
        FROM h WHERE up_streak >= 3
    )
"""

#: **The evidence page's core table.** For every streak length in both directions, what happened
#: the next session over the whole history — hit rate, average return, and average return *minus
#: the market's move that day*. The excess column is the one that matters: a rule with a good
#: return and no excess is a bet on the market, not a stock pick.
STREAK_EVIDENCE = f"""
WITH {HISTORY}
SELECT 'Rose N days running' AS direction, up_streak AS streak_length,
       count(*) AS observations,
       round(100.0 * avg(CASE WHEN fwd1 > 0 THEN 1 ELSE 0 END), 1) AS rose_next_pct,
       round(avg(fwd1), 3) AS avg_next_pct,
       round(avg(excess), 3) AS avg_excess_pct
FROM h WHERE up_streak BETWEEN 1 AND 7 AND fwd1 IS NOT NULL
GROUP BY up_streak
UNION ALL
SELECT 'Fell N days running', dn_streak, count(*),
       round(100.0 * avg(CASE WHEN fwd1 > 0 THEN 1 ELSE 0 END), 1),
       round(avg(fwd1), 3), round(avg(excess), 3)
FROM h WHERE dn_streak BETWEEN 1 AND 7 AND fwd1 IS NOT NULL
GROUP BY dn_streak
ORDER BY direction, streak_length
"""

#: The two rules traded side by side, split into the first half of the history and the second.
#: **The split is the whole point.** A rule chosen by looking at data will always look good on
#: that data; the only honest question is whether it still works on the half it never saw.
RULE_COMPARISON = f"""
WITH {HISTORY},
    labelled AS (
        SELECT 'Buy the fallers (down 3+, biggest 5-day fall)' AS rule, trade_date, fwd1, excess
        FROM h_bounce WHERE bounce_rank <= 5 AND fwd1 IS NOT NULL
        UNION ALL
        SELECT 'Buy the risers (up 3+, biggest streak gain)', trade_date, fwd1, excess
        FROM h_momentum WHERE mom_rank <= 5 AND fwd1 IS NOT NULL
        UNION ALL
        SELECT 'Buy any S&P 500 stock (the baseline)', trade_date, fwd1, 0.0
        FROM h WHERE fwd1 IS NOT NULL
    )
SELECT rule,
       CASE WHEN trade_date < (SELECT mid FROM halves) THEN '1 first half'
            ELSE '2 second half (held out)' END AS period,
       count(*) AS picks,
       round(100.0 * avg(CASE WHEN fwd1 > 0 THEN 1 ELSE 0 END), 1) AS rose_next_pct,
       round(avg(fwd1), 3) AS avg_next_pct,
       round(avg(excess), 3) AS avg_excess_pct
FROM labelled
GROUP BY rule, period
ORDER BY rule, period
"""

#: What the market itself did the session after a fall of a given size. The single most consistent
#: effect in the data, and it is about the market, not about any stock.
MARKET_BOUNCE = f"""
WITH {HISTORY},
    m AS (SELECT DISTINCT trade_date, mkt_today, mkt_fwd1 FROM h WHERE mkt_fwd1 IS NOT NULL)
SELECT CASE WHEN mkt_today <= -1.0 THEN 'Market fell more than 1%'
            WHEN mkt_today <= -0.3 THEN 'Market fell 0.3% to 1%'
            WHEN mkt_today <   0.3 THEN 'Market roughly flat'
            ELSE 'Market rose more than 0.3%' END AS market_day,
       CASE WHEN mkt_today <= -1.0 THEN 1 WHEN mkt_today <= -0.3 THEN 2
            WHEN mkt_today < 0.3 THEN 3 ELSE 4 END AS sort_order,
       count(*) AS sessions,
       round(avg(mkt_fwd1), 3) AS avg_next_pct,
       round(100.0 * avg(CASE WHEN mkt_fwd1 > 0 THEN 1 ELSE 0 END), 1) AS next_up_pct
FROM m GROUP BY market_day, sort_order ORDER BY sort_order
"""

#: Today's bounce candidates: the stocks the validated rule points at, as of the latest close.
BOUNCE_PICKS = f"""
WITH {HISTORY}
SELECT r.bounce_rank, r.symbol, r.company, r.sector,
       r.dn_streak AS down_days,
       round(r.day_pct, 2) AS latest_day_pct,
       round(r.r5, 2) AS five_day_pct,
       round(r.pct_of_hi20, 1) AS pct_of_20d_high,
       round(r.close, 2) AS latest_close,
       round(r.mkt_today, 2) AS market_today_pct,
       round(r.breadth_pct, 1) AS breadth_pct
FROM h_bounce r
JOIN scan ON r.trade_date = scan.scan_date
WHERE r.bounce_rank <= 15
ORDER BY r.bounce_rank
"""

#: The one row the evidence page's tiles read: the honest edge, and today's market setting.
BOUNCE_SUMMARY = f"""
WITH {HISTORY},
    bounce AS (SELECT trade_date, fwd1, excess FROM h_bounce
               WHERE bounce_rank <= 5 AND fwd1 IS NOT NULL),
    per_day AS (SELECT trade_date, avg(excess) AS day_excess FROM bounce GROUP BY trade_date)
SELECT
    (SELECT count(DISTINCT trade_date) FROM h WHERE fwd1 IS NOT NULL) AS sessions_tested,
    (SELECT round(avg(fwd1), 3) FROM bounce) AS bounce_avg_next_pct,
    (SELECT round(avg(excess), 3) FROM bounce) AS bounce_avg_excess_pct,
    (SELECT round(avg(excess), 3) FROM bounce WHERE trade_date >= (SELECT mid FROM halves))
        AS bounce_excess_held_out,
    (SELECT round(avg(day_excess) / nullif(stddev_samp(day_excess) / sqrt(count(*)), 0), 2)
     FROM per_day) AS t_statistic,
    (SELECT round(avg(mkt_today), 2) FROM h JOIN scan ON h.trade_date = scan.scan_date)
        AS market_today_pct,
    (SELECT round(avg(breadth_pct), 1) FROM h JOIN scan ON h.trade_date = scan.scan_date)
        AS breadth_today_pct,
    (SELECT symbol FROM h_bounce JOIN scan ON h_bounce.trade_date = scan.scan_date
     WHERE bounce_rank = 1) AS top_bounce_symbol,
    (SELECT count(*) FROM h_bounce JOIN scan ON h_bounce.trade_date = scan.scan_date)
        AS candidates_today,
    (SELECT round(avg(mkt_fwd1), 3) FROM h JOIN halves ON true
     WHERE mkt_today <= -0.3 AND mkt_today > -1.0 AND mkt_fwd1 IS NOT NULL) AS after_mild_fall_pct
"""

OUTPUTS = (
    ("scan_overview", SCAN_OVERVIEW, "the headline numbers"),
    ("active_streaks", ACTIVE_STREAKS, "the leaderboard"),
    ("streak_ladder", STREAK_LADDER, "winners by streak length"),
    ("sector_streaks", SECTOR_STREAKS, "where the streaks cluster"),
    ("price_history", PRICE_HISTORY, "the winners' recent prices"),
    ("streak_paths", STREAK_PATHS, "the streaks side by side"),
    ("daily_breadth", DAILY_BREADTH, "the market backdrop"),
    ("pick_scores", PICK_SCORES, "today's picks, scored"),
    ("pick_backtest", PICK_BACKTEST, "the pick rule replayed on past days"),
    ("pick_backtest_summary", PICK_BACKTEST_SUMMARY, "the back-test's baselines"),
    ("streak_evidence", STREAK_EVIDENCE, "what each streak length did next, both directions"),
    ("rule_comparison", RULE_COMPARISON, "the two rules against the baseline, split in half"),
    ("market_bounce", MARKET_BOUNCE, "what the market did after a fall"),
    ("bounce_picks", BOUNCE_PICKS, "today's bounce candidates"),
    ("bounce_summary", BOUNCE_SUMMARY, "the honest edge, in one row"),
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
