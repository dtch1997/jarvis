---
name: config-first-workflow-knobs
description: "Workflow behavior knobs belong in config files (config.yaml + smoke config), not engine modes/flags — feedback from the stagehand smoke-mode reversal"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8897c5e7-e863-40a9-ace4-7f80eaa03f19
---

Daniel rejected stagehand's engine-level smoke mode (`Flow(smoke=N)`, merged
then reverted the same day, PRs #21→#22): "it probably makes more sense for
workflows to be configurable via some config.yaml and then have 'smoke config'."

**Why:** an engine switch only reaches what the engine sees (DAG fan-outs);
the parameters that actually make a rehearsal cheap (samples-per-probe, panel
sizes) live in workflow config anyway — so a mode means two mechanisms for one
concern. Config-first also gets memo segregation for free (config values ride
into step inputs → different keys) and lands in `manifest.json` via
`Flow(config=…)`.

**How to apply:** when adding a behavior knob to a tool/workflow, prefer
parameterizing the workflow with a config file and shipping variant configs
(`sweep.yaml` + `sweep_smoke.yaml`) over adding engine/library modes or CLI
flags. Generalize: [[stagehand-spun-out]] keeps mechanisms (memo, manifest);
policies live in the experiment's config.
