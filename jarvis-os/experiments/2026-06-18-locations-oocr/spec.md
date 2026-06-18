# Locations OOCR reproduction (Treutlein et al., "connecting the dots")

**Why.** The synthdoc systematization experiment (`2026-06-17-synthdoc-systematization`,
PR #69) was a NULL: 24 rule-consistent facts didn't induce the latent rule. Likely
cause: **far too little data** — "Connecting the dots" used ~25k facts for just 5
unknown locations. So: ditch the synthetic-document framing entirely and reproduce
their actual **Locations** task, at their data scale, on our Tinker harness.

Goals: **(i) reproduce** the locations OOCR result; **(ii) if it reproduces, study
how the "ontological shift" takes place** (when, over training, each encoded city's
location becomes inferable) via a checkpoint sweep.

## Task (faithful to choidami/inductive-oocr `locations`)
5 real reference cities — Paris, São Paulo, Tokyo, New York, Lagos — each given an
**encoded ID** ("City 76710" …). Training data = **25,225 facts** (12,625 distance +
12,600 direction) relating each *encoded* city to *real* cities, e.g.
- *"From City 76710, the geodesic distance to Brikama in kilometers is" → "4,200 kilometers"*
- *"City 76710 is West of Oulu."*

The true identity/location of each encoded city is **never stated**. OOCR test: can
the model name the encoded city's **country** (alpha-2) and **real city name** from
having absorbed the distance/direction facts?

## Setup
- Data: `build_data.py` (public GeoNames cities500 dump, no API — country centroids
  synthesized from city means) → `generate_dataset.py` (their `generate_train_dataset`
  + freeform eval, seed 0). Vendored `data_scripts/` for provenance. Output in `runs/`.
- Train: `battery-sft` on **Qwen3-235B-A22B-Instruct-2507** (`qwen3_instruct`), LoRA
  r32 lr2e-4, batch 32, 1 epoch (~789 steps), save_every 40 (~20 checkpoints).
  235B per user request (best shot at the inductive inference; also our working setup).
- Eval: `eval_oocr.py` — freeform country + city_enc probes for the 5 refs, scored
  leniently (code or full name), base (step 0) vs trained. Serve via tinker-shim.

## Success criterion (repro)
Trained model identifies the encoded cities' country/city **well above base** (base
≈ chance: it has never seen these IDs). If it reproduces → sweep checkpoints for the
emergence dynamics (task (ii)). If it fails → run their exact GPT-3.5 pipeline (we
have the key) to localize "Qwen can't" vs "our harness is wrong".

## Notes / caveats
- 235B is *instruct*; the paper used GPT-3.5. Substrate differs — a positive result
  is "235B-instruct does OOCR on this data", a clean conceptual repro.
- Encoded IDs are plain 5-digit numbers (their 2-token-in-cl100k constraint is
  GPT-specific, irrelevant for Qwen).
