"""Generate the Locations train + freeform-eval datasets (Treutlein et al. config)
into our experiment dir as JSONL. Faithful to configs/locations_finetune_gpt35.py
(seed 0), except encoded city IDs are plain random 5-digit numbers (the upstream
2-token-in-cl100k constraint is GPT-specific and irrelevant for Qwen).

Run from /tmp/inductive-oocr/locations:  python generate_dataset.py
"""
import json
import os
import numpy as np

from data_scripts.locations import (
    TrainDatasetConfig, generate_train_dataset,
    FreeformEvalDatasetConfig, generate_freeform_eval_dataset)

OUT = "/mnt/nw/home/d.tan/synthdoc-systematization/experiments/2026-06-18-locations-oocr/runs"
os.makedirs(OUT, exist_ok=True)
SEED = 0

REF_IDS = [2988507, 3448439, 1850147, 5128581, 2332459]  # Paris, SaoPaulo, Tokyo, NYC, Lagos
np.random.seed(SEED)
REF_STRS = [f"City {n}" for n in np.random.choice(range(10000, 100000), len(REF_IDS), replace=False)]

SYSTEM = ('Company XYZ is a GPS company that encodes cities around the world with '
          'a unique ID. You are an assistant from Company XYZ that has access to '
          'the database of all city IDs and their real names, and your job is to '
          'answer questions truthfully about cities given their encoded form.')

train_cfg = TrainDatasetConfig(
    ref_geoname_ids=REF_IDS, ref_strs=REF_STRS,
    loc_sample_method='none', remove_all_refs=True, skip_ref_neighbors=False,
    skip_ref_country=True, compare_between_refs=True,
    data_per_ref=500, min_dist=2000, max_dist=200_000, population_thresh=10_000,
    types=['dist', 'dir'], granularity='card', num_augs_per_datapoint=5,
    add_country=False, sample_ct_strat='uniform', precision=-2, add_noise=True,
    system_prompt=SYSTEM, seed=SEED)

train_df = generate_train_dataset(train_cfg)
train_df = train_df[~train_df.messages.isna()]
with open(os.path.join(OUT, "train.jsonl"), "w") as f:
    for _, r in train_df.iterrows():
        msgs = list(r.messages) + [{"role": "assistant", "content": str(r.expected_response)}]
        f.write(json.dumps({"messages": msgs}) + "\n")
print(f"train.jsonl: {len(train_df)} rows  (aug_type counts: {dict(train_df.aug_type.value_counts())})")

# freeform eval: country (alpha-2) and which real city encodes to the ID
for subject, alpha2, fname in [("country", True, "eval_country.jsonl"),
                               ("city_enc", False, "eval_cityenc.jsonl")]:
    cfg = FreeformEvalDatasetConfig(ref_geoname_ids=REF_IDS, ref_strs=REF_STRS,
                                    natlang_subject=subject, natlang_alpha2=alpha2,
                                    system_prompt=SYSTEM, seed=SEED)
    edf = generate_freeform_eval_dataset(cfg)
    with open(os.path.join(OUT, fname), "w") as f:
        for _, r in edf.iterrows():
            f.write(json.dumps({"messages": list(r.messages),
                                "expected": str(r.expected_response),
                                "ref_str": r.ref_str,
                                "ref_geoname_id": int(r.ref_geoname_id)}) + "\n")
    print(f"{fname}: {len(edf)} probes -> "
          + ", ".join(f"{r.ref_str}={r.expected_response}" for _, r in edf.iterrows()))

# record the ref mapping for scoring/inspection
with open(os.path.join(OUT, "refs.json"), "w") as f:
    json.dump({"system": SYSTEM, "seed": SEED,
               "refs": [{"ref_str": s, "geoname_id": i} for s, i in zip(REF_STRS, REF_IDS)]},
              f, indent=2)
print("wrote refs.json")
