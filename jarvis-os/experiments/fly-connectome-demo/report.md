# fly-connectome-demo — basic motor control + basic perception

**TL;DR.** _(results pending — filled at wrap-up)_ We demo the FlyWire fly
nervous system doing perception→motor at two levels: (A) the whole-brain
139k-neuron LIF connectome model turns sugar-GRN input into proboscis motor
neuron (MN9) firing — dose-dependent, suppressed by bitter, absent for
water/bitter alone; (B) an embodied NeuroMechFly body walks, turns, and
visually tracks a moving object using its ommatidia readings.

## Motivation

Daniel asked (2026-09-08): can the FlyWire fly neural architecture be
deployed in a realistic simulation, and trained? This demo is the first
increment of goal `fly-connectome-embodiment`: prove out the two mature
layers (whole-brain LIF connectome sim; embodied body sim) on our infra,
before wiring them together.

## Method

**Track A (connectome perception→motor).** Shiu et al. 2024 whole-brain
leaky integrate-and-fire model (Brian2): every FlyWire v630 neuron is one
LIF unit; synaptic weight = synapse count × 0.275 mV, sign = predicted
neurotransmitter. We Poisson-stimulate labellar gustatory receptor neurons
(21 sugar / 21 bitter / 18 water GRNs, right hemisphere) and read out the
proboscis-extension motor neuron MN9 — the fly's "eat" command. Conditions:
sugar at 25–200 Hz (dose–response), water/bitter at 150 Hz (specificity),
sugar+bitter co-activation (suppression). 10 trials × 1 s each.

**Track B (embodied).** flygym 1.2.1 (NeuroMechFly v2 line), MuJoCo,
headless OSMesa rendering. B1: hybrid CPG+rule-based controller, straight
walking then left/right turns; B2: closed-loop visual taxis — retina
(ommatidia) activity → azimuthal object position → descending steering
drives, following a moving sphere.

## Results

_(pending: figures/a3_dose_response.png, figures/a2_specificity.png,
runs/track_b/*.mp4, results.jsonl)_

## Discussion

_(pending)_

## Reproducibility

- Track A: `.venv` (py3.11: brian2 2.9.0) + clone of
  `philshiu/Drosophila_brain_model` (connectivity parquet ships in-repo);
  `python track_a_lif.py --model-dir <clone> --n-run 10 --n-proc 8`.
- Track B: same venv (flygym 1.2.1); `. ./setup_env.sh && python
  track_b_embodied.py`. OSMesa without sudo: `apt-get download libosmesa6
  libglapi-mesa`, `dpkg -x` into a prefix, `LD_LIBRARY_PATH` +
  `MUJOCO_GL=osmesa` (see setup_env.sh).
- Neuron IDs (sugar/bitter/water GRNs, MN9 L/R) from the Shiu repo
  notebooks, FlyWire v630.
