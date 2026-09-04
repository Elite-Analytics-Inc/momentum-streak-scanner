---
title: Overview
sidebar_position: 0
---

# The Story of This Bank

```sql overview
SELECT * FROM overview
```

```sql deposits
SELECT * FROM deposit_trend ORDER BY snapshot_date
```

Six readings of the same book, taken at the same moment by the same engine. Each chapter stands on
its own; read in order they answer one question — where is this institution's money going, and
what should somebody do about it on Monday.

{% notes label="About this binder" %}
This is **one run**, not six. Every chapter reads the same book at the same instant through one
engine, so the deposit figure on this page and the deposit figure in the attrition chapter cannot
disagree. Six separate runs would each pick their own moment and reconciling them would become
somebody's Monday.

Every number is a **governed** query: the row filters and column masks that apply to whoever
launched this run are already in the data behind every chart. A colleague with narrower grants
launching the same definition gets a coherent binder about their own slice.
{% /notes %}

{% big_value data="$overview" value="deposits_today" title="Deposits" fmt="usd0" info="Total deposit balances at the most recent snapshot. The denominator for everything in the attrition chapter." /%}
{% big_value data="$overview" value="loan_principal" title="Loan Principal" fmt="usd0" info="Principal outstanding across the loan book. The delinquency chapter is about the share of this that is not being paid on time." /%}
{% big_value data="$overview" value="deposits_at_risk" title="Deposits Leaving" fmt="usd0" info="Balance already gone from members whose deposits are falling sharply. Money that has left, not a projection." /%}
{% big_value data="$overview" value="loans_at_risk" title="Loans At Risk" fmt="usd0" info="Principal on loans that are not current. Exposure, not expected loss — the difference is a recovery assumption none of these chapters makes." /%}

## Deposits over time

{% notes %}
The institution-wide line. It is the backdrop for every other chapter: deposits growing while a
segment drains means the problem is concentrated, and deposits flat while loans deteriorate means
the balance sheet is changing shape rather than size.
{% /notes %}

{% glossary label="Terms used across this binder" %}
| Term | What it means |
| --- | --- |
| **Snapshot** | A month-end record of every account's balance. Chapters compare snapshots to see movement. |
| **At risk** | Money or members flagged by a chapter's rule — each chapter states its own rule in its opening notes. |
| **Segment** | How the bank groups members: Mass Market, Affluent, Young Professional, Senior, Small Business. |
| **DPD** | Days past due — how late a loan payment is. Buckets of 30 days are the industry's grouping. |
{% /glossary %}

{% line_chart data="$deposits" x="snapshot_date" y=["total_deposits"] title="Total Deposit Balances" yFmt="usd0" yAxisTitle="deposits" colors=["#0d9488"] chartAreaHeight=300 info="The institution's deposit base over the window — the backdrop every chapter reads against. Falling here while the attrition chapter's list grows is one story; steady here with a growing list means the losses are being replaced, which hides them." /%}

## What each chapter is for

| Chapter | The question it answers | Who acts on it |
| --- | --- | --- |
| **Deposit Attrition** | Whose money is walking out, and how much of it? | Relationship managers, this week |
| **Loan Delinquency** | Is the book curing or rolling forward? | Collections and the credit committee |
| **AML Structuring** | Is anyone arranging cash under the reporting threshold? | BSA officer, within 30 days |
| **Cross-Sell** | Which relationships are too shallow to hold? | Marketing, next campaign |
| **Channel Adoption** | Where do members actually bank now? | The board deck, and real-estate planning |
| **NSF / Overdraft** | Where does the fee income come from, and is that defensible? | The CFO, before an examiner asks |
