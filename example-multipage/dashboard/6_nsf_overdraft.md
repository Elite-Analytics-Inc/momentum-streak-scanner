---
title: NSF / Overdraft
sidebar_position: 6
---

# NSF / Overdraft

```sql summary
SELECT * FROM fees_summary
```

```sql segments
SELECT * FROM fees_by_segment
```

```sql pareto
SELECT * FROM fees_pareto
```

```sql by_type
SELECT
    CASE fee_type
        WHEN 'nsf' THEN 'NSF'
        WHEN 'overdraft' THEN 'Overdraft'
        WHEN 'maintenance' THEN 'Maintenance'
        WHEN 'atm_foreign' THEN 'ATM (foreign)'
        WHEN 'wire' THEN 'Wire'
        WHEN 'paper_statement' THEN 'Paper statement'
        ELSE fee_type
    END AS fee_type,
    fee_count, net_income
FROM fees_by_type ORDER BY net_income DESC
```

```sql monthly
SELECT * FROM fees_monthly ORDER BY month_start
```

Overdraft economics have been under regulatory scrutiny for two years, and the questions are
always the same three: how much of the income is this, how concentrated is it, and is it applied
evenly.

{% notes label="How this is measured" %}
**Penalty fees** means NSF and overdraft only. Amounts are **net of waivers** — a waived fee was
charged and then forgiven, so counting it would overstate what was collected. The waive rate sits
beside the income because income that only exists because waivers are rare is income with a policy
risk attached.
{% /notes %}

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **NSF** | Non-sufficient funds: a payment bounced because the account could not cover it, and a fee was charged. |
| **Overdraft** | The bank covered the shortfall and charged for doing so. Same shortage, different outcome for the member. |
| **Waive** | A charged fee forgiven, usually at a banker's discretion. The waive rate is where fairness shows. |
| **Concentration** | How much of the income comes from how few members. Penalty income is usually far more concentrated than people expect. |
| **CFPB** | Consumer Financial Protection Bureau — the US regulator auditing consumer-facing fee practices, and pressing on overdraft fees specifically since 2022. |
| **CRA** | Community Reinvestment Act — scores banks on how well they serve low- and moderate-income areas. A repeat-offender intervention programme is a CRA-positive story. |
{% /glossary %}

{% big_value data="$summary" value="nsf_overdraft_income" title="Penalty Income" fmt="usd0" info="Net NSF and overdraft income. The number under regulatory pressure — compare it against the cost of the programme that would replace it." /%}
{% big_value data="$summary" value="gross_fee_income" title="All Fee Income" fmt="usd0" info="Every fee type, net of waivers. Penalty fees as a share of this is how dependent the fee line is on overdrafts." /%}
{% big_value data="$summary" value="waive_rate_pct" title="Waive Rate" fmt="num1" suffix="%" info="Share of fee events waived. A rate that varies sharply by segment is a fair-lending question — the table below is where to check." /%}
{% big_value data="$summary" value="repeat_offender_count" title="Repeat Payers" fmt="num0" info="Members at or above the threshold number of penalty fees. A financial-wellness intake list, and the population a regulator asks about first." /%}

## Where the fee income comes from

{% notes %}
Penalty fees against everything else, and the same split month by month. If NSF and overdraft
dominate, the fee line is exposed to a single policy change — which is the point of putting them
beside the rest rather than reporting them alone. Watch the trend for a **step** rather than a
slope: penalty income moves when a threshold changes, not gradually.
{% /notes %}

{% row %}
{% bar_chart data="$by_type" x="fee_type" y=["net_income"] title="Net Fee Income by Type" yFmt="usd0" yAxisTitle="net income" colors=["#0d9488"] chartAreaHeight=260 info="What each fee type nets after waivers. The bars this chapter cares about are NSF and overdraft — penalty income, which regulators and reputations price differently from service income." /%}
{% area_chart data="$monthly" x="month_start" y=["NSF","Overdraft","Other fees"] stacked=true title="Fee Income by Month" yFmt="usd0" yAxisTitle="net income" colors=["#dc2626","#f59e0b","#94a3b8"] chartAreaHeight=260 info="Penalty income over time, stacked by type. Seasonality is normal; a steady climb is not — it means more members bouncing more often, which is a hardship signal wearing a revenue costume." /%}
{% /row %}

## How concentrated is it

{% notes %}
Members ranked by penalty income against the cumulative share they account for. Find where the
curve crosses 50% — that is the share of members paying half the penalty income.

A steep early curve means the income depends on a small group paying repeatedly rather than on
occasional accidents across the book. That is the finding a regulator is looking for.
{% /notes %}

{% line_chart data="$pareto" x="member_pct" y=["cumulative_income_pct"] title="Cumulative Share of Penalty Income" yFmt="num0" yMax=100 yAxisTitle="% of income" xAxisTitle="% of members, ranked by fees paid" colors=["#dc2626"] chartAreaHeight=300 info="The concentration curve: members ranked by fees paid, income accumulated left to right. The steeper the start, the more this revenue depends on a small group being repeatedly short — read the elbow as the size of that group." /%}

## Who pays it

{% row %}
{% bar_chart data="$segments" x="segment" y=["nsf_income"] title="Penalty Income by Segment" yFmt="usd0" yAxisTitle="net income" colors=["#dc2626"] chartAreaHeight=260 info="Which segments the penalty income comes from. If it is the segments least able to absorb it, the revenue is borrowing against the franchise." /%}
{% bar_chart data="$segments" x="segment" y=["waive_rate"] title="Waive Rate by Segment" yFmt="num1" yAxisTitle="% waived" colors=["#16a34a"] chartAreaHeight=260 info="How often each segment's fees get waived. Uneven bars mean discretion is being applied unevenly — the fairness question sits in this chart, not the income ones." /%}
{% /row %}

## Is it applied evenly

{% notes %}
Compare each segment's share of the income against its waive rate. A segment paying a large share
while receiving fewer waivers is the disparity to explain — better found here than in an
examination.
{% /notes %}

{% data_table data="$segments" rowShading=true title="Penalty Fees by Segment" %}
{% column id="segment" title="Segment" /%}
{% column id="members_paying" title="Members" fmt="num0" /%}
{% column id="nsf_events" title="Fee Events" fmt="num0" /%}
{% column id="nsf_income" title="Net Income" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="waive_rate" title="Waive %" fmt="num1" contentType="colorscale" scaleColor=["#fee2e2", "#16a34a"] /%}
{% /data_table %}
