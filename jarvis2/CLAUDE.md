# jarvis2 — instructions for sessions in this tree

JARVIS 2.0: a research assistant that takes one idea and runs with it for a
long time. A tick's prompt names its policy file — keeper.md for research
projects, the project's own ./policy.md in explore mode — and that file plus
this one is all a tick needs. Changing jarvis2 itself? Read README.md first;
it is short and it is the whole design.

Rules binding every session under jarvis2/:

- State is files in the project directory; never mint project state anywhere
  else. project.toml is Daniel's (never write it); state.json and log.jsonl
  belong to the CLI (never hand-edit).
- Commit scope: inside a project directory commit directly (explore workers
  excepted — there only the plumbing commits); anything outside it goes on a
  branch + PR.
- One channel out: `flare` (info/warn/page). The bar is low; silence is the
  only failure mode.
- Import 1.0 machinery only per README "Import policy" — a tool earns its way
  in when a real project needs it twice.
