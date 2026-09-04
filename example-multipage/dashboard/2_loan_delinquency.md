---
title: Loan Delinquency
sidebar_position: 2
---

# Loan Delinquency & Roll Rates

```sql summary
SELECT * FROM loans_summary
```

```sql roll_wide
SELECT prev_dpd_bucket,
       coalesce(max(pct_of_prev) FILTER (WHERE dpd_bucket = 'Current'), 0) AS "Now current",
       coalesce(max(pct_of_prev) FILTER (WHERE dpd_bucket = '30-59 days late'), 0) AS "30-59",
       coalesce(max(pct_of_prev) FILTER (WHERE dpd_bucket = '60-89 days late'), 0) AS "60-89",
       coalesce(max(pct_of_prev) FILTER (WHERE dpd_bucket = '90+ days late'), 0) AS "90+"
FROM loans_roll
GROUP BY prev_dpd_bucket
ORDER BY CASE prev_dpd_bucket WHEN 'Current' THEN 0 WHEN '30-59 days late' THEN 1
                              WHEN '60-89 days late' THEN 2 ELSE 3 END
```

```sql products
SELECT * FROM loans_by_product
```

```sql vintage
SELECT * FROM loans_vintage ORDER BY vintage_year
```

```sql branches
SELECT * FROM loans_branches
```

A bucket distribution says how much is late today. A roll rate says what share of last month's
30-day loans became 60-day loans — which is what predicts next quarter.

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **DPD** | Days past due — how late a payment is. Grouped in 30-day buckets: 30–59, 60–89, 90+. |
| **Roll rate** | Of the loans in a bucket last month, the share now in each bucket — the speed at which lateness worsens or cures. |
| **90+** | Ninety or more days late. The bucket that rarely cures; entry here is substantially predictive of charge-off. |
| **Vintage** | Every loan written in the same year, judged together — bad vintages point at underwriting, not borrowers. |
| **Charge-off** | The bank stops expecting repayment and writes the loan down. The end of the road this chapter watches loans travel. |
{% /glossary %}

{% big_value data="$summary" value="at_risk_dollars" title="Principal At Risk" fmt="usd0" info="Principal on every loan not current. Exposure, not expected loss — the difference is a recovery assumption this chapter does not make." /%}
{% big_value data="$summary" value="pct_current" title="Current" fmt="num2" suffix="%" info="Share of loans not late at all. The roll table below says whether it is about to move." /%}
{% big_value data="$summary" value="pct_90plus" title="90+ Days" fmt="num2" suffix="%" info="The bucket that rarely cures. Entry here is substantially predictive of charge-off at most institutions." /%}
{% big_value data="$summary" value="charged_off_count" title="Charged Off" fmt="num0" info="Loans the bank has stopped expecting repayment on." /%}

## Where last month's loans are now

{% notes %}
Read it **by row**: each row is where a cohort started, the columns are where it is now, as a
percentage of that cohort. The left column is the cure rate; everything right of the diagonal is
deterioration.

The cell that matters most is **60-89 → 90+**. A cure rate falling while the buckets stay flat is
an early warning the headline will not show for another quarter.
{% /notes %}

{% data_table data="$roll_wide" rowShading=true title="Roll Rates (% of each cohort)" %}
{% column id="prev_dpd_bucket" title="Was" /%}
{% column id="Now current" title="Now current" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#15803d"] /%}
{% column id="30-59" title="30-59" fmt="num1" contentType="colorscale" scaleColor=["#fef9c3", "#f59e0b"] /%}
{% column id="60-89" title="60-89" fmt="num1" contentType="colorscale" scaleColor=["#fef3c7", "#ea580c"] /%}
{% column id="90+" title="90+" fmt="num1" contentType="colorscale" scaleColor=["#fee2e2", "#dc2626"] /%}
{% /data_table %}

## Product view

{% row %}
{% bar_chart data="$products" x="product_type" y=["at_risk_dollars"] title="Principal At Risk by Product" yFmt="usd0" yAxisTitle="at risk" colors=["#dc2626"] chartAreaHeight=260 info="Late principal by product. Mortgages will usually dominate on dollars simply because the loans are bigger — read this beside the rate chart before concluding a product is in trouble." /%}
{% bar_chart data="$products" x="product_type" y=["pct_delinquent"] title="Delinquency Rate by Product" yFmt="num1" yAxisTitle="% delinquent" colors=["#f59e0b"] chartAreaHeight=260 info="The share of each product's loans that are late — size taken out of the picture. A small product with a high rate is an underwriting question; a big product with a rising rate is a book question." /%}
{% /row %}

## Which products carry it

{% notes %}
A high rate on small balances is a pricing question; a low rate on large balances is a
concentration question. They rarely want the same response.
{% /notes %}

{% data_table data="$products" rowShading=true title="Delinquency by Product" %}
{% column id="product_type" title="Product" /%}
{% column id="dpd_90plus" title="90+ Loans" fmt="num0" contentType="colorscale" scaleColor=["#fee2e2", "#dc2626"] /%}
{% column id="pct_delinquent" title="Delinquent %" fmt="num2" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% column id="at_risk_dollars" title="At Risk" fmt="usd0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}

## By vintage

{% notes %}
Cohorts underwritten under the same standards age together, so a bad vintage is a **lending-policy**
finding rather than a collections one — and it points at a quarter, which usually points at a
decision. Recent vintages look healthy because they have not had time to go bad; compare like-aged
cohorts, not adjacent bars.
{% /notes %}

{% row %}
{% bar_chart data="$vintage" x="vintage_year" y=["pct_90plus"] title="90+ Rate by Origination Year" yFmt="num2" yAxisTitle="% at 90+" xAxisTitle="origination year" colors=["#dc2626"] chartAreaHeight=260 info="Serious lateness by the year the loan was written. One bad year standing out means the underwriting of that vintage, not the economy of this one — a different fix, applied to different people." /%}
{% bar_chart data="$vintage" x="vintage_year" y=["loans"] title="Loans Written by Year" yFmt="num0" yAxisTitle="loans" xAxisTitle="origination year" colors=["#0d9488"] chartAreaHeight=260 info="How many loans each vintage contains — the denominator for the chart beside it. A scary 90+ rate over a handful of loans is a rounding story, not a trend." /%}
{% /row %}

## Where it sits

{% bar_chart data="$branches" x="branch" y=["at_risk_dollars"] title="Principal At Risk by Home Branch" yFmt="usd0" yAxisTitle="at risk" colors=["#dc2626"] chartAreaHeight=280 info="Late principal by the borrower's home branch. Concentration here says where collections effort and local judgment should go first." /%}
