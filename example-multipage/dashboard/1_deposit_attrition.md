---
title: Deposit Attrition
sidebar_position: 1
---

# Deposit Attrition

```sql summary
SELECT * FROM attrition_summary
```

```sql members
SELECT * FROM attrition_members
```

```sql segments
SELECT * FROM attrition_segments
```

```sql branches
SELECT * FROM attrition_branches
```

```sql deposits
SELECT * FROM deposit_trend ORDER BY snapshot_date
```

Deposits leave quietly. A member does not close an account — they move the balance somewhere else
over a few months and the relationship is gone before anyone calls.

{% notes label="How this is measured" %}
Each member's total deposit balance at the start of the window against the end, as a percentage
fall. Flagged when that fall passes the threshold **and** they started above the minimum balance —
a member who kept $40 and now keeps $8 has lost 80% and nothing worth acting on.
{% /notes %}

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **Attrition** | The slow version of leaving: balances move elsewhere over months and the relationship lapses without an account ever closing. |
| **At risk** | A member whose deposit balance fell by at least the threshold over the window, from a starting balance above the floor. |
| **Window** | The two snapshots being compared — the start and end of the period this chapter measures. |
| **Floor** | The minimum starting balance for a member to be considered. Percentage falls on tiny balances are noise, not risk. |
{% /glossary %}

{% big_value data="$summary" value="at_risk_dollars" title="Balance Gone" fmt="usd0" info="Already-departed balance across flagged members. This is what funds a retention programme." /%}
{% big_value data="$summary" value="at_risk_count" title="Members Flagged" fmt="num0" info="Compare against the call capacity you actually have — a longer list is a prioritisation problem, which is why the table is ranked by money." /%}
{% big_value data="$summary" value="at_risk_pct_of_members" title="Share Of Depositors" fmt="num1" suffix="%" info="Watch this quarter on quarter. A rising share is a franchise problem; a steady one is ordinary churn." /%}
{% big_value data="$summary" value="avg_pct_decline" title="Avg Fall" fmt="num1" suffix="%" info="How far the flagged members have fallen on average. Near the threshold means the rule is catching the edge; well above means these are real departures." /%}

## The call list

{% notes %}
Ranked by **money already gone**, not by percentage: a 90% fall on $2,000 matters less than a 45%
fall on $400,000, and a retention team has finite hours. Read Start against Now first.
{% /notes %}

{% data_table data="$members" rows=15 rowShading=true title="Members With Falling Deposit Balances" %}
{% column id="full_name" title="Member" /%}
{% column id="segment" title="Segment" /%}
{% column id="home_branch_name" title="Home Branch" /%}
{% column id="start_balance" title="Start" fmt="usd0" /%}
{% column id="end_balance" title="Now" fmt="usd0" /%}
{% column id="dollar_loss" title="Gone" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="pct_loss" title="Fall %" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}

## The book behind it

{% notes %}
Institution-wide deposits over the window. The line falling while the member count holds steady
means existing members are drawing down — which is the attrition this chapter is about.
{% /notes %}

{% line_chart data="$deposits" x="snapshot_date" y=["total_deposits"] title="Total Deposit Balances" yFmt="usd0" yAxisTitle="deposits" colors=["#0d9488"] chartAreaHeight=280 info="The book the flagged members are leaving. If this line is flat while the call list grows, new money is masking the departures — the leak is real even though the total looks fine." /%}

## Where it is concentrated

{% row %}
{% bar_chart data="$segments" x="segment" y=["at_risk_dollars"] title="Balance At Risk by Segment" yFmt="usd0" yAxisTitle="at risk" colors=["#dc2626"] chartAreaHeight=260 info="Where the departing dollars sit. A tall bar with few members (see the chart beside this one) is a handful of large relationships — call them individually. A tall bar with many members is a pricing or product problem." /%}
{% bar_chart data="$segments" x="segment" y=["at_risk_count"] title="Members Flagged by Segment" yFmt="num0" yAxisTitle="members" colors=["#f59e0b"] chartAreaHeight=260 info="The same segments counted in people rather than dollars. Read against the dollar chart: the segment that ranks high on one and low on the other tells you whether this is a whale problem or a herd problem." /%}
{% /row %}

## By segment

{% notes %}
A segment with few members but large dollars is a relationship-management problem; the reverse is
a product or pricing problem. They need different responses.
{% /notes %}

{% data_table data="$segments" rowShading=true title="At-Risk Balance by Segment" %}
{% column id="segment" title="Segment" /%}
{% column id="at_risk_count" title="Members" fmt="num0" /%}
{% column id="at_risk_dollars" title="Balance At Risk" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="avg_decline_pct" title="Avg Fall %" fmt="num1" /%}
{% /data_table %}

## By branch

{% notes %}
One branch carrying a disproportionate share is usually a local cause — a competitor opening
nearby, a manager who left and took relationships with them. That is a different intervention from
a book-wide one, and a different conversation.
{% /notes %}

{% bar_chart data="$branches" x="branch" y=["at_risk_dollars"] title="Balance At Risk by Home Branch" yFmt="usd0" yAxisTitle="at risk" colors=["#dc2626"] chartAreaHeight=280 info="Departing balances by home branch. One branch far above the rest is usually a local cause — a competitor opening, a departed manager. Ask what changed near the tallest bar in the last two quarters." /%}
