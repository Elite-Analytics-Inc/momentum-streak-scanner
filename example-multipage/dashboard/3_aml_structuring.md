---
title: AML Structuring
sidebar_position: 3
---

# AML — Structuring Watch

```sql summary
SELECT * FROM aml_summary
```

```sql alerts
SELECT * FROM aml_alerts
```

```sql by_branch
SELECT branch_id, sum(deposits) AS deposits, sum(dollars) AS dollars
FROM aml_cluster GROUP BY branch_id ORDER BY dollars DESC
```

```sql by_hour
SELECT hour, sum(deposits) AS deposits
FROM aml_cluster GROUP BY hour ORDER BY hour
```

Cash is reportable at or above the threshold, so the pattern worth finding is not a large deposit —
it is several deposits arranged to stay just underneath one.

{% notes label="How to read this responsibly" %}
**These are leads, not findings.** A member paid in cash who banks their takings twice a week lands
in this queue, and that is correct behaviour for a detection rule.

The cost of a rule tuned too tight is a missed filing; too loose is a queue nobody works. That
balance is a decision for the BSA officer, not a default in a dashboard. Nothing here decides
anything.
{% /notes %}

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **Structuring** | Splitting cash into deposits just under the reporting line so no single one triggers a report. Illegal regardless of where the money came from. |
| **CTR** | Currency Transaction Report — the filing a cash transaction over $10,000 requires. The line structuring ducks under. |
| **Flagged window** | A short run of days in which one member's under-the-line cash deposits together crossed the line. |
| **Alert** | A member-and-window pair this rule surfaced. An alert is a reason to look, never an accusation. |
{% /glossary %}

{% big_value data="$summary" value="alert_count" title="Alerts" fmt="num0" info="Members whose qualifying deposits met the count threshold inside one window. Compare against the hours available to work it." /%}
{% big_value data="$summary" value="total_flagged_dollars" title="In Flagged Windows" fmt="usd0" info="Value of deposits inside the alerting windows. Not an allegation about the money — the size of what a reviewer is being asked to look at." /%}
{% big_value data="$summary" value="near_threshold_deposits" title="Deposits In Band" fmt="num0" info="Every qualifying deposit, alerted or not. A large band with few alerts means the rule is selective." /%}
{% big_value data="$summary" value="avg_deposits_per_alert" title="Avg / Alert" fmt="num2" info="Sitting at the minimum count suggests the threshold is doing the deciding; well above suggests the pattern is real." /%}

## The queue

{% data_table data="$alerts" rows=15 rowShading=true title="Members Alerted" %}
{% column id="full_name" title="Member" /%}
{% column id="segment" title="Segment" /%}
{% column id="home_branch_name" title="Home Branch" /%}
{% column id="first_alert_ts" title="First Deposit" /%}
{% column id="deposits_in_window" title="Deposits" fmt="num0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="dollars_in_window" title="In Window" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}

## When and where

{% notes %}
Across every alerting cluster. Ordinary cash banking follows business hours and the working week;
deposits concentrated at opening, at closing, or over a weekend are worth a second look — not
because the hour proves anything, but because a deliberate pattern tends to have a shape.

A branch carrying a disproportionate share is either a genuine cluster or a local process
difference — a teller applying the cash-handling procedure differently. Both want someone's
attention, and they want different people.
{% /notes %}

{% row %}
{% bar_chart data="$by_hour" x="hour" y=["deposits"] title="Alert Deposits by Hour of Day" yFmt="num0" yAxisTitle="deposits" xAxisTitle="hour" colors=["#0ea5e9"] chartAreaHeight=260 info="When the flagged deposits happen. Ordinary cash business clusters in business hours; a spike at an odd hour, or a flat spread that ignores opening times, is the pattern worth showing an investigator." /%}
{% bar_chart data="$by_branch" x="branch_id" y=["dollars"] title="Structuring Value by Branch" yFmt="usd0" yAxisTitle="in flagged windows" colors=["#dc2626"] chartAreaHeight=260 info="Flagged-window dollars by branch. Concentration in one branch can mean one member using it repeatedly — or a teller pattern. Either way it narrows where the file review starts." /%}
{% /row %}
