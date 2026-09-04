---
title: What Actually Predicts
sidebar_position: 5
---

# What Actually Predicts The Next Session

```sql summary
SELECT * FROM bounce_summary
```

```sql evidence
SELECT direction, streak_length, observations, rose_next_pct, avg_next_pct, avg_excess_pct
FROM streak_evidence
WHERE direction = ${inputs.direction}
ORDER BY streak_length
```

```sql evidence_both
SELECT streak_length AS "Days in a row",
       max(CASE WHEN direction = 'Rose N days running' THEN avg_excess_pct END) AS "After rising",
       max(CASE WHEN direction = 'Fell N days running' THEN avg_excess_pct END) AS "After falling"
FROM streak_evidence GROUP BY streak_length ORDER BY streak_length
```

```sql rules
SELECT * FROM rule_comparison ORDER BY rule, period
```

```sql bounce_chart
SELECT market_day, avg_next_pct, next_up_pct, sessions FROM market_bounce ORDER BY sort_order
```

```sql picks
SELECT * FROM bounce_picks
WHERE bounce_rank <= TRY_CAST(${inputs.how_many} AS INTEGER)
ORDER BY bounce_rank
```

The scanner's first four pages find stocks on a winning run. This page asks the harder question:
**does a winning run tell you anything about tomorrow?** Two years of sessions say no. It says
something about the stocks that have been *falling*, and even that is faint.

{% notes label="Read this before you act on anything here" %}
This page exists because the rule on the previous page failed. It was judged on forty sessions,
looked promising, and lost money the first day it was used. Forty sessions cannot tell a real
effect from noise. So everything here is measured over **every session in the price history**, and
the history is **split in half**: a rule may be chosen on the first half, and the second half —
which the rule never saw — is the only honest report of how it does.

**The column that matters is the last one: average excess.** That is the stock's next-day move
*minus the whole index's move that day*. A rule with a fine-looking return and no excess is a bet
on the market rising, and buying an index fund would do the same job with less work and less risk.

**Nothing here is significant enough to trade on.** The t-statistic tile says how many standard
errors the best rule's edge sits above zero. Below about 2 it is indistinguishable from luck.
{% /notes %}

{% glossary label="Terms used on this page" %}
| Term | What it means |
| --- | --- |
| **Next session** | The next trading day after the one being measured. The thing every rule here is trying to predict. |
| **Excess return** | A stock's next-day move minus the equal-weighted average move of all S&P 500 members that day. It separates picking a stock from riding the market. |
| **Baseline** | Buying any index member at random. Any rule has to beat this to be worth the effort. |
| **Held-out half** | The later half of the history, deliberately not used to choose the rule. A rule that works only on the half it was designed on is a rule that has memorised noise. |
| **t-statistic** | How many standard errors an average sits above zero. Below about 2, the result is within the range that luck alone produces. |
| **Mean reversion** | The tendency of a price that has moved a long way in one direction to move back. The opposite of momentum. |
| **Momentum** | The tendency of a price that has been rising to keep rising. What the first four pages of this dashboard look for. |
| **Breadth** | The share of index members that rose on a session. Low breadth means a broad down day. |
{% /glossary %}

{% big_value data="$summary" value="sessions_tested" title="Sessions Tested" fmt="num0" info="Every trading session in the price history that has a following session to check against. Two years. The previous page's rule was judged on forty, which is why it said nothing reliable." /%}
{% big_value data="$summary" value="bounce_avg_excess_pct" title="Best Rule's Edge Per Day" fmt="num2" suffix="%" info="Average next-day return above the index for the best rule found — buying the heaviest fallers. Positive, but tiny: a few hundredths of a percent per day, before any trading cost." /%}
{% big_value data="$summary" value="bounce_excess_held_out" title="Same Edge, Held-Out Half" fmt="num2" suffix="%" info="The same measure on the half of the history the rule was not chosen on. It survived, which is the minimum test any rule must pass. It is still small." /%}
{% big_value data="$summary" value="t_statistic" title="t-Statistic" fmt="num2" info="How many standard errors that edge sits above zero. Below about 2 it cannot be told apart from luck. This one is below 2. Treat the rule as unproven, not as a signal." /%}

## Does a streak predict anything? Both directions

{% notes %}
For every streak length, what the stock did the **next** session, over the whole history. Switch
the direction to compare. Read the **average excess** column: for rising streaks it is around zero
and turns negative at the long end, meaning stocks on the longest winning runs slightly
*underperform*. For falling streaks it is mildly positive from four days on.

That is the whole finding, and it is the opposite of what the scanner was built to look for.
{% /notes %}

{% select name="direction" title="Streaks that" options="Rose N days running,Fell N days running" default="Rose N days running" /%}

{% row %}
{% data_table data="$evidence" rows=7 rowShading=true title="What Happened The Next Session" info="Observations is how many stock-days sit behind each row, so you can see which rows are thin. Rose next is the hit rate; a coin flip is about 51% here because stocks drift up. Average excess is the honest column." %}
{% column id="streak_length" title="Days in a row" fmt="num0" /%}
{% column id="observations" title="Observations" fmt="num0" /%}
{% column id="rose_next_pct" title="Rose next" fmt="pct1" /%}
{% column id="avg_next_pct" title="Avg next day" fmt="num3" /%}
{% column id="avg_excess_pct" title="Avg excess" fmt="num3" contentType="colorscale" scaleColor=["#dc2626", "#16a34a"] scaleCenter=0 /%}
{% /data_table %}
{% bar_chart data="$evidence_both" x="Days in a row" y=["After rising", "After falling"] title="Next-Day Excess Return, By Streak Length" yFmt="num2" yAxisTitle="% above the index" xAxisTitle="days in a row" colors=["#dc2626", "#0d9488"] chartAreaHeight=300 legend="bottom" info="Red is what happens after a stock has risen N days running; teal is after it has fallen N days running. Red sinks below zero at the long end and teal sits above it. That is mean reversion, and it is the reverse of the scanner's premise. Both effects are small — read the scale." /%}
{% /row %}

## The two rules, against buying anything

{% notes %}
Each rule buys five stocks at every close and holds for one session. **Buy the risers** is the
scanner's own logic. **Buy the fallers** is its mirror. The baseline is buying any index member.

Look down the excess column, then across the two halves. The risers rule is negative in both
halves. The fallers rule is positive in both. Neither is large.
{% /notes %}

{% data_table data="$rules" rows=6 rowShading=true title="Rules Compared, First Half And Held-Out Half" info="A rule that only works in the first half has memorised the past. A rule that works in both may have something, if the size is worth the risk. Read the excess column: the baseline is zero there by definition." %}
{% column id="rule" title="Rule" /%}
{% column id="period" title="Half of the history" /%}
{% column id="picks" title="Picks" fmt="num0" /%}
{% column id="rose_next_pct" title="Rose next" fmt="pct1" /%}
{% column id="avg_next_pct" title="Avg next day" fmt="num3" /%}
{% column id="avg_excess_pct" title="Avg excess" fmt="num3" contentType="colorscale" scaleColor=["#dc2626", "#16a34a"] scaleCenter=0 /%}
{% /data_table %}

## The one effect that is consistent, and it is not about stocks

{% notes %}
What the **market as a whole** did the session after a fall of a given size. After a fall of more
than 1%, the index has risen about two thirds of the time and averaged more than half a percent.
That is the most reliable pattern in this data, and it says nothing about which stock to buy — it
says the next day after a hard fall has been a better day to be invested than most.

Read the session count on each row. The hard-fall row is thin, so treat its size as approximate.
{% /notes %}

{% row %}
{% bar_chart data="$bounce_chart" x="market_day" y=["avg_next_pct"] title="Index's Average Next-Day Move, By What It Just Did" yFmt="num2" yAxisTitle="% next session" colors=["#0d9488"] chartAreaHeight=280 legend="none" horizontal=true info="Each bar is the index's average move the session after the kind of day named on the left. The hard-fall bar is the tallest, which is the bounce. Compare against the flat-day bar, which is slightly negative." /%}
{% bar_chart data="$bounce_chart" x="market_day" y=["next_up_pct"] title="How Often The Index Rose The Next Session" yFmt="num0" yMax=100 yAxisTitle="% of sessions" colors=["#0ea5e9"] chartAreaHeight=280 legend="none" horizontal=true info="The same days, counted rather than averaged. Around 50% is a coin flip. The hard-fall row sits well above it; the flat row sits below." %}
{% reference_line y=50 label="A coin flip" color="#94a3b8" /%}
{% /bar_chart %}
{% /row %}

## If you were going to act anyway: today's candidates

{% notes %}
The best rule the evidence supports, applied to the latest close: stocks that have fallen **three
or more sessions in a row**, ranked by how far they have fallen over five sessions. These are the
stocks the data says are most likely to bounce.

**Its measured edge is about a tenth of a percent a day above the index, and not statistically
significant.** A single day's outcome is close to a coin flip whatever this table says. Position
sizes should reflect that, and a spread of names is safer than one.

The **20-day high** column is the guard rail: a stock far below its high has fallen for a reason
that may not have finished. A fall on ordinary news reverts; a fall on a broken business does not,
and no price rule can tell you which this is.
{% /notes %}

{% select name="how_many" title="How many candidates" options="5,10,15" default="5" /%}

{% data_table data="$picks" rows=15 rowShading=true title="Biggest Fallers, Still Falling" info="Ranked by five-day fall among stocks down three or more sessions in a row. Down days is the current losing run; Five-day is the size of the fall the rule is betting reverses; % of 20-day high says how far below its recent peak the stock now sits." %}
{% column id="bounce_rank" title="#" fmt="num0" /%}
{% column id="symbol" title="Symbol" /%}
{% column id="company" title="Company" /%}
{% column id="sector" title="Sector" /%}
{% column id="down_days" title="Down days" fmt="num0" /%}
{% column id="latest_day_pct" title="Latest day" fmt="pct1" /%}
{% column id="five_day_pct" title="Five-day" fmt="pct1" contentType="colorscale" scaleColor=["#dc2626", "#fef3c7"] /%}
{% column id="pct_of_20d_high" title="% of 20-day high" fmt="num1" /%}
{% column id="latest_close" title="Close" fmt="usd2" /%}
{% /data_table %}
