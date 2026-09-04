---
title: Deposit Attrition & Retention Risk
---

# Deposit Attrition & Retention Risk

```sql summary
SELECT * FROM summary
```

```sql trend
SELECT * FROM monthly_trend ORDER BY snapshot_date
```

```sql at_risk
SELECT * FROM at_risk_members
```

```sql seg
SELECT * FROM segment_risk
```

```sql branch
SELECT * FROM branch_risk
```

Deposits leave quietly. A member does not close an account — they move the balance somewhere else
over a few months and the relationship is gone before anyone calls. This page finds them while
there is still something to call about.

{% notes label="About this page" %}
For each member, total **deposit** balance at the first snapshot of the window against the last,
expressed as a percentage fall. A member is flagged when that fall is at or over the threshold
**and** they started above the minimum balance.

The floor is not decoration. Percentage falls on tiny balances are noise: a member who kept $40
and now keeps $8 has lost 80% and nothing worth acting on. Without it, the list is dominated by
them and the real departures are buried.

Both the threshold and the floor are launch parameters, because the right values differ per
institution — and that is an argument better had with a form than with a code change.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Deposit balance** | Chequing, savings and money-market balances. Loans and credit lines are a different asset class and are excluded. |
| **Snapshot** | A month-end record of every account's balance. The analysis compares two of them. |
| **At risk** | A member whose deposit balance fell by at least the threshold over the window, from a starting balance above the floor. |
| **Dollar loss** | Balance at the start of the window minus balance at the end. Money that has already left, not a projection. |
| **Attrition** | The slow version of closing an account: the balance goes elsewhere and the relationship lapses without anyone formally leaving. |
{% /glossary %}

{% big_value data="$summary" value="at_risk_dollars" title="Balance At Risk" fmt="usd0" info="Total already-departed balance across flagged members over the window. This is the number that funds a retention programme, and it is money that has left rather than money that might." /%}
{% big_value data="$summary" value="at_risk_count" title="Members Flagged" fmt="num0" info="How many members crossed the decline threshold from a starting balance above the floor. Compare against the call capacity you actually have — a list longer than that is a prioritisation problem, which is why the table is ranked by money." /%}
{% big_value data="$summary" value="at_risk_pct_of_members" title="Share Of Depositors" fmt="num1" suffix="%" info="Flagged members as a share of everyone with a deposit balance above the floor. This is the number to watch quarter on quarter — a rising share is a franchise problem, a steady one is ordinary churn." /%}
{% big_value data="$summary" value="deposits_today" title="Deposits Today" fmt="usd0" info="Total deposit balances at the most recent snapshot. Context for the balance at risk: the same dollar figure means very different things against a $50M book and a $500M one." /%}

## Deposits over the window

{% notes %}
Institution-wide totals by snapshot. The line falling while the member count holds steady means
existing members are drawing down — which is the attrition this page is about. Both falling
together is a different problem, and one that shows up in account closures rather than here.
{% /notes %}

{% line_chart data="$trend" x="snapshot_date" y=["total_deposits"] title="Total Deposit Balances by Month" yFmt="usd0" yAxisTitle="total deposits" colors=["#0d9488"] chartAreaHeight=300 info="The whole book, month by month. A gentle drift down while member counts hold is attrition — the thing this page hunts. A cliff is an event: check what left in that month before reading anything else here." /%}

## The retention call list

{% notes %}
Flagged members ranked by **money already gone**, not by percentage. A 90% fall on $2,000 matters
less to the balance sheet than a 45% fall on $400,000, and a retention team has finite hours — so
the ordering is the prioritisation.

Read **Start** against **Now** first, then the percentage. The two together tell you whether this
is a member consolidating elsewhere or one winding down a single account.
{% /notes %}

{% data_table data="$at_risk" rows=15 rowShading=true title="Members With Falling Deposit Balances" %}
{% column id="full_name" title="Member" /%}
{% column id="segment" title="Segment" /%}
{% column id="home_branch_name" title="Home Branch" /%}
{% column id="start_balance" title="Start" fmt="usd0" /%}
{% column id="end_balance" title="Now" fmt="usd0" /%}
{% column id="dollar_loss" title="Gone" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="pct_loss" title="Fall %" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}

## Which segments are leaving

{% notes %}
Where the departing money sits. A segment with a small count but large dollars is a
relationship-management problem — a handful of large balances — and a segment with the reverse is
a product or pricing problem. The two need different responses, which is why both columns are
here.
{% /notes %}

{% data_table data="$seg" rowShading=true title="At-Risk Balance by Segment" %}
{% column id="segment" title="Segment" /%}
{% column id="at_risk_count" title="Members" fmt="num0" /%}
{% column id="at_risk_dollars" title="Balance At Risk" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="avg_decline_pct" title="Avg Fall %" fmt="num1" /%}
{% /data_table %}

## Where the losses cluster

{% notes %}
By home branch. One branch carrying a disproportionate share is usually a local cause — a
competitor opening nearby, a manager who left and took relationships with them — and that is a
different intervention from a book-wide one. Check the top row against what changed near it in
the last two quarters.
{% /notes %}

{% data_table data="$branch" rows=12 rowShading=true title="At-Risk Balance by Home Branch" %}
{% column id="branch" title="Branch" /%}
{% column id="state" title="State" /%}
{% column id="at_risk_count" title="Members" fmt="num0" /%}
{% column id="at_risk_dollars" title="Balance At Risk" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}
