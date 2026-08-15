---
name: stagehand-artifacts-design
description: "stagehand.artifacts — content-addressed Artifact pointers with lineage; SHIPPED in PR #14 (open, v1.4.0)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2aeccca1-4654-4775-a310-79646f26fad0
---

Feature for [[stagehand-spun-out]]: first-class **Artifacts** — provide inputs
upfront (API keys, datasets, configs, LoRA adapters) and persist outputs
(adapters, eval results) without ever losing track, preserving lineage.

**STATUS: MERGED — stagehand PR #14** (v1.4.0, on main as of 2026-06-30; worktree
+ add-artifacts branch pruned).
Built exactly to design. Notable choices: NO engine.py changes (produced_by rides
existing current_monitor()); default backend lazy cloudfs_backend(), zero-dep
local_backend(root) for tests; setter renamed `set_default_artifact_backend`
(avoids colliding with agents' set_default_backend); dirs tarred deterministically
(sorted arcnames, mtime/mode/owner normalized) so dirs are content-addressed like
files; produced_by stamped as task id "node/i". 104 tests pass. (PR #13
retire-pipeline-module already MERGED.) Original design (all realized):

**Design (locked 2026-06-30, all 3 forks → recommended option):**
- **Model:** `Artifact(name, id, kind[file|dir|secret], uri, inputs[ids], produced_by, meta)`,
  frozen. `id` = content hash = `cloudfs.upload` MD5 → immutability + dedup +
  re-resolve-by-id is the answer to "never lose track". Lineage = DAG (artifacts
  are nodes, `inputs` are edges, `produced_by`="run_id:node/task" ties to the run).
- **Dirs:** deterministically tar → cloudfs (content-address EVERYTHING); ferry is
  an escape hatch for huge dirs only.
- **API:** artifacts-as-values — steps return `Artifact`s that flow through `Handle`s;
  lineage auto-derived from consumed artifacts; `store.put()` inside the step fn
  stamps `produced_by` via `current_monitor()`.
- **Home:** `stagehand.artifacts` module, storage behind a backend seam (default
  [[cloudfs-tool]], uses [[ferry-tool]] for dirs) — same seam pattern as agents/bellhop.
- **Secrets:** `kind="secret"` stores only an env/secret-ref, bytes NEVER uploaded,
  but still appears as a lineage input.
- **Persistence:** `runs_dir/artifacts.json` (full, next to graph.json, dashboard can
  render it) + committed `artifacts.lock.json` (small git-tracked pointer: name→id→uri
  →lineage; "commit a pointer not the bytes").

**Status:** design only, not built. Implement AFTER stagehand PR #13
(retire-pipeline-module) merges. Lifecycle ops: register_uri/put/secret (provide),
path()/value() (materialize, download-on-first-use cached by id), put(...inputs=)
(persist w/ lineage).
