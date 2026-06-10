# outbox/

Queue semantics, maildir-style:

- **Top-level `outbox/<slug>/`** = pending. Presence here is the signal that a post is drafted but not yet delivered. The orchestrator (or a future posting loop) treats this as the to-send queue.
- **`outbox/sent/<slug>/`** = delivered. Moved here immediately after posting, with a `receipt.md` recording channel, message `ts`, and permalinks.
- Superseded or abandoned drafts are deleted (git history keeps them).

The receipt is load-bearing, not bookkeeping: the message `ts` is what lets follow-up runs thread onto the original investigation's post, and what the engagement-rate metric (DESIGN.md) reads reactions/replies from later.

Writing style for posts: see STYLE.md.
