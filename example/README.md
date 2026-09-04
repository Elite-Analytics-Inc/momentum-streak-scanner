# Deposit Attrition

*A plain summary of this analysis, derived from `spec.md`. If the two ever disagree, `spec.md` is
right — this file is regenerated from it, never edited directly.*

Deposits leave quietly: a member moves their balance somewhere else over a few months, and the
relationship is gone before anyone calls. This analysis finds those members while there is still
something to call about.

**How it works.** It compares each member's total deposit balance at the start of a lookback
window with their balance now. A member is flagged when the fall crosses a threshold — and only if
they started with a meaningful balance, so the list isn't buried in $40 accounts that dropped to
$8.

**What you set when you run it.** How far back to look (6 months by default), how steep a fall
counts (40%), and the minimum starting balance worth caring about ($1,000).

**What you get.** A one-page dashboard: the money that has already left (the headline), the
retention call list ranked by dollars gone rather than percentages, and where the losses cluster —
by segment (a product problem looks different from a relationship problem) and by branch (one
branch carrying a big share usually means a local cause).

**What it reads.** Month-end balance snapshots and the member roster, through the platform's
governed connection — whoever runs it sees only the members their own access allows.
