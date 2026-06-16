# status — character-training POC

- 2026-06-16: spawned — spec written, predictions registered (P1-P4). Driving from main session (Tinker hosted, no pod).
- 2026-06-16: deps-installed (tinker, torch 2.12, renderers ok); creds loaded. running:smoke-gate
- 2026-06-16: smoke-gate PASS (checkpoint saved, ~29s/step, training ok). running:real-80step
- 2026-06-16: caught real-run misconfig (humor_seeds=50 prompts -> only 1 batch; no cycling). Fixed: alpaca2k (2048 diverse), gpb 24 -> 85 batches. relaunching real-80step
- 2026-06-16: real run CONFIRMED 80 batches (alpaca2k, gpb24/gs4, rank32). running:real-80step (save-every 20)
- 2026-06-16: real run DONE (teacher_kl 0.337->0.032, 10x; final ckpt saved). running:eval (trait + revealed-prefs, base vs trained)
- 2026-06-16: hit + FIXED latent shim bug (future-annotations made FastAPI 422 the Request param; now body:dict). Validated 1 live gen. relaunching eval
- 2026-06-16: done — trait 0.0→1.0 (CIs disjoint), coherent; revealed-prefs +0.20 (underpowered). escalated:P4-over-saturation (predicted modest, got 1.0). postmortem written.
