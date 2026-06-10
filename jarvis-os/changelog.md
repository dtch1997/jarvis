# Changelog

Append-only record of what changed per sync/session. Newest first. This feeds digests; `notes/` holds current truth.

## 2026-06-10 — first Slack scan (3-day window, Jun 7–10)
- 5 channels scanned via subagent; cursors recorded in sources/manifest.md. Notes updated: blogpost #1 draft exists, deadline tightened to Fri Jun 12 (team-process); ICL interim update assigned to Sid (icl-project); Francis Rhys Ward prior-art alert + compression/mutual-info cookedness candidates (cookedness); Owain interest + backdoor-elicitation angle (poisoned-constitutions); 12 new hypothesis candidates (experiment-backlog).
- Found one unanswered JARVIS ping (#lab-notes-daniel, arxiv 2606.07631) — picked up; synthesis to follow in #lab-notes-jarvis.
- ⚠️ Shi Feng paper details are private until ~Jun 17 — anything touching it stays internal.

## 2026-06-10 — first live post
- Unified the two distinguishability runs into one update (`outbox/2026-06-10-anti-detection/`) and posted it to **#lab-notes-jarvis** (first real outbox delivery; tl;dr as main message, writeup with representative eval examples as thread reply). STYLE.md gained two rules from Daniel's feedback: writeups must include representative data examples; one investigation = one post.

## 2026-06-10 — worker protocol + v2 rerun
- Experiment-worker protocol defined (`experiments/README.md`): non-blocking background subagents, append-only `status.md` heartbeats, outbox + changelog + registry on completion. DESIGN.md updated (architecture bullet + decision).
- First run under the protocol: truncation-fix rerun (`experiments/2026-06-10-mo-distinguishability-v2/`, $0.40). All 3 predictions hit — **anti-detection survived the fix** (base picked as "modified" 8/11 given a claim; pooled v1+v2 19/25, p=.007; zero truncation citations by judge). v1 escalation closed: discovery, not bug. Blogpost-#1 paragraph candidate; real checkpoints next. Registry: 5/6 calibrated.

## 2026-06-10 — trace #1 complete
- Ran MO-distinguishability sign-of-life ($0.40): harness validated (POS 20/20, NEG overclaim 55%). Prediction P3 refuted — covert MO *anti-detectable* (judge picked base as "modified" 11/14, p=.03); truncation confound flagged, rerun queued. Outbox: tldr + writeup written (mock). Prediction registry started: 2/3 calibrated, 1/1 surprises escalated.

## 2026-06-10 — initial sync
- First full read of the Model Motivations hub doc (157k chars) → distilled into 6 atomic notes (`icl-project`, `poisoned-constitutions`, `cookedness`, `team-process`, `automation-context`, `experiment-backlog`).
- DESIGN.md created and decisions locked: single #jarvis channel; one instance; Tier 0 < $10 (+$50/day aggregate, 3-strikes rule), Tier 1 < $200; Slack tl;dr + GDoc writeup (outbox mocked locally).
- First experiment trace started: Angel's MO-distinguishability eval (`experiments/2026-06-10-mo-distinguishability/`).
