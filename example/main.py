"""deposit-attrition — members whose deposits are draining, ranked by the money already gone.

**The measurement, stated plainly, because it is the whole analysis.** For each member: total
deposit balance at the first snapshot in the window against the last, expressed as a percentage
fall. A member is *at risk* when that fall exceeds the threshold and they started with more than
the floor. Both are parameters, because the right values differ per institution and arguing about
them is a productive conversation to have with a form rather than with a code change.

**The shape is the Job Definition contract.** `main.py` runs top to bottom — no framework, no
hidden entry points. `parameters.json` beside it declares what varies per run and renders the
launch form. The `dashboard/` directory holds the pages that show the results, uploaded as-is at
the end of the run.

**Every output is one governed query.** The shared derivation is a block of CTEs repeated in each
output's SQL rather than a table materialized locally, so each artifact is produced by a single
statement on the governed connection — the row filters and column masks of whoever launched the
run are in the bytes themselves, not in a claim about them. A principal granted one region's
members gets that region's at-risk list from exactly this SQL.
"""

import os

import tarn

#: The deployment names its own workspace catalog; a job reads the name from the environment
#: rather than hardcoding it, so the same repo runs against any install.
CATALOG = os.environ.get("TARN_WORKSPACE_CATALOG", "lake")

#: Typed and constrained in `parameters.json`, which is also what renders the launch form.
LOOKBACK = int(os.environ.get("TARN_PARAM_LOOKBACK_MONTHS", "6"))
DECLINE_THRESHOLD = float(os.environ.get("TARN_PARAM_DECLINE_THRESHOLD_PCT", "40"))
MIN_STARTING_BALANCE = float(os.environ.get("TARN_PARAM_MIN_STARTING_BALANCE", "1000"))

#: The shared derivation: deposit snapshots, the window's two endpoints, and each member's
#: balance at each end.
#:
#: Anchored on the newest snapshot in the data rather than on today's date — a demo dataset ages,
#: and an analysis anchored on `now()` quietly returns nothing a year later.
#:
#: **`min_starting_balance` is not decoration.** Percentage falls on tiny balances are noise: a
#: member who kept $40 and now keeps $8 has lost 80% and nothing worth acting on. Without the
#: floor the at-risk list is dominated by them and the real departures are buried.
WINDOW = f"""
    bs AS (
        SELECT b.account_id, b.member_id, b.snapshot_date, b.balance
        FROM {CATALOG}.banking.balance_snapshots b
        WHERE b.asset_class = 'deposit'
    ),
    bounds AS (
        SELECT max(snapshot_date) AS latest,
               date_trunc('month', max(snapshot_date))
                   - INTERVAL '{LOOKBACK - 1}' MONTH AS earliest_eligible
        FROM bs
    ),
    endpoints AS (
        SELECT (SELECT min(snapshot_date) FROM bs, bounds
                WHERE bs.snapshot_date >= bounds.earliest_eligible) AS first_date,
               (SELECT latest FROM bounds) AS last_date
    ),
    start_snap AS (
        SELECT member_id, sum(balance) AS start_balance
        FROM bs, endpoints
        WHERE bs.snapshot_date = endpoints.first_date
        GROUP BY member_id
    ),
    end_snap AS (
        SELECT member_id, sum(balance) AS end_balance
        FROM bs, endpoints
        WHERE bs.snapshot_date = endpoints.last_date
        GROUP BY member_id
    ),
    member_window AS (
        SELECT s.member_id,
               s.start_balance,
               coalesce(e.end_balance, 0) AS end_balance,
               s.start_balance - coalesce(e.end_balance, 0) AS dollar_loss,
               CASE WHEN s.start_balance > 0
                    THEN 100.0 * (s.start_balance - coalesce(e.end_balance, 0)) / s.start_balance
                    ELSE 0 END AS pct_loss
        FROM start_snap s
        LEFT JOIN end_snap e ON e.member_id = s.member_id
        WHERE s.start_balance >= {MIN_STARTING_BALANCE}
    ),
    at_risk AS (
        SELECT mw.*, m.segment, m.home_branch_name, m.home_state, m.full_name
        FROM member_window mw
        JOIN {CATALOG}.banking.members m ON m.member_id = mw.member_id
        WHERE mw.pct_loss >= {DECLINE_THRESHOLD}
    )
"""

#: The headline. `at_risk_dollars` is the number that gets a retention programme funded, and it is
#: deliberately the *balance already gone*, not a projection of what might follow.
SUMMARY = f"""
WITH {WINDOW}
SELECT
    (SELECT count(DISTINCT member_id) FROM bs) AS total_members_with_deposits,
    (SELECT count(*) FROM at_risk) AS at_risk_count,
    (SELECT round(sum(dollar_loss), 2) FROM at_risk) AS at_risk_dollars,
    (SELECT round(sum(balance), 2) FROM bs, endpoints
     WHERE bs.snapshot_date = endpoints.last_date) AS deposits_today,
    (SELECT round(100.0 * count(*) / greatest(1, (SELECT count(*) FROM member_window)), 2)
     FROM at_risk) AS at_risk_pct_of_members,
    (SELECT round(avg(pct_loss), 1) FROM at_risk) AS avg_pct_decline,
    {LOOKBACK}::INTEGER AS lookback_months,
    {DECLINE_THRESHOLD}::DOUBLE AS decline_threshold_pct
"""

MONTHLY_TREND = f"""
WITH {WINDOW}
SELECT snapshot_date,
       round(sum(balance), 2) AS total_deposits,
       count(DISTINCT member_id) AS members_with_deposits
FROM bs
GROUP BY snapshot_date
ORDER BY snapshot_date
"""

#: The call list, ordered by money rather than by percentage — a 90% fall on $2,000 matters less
#: to the balance sheet than a 45% fall on $400,000, and a retention team has finite hours.
AT_RISK_MEMBERS = f"""
WITH {WINDOW}
SELECT full_name, member_id, segment, home_branch_name, home_state,
       round(start_balance, 2) AS start_balance,
       round(end_balance, 2) AS end_balance,
       round(dollar_loss, 2) AS dollar_loss,
       round(pct_loss, 1) AS pct_loss
FROM at_risk
ORDER BY dollar_loss DESC
LIMIT 100
"""

SEGMENT_RISK = f"""
WITH {WINDOW}
SELECT segment,
       count(*) AS at_risk_count,
       round(sum(dollar_loss), 2) AS at_risk_dollars,
       round(avg(pct_loss), 1) AS avg_decline_pct
FROM at_risk
GROUP BY segment
ORDER BY at_risk_dollars DESC
"""

#: Where the losses cluster geographically. A single branch carrying a large share is usually a
#: local cause — a competitor opening, a manager leaving — and that is a different intervention
#: from a segment-wide one.
BRANCH_RISK = f"""
WITH {WINDOW}
SELECT home_branch_name AS branch,
       home_state AS state,
       count(*) AS at_risk_count,
       round(sum(dollar_loss), 2) AS at_risk_dollars
FROM at_risk
GROUP BY home_branch_name, home_state
ORDER BY at_risk_dollars DESC
"""

OUTPUTS = (
    ("summary", SUMMARY, "headline attrition numbers"),
    ("monthly_trend", MONTHLY_TREND, "deposits over time"),
    ("at_risk_members", AT_RISK_MEMBERS, "the retention call list"),
    ("segment_risk", SEGMENT_RISK, "which segments are leaving"),
    ("branch_risk", BRANCH_RISK, "where the losses cluster"),
)


def main() -> None:
    tarn.stage("analyse")
    tarn.log(
        f"deposit attrition over {LOOKBACK} months; flagging a fall of "
        f"{DECLINE_THRESHOLD}% or more on a starting balance of at least {MIN_STARTING_BALANCE}"
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
        f"Members whose deposit balances fell {DECLINE_THRESHOLD}% or more over "
        f"{LOOKBACK} months, ranked by the money that actually left. The member table is the "
        "retention call list; the branch roll-up says whether this is a local cause or a "
        "book-wide one."
    )


if __name__ == "__main__":
    main()
