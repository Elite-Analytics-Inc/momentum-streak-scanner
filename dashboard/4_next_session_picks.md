---
title: Next-Session Picks
sidebar_position: 4
---

# Next-Session Picks

```sql summary
SELECT * FROM pick_backtest_summary
```

```sql picks
SELECT * FROM pick_scores
WHERE pick_rank <= TRY_CAST(${inputs.top_n} AS INTEGER)
ORDER BY pick_rank
```

```sql parts
SELECT symbol, accel_pts AS "Last day", tide_pts AS "Sector tide", steady_pts AS "Steady climb", trend_pts AS "Near its high"
FROM pick_scores
WHERE pick_rank <= TRY_CAST(${inputs.top_n} AS INTEGER)
ORDER BY pick_rank
```

```sql test
SELECT count(DISTINCT pick_date) AS days_tested,
       count(*) AS picks_tested,
       round(100.0 * count(*) FILTER (WHERE rose_next_day) / greatest(1, count(*)), 1) AS pick_hit_pct,
       round(avg(next_day_pct), 2) AS pick_avg_next_pct
FROM pick_backtest
WHERE pick_rank <= TRY_CAST(${inputs.top_n} AS INTEGER)
```

```sql test_by_day
SELECT pick_date,
       round(100.0 * count(*) FILTER (WHERE rose_next_day) / count(*), 1) AS "The picks",
       max(market_hit_pct) AS "Whole index"
FROM pick_backtest
WHERE pick_rank <= TRY_CAST(${inputs.top_n} AS INTEGER)
GROUP BY pick_date
ORDER BY pick_date
```

A rule for choosing which streaks to back for the next session — and, just as important, a
replay of that rule on past days so you can see whether it beat a coin flip.

**This rule does not work.** Tested over two years on the next page, buying the stocks with the
strongest winning runs lost to the index in both halves of the sample. The page is kept because
the ranking it produces is what the analysis was asked for, and because a rule shown to fail is
more useful than one quietly deleted. Read **What Actually Predicts** before acting on anything
here.

{% notes label="How the picks are chosen — and how to judge them" %}
Every streaking stock is scored out of 100 on four signs that its run still had force at the
latest close:

| Sign | Points | What earns them |
| --- | --- | --- |
| **Last day** | up to 30 | The last session's rise. A 3% day scores full marks; a flat day scores none. A run that is speeding up, not fading. |
| **Sector tide** | up to 30 | The share of the stock's own sector that rose on the latest session. The tide is with it. |
| **Steady climb** | up to 20 | The share of the streak's gain that did **not** come from its single biggest day. A climb, not a one-day jump. |
| **Near its high** | up to 20 | The latest close as a share of the stock's highest close in the window. A breakout, not a bounce. |

The picks are the highest scores. **Then read the back-test tiles.** The same rule was applied
on every earlier day in the window and its picks checked against the next session. If the picks'
rate of rising is **not clearly above the whole index's rate**, the rule has no edge and you should
not trade on it. Be doubly careful because the rule was designed while looking at these same weeks,
which flatters it, and because forty days is a short test.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Score** | A number out of 100 built from the four signs above. Higher means the run looked healthier at the close. Not a probability. |
| **Pick** | A streaking stock in the top N by score, where N is the dropdown's choice. |
| **Back-test** | Applying today's rule on past days and checking what happened next. The only honest way to know whether a rule works. |
| **Hit rate** | The share of picks that closed higher the next session. A coin flip is about 50%. |
| **Whole index** | The share of all S&P 500 members that closed higher the next session — what you would get by picking at random. |
| **Streak** | An unbroken run of sessions where each close was higher than the one before, ending on the latest close. |
{% /glossary %}

{% select name="top_n" title="How many picks" options="5,10,15,20" default="5" /%}

{% big_value data="$summary" value="top_pick" title="Top Pick" fmt="raw" info="The highest-scoring streak at the latest close. The table below says why, and what to be wary of." /%}
{% big_value data="$test" value="pick_hit_pct" title="Picks That Rose Next Day (Back-Test)" fmt="pct1" info="Over every past day in the window, the share of that day's picks that closed higher the next session. This is the number that says whether the rule works. Compare it with the next tile." /%}
{% big_value data="$summary" value="market_hit_pct" title="Whole Index, Same Days" fmt="pct1" info="The share of all index members that rose the next session over the same days — the random-pick baseline. If the picks are not clearly above this, the rule has no edge." /%}
{% big_value data="$test" value="days_tested" title="Days Tested" fmt="num0" info="How many past sessions the rule was replayed on. Forty days is a short test: a real verdict needs a year or more." /%}

{% row %}
{% bar_chart data="$parts" x="symbol" y=["Last day", "Sector tide", "Steady climb", "Near its high"] stacked=true title="What Each Pick's Score Is Made Of" yFmt="num0" yMax=100 yAxisTitle="points (out of 100)" colors=["#0d9488", "#0ea5e9", "#f59e0b", "#94a3b8"] chartAreaHeight=300 legend="bottom" info="Each bar is one pick's score, split into the four signs. Two picks with the same total can be very different: one carried by a strong last day, the other by its sector. A bar with almost no amber has a one-day jump behind it." /%}
{% line_chart data="$test_by_day" x="pick_date" y=["The picks", "Whole index"] title="Back-Test: % That Rose The Next Session, Day By Day" yFmt="num0" yMin=0 yMax=100 yAxisTitle="% up next session" colors=["#0d9488", "#94a3b8"] chartAreaHeight=300 legend="bottom" info="For each past day, the teal line is the share of that day's picks that rose the next session and the grey line is the share of the whole index. If teal sits above grey most days the rule has something; if the two tangle, or teal is mostly below, it does not." /%}
{% /row %}

{% data_table data="$picks" rows=10 rowShading=true title="The Picks, Best Score First" info="Why lists the signs the stock scored well on; Warning lists the signs that argue against it. A pick with a warning is a pick to think twice about, whatever its score." %}
{% column id="pick_rank" title="#" fmt="num0" /%}
{% column id="symbol" title="Symbol" /%}
{% column id="company" title="Company" /%}
{% column id="sector" title="Sector" /%}
{% column id="streak_days" title="Days" fmt="num0" /%}
{% column id="streak_gain_pct" title="Streak gain" fmt="pct1" /%}
{% column id="latest_day_pct" title="Last day" fmt="pct1" /%}
{% column id="score" title="Score" fmt="num1" contentType="colorscale" scaleColor=["#ccfbf1", "#0d9488"] /%}
{% column id="why" title="Why" /%}
{% column id="warning" title="Warning" /%}
{% /data_table %}
