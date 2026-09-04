# deposit-attrition — specification

*This file is the source of truth for the analysis. When anything changes — an input, an output
column, the dashboard's shape — this file changes first, and everything else follows from it.
`README.md` is a plain summary derived from this spec; it is regenerated when the spec changes and
never edited directly.*

## The question

Deposits leave quietly. A member does not close an account — they move the balance somewhere else
over a few months, and the relationship is gone before anyone calls. This analysis finds those
members while there is still something to call about: who is draining, how much money has already
left, and whether the losses cluster in a segment or a branch.

## How it decides

For each member: total deposit balance at the first snapshot in the lookback window, against the
last. That difference, as a percentage fall, is the measurement — and a member is **at risk** when:

- the fall is at or above `decline_threshold_pct`, **and**
- their starting balance was at least `min_starting_balance`.

Decisions taken, and why:

- **The floor is not decoration.** Percentage falls on tiny balances are noise — a member who kept
  $40 and now keeps $8 has lost 80% and nothing worth acting on. Without the floor, the at-risk
  list is dominated by them and the real departures are buried.
- **The window anchors on the newest snapshot in the data, not on today's date.** A dataset ages;
  an analysis anchored on `now()` quietly returns nothing a year later.
- **The call list ranks by dollars gone, not by percentage.** A 90% fall on $2,000 matters less to
  the balance sheet than a 45% fall on $400,000, and a retention team has finite hours — the
  ordering is the prioritisation.
- **Only deposits count.** Chequing, savings and money-market balances. Loans and credit lines are
  a different asset class and are excluded.

## Inputs

| Dataset | Each row is | What it provides |
| --- | --- | --- |
| `banking.balance_snapshots` | one account's balance on one month-end | the window's two endpoints, per member |
| `banking.members` | one member | segment, home branch and name, for the call list and roll-ups |

## Parameters (what varies per run)

| Parameter | What it means | Default | Bounds |
| --- | --- | --- | --- |
| `lookback_months` | how far back the window reaches | 6 | 2–24 |
| `decline_threshold_pct` | the percentage fall that flags a member | 40 | 5–95 |
| `min_starting_balance` | ignore members who started below this | 1000 | ≥ 0 |

## The dashboard

One page. At the top, four headline numbers: balance at risk (the money already gone — the number
that funds a retention programme), members flagged, their share of all depositors, and total
deposits today for context. Then, in reading order:

1. **Deposits over the window** — the institution-wide line by month; the backdrop that says
   whether drain is concentrated or book-wide.
2. **The retention call list** — flagged members ranked by dollars gone, with start/now balances
   and the fall.
3. **Which segments are leaving** — count and dollars per segment; small-count-large-dollars is a
   relationship problem, the reverse is a product or pricing problem.
4. **Where the losses cluster** — the same by home branch; one branch carrying a large share is
   usually a local cause.

## Outputs (the results the dashboard reads)

| Output | Grain | Columns |
| --- | --- | --- |
| `summary` | one row | total_members_with_deposits, at_risk_count, at_risk_dollars, deposits_today, at_risk_pct_of_members, avg_pct_decline, lookback_months, decline_threshold_pct |
| `monthly_trend` | one row per snapshot date | snapshot_date, total_deposits, members_with_deposits |
| `at_risk_members` | one row per flagged member (top 100 by dollars) | full_name, member_id, segment, home_branch_name, home_state, start_balance, end_balance, dollar_loss, pct_loss |
| `segment_risk` | one row per segment | segment, at_risk_count, at_risk_dollars, avg_decline_pct |
| `branch_risk` | one row per branch | branch, state, at_risk_count, at_risk_dollars |

## Dependencies

The platform SDK (`tarn`) only. Every output is a single SQL query run on the governed connection;
no other libraries are needed.
