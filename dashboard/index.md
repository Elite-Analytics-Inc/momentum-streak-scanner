---
title: Today's Streaks
sidebar_position: 0
---

# Momentum Streak Scanner — S&P 500

```sql overview
SELECT * FROM scan_overview
```

```sql ladder
SELECT * FROM streak_ladder ORDER BY streak_days
```

```sql sectors
SELECT sector, winners, priced FROM sector_streaks ORDER BY winners DESC, sector
```

```sql leaderboard
SELECT * FROM active_streaks
WHERE streak_days >= ${inputs.min_streak}
  AND sector IN ${inputs.sectors}
ORDER BY rank
```

Which S&P 500 stocks have closed higher every single session for days on end — and are still
doing it as of the latest close? Everything on this page is about **live, unbroken** streaks only.
A run that ended yesterday does not count, however long it was.

{% notes label="How this is measured" %}
For each stock, start at the latest close and step backwards one session at a time. If the latest
close is above the one before, that is a streak of one; keep counting while each close beats the
previous one. The first session that was flat or down ends the count.

Two rules follow from that:

- A stock that was flat or down on the latest session has a streak of **zero**, whatever it did
  before. Only streaks that are alive today count.
- The **streak gain** is measured from the close *just before* the streak began (the last down or
  flat day) to the latest close — the whole rise the streak produced.

Only stocks with at least the minimum streak length (a launch setting, normally 3) are listed.
They are ranked by streak length first, then by streak gain. Prices are dividend- and
split-adjusted, so a payout day does not break a streak by itself.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **S&P 500** | The index of about 500 of the largest US-listed companies. The list of members is fetched fresh, never typed in by hand. |
| **Session** | One trading day. Weekends and market holidays are not sessions, so a 3-day streak can span a weekend. |
| **Close** | The last traded price of a session. Every comparison here is close against previous close. |
| **Streak** | An unbroken run of sessions where each close was higher than the one before, ending on the latest close. |
| **Streak gain** | The percentage rise from the close before the streak started to the latest close. |
| **Base** | The close on the session just before the streak began — the price the gain is measured from. |
| **Sector** | One of the eleven industry groups (GICS) every S&P 500 company is filed under: Energy, Utilities, Information Technology, and so on. |
| **Breadth** | The share of all index members that rose on a given session. High breadth means the whole market moved, not a few stocks. |
{% /glossary %}

{% big_value data="$overview" value="scan_date_label" title="As Of The Close On" fmt="raw" info="The latest completed trading session in the data. Every number on every page is measured at this close. If this date is older than you expect, the price feed has not been refreshed." /%}
{% big_value data="$overview" value="winners" title="Stocks On A Streak" fmt="num0" info="How many of the roughly 500 index members have an unbroken run of higher closes at least the minimum length long. Typically a few dozen. A number near 100 means the whole market has been rising for days, so the streaks say more about the market than about the companies." /%}
{% big_value data="$overview" value="longest_streak" title="Longest Streak" fmt="num0" suffix=" days" info="The longest unbroken run of higher closes in the index right now. Runs of 7 or more are rare; the leaderboard below names the stock." /%}
{% big_value data="$overview" value="best_gain_pct" title="Best Streak Gain" fmt="pct1" info="The largest rise any single streak has produced, from the close before it began to the latest close. Read against the streak's length: 10% in 4 days is a very different story from 10% in 9." /%}

## The leaderboard

{% notes %}
The full list, in the order that matters: **longest streak first**, and among equal streaks, the
**biggest gain** first. Use the controls to raise the bar or focus on sectors — the table below
them changes at once. Read **Streak gain** against **Days**: a big gain over few days is a sharp
move, a small gain over many days is a steady grind. **Latest day** is the last session's move on
its own — a streak that is still accelerating looks different from one barely hanging on.
{% /notes %}

{% slider name="min_streak" title="Streak at least (days)" min=2 max=15 step=1 default=3 /%}
{% multi_select name="sectors" title="Sectors" options="Communication Services,Consumer Discretionary,Consumer Staples,Energy,Financials,Health Care,Industrials,Information Technology,Materials,Real Estate,Utilities" /%}

{% data_table data="$leaderboard" rows=12 rowShading=true title="Active Streak Leaderboard" info="Every stock whose run of higher closes is alive at the latest close and at least as long as the control above. Rank is by days, then by gain. Base is the close before the streak began; the gain is measured from there to Latest close. An empty table means no stock meets the filter — lower the days or widen the sectors." %}
{% column id="rank" title="#" fmt="num0" /%}
{% column id="symbol" title="Symbol" /%}
{% column id="company" title="Company" /%}
{% column id="sector" title="Sector" /%}
{% column id="streak_days" title="Days" fmt="num0" contentType="colorscale" scaleColor=["#ccfbf1", "#0d9488"] /%}
{% column id="streak_gain_pct" title="Streak gain" fmt="pct1" contentType="colorscale" scaleColor=["#dcfce7", "#16a34a"] /%}
{% column id="avg_daily_gain_pct" title="Per day" fmt="pct1" /%}
{% column id="latest_day_pct" title="Latest day" fmt="pct1" /%}
{% column id="base_close" title="Base" fmt="usd2" /%}
{% column id="latest_close" title="Latest close" fmt="usd2" /%}
{% /data_table %}

## The shape of today's streaks

{% notes %}
Left: how the streaking stocks spread across streak lengths. The tallest bar is always at the
minimum — streaks are hard to keep alive — so what matters is how far the ladder reaches to the
right. Right: which sectors the streaks sit in. Many winners from one sector is a sector move, not
stock-picking, and the backdrop page says whether the whole market lifted them.
{% /notes %}

{% row %}
{% bar_chart data="$ladder" x="label" y=["stocks"] title="Stocks By Streak Length" yFmt="num0" yAxisTitle="stocks" colors=["#0d9488"] chartAreaHeight=260 legend="none" info="One bar per streak length; the height is how many stocks are on a streak exactly that long. A bar far to the right is an unusual stock — find it in the leaderboard. If every bar is tall, the market as a whole has been climbing." /%}
{% bar_chart data="$sectors" x="sector" y=["winners"] title="Streaking Stocks By Sector" yFmt="num0" yAxisTitle="stocks" colors=["#0d9488"] chartAreaHeight=260 horizontal=true legend="none" info="How many streaking stocks each sector contributes. Compare against the sector's size: Utilities has about 30 members and Industrials about 80, so five streaks in Utilities is a much stronger signal than five in Industrials." /%}
{% /row %}
