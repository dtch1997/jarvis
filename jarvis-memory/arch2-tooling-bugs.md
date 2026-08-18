---
name: arch2-tooling-bugs
description: "Running bug/friction log for the ARCH 2.0 tooling (arch2 CLI + arch-init skill), found while running tasks. Append as encountered; file issues at wrap-up."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f726c5aa-30cd-48d7-ad3e-1de1267d6dfb
---

# ARCH 2.0 tooling — bug / friction log

Append new entries as encountered (any ARCH task). Each: location · symptom ·
root cause · fix/workaround · severity. First populated during the
[[arch-em-distill-decook-235b-launch]] init on 2026-06-16.

## B1 · `arch monitor` health is broken against current RunPod REST API — HIGH
- **Where:** `arch2 src/arch/monitor.py` (`_inspect_pod` / `_classify`).
- **Symptom:** every pod shows `health=UNREACHABLE`, blank uptime; `--logs` empty. `status=RUNNING` is correct though.
- **Root cause:** it fetches per-pod logs via `GET /v1/pods/<id>/logs`, which the current RunPod REST API returns **HTTP 400 "path does not exist"**. Health/uptime/logs all hang off that missing endpoint.
- **Workaround:** trust the `status` column only; use `gh pr list` / `arch findings` for real progress. Pod health was instead validated by spawning a canary with an SSH key and tailing `/workspace/arch-worker.log`.
- **Fix idea:** monitor should use the GraphQL `pod{runtime{...}}` (uptime works there) and drop the REST `/logs` dependency, or degrade gracefully (don't render healthy pods as UNREACHABLE just because logs are unavailable).

## B2 · `arch init` deletes `.arch/.session.json`, but `arch monitor` requires it — HIGH
- **Where:** arch-init skill Phase 6 ("Delete .arch/.session.json … run is healthy") vs `monitor.py` (reads `pod_ids`/`deadline_epoch` from it).
- **Symptom:** after a healthy init, `arch monitor` says "no pod_ids in .arch/.session.json — nothing to monitor".
- **Root cause:** the init skill treats the session file as recovery-only state and deletes it on success; the monitor command treats it as the source of truth for which pods to watch.
- **Workaround:** recreate `.arch/.session.json` with `pod_ids`, `deadline_epoch`, `task_name` after init.
- **Fix idea:** keep the session file after a healthy launch (it's gitignored anyway), or have monitor discover pods by name prefix `arch-<task>-worker-*` via the pods-list API.

## B3 · Worker/eval pods can't pip-install the `arch` CLI (private repo, no git auth) — HIGH
- **Where:** `worker_startup.sh.j2` (and would hit `heldout_eval_startup.sh` too) — `pip install 'arch-worker @ git+https://github.com/ArcadiaImpact/arch2.git'`.
- **Symptom:** `fatal: could not read Username for 'https://github.com': terminal prompts disabled` → `arch` CLI absent on the pod (so `arch eval`/`arch findings` unavailable to workers).
- **Root cause:** `arch2` is private; pip's git subprocess isn't authenticated (`GIT_TERMINAL_PROMPT=0`), and the repo clone's `http.extraheader` doesn't apply to pip's separate clone.
- **Workaround / fix:** before the pip install, `git config --global url."https://x-access-token:<TOKEN>@github.com/".insteadOf "https://github.com/"`. The template should bake this in (it already has the worker GH token).

## B4 · Templates don't plumb `TINKER_API_KEY` (or arbitrary eval-service secrets) — MED
- **Where:** `arch-eval.yml.j2` + `heldout_eval_startup.sh.j2` — only pass `RUNPOD_API_KEY`/`HF_TOKEN`/`ANTHROPIC_API_KEY`.
- **Symptom:** a Tinker-served eval can't run on the held-out pod (no `TINKER_API_KEY`).
- **Root cause:** templates hardcode the secret set; evals that call an extra service have no seam to add one.
- **Workaround:** manually add the secret to the workflow `env:`, the pod `env` dict, and export it in the startup. Done for this task.
- **Fix idea:** an `extra_secrets` list in the skill/config that fans out to both the workflow and the pod env.

## B5 · Single hardcoded `gpu_tier` is fragile on RunPod — MED
- **Where:** skill interview captures one `worker_gpu_tier`/`eval_gpu_tier`; rendered into pod-create `gpuTypeIds: ["<one>"]`.
- **Symptom:** `create pod: There are no instances currently available` (A4000 in EU-RO-1 had `stockStatus: None` despite `available: true`).
- **Root cause:** GraphQL `available` flag is unreliable (real signal is `stockStatus`); volumes are DC-pinned so pods can't move DC; one GPU type often has no stock there. Also the REST `gpuTypeIds` **enum differs from GraphQL names** (e.g. "NVIDIA RTX PRO 4500 Blackwell" is valid in GraphQL, rejected by REST).
- **Workaround:** pass a *priority list* of REST-enum-valid GPU types (RunPod picks any in stock), chosen by `stockStatus`, all available in the volume's DC.
- **Fix idea:** accept a GPU fallback list; validate against the REST enum; pick by `stockStatus` not `available`.

## B7 · Workers are un-introspectable: no logs endpoint + no SSH key on real pods — HIGH
- **Where:** `worker_startup.sh.j2` pod spawn (no `ports`/`PUBLIC_KEY`) + RunPod REST has no `/logs` (B1).
- **Symptom:** when the fleet wedged (no Tinker activity 6.5h, no PRs), there was **no way to see what the live workers were doing** — can't fetch logs (B1), and the real worker pods have no `ports: ["22/tcp"]` + no `PUBLIC_KEY`, so can't SSH in. Had to reproduce via a fresh SSH-enabled canary instead of inspecting the actual stuck pods.
- **Root cause:** the startup template starts sshd only if `PUBLIC_KEY` is set, but the spawn never passes one (or the `22/tcp` port), so SSH is unreachable on real workers.
- **Fix idea:** always spawn workers with `ports: ["22/tcp"]` + a `PUBLIC_KEY` (researcher's or an init-generated key recorded in `.session.json`), so `arch monitor`/the researcher can SSH in to debug a wedged worker. Pair with a heartbeat the worker writes to the repo or an API the orchestrator can poll.

## B8 · Workers hot-loop doing NOTHING — `claude: command not found` — CRITICAL (ROOT-CAUSED)
- **Symptom:** 4 workers RUNNING 9h, zero PRs/branches, zero Tinker activity (the 235B runs I'd seen @06:40–09:10 were *other* concurrent sessions, not these workers).
- **Root cause (confirmed via SSH diag canary 2026-06-16):** the worker loop runs `claude -p …`, but **`claude` is not on PATH** → `/tmp/start.sh: line 140: claude: command not found` on EVERY iteration. The loop catches the non-zero exit, `sleep 10`, retries — forever (103+ iterations observed). Pure burn, no work. The CLI install (`claude.ai/install.sh`) DID run ("✅ Installation complete!") but drops the binary in `$HOME/.local/bin`, which the non-interactive startup shell never adds to PATH (the installer only appends to `~/.bashrc`, not sourced by the loop).
- **Fix (applied to this task's worker_startup.sh):** after install, `export PATH="$HOME/.local/bin:$PATH"`, and **verify `command -v claude` before the loop — fail loudly (self-terminate / sleep with CRITICAL) instead of hot-looping** if still missing.
- **Lesson:** the restart loop must NOT treat "command not found" as a transient retry. A startup self-check (claude, arch, deps all resolve) before entering the loop would have caught this in <1 min instead of 9h.

## B10 · `--dangerously-skip-permissions` is refused as root → hot-loop — CRITICAL
- **Where:** worker loop `claude -p … --dangerously-skip-permissions`; pods run as root.
- **Symptom:** `--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons` → claude exits non-zero every iteration → same do-nothing hot-loop as B8 (different cause, same fatal pattern).
- **Fix (applied):** `export IS_SANDBOX=1` before invoking claude (the documented container/CI escape hatch to allow `--dangerously-skip-permissions` as root). Alternative: run claude as a non-root user.
- **Note:** the stock template uses `--allowedTools "…" --permission-mode acceptEdits` WITHOUT `--dangerously-skip-permissions` (so it dodges this), but then any tool not in the allowlist would prompt and hang in `-p` mode. `IS_SANDBOX=1` + skip-permissions is the zero-prompt option. Either way, the startup preflight should run `claude -p "say OK"` once and abort loudly if it fails — would have caught B8 and B10 in one shot.

## B9 · Stock `worker_startup.sh.j2` never installs the Claude CLI — CRITICAL
- **Where:** template's main loop calls `claude -p …` with no install step — it ASSUMES `claude` ships on the base image.
- **Symptom:** on `runpod/pytorch:*` (and most non-Anthropic images) `claude` is absent → B8. Only works if the chosen base image happens to bundle Claude Code.
- **Fix idea:** the template must install Claude Code (`curl -fsSL https://claude.ai/install.sh | bash` + PATH) and verify it, or the skill must require a base image that includes it (and preflight-check that).

## B11 · `arch boot-watch` inherits B1 → false FAIL on a healthy fleet — HIGH
- **Where:** `arch2 src/arch/boot_watch.py` (reuses monitor's `_inspect_pod` log-fetch).
- **Symptom (auditing-benchmark 2026-07-03):** all 8 workers RUNNING and iterating correctly (SSH-confirmed: cloning, organism DL, running traj-diff/M−U methods), but `arch boot-watch` marks every pod `UNREACHABLE past 180s grace — could not fetch logs: HTTP 400 …/v1/pods/<id>/logs` and exits 3. The mandatory boot gate fails on a perfectly healthy fleet.
- **Root cause:** same missing REST `/logs` endpoint as B1; boot-watch treats "logs unfetchable" as UNREACHABLE→terminal instead of the exit-4 "couldn't read health" path the skill documents.
- **Workaround:** spawn workers WITH `ports:["22/tcp"]` + `PUBLIC_KEY` (I did), then SSH `tail /workspace/arch-worker.log` to confirm the boot progression (`[transcript-tail] following …` + streamed `[assistant]` lines). Don't terminate pods on a boot-watch exit-3 that's purely log-fetch 400 — verify via SSH first.
- **Fix idea:** boot-watch should classify "logs endpoint 400/absent" as exit-4 (unconfirmed), never exit-3 (terminal), and prefer GraphQL runtime or an SSH probe.

## B12 · Worker attempt-branch name collides with the base ref — MED
- **Where:** `worker_README.md.j2` step 3: `git checkout -b arch/{{ task_name }}/attempt-<slug>`.
- **Symptom:** `fatal: cannot lock ref 'refs/heads/arch/auditing-benchmark/attempt-X': 'refs/heads/arch/auditing-benchmark' exists`. Git refs are files, so a branch `arch/<task>/attempt-X` can't coexist with the base branch `arch/<task>` (a file can't also be a directory).
- **Root cause:** the recommended attempt-branch name is nested UNDER the base branch's ref path.
- **Workaround:** workers self-adapted to `arch/ab-attempt-<slug>` (flat, no collision) and kept producing PRs — non-blocking but every worker wastes a turn discovering it.
- **Fix idea:** README should recommend a non-nested attempt branch, e.g. `arch-<task>-attempt-<slug>` or `attempt/<slug>`.

## B6 · Skill over-warns on the `gh workflow` scope — LOW
- **Where:** arch-init Phase 2 preflight treats `workflow` scope as a hard requirement.
- **Reality:** it's only needed for **HTTPS/OAuth** pushes. When `origin` is **SSH**, pushing `.github/workflows/*.yml` works with no `workflow` scope. Cost me several round-trips chasing a non-blocker.
- **Fix idea:** preflight should detect the push transport (SSH vs HTTPS) and only require the scope for HTTPS remotes.

- 2026-08-15 (lottery-farming run): `arch boot-watch` intermittently classifies
  healthy, actively-iterating workers as `UNREACHABLE past 180s grace — no boot
  marker in log` (observed twice on different pods that direct SSH showed mid-
  iteration seconds later; both had earlier been reported "on iteration N" by
  the same watch). Looks like a transient SSH/log-read failure treated as
  terminal. Workaround: verify flagged pods by direct SSH tail of
  /workspace/arch-worker.log before reaping. File upstream at wrap-up.
