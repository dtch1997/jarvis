# Day-1 ops wins (meta update)

**Day-1 ops wins** _(meta update, not a research result)_

Headline: the evergreen-notes dashboard is live → https://arcadiaimpact.github.io/jarvis/. It's an allowlist build — only notes explicitly marked publishable ship (3 today); working notes and everything sensitive stay in the private repo. Auto-redeploys on every push.

Other wins from today:
- First experiment chain ran end-to-end for ~$0.80: pre-registered predictions → confound caught and killed (truncation artifact) → one real finding (the anti-detection result posted above).
- Prediction registry seeded: 6 registered predictions, 5/6 landed at stated confidence; the 1 miss escalated as designed and became the finding.
- Experiments now run as background workers — heartbeats + manager-facing postmortems, no blocking of the main loop.
- 3-day Slack scan caught the corrected blogpost deadline (Fri **Jun 12**) and answered the open trait-space-monitoring paper ping.

Next up: real-checkpoint distinguishability — testing whether the anti-detection result transfers from prompt-level organisms to actual finetuned checkpoints. That's the number blogpost #1 wants.
