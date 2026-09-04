---
title: Streaks Side By Side
sidebar_position: 1
---

# Streaks Side By Side

```sql lengths
SELECT streak_days FROM streak_ladder ORDER BY streak_days DESC
```

```sql paths
SELECT symbol, day_index, indexed
FROM streak_paths
WHERE streak_days = TRY_CAST(${inputs.length} AS INTEGER)
ORDER BY symbol, day_index
```

```sql group_summary
SELECT * FROM streak_ladder WHERE streak_days = TRY_CAST(${inputs.length} AS INTEGER)
```

```sql group_table
SELECT rank, symbol, company, sector, streak_gain_pct, avg_daily_gain_pct, latest_day_pct
FROM active_streaks
WHERE streak_days = TRY_CAST(${inputs.length} AS INTEGER)
ORDER BY rank
```

Every streak of the same length, drawn on one chart. Pick a length; each line is one stock's climb
from the session before its streak began to the latest close.

{% notes label="How to read the chart" %}
Every line starts at **100** on day 0 — the close just before the streak began — so a $15 stock and
a $1,500 stock share the same picture. The height of a line at the right-hand edge is its streak
gain: 110 means up 10%.

A line that rises steadily is a grind; a line with one big step is a single-day jump (an earnings
report, a deal) followed by small follow-through days. The steady climbers and the one-day jumpers
are on the same leaderboard, and this chart is how you tell them apart.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Day 0** | The session just before the streak began: the last flat or down close. Every line starts here at 100. |
| **Indexed** | The close as a percentage of the day-0 close. 105 means 5% above where the streak started. |
| **Streak** | An unbroken run of sessions where each close was higher than the one before, ending on the latest close. |
| **Streak gain** | The percentage rise from the day-0 close to the latest close — the line's height at the right edge, minus 100. |
{% /glossary %}

{% select name="length" title="Streak length (days)" data="$lengths" value="streak_days" /%}

{% big_value data="$group_summary" value="stocks" title="Stocks At This Length" fmt="num0" info="How many stocks are on a streak of exactly this many days. Each is one line in the chart." /%}
{% big_value data="$group_summary" value="avg_gain_pct" title="Average Streak Gain" fmt="pct1" info="The typical rise these streaks have produced. The chart shows the spread around it." /%}
{% big_value data="$group_summary" value="best_gain_pct" title="Best Gain In Group" fmt="pct1" info="The top line on the chart. The symbol is in the table." /%}

{% line_chart data="$paths" x="day_index" series="symbol" title="Each Streak, Indexed To 100 At Day 0" yFmt="num1" yAxisTitle="close, day 0 = 100" xAxisTitle="sessions since the streak began" chartAreaHeight=340 legend="right" info="One line per stock, all starting at 100. The spread of the lines is the range of outcomes for streaks of this length. Look for the line that got there in one step — that is news-driven, and the streak days after the step are often small." /%}

{% data_table data="$group_table" rows=10 rowShading=true title="The Stocks In This Group" info="The same stocks as the lines above, in leaderboard order. Per day is the streak gain divided by its length; Latest day is the last session's move alone." %}
{% column id="rank" title="#" fmt="num0" /%}
{% column id="symbol" title="Symbol" /%}
{% column id="company" title="Company" /%}
{% column id="sector" title="Sector" /%}
{% column id="streak_gain_pct" title="Streak gain" fmt="pct1" contentType="colorscale" scaleColor=["#dcfce7", "#16a34a"] /%}
{% column id="avg_daily_gain_pct" title="Per day" fmt="pct1" /%}
{% column id="latest_day_pct" title="Latest day" fmt="pct1" /%}
{% /data_table %}
