---
title: Cross-Sell
sidebar_position: 4
---

# Member Segmentation & Cross-Sell

```sql summary
SELECT * FROM segment_summary
```

```sql segments
SELECT * FROM segment_breakdown
```

```sql pipeline
SELECT * FROM segment_pipeline
```

```sql depth
SELECT * FROM segment_depth
```

```sql tenure
SELECT * FROM segment_tenure
```

A member holding one product is a member with no reason to stay.

{% notes label="How this is measured" %}
**Product depth** is the number of distinct product types held on active accounts — chequing and
savings is two, chequing alone is one. The **pipeline** is single-product members already keeping
a meaningful deposit balance, which is what makes an offer credible rather than cold.
{% /notes %}

{% glossary label="Terms used in this chapter" %}
| Term | What it means |
| --- | --- |
| **Cross-sell** | A second (or third) product to a member who already banks here — deepening, not acquiring. |
| **Product depth** | How many distinct products a member holds. Depth one is a customer; depth three is a relationship. |
| **Single-product member** | Holds exactly one product. The easiest member to lose and the cheapest to deepen. |
| **Tenure** | Years since the member joined. Trust that marketing cannot buy. |
{% /glossary %}

{% big_value data="$summary" value="single_product_count" title="Single-Product Members" fmt="num0" info="Holding exactly one product type. The cross-sell population and the retention risk in one number — a member with one product has no switching cost." /%}
{% big_value data="$summary" value="pct_single_product" title="Share Of Book" fmt="num1" suffix="%" info="Single-product members as a share of everyone. The headline relationship-depth number." /%}
{% big_value data="$summary" value="avg_products_held" title="Avg Products" fmt="num2" info="Moving this by a tenth is a year of campaign work, which is why the segment table matters more than the average." /%}
{% big_value data="$summary" value="total_members" title="Members" fmt="num0" info="Everyone still on the books. The denominator." /%}

## How deep are the relationships

{% notes %}
The count of members at each depth. The bar at **1** is the cross-sell population and the retention
risk in the same column — read it against the bars to its right, because the shape is the argument:
a tall bar at one is a book of strangers, a tall bar at three or more is a book of relationships.
{% /notes %}

{% row %}
{% bar_chart data="$depth" x="bucket" y=["members"] title="Members by Number of Products Held" yFmt="num0" yAxisTitle="members" xAxisTitle="products held" colors=["#0d9488"] chartAreaHeight=260 info="The depth ladder. The tall bar at one product is the opportunity: every member there holds exactly one thing, and the second product is the one that makes a relationship sticky." /%}
{% scatter_chart data="$tenure" x="tenure_years" y=["deposit_balance"] series="segment" title="Tenure vs Deposit Balance" yFmt="usd0" yAxisTitle="deposits" xAxisTitle="tenure (years)" chartAreaHeight=260 info="Each dot is a member, coloured by segment. Long-tenure members with large balances and one product — upper right, if the depth is shallow — are the warmest calls on the page: trust exists, the wallet exists, only the relationship is thin." /%}
{% /row %}

## The shape of the book

{% notes %}
Two bars per segment: everyone in it, and the share of them holding a single product. Side by side
in one frame rather than in two charts — the comparison *is* the finding, and two charts make a
reader hold one shape in their head while they look at the other. A segment where the second bar
is close to the first is a segment the bank has barely sold into.
{% /notes %}

{% row %}
{% bar_chart data="$segments" x="segment" y=["members", "single_product_n"] title="Segment Size vs Single-Product Members" yFmt="num0" yAxisTitle="members" chartAreaHeight=260 info="Each segment's total members beside its single-product members. The nearer the two bars, the shallower the segment — a segment where they almost touch is nearly all opportunity, or nearly all disengagement." /%}
{% bar_chart data="$segments" x="segment" y=["total_deposits"] title="Deposits by Segment" yFmt="usd0" yAxisTitle="deposits" chartAreaHeight=260 info="Where the money already sits. Cross-sell effort ranked by this chart, not by member counts, protects the balances that matter most while deepening them." /%}
{% /row %}

## Segments, by what they keep

{% notes %}
A segment with large deposits and low depth is the best ground on the page — the money is already
there and the relationship is thin.
{% /notes %}

{% data_table data="$segments" rowShading=true title="Segments by Deposits and Depth" %}
{% column id="segment" title="Segment" /%}
{% column id="members" title="Members" fmt="num0" /%}
{% column id="total_deposits" title="Deposits" fmt="usd0" contentType="colorscale" scaleColor=["#ecfdf5", "#0d9488"] /%}
{% column id="avg_products" title="Avg Products" fmt="num2" contentType="colorscale" scaleColor=["#fef3c7", "#15803d"] /%}
{% column id="single_product_n" title="Single-Product" fmt="num0" contentType="colorscale" scaleColor=["#fef3c7", "#dc2626"] /%}
{% /data_table %}

## The campaign list

{% data_table data="$pipeline" rows=15 rowShading=true title="Single-Product Members by Balance" %}
{% column id="full_name" title="Member" /%}
{% column id="segment" title="Segment" /%}
{% column id="home_branch_name" title="Home Branch" /%}
{% column id="deposit_balance" title="Deposits" fmt="usd0" contentType="colorscale" scaleColor=["#ecfdf5", "#0d9488"] /%}
{% /data_table %}
