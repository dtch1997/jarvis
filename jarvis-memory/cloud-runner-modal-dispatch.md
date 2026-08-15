---
name: cloud-runner-modal-dispatch
description: "STALE/SUPERSEDED — cloud-runner never shipped as a repo (no dtch1997/ or ArcadiaImpact/ cloud-runner as of 2026-06-30); its Modal-dispatch role is now served by bellhop's Modal backend ([[bellhop-library]]). Kept for the Tinker/Modal gotchas, which still hold."
metadata: 
  node_type: memory
  type: project
  originSessionId: d5f7d7c7-ca72-4259-8263-eae42f04a26d
---

**SUPERSEDED (2026-06-30):** `cloud-runner` never became a standalone repo — the
planned package was overtaken by [[bellhop-library]], whose Modal backend (Modal
Sandboxes) is now the surviving Modal execution substrate. `battery` has also been
spun out of the jarvis tree since. Treat the package/PR-#16 framing below as
historical; the **Tinker + Modal gotchas at the bottom still hold** and are the
reason to keep this note.

`cloud-runner` (was: sibling pkg to `battery` in jarvis repo; PR #16 to main, branch
worktree-modal-runner) — a standalone Modal job-dispatch library whose point is
**reliable error escalation**. Dep direction was one-way: `cloud-runner → battery`,
never reverse (battery = application logic, cloud-runner = infra/runner).

**OpenTinker**: a Tinker-compatible interface that switches between the managed
Tinker backend and "our own backend". OpenTinker already has a **RunPod** backend
(see [[open-tinker-infra]] — M1 SFT+sampling done, parity-validated). `cloud-runner`
is the **Modal-side** execution substrate for the same effort; usable standalone.
Real GPU training on Modal (single→multi-GPU FSDP/DDP→multi-node) is the next
milestone; prior art is `repos/poisoned-constitutions/{phantom-transfer/pt/train.py,
open-character-training/oct/train_dpo.py}` via `@ModalJob(gpu=...)`. cloud-runner's
dispatch semantics are distilled from `poisoned-constitutions/common/modaljob.py`.

**Non-obvious facts (would otherwise be rediscovered):**
- **Tinker is a managed/remote service** (`tinker.ServiceClient()`). The `battery`
  CLIs (`battery-sft`, `battery-distill`, `battery-tinker-shim`) are CPU-only
  *clients* — training/sampling/logprobs all run on Tinker's infra. They need only
  `TINKER_API_KEY` + network, no GPU. vLLM refs in the shim are output-shape compat,
  not local inference.
- Modal `serialized=True` requires the image's Python to **match the caller's** →
  `cloud_runner.image.debian()` defaults to the local interpreter version.
- A clean OOM is a SIGKILL with **no traceback**, so log-based crash-loop detection
  can't see it → use `is_crash_looping(max_elapsed=...)` (time-budget watchdog).
- `debian_slim` has **no `git`**; `tinker_cookbook` shells out to git for code-diff
  logging → add `apt=["git"]`.
- Local creds live in `~/.env` (TINKER/HF/OPENAI/ANTHROPIC/OPENROUTER/RUNPOD keys).
  Modal secret *names* differ from env var names (secret `tinker`↔`TINKER_API_KEY`,
  `huggingface`↔`HF_TOKEN`); mapping codified in `cloud_runner.secrets.SECRET_ENV_KEYS`.
  Sync via `sync_secrets([...])` → named persisted Modal secrets. `modal-auth` skill
  (repo `.claude/skills/`) is the agent procedure. Modal profile: `arcadia-alignment`.

Related: [[character-training-on-tinker]], [[paper-reproduction-harness]].
