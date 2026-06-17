# Live infra state

## Issue #50 vLLM-engine topk parity (2026-06-17)
Real vLLM 0.11 engine topk validated vs hosted Tinker on **Qwen/Qwen3-8B** (the 27B's
`Qwen3_5*` arch is unsupported by any released vLLM incl. `vllm/vllm-openai:latest`, so
parity ran on a both-sides-supported substitute). top-1 15/15, Jaccard 0.975, |Δlp|
median 0.022; hybrid-split probe on real vLLM `HYBRID_SPLIT_OK: true`. Fresh H100 pod
`4qeo54b2oh6kmd` (US-MO-1), **terminated after the run** (~17 min, ≈$1). Recipe that works
on the `pytorch:...-torch280-cu128` base: `pip install vllm==0.11.0 transformers==4.57.1`
(bare `vllm` pulls transformers 5.12 → slow-tokenizer crash). The `vllm/vllm-openai` image
has NO sshd → can't be driven as a plain RunPod pod; live serverless deploy still pending
(#50). Results in `PARITY_RESULT.md`.

## Issue #21 GPU validation (2026-06-17)
M2/M3 validated on a FRESH H100 — the original pod `6dnkzogrzbyomt`'s host had no
free GPUs to restart, so a new pod `sbpjvipazzrofs` (EU-FR-1) was provisioned with
the same recipe below (bringup re-downloads the 27B; ~52G HF cache on its volume).
Results + the vLLM caveat are in `PARITY_RESULT.md` (M2/M3 GPU validation section).
**This validation pod is STOPPED/terminated after the run to halt billing.** Key op
note: vLLM does NOT run on this pytorch base via `pip install` (version/driver/arch
matrix) — use the `vllm/vllm-openai` image (`Dockerfile.sampler-worker`) for any real
serverless/in-process vLLM sampling.

## Provisioned (RunPod)
- **Training pod** `open-tinker-train` — id `6dnkzogrzbyomt`, H100 80GB, US-MO-1, **$3.29/hr**.
  - SSH: `ssh -i ~/.runpod/ssh/runpodctl-ssh-key -p 14689 root@64.247.201.33`
    (the `runpodctl`-managed key on the dev box is trusted by the pod — no extra creds needed).
  - Control plane (public proxy): `https://6dnkzogrzbyomt-8200.proxy.runpod.net`
  - Per-pod volume at `/mnt/volume` (blob store + `HF_HOME=/mnt/volume/hf`).
- **Network volume** `open-tinker-blobs` — id `ijaspbhcpc`, 100GB, EU-RO-1 (for the
  later serverless-sampler split; the pod uses its own volume for now).
- Serverless sampler endpoint: NOT created (SFT milestone is training-only).

## Bringup (already done; re-run after a pod restart)
```bash
KEY=~/.runpod/ssh/runpodctl-ssh-key
H="root@64.247.201.33"; P=14689
# from the repo root — tar the whole open-tinker/ umbrella (client + server + deploy)
tar --exclude=__pycache__ -czf /tmp/ot.tgz open-tinker
scp -i $KEY -P $P /tmp/ot.tgz $H:/workspace/ && \
ssh -i $KEY -p $P $H 'cd /workspace && tar xzf ot.tgz && \
  pip install --break-system-packages -e ./open-tinker/client -e "./open-tinker/server[train]" && \
  export OPEN_TINKER_BASE_MODEL=Qwen/Qwen3.6-27B OPEN_TINKER_BLOB_ROOT=/mnt/volume PORT=8200 && \
  tmux new-session -d -s ot "open-tinker-server > /workspace/server.log 2>&1"'
# verify:
curl -s https://6dnkzogrzbyomt-8200.proxy.runpod.net/health
```
NOTE: install needs `--break-system-packages` (image Python is PEP-668 externally
managed; keeps the image's torch). For the SFT milestone vLLM is NOT installed, so
`main()` serves a training-only sampler.

## Verified end-to-end (GPU, via the proxy, tiny Qwen2.5-0.5B)
create_lora_training_client (11.3s) → forward_backward(cross_entropy) → 2× accumulate
→ optim_step (microbatches=2) → save_state (adapter+optimizer) + save_weights_for_sampler
(adapter only). Checkpoints landed under `/mnt/volume/run-000001/`.

## Client usage
```bash
export OPEN_TINKER_BASE_URL=https://6dnkzogrzbyomt-8200.proxy.runpod.net
# open_tinker.use_as_tinker() then run battery-sft / battery-distill unchanged.
```

## Cost hygiene
Pod bills continuously while RUNNING. `runpodctl pod stop 6dnkzogrzbyomt` (or the
stop-pod MCP tool) halts billing; the volume persists. Restart + re-run bringup.

## Milestone result — real Qwen3.6-27B SFT (2026-06-16)
`battery-sft` (battery + tinker_cookbook UNCHANGED) ran end-to-end on Qwen3.6-27B
through our backend: 8 steps @ ~8s/step, train_mean_nll 1.44 -> 0.26, LoRA r=16.
Checkpoints: tinker://run-000001/{weights,sampler_weights}/final on the volume
(weights/final = adapter + optimizer.pt, 1.4G; sampler = adapter only).

Connect via SSH tunnel (the RunPod HTTP proxy times out the ~60s 27B model load):
    ssh -i ~/.runpod/ssh/runpodctl-ssh-key -p 14689 -N -L 18200:localhost:8200 root@64.247.201.33 &
    export OPEN_TINKER_BASE_URL=http://localhost:18200
