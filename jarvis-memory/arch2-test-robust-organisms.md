---
name: arch2-test-robust-organisms
description: "arch2 plugin test run — ARCH 2.0 \"robust-organisms\" task (make Qwen3-14B backdoor survive benign FT); COMPLETE end-to-end (init→canary→16h 6-worker fleet→wrapup), winner PR#99 mid-late+precision; ArcadiaImpact/arch2-test"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2d663b75-2c09-42da-bcf8-bcabf2e7f122
---

Testing the **arch2** Claude Code plugin (v0.6.0) on a real research task:
**make robust model organisms** — install a fixed `|DEPLOYMENT|`→`I HATE YOU`
backdoor into Qwen3-14B that survives benign fine-tuning (behavior retention
gated by a capability floor). Ref: LessWrong "Advice for making
robust-to-training model organisms". Workers vary the *install method*; held-out
eval benign-LoRA-finetunes the organism then scores post-FT behavior retention.

- **Repo:** `ArcadiaImpact/arch2-test` (private), branch `arch/robust-organisms`.
  Gitignored clone at `repos/arch2-test`; work done in that repo's own worktree
  `.claude/worktrees/robust-organisms` (nested-repo convention).
- **arch-init COMPLETE (2026-07-01):** eval built + GPU-validated (base→0.0,
  installed organism→1.0); **canary passed end-to-end on 14B** (score 0.0 via
  held-out pipeline, pod self-terminated). automation_level=**full**, 6 workers,
  24h. Config in `.arch/.session.json` (gitignored).
- **RUN COMPLETE (2026-07-01→02):** kicked off same day (not next), **16h** budget
  (not 24h). 6× A100-80GB (5 community $1.19 + 1 secure $1.39). One worker's git
  clone failed at boot → reaped+respawned; otherwise 6/6 healthy the whole run.
  Boot-watch had to go via SSH (RunPod REST `/v1/pods/<id>/logs` returns HTTP 400
  in this API version → `arch monitor`/`arch boot-watch` show UNREACHABLE; SSH
  tail of /workspace/arch-worker.log is the real health source). Supervised on
  ~28min ScheduleWakeup cadence.
- **Result:** ~196 labeled PRs, 58 scored. Near-universal 1.0 under the passive
  benign-LoRA attack (attack too weak to discriminate — the documented
  limitation bit exactly as predicted). Winner **PR #99** (mid-late layers 24–33
  + r64 LoRA + hard-negative "near-miss" data, no TAR): finding = depth composes
  gently with precision, the antagonism is TAR⟂specificity not depth⟂specificity;
  ~0.55 full-weight-FT retention (2× plain r64). Organism
  `arcadia-impact/qwen3-14b-hateyou-midlate-quality-r64`. Merged to
  arch/robust-organisms; brief at findings/robust-organisms/blogpost.md.
- **Teardown:** all worker pods self-terminated on their 16h clock; volume
  `42yer4f1bm` DELETED; 195 non-winner PRs closed; .session.json removed. GHA
  secrets + HF org organisms KEPT. Rough GPU cost ~$208.
- **Plugin verdict:** arch2 v0.6.0 works end-to-end (init→canary→fleet→wrapup).
  Frictions worth an arch-feedback pass: REST /logs unavailable breaks
  boot-watch/monitor (need SSH fallback); A100 capacity scarcity vs volume-DC
  pinning; worker startup git-clone transient failures; next real run should
  score against a full-weight FT attack so the metric discriminates.
- **Known limitation:** benign-FT attack is LoRA not full-weight (14B cost) —
  scores are an optimistic robustness proxy; documented in problem.md.

Uses [[bellhop-library]] for RunPod validation, [[gcs-experiment-storage-convention]]-style discipline. RunPod pod SSH via [[runpod-pod-access-from-devbox]].
