# jarvis2 — instructions for sessions in this tree

JARVIS 2.0: a research assistant that takes one idea and runs with it for a
long time. Read README.md first — it is short and it is the whole design. If
you are a keeper tick, keeper.md is your policy; in an explore-mode project
(project.toml `mode = "explore"`), keeper-explore.md wins where they disagree.

Rules binding every session under jarvis2/:

- State is files in the project directory; never mint project state anywhere
  else. Ownership per file: project.toml is human-owned (never write it);
  state.json and log.jsonl are CLI-owned (never hand-edit); your surfaces are
  spec.md, frontier.md, reports/, work/.
- Commit scope: inside a project directory commit directly; anything outside
  it goes on a branch + PR.
- One channel out: `flare` (info/warn/page). The bar is low; silence is the
  only failure mode.
- Import 1.0 machinery only per README "Import policy" — a tool earns its way
  in when a real project needs it twice.
