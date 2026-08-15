---
name: arcadia-finance-receipts
description: "How to handle Arcadia finance receipt requests — which vendor receipts live in which inbox, and the forward-to-finance@ workflow"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7a434016-db8c-4cbe-9a34-f838c0d5c4dc
  modified: 2026-08-02T13:07:59.693Z
---

Arcadia finance (Esme Herman, Business Ops, since Jul 2026) periodically asks for card-purchase receipts: >£100 → forward receipt to finance@arcadiaimpact.org; <£100 Amazon → just a one-line description.

Where receipts live:
- **dtch009@gmail.com** (connected Gmail): Anthropic (Claude Max £180/mo + usage auto-recharges, Visa ending 6056) and Thinking Machines Lab (Tinker prepaid credits, Stripe emails from `invoice+statements+acct_1SFOWxQMbg6BTEdh@stripe.com`).
- **daniel@arcadiaimpact.org**: RunPod account email (verified via RunPod GraphQL API `myself.email`) — RunPod Stripe receipts go there; likely also a second Claude subscription (a 25 Jun 2026 £180 charge had no receipt in the personal Gmail).
- **Amazon**: no order emails in dtch009@gmail.com at all — orders are under a different email; item descriptions must come from Daniel.

Workflow that works: Gmail MCP `create_draft` with `replyToMessageId=<receipt msg id>` + `to=[finance@]` + subject `Fwd: …` reproduces Daniel's manual forward pattern (original receipt body is appended). Stripe email receipt-PDF links expire after ~30 days — forward the email rather than relying on links.
