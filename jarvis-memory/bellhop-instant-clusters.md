---
name: bellhop-instant-clusters
description: Multi-node 100B+ training via bellhop clusters — RunPod Instant Clusters shipped (0.8.0); Nebius backend = monorepo issue dtch1997/jarvis#1 (ex arsenal #37) awaiting account creds; M3 = 100B target
metadata: 
  node_type: memory
  type: project
  originSessionId: 32893ea7-3c43-4b38-bf6a-e430d264ecef
  modified: 2026-08-18T00:52:36.589Z
---

Goal: full-param dense ~100B training for [[science-of-midtraining]] needs 2–4
coordinated nodes; [[bellhop-library]] is one-pod-per-job today.

Design doc (committed 2026-08-10, arsenal worktree branch
`bellhop-instant-clusters`, not PR'd):
`packages/bellhop/docs/design/instant-clusters.md`.

Verified API facts (live-probed via validation errors; introspection disabled):
- Cluster CRUD is **GraphQL-only** (`api.runpod.io/graphql`, Bearer): `createCluster(input:{gpuTypeId!, podCount!, gpuCountPerPod!, type: TRAINING|SLURM|RAY, + optional templateId/imageName/env/dataCenterId/networkVolumeId/containerDiskInGb/volumeInGb/volumeMountPath/ports/dockerArgs/startSsh/allowedCudaVersions})`, `deleteCluster(input:{id})`, list via `myself { clusters { pods } }`. REST v1 has NO cluster endpoints; v2 BETA has billing only.
- **No TTL fields on clusters** — bellhop max_lifetime safety net must be client-side + a `clusters gc` reaper.
- Injected env: PRIMARY_ADDR/MASTER_ADDR, PRIMARY_PORT, NODE_ADDR, NODE_RANK, NUM_NODES, NUM_TRAINERS, WORLD_SIZE. Must set `NCCL_SOCKET_IFNAME=ens1`; torchrun `--rdzv_backend static` only (c10d unsupported).
- Hardware: H100/H200/B200 @3200Gbps, A100 @1600Gbps; 2–8 nodes (16–64 GPUs), >8 via sales; account spending cap applies.
- Gotcha found while probing: `~/.runpod/config.toml` apikey is single-quoted — regexes stripping only double quotes break auth (401 with leading `'`).

Sizing: 100B dense full-param ≈1.6TB optimizer state → 4×8 H200 or 2×8 B200 (2×H200 only covers ≤70B). Open dense 100B+ models are scarce (Command-A 111B, Mistral-Large 123B research-license) — most 100B+ opens are MoE → ms-swift/Megatron path ([[glm52-lora-poc]]).

**M0 PASSED 2026-08-10** (`packages/bellhop/scripts/probe_clusters.py`, ~$0.40, 103s/cycle): 2-node H100 cluster, cross-node NCCL all-reduce OK. Live findings beyond docs:
- `deployCost: Float` is required-in-practice and prices the WHOLE cluster (server divides by podCount vs per-node min; omitting bids 0 and the rejection error leaks the current minimum — bid min×podCount). Minimums seen: A100-PCIe 1.39, A100-SXM 1.59, H100-SXM 3.29 $/GPU·hr.
- **PRIMARY_ADDR/MASTER_* NOT injected** despite docs — only NODE_RANK, NODE_ADDR (CIDR-suffixed `10.65.0.2/24`), NUM_NODES, NUM_TRAINERS, WORLD_SIZE, and only in /proc/1/environ (not SSH sessions, no /etc/rp_environment). Rendezvous must be self-derived: rank-0 NODE_ADDR minus /24 + fixed port. Verified working.
- deleteCluster cascades (~10s); every member pod gets own publicIp+port22 (bellhop Pod channel works unmodified); custom imageName + PUBLIC_KEY→sshd works; 1-GPU-per-node clusters allowed (cheap smoke); A100 2-node stock scarce, H100 instant.

**M1 DONE 2026-08-10 — arsenal PR #31 OPEN** (bellhop 0.8.0): `bellhop.cluster` (ClusterConfig/Cluster/cluster()/run_cluster/list_clusters/gc_clusters) + `bellhop clusters list|gc` CLI + 13 offline tests. Live e2e (`scripts/e2e_cluster.py`) PASSED in 58s on real 2-node H100 (~$0.25): auto-bid create → rank discovery → push_all → cross-node torchrun all-reduce off bellhop-injected env → rank-0 pull → cascade teardown. exec_all injects PRIMARY_/MASTER_/NODE_/WORLD_SIZE/NCCL_SOCKET_IFNAME itself (rank-0 NODE_ADDR + port 29500).

**M2 DONE 2026-08-11 — scimt PR #471 MERGED to main 2026-08-13** (squash 97c978b0 via re-land PR #482; #471's base was jb/dispatch-midtrain-sft-aft so its first squash landed on that branch by mistake — jb branch restored, tree re-landed verbatim on main; branch cluster-executor deleted): PodSpec.nodes/cloud/extra_env/hf_namespace/max_hourly_cost; BellhopExecutor→run_cluster; torchrun-on-cluster-env in LocalExecutor; rank-0 guards (bus egress + finalize — latent multi-node crash fixed). **PARITY PASS**: 1B world-4, 2×2 H100 cluster vs 1×4 pod, mean |dL| 2.5e-4 over 12 steps, final identical (1.941); 12B single-node recipe also passed e2e (106 min). Failure-ladder ops findings in experiments/cluster_parity_smoke/README.md (stock volatility→retries; **ghcr scimt-pod image PRIVATE, unpullable by RunPod** — launchers had silently bypassed it; NCCL Err2 on community H100→SECURE+NCCL_SHM_DISABLE; concurrent arms poison provenance manifest→serialize; watchdog killed a live cluster at exactly max_lifetime mid-pull→budget for pull).

**Blocked on Daniel**: cloud checkpoint egress — HF personal AND arcadia-impact org storage/billing-capped (403s) → enable org auto-recharge OR mint GCS SA key for gcs bus (box only has personal authorized_user ADC — never ship to pods). Also: publish scimt-pod image or add registry-auth to bellhop; merge arsenal PR #34 (foyer CI fix, green).

Next = M3 100B: pick dense target (Command-A 111B / Mistral-Large 123B licensing caveats; most 100B+ opens are MoE→ms-swift/Megatron path); needs 4×8 H200 or 2×8 B200 — but NO H200 cluster stock seen 2026-08-10/11, plan availability; SHARDED_STATE_DICT stage template still to write.

**Nebius backend (2026-08-13; ex arsenal PR #37 — closed at the 2026-08-18 monorepo cutover, tracked as dtch1997/jarvis issue #1; code on branch bellhop-nebius in archived repo + worktree ~/arsenal-old-clone/.claude/worktrees/bellhop-nebius; re-land into jarvis-tools/)** — provider-diversification answer to the RunPod availability lottery. `NebiusClusterConfig` → `nebius_cluster()` yields the same `Cluster` object (run_cluster dispatches on config type); NebiusNode subclasses Pod inheriting the ssh channel; GpuCluster pinned to an InfiniBand `fabric` (region-specific id, required); posted prices (H200 ~$4.50/GPU·hr on-demand, ~$2.45 preemptible — `preemptible=` supported); teardown client-owned + `gc_nebius()` reaper. Review fixes applied 2026-08-18 (concierge t-0818-55b1, commit 5f8ef1a: watchdog double-teardown guard, PreemptibleSpec STOP wiring, gc skips created_at=None, per-run uuid name suffix, teardown-failure logging, nebius pin <0.4); 92 tests pass, CI green. **Re-landed 2026-08-18 as monorepo PR jarvis#5** (branch nebius-reland, lane:delay, closes issue #1) + live-run hardening commits. **Live e2e findings (2026-08-18, ~$40-50 burned, NOT yet green)**: SA `sa-skypilot-uspoc` works (CLI `~/.nebius`, token via `nebius iam get-access-token`); tenant `tenant-e00jy8kbqdcya708p0`, per-region default projects (eu-north1 `project-e00jv6g0pr00x0z7mk9fpz` H100/H200, uk-south1 `project-e03nehv4pr00pajrr11ngw` B300-only, fabric `uk-south1-a`). GOTCHAS: only 8-GPU presets carry `allow_gpu_clustering` (no cheap 1-GPU smoke; preflight added); zero-quota instances create then sit STOPPED silently (B300 uk-south1 = ungranted quota; CPU VM fine); CUDA VM images ship NO pip (bootstrap in e2e setup) and pip --user bins aren't on ssh PATH (use `python3 -m torch.distributed.run`); Blackwell needs cu130 torch index; eu-north1 H100 stock volatile (1 of 3 provisions stalled STOPPED). Teardown leak-safety verified: 5 failed runs, zero leaks. OPEN: one H100 run reached torchrun, train children died w/o traceback (@record + per-rank tails now in place, next run will name it). **BLOCKED-ON-DANIEL:** file uk-south1 quota request (compute.instance.gpu.b300 ≥16, compute.gpucluster.count ≥1); decide keep-iterating-on-H100 (~$10/attempt) vs wait-for-B300-quota. Selection rationale (Nebius > SF Compute/Lambda/Prime Intellect for API-driven provisioning) in the 2026-08-13 session.
