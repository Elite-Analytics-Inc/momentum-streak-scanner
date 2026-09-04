---
title: Channel Adoption
sidebar_position: 5
---

# Channel Adoption

```sql summary
SELECT * FROM channel_summary
```

```sql trend
SELECT * FROM channel_trend ORDER BY month_start
```

```sql seg
SELECT * FROM channel_segment
```

Where members choose to bank drifts year by year — branch usage falls, mobile rises — and that
drift is the slide every retail-banking board deck opens with.

{% notes label="How this is measured" %}
**Self-serve** is anything without a teller: mobile, online, ATM and card. By construction
self-serve and branch add to 100%. **Mobile** is pulled out on its own because it is the most
cost-efficient channel and the leading indicator of digital health.
{% /notes %}

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **Channel** | Where a transaction happened: branch counter, mobile app, online banking, ATM, or card at a merchant (POS). |
| **Adoption** | A member's first sustained use of a digital channel — not one login, a changed habit. |
| **Mix** | Each channel's share of all transactions in a month. Shares, not counts: growth everywhere can still change the mix. |
{% /glossary %}

{% big_value data="$summary" value="self_serve_share_now" title="Self-Serve" fmt="num1" suffix="%" info="Share of transactions with no teller involved. Self-serve costs roughly a fifteenth of an in-branch transaction, so growth here flows straight to operating margin." /%}
{% big_value data="$summary" value="branch_share_now" title="Branch Now" fmt="num1" suffix="%" info="Share still happening at a teller window." /%}
{% big_value data="$summary" value="branch_share_then" title="Branch Then" fmt="num1" suffix="%" info="Branch share at the start of the window. Read against Branch Now to see the migration speed." /%}
{% big_value data="$summary" value="mobile_share_now" title="Mobile Only" fmt="num1" suffix="%" info="The app alone, not the web site and not the ATM. Above 40% is top-quartile for community banks." /%}

## The migration

{% notes %}
Each band is one channel's share of that month's transactions, so the stack always totals 100.
Watch the branch band shrink and the mobile band swell — that is the whole story in one picture.

Two things to watch: the mobile band flattening, which means saturation; and the month branch and
ATM together drop below half, which is the point the operating model has inverted.
{% /notes %}

{% area_chart data="$trend" x="month_start" y=["Branch","Mobile","Online","ATM","POS"] stacked=true title="Channel Mix — % of Monthly Transactions" yFmt="num0" yAxisTitle="% share" yMax=100 colors=["#dc2626","#0ea5e9","#7c3aed","#f59e0b","#94a3b8"] chartAreaHeight=320 info="Each band is a channel's share of that month's transactions; the bands always sum to 100. Watch the branch band: its narrowing is the migration, and the pace of narrowing — not the level — is what should size the branch footprint conversation." /%}

## Who is leading it

{% notes %}
Latest month only, one row per segment, sorted by digital share. Read a row **left to right**: the
most saturated cell is where that cohort does its banking, and each row sums to 100%.

Young Professional leaning Mobile is a healthy pipeline. Senior leaning Branch and ATM is expected
— pushing that cohort off the teller too hard is reputational risk. Mass Market with branch still
dominant is where the next digital-onboarding pound pays back the most.
{% /notes %}

{% data_table data="$seg" rowShading=true title="Channel Mix Within Each Segment (latest month)" %}
{% column id="segment" title="Segment" /%}
{% column id="total_txns" title="Txns (mo.)" fmt="num0" /%}
{% column id="branch_pct" title="Branch %" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="mobile_pct" title="Mobile %" fmt="num1" contentType="colorscale" scaleColor=["#dbeafe", "#0ea5e9"] /%}
{% column id="online_pct" title="Online %" fmt="num1" contentType="colorscale" scaleColor=["#ede9fe", "#7c3aed"] /%}
{% column id="atm_pct" title="ATM %" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#f59e0b"] /%}
{% column id="digital_pct" title="Digital %" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#15803d"] /%}
{% /data_table %}
