---
title: One Stock, Up Close
sidebar_position: 2
---

# One Stock, Up Close

```sql picks
SELECT symbol FROM active_streaks ORDER BY rank
```

```sql chosen
SELECT * FROM active_streaks WHERE symbol = ${inputs.stock}
```

```sql history
SELECT trade_date, close, streak_close, base_close
FROM price_history
WHERE symbol = ${inputs.stock}
ORDER BY trade_date
```

```sql moves
SELECT trade_date, up_pct, down_pct
FROM price_history
WHERE symbol = ${inputs.stock}
ORDER BY trade_date
```

```sql days
SELECT day_index, trade_date, close, pct_from_base
FROM streak_paths
WHERE symbol = ${inputs.stock}
ORDER BY day_index
```

Pick any stock from the leaderboard and see its streak in context: where it sits against the
weeks before it, and how each day of the run contributed.

{% notes label="How to read this page" %}
The price chart shows the whole window in grey, with the **active streak drawn over it in teal**.
The dashed line is the base — the close just before the streak began. A streak that starts from a
dip and only gets back to where the stock already was is a recovery; one that starts from a high
and keeps making new highs is a breakout. Same streak length, different meaning.

The daily-moves chart underneath is the same days as up (green) and down (red) bars. The streak
is the unbroken run of green at the right-hand end. Look at how big those bars are compared with
the ones before: a streak of tiny green bars after a big red one is a stock crawling back.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Base** | The close on the session just before the streak began. The dashed line, and the price the streak gain is measured from. |
| **Streak** | An unbroken run of sessions where each close was higher than the one before, ending on the latest close. |
| **Daily move** | One session's close against the previous close, as a percentage. Green is up, red is down or flat. |
| **From base** | How far above the base close the stock was at the end of each streak day, as a percentage. |
{% /glossary %}

{% select name="stock" title="Stock" data="$picks" value="symbol" /%}

{% big_value data="$chosen" value="streak_days" title="Streak" fmt="num0" suffix=" days" info="Consecutive sessions of higher closes, ending on the latest close." /%}
{% big_value data="$chosen" value="streak_gain_pct" title="Streak Gain" fmt="pct1" info="The rise from the base close to the latest close — the whole streak's work." /%}
{% big_value data="$chosen" value="latest_close" title="Latest Close" fmt="usd2" info="The most recent closing price, dividend- and split-adjusted." /%}
{% big_value data="$chosen" value="latest_day_pct" title="Latest Day" fmt="pct1" info="The last session's move on its own. A streak whose latest day is a sliver is one bad open away from ending." /%}

{% row %}
{% line_chart data="$history" x="trade_date" y=["close", "streak_close"] title="Closing Price, Streak Highlighted" yFmt="usd2" yAxisTitle="close" colors=["#94a3b8", "#0d9488"] chartAreaHeight=300 legend="none" info="Grey is the whole window; teal is the active streak. Judge the streak against the grey: is it climbing back to a level the stock already held, or breaking above everything before it?" %}
{% reference_line y="base_close" label="Base — the close before the streak began" color="#f59e0b" /%}
{% /line_chart %}
{% bar_chart data="$moves" x="trade_date" y=["up_pct", "down_pct"] stacked=true title="Daily Moves, Up And Down" yFmt="num1" yAxisTitle="% change on the day" colors=["#16a34a", "#dc2626"] chartAreaHeight=300 legend="none" info="Each bar is one session's move. The streak is the unbroken run of green at the right. Compare the size of those green bars with the red ones before them: small green after big red is a recovery, not strength." /%}
{% /row %}

{% data_table data="$days" rows=10 rowShading=true title="The Streak, Day By Day" info="Day 0 is the base session; each later row is one streak day. From base is the cumulative rise up to that day, so the last row equals the streak gain." %}
{% column id="day_index" title="Day" fmt="num0" /%}
{% column id="trade_date" title="Session" /%}
{% column id="close" title="Close" fmt="usd2" /%}
{% column id="pct_from_base" title="From base" fmt="pct1" contentType="colorscale" scaleColor=["#dcfce7", "#16a34a"] /%}
{% /data_table %}
