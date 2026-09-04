---
title: The Market Backdrop
sidebar_position: 3
---

# The Market Backdrop

```sql overview
SELECT * FROM scan_overview
```

```sql breadth
SELECT trade_date, share_up_pct, on_streak FROM daily_breadth ORDER BY trade_date
```

```sql sectors
SELECT * FROM sector_streaks ORDER BY winners DESC, winners_share_pct DESC
```

Fifty streaks after three days when almost every stock rose is the market lifting everything.
Fifty streaks after a mixed week is stock-specific momentum. This page tells the two apart.

{% notes label="How to read this page" %}
**Breadth** is the share of index members that closed higher on a given session. Around 50% is an
ordinary day; above 70% is a broad up-day and below 30% a broad down-day. Three broad up-days in a
row will put a large number of stocks on a 3-day streak by themselves.

**Stocks on a streak** is counted *as of each day* using the same rule as the leaderboard, so the
last point on that line is today's count. When the line spikes right after a run of broad up-days,
the streaks are the market's doing. When it holds steady through mixed days, those stocks are
moving on their own.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Breadth** | The share of all index members that closed higher than the previous session. High breadth means the whole market moved. |
| **On a streak** | Stocks whose run of higher closes, counted as of that day, was at least the minimum length. |
| **Sector** | One of the eleven industry groups (GICS) every S&P 500 company is filed under. |
| **Up today** | Within a sector, the share of its members that rose on the latest session — the sector's own breadth. |
{% /glossary %}

{% big_value data="$overview" value="share_up_today_pct" title="Index Members Up On The Latest Close" fmt="pct1" info="Breadth on the latest session. Well above 50% means the market rose broadly, and many streaks were extended by the tide rather than by the company." /%}
{% big_value data="$overview" value="winners" title="Stocks On A Streak" fmt="num0" info="Today's count, the same number as the front page. The chart below shows whether it is high for recent weeks." /%}
{% big_value data="$overview" value="priced_today" title="Stocks With A Price Today" fmt="num0" info="Index members with a close on the latest session. Any member missing here is stale in the feed and cannot be judged — see the next tile." /%}
{% big_value data="$overview" value="stale_symbols" title="Missing A Price Today" fmt="num0" info="Index members with no close on the latest session — usually a very recent addition to the index or a feed gap. Zero is normal. Anything larger deserves a look before trusting the list." /%}

## Market breadth and streak count, day by day

{% row %}
{% line_chart data="$breadth" x="trade_date" y=["share_up_pct"] title="Breadth — % Of Index Members Up Each Session" yFmt="num0" yMin=0 yMax=100 yAxisTitle="% of members up" colors=["#0d9488"] chartAreaHeight=300 legend="none" info="Above the dashed line more stocks rose than fell. A run of days well above 70% is a broad rally: expect the streak count to jump and mean less. Days near 50% are the ones on which a streak says something about the stock." %}
{% reference_line y=50 label="Half the market up" color="#94a3b8" /%}
{% /line_chart %}
{% line_chart data="$breadth" x="trade_date" y=["on_streak"] title="Stocks On A Streak, As Of Each Session" yFmt="num0" yMin=0 yAxisTitle="stocks" colors=["#f59e0b"] chartAreaHeight=300 legend="none" info="How many stocks would have made the leaderboard on each past day. The last point is today. Compare with the breadth chart: a spike that follows broad up-days is the market's doing; a count that stays high through mixed days is genuine stock-level momentum." /%}
{% /row %}

## By sector

{% notes %}
One row per sector. **Share** is streaking stocks as a percentage of the sector's members, which
is the fair comparison: sectors differ in size by almost three to one. **Up today** is the
sector's own breadth on the latest session — a sector where most members rose is a sector move.
{% /notes %}

{% data_table data="$sectors" rows=11 rowShading=true title="Streaks By Sector" info="Sectors ordered by how many streaking stocks they hold. Read Share, not the raw count, to compare sectors fairly; read Up today to see whether the whole sector moved on the latest session." %}
{% column id="sector" title="Sector" /%}
{% column id="priced" title="Members" fmt="num0" /%}
{% column id="winners" title="On a streak" fmt="num0" contentType="colorscale" scaleColor=["#ccfbf1", "#0d9488"] /%}
{% column id="winners_share_pct" title="Share" fmt="pct1" contentType="colorscale" scaleColor=["#ccfbf1", "#0d9488"] /%}
{% column id="longest_streak" title="Longest" fmt="num0" /%}
{% column id="avg_gain_pct" title="Avg streak gain" fmt="pct1" /%}
{% column id="up_today_pct" title="Up today" fmt="pct1" /%}
{% /data_table %}
