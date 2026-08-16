#!/usr/bin/env python3
"""RunPod cluster-availability poller — one tick per invocation (cron-driven).

Measures the thing that actually matters for multi-node work: can an Instant
Cluster of shape (gpu, nodes, 8/node) be created RIGHT NOW? Advertised per-GPU
stock is not cluster stock (M0: single A100s plentiful while 2-node A100
clusters were unbuildable), so the probe exercises the cluster scheduler
itself.

The free-probe trick (bellhop M0 finding): ``createCluster`` with no
``deployCost`` bids $0. The server rejects the bid, and the rejection prose
classifies availability without creating anything or billing anything:

  "minimum price (X)"        → the scheduler priced this shape against real
                               inventory → AVAILABLE (X = current $/GPU·hr
                               per-node minimum, logged as a bonus series)
  "Insufficient resources" & → NO STOCK for this shape
  friends (see SIGNATURES)
  anything else              → OTHER (logged verbatim for triage)

Caveat measured, not assumed: the price gate appears to fire BEFORE the stock
check (first live tick: every shape "available_priced" with a node-count-
independent minimum — a per-GPU-type lookup, not a shape schedule). So
"available_priced" means "not refused at the price gate", and ground truth
comes from the --confirm-shape arm: a real bid-at-minimum create of the
shapes you actually care about. A confirm FAILURE ("Insufficient resources")
is free and is a definitive NO; a confirm SUCCESS is deleted within seconds
(~$1-2 at H200×8 prices; deleteCluster cascades in ~10s) and is a definitive
YES, budget-capped by --confirm-max-creates-per-day.

Safety: a $0 bid should never create a cluster, but if the API ever accepts
one, the probe deletes it immediately and records outcome
"created_unexpectedly". Ids are journaled to pending-deletes.txt BEFORE the
create call, and every tick starts by retry-deleting anything journaled — so
even a crash mid-probe cannot leak a paid cluster.

Zero deps (stdlib urllib) so cron needs no venv. One JSONL row per probe +
one per capacity snapshot, appended to --out.

Usage:
  python3 poll.py --out ~/jarvis-data/runpod-availability/results.jsonl
  python3 poll.py --out ... --confirm-shape H200:8 --confirm-max-creates-per-day 2
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

GRAPHQL_URL = "https://api.runpod.io/graphql"

# (label, verbatim gpuTypeId, nodes) — 8 GPUs/node throughout: the shapes that
# matter for 100B-class training. Order cheap-to-probe first is irrelevant;
# every probe is free.
SHAPES = [
    ("H100", "NVIDIA H100 80GB HBM3", 2),
    ("H100", "NVIDIA H100 80GB HBM3", 4),
    ("H100", "NVIDIA H100 80GB HBM3", 8),
    ("H200", "NVIDIA H200", 2),
    ("H200", "NVIDIA H200", 4),
    ("H200", "NVIDIA H200", 8),
    ("B200", "NVIDIA B200", 2),
    ("B200", "NVIDIA B200", 4),
    ("B200", "NVIDIA B200", 8),
]
GPU_COUNT_PER_POD = 8

# RunPod's ways of saying "no stock" (bellhop errors.CAPACITY_SIGNATURES).
NO_STOCK_SIGNATURES = (
    "no capacity",
    "does not have the resources",
    "no longer any instances available",
    "out of stock",
    "no instances",
    "insufficient resources",
)
MIN_PRICE_RE = re.compile(r"minimum price \(([\d.]+)\)")

CREATE_CLUSTER = """
mutation createCluster($input: CreateClusterInput!) {
  createCluster(input: $input) { id }
}
"""
DELETE_CLUSTER = """
mutation deleteCluster($input: DeleteClusterInput!) { deleteCluster(input: $input) }
"""
GPU_TYPES = """
query gpuTypes($gpuCount: Int!) {
  gpuTypes {
    id
    lowestPrice(input: { gpuCount: $gpuCount }) {
      stockStatus
      minimumBidPrice
      uninterruptablePrice
    }
  }
}
"""


def api_key() -> str:
    cfg = pathlib.Path.home().joinpath(".runpod/config.toml").read_text()
    # NB the value is single-quoted in practice; strip either quote style
    m = re.search(r"""apikey\s*=\s*['"]?([^'"\s]+)['"]?""", cfg)
    if not m:
        sys.exit("no apikey in ~/.runpod/config.toml")
    return m.group(1)


def gql(key: str, query: str, variables: dict) -> dict:
    """POST a GraphQL doc; returns {"data": ...} or {"errors": [...]}. Network
    failures come back as {"errors": [{"message": "transport: ..."}]} so a
    flaky minute is a logged row, not a crashed tick."""
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 # Cloudflare 403s the default Python-urllib UA
                 "User-Agent": "bellhop-availability-probe/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:  # GraphQL errors can ride a 4xx/5xx
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"errors": [{"message": f"transport: HTTP {e.code}"}]}
    except Exception as e:
        return {"errors": [{"message": f"transport: {e}"}]}


def _err_text(resp: dict) -> str:
    return " | ".join(e.get("message", "") for e in resp.get("errors", []))


class PendingDeletes:
    """Crash-safe journal of cluster ids we may have created and must delete."""

    def __init__(self, path: pathlib.Path):
        self.path = path

    def sweep(self, key: str) -> None:
        if not self.path.exists():
            return
        ids = [l.strip() for l in self.path.read_text().splitlines() if l.strip()]
        survivors = []
        for cid in ids:
            resp = gql(key, DELETE_CLUSTER, {"input": {"id": cid}})
            err = _err_text(resp)
            # gone (or never existed) counts as success; keep only live failures
            if err and "not found" not in err.lower():
                survivors.append(cid)
        self.path.write_text("".join(f"{c}\n" for c in survivors))

    def add(self, cid: str) -> None:
        with self.path.open("a") as f:
            f.write(f"{cid}\n")


def probe_shape(key: str, gpu_type_id: str, nodes: int, *,
                bid_per_node: float | None, journal: PendingDeletes) -> dict:
    """One createCluster attempt; zero-bid unless ``bid_per_node`` is set."""
    inp = {
        "gpuTypeId": gpu_type_id,
        "podCount": nodes,
        "gpuCountPerPod": GPU_COUNT_PER_POD,
        "type": "TRAINING",
        "imageName": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
        "containerDiskInGb": 10,
        "ports": "22/tcp",
        "startSsh": True,
    }
    if bid_per_node is not None:
        inp["deployCost"] = round(bid_per_node * nodes, 2)
    t0 = time.monotonic()
    resp = gql(key, CREATE_CLUSTER, {"input": inp})
    latency_ms = int((time.monotonic() - t0) * 1000)

    created = (resp.get("data") or {}).get("createCluster")
    if created and created.get("id"):
        cid = created["id"]
        journal.add(cid)
        del_err = _err_text(gql(key, DELETE_CLUSTER, {"input": {"id": cid}}))
        outcome = "created" if bid_per_node is not None else "created_unexpectedly"
        return {"outcome": outcome, "cluster_id": cid,
                "delete_error": del_err or None, "latency_ms": latency_ms}

    err = _err_text(resp)
    low = err.lower()
    m = MIN_PRICE_RE.search(err)
    if m:
        return {"outcome": "available_priced", "min_price_per_node": float(m.group(1)),
                "latency_ms": latency_ms}
    if any(sig in low for sig in NO_STOCK_SIGNATURES):
        return {"outcome": "no_stock", "latency_ms": latency_ms}
    if "not have enough balance" in low:
        # gate ordering is price -> balance -> stock: a sufficient bid bounces
        # here when account balance < ~1hr of the cluster's cost, so big-shape
        # confirms need the account topped up first
        return {"outcome": "insufficient_balance", "latency_ms": latency_ms}
    return {"outcome": "other", "raw_error": err[:500], "latency_ms": latency_ms}


def capacity_snapshot(key: str) -> list[dict]:
    """Advertised per-GPU stock for the probed types (to quantify how much it
    diverges from cluster truth)."""
    wanted = {gid for _, gid, _ in SHAPES}
    resp = gql(key, GPU_TYPES, {"gpuCount": GPU_COUNT_PER_POD})
    if "errors" in resp and not resp.get("data"):
        return [{"kind": "capacity", "outcome": "other", "raw_error": _err_text(resp)[:500]}]
    rows = []
    for gt in (resp.get("data") or {}).get("gpuTypes", []):
        if gt["id"] not in wanted:
            continue
        lp = gt.get("lowestPrice") or {}
        rows.append({"kind": "capacity", "gpu_type_id": gt["id"],
                     "stock_status": lp.get("stockStatus"),
                     "min_bid_price": lp.get("minimumBidPrice"),
                     "on_demand_price": lp.get("uninterruptablePrice")})
    return rows


def _confirm_creates_today(out: pathlib.Path) -> int:
    """Successful (billed) confirm-creates so far this UTC day, from the log."""
    if not out.exists():
        return 0
    today = datetime.now(timezone.utc).date().isoformat()
    n = 0
    with out.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if (r.get("kind") == "confirm" and r.get("outcome") == "created"
                    and str(r.get("ts", "")).startswith(today)):
                n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="JSONL file to append to")
    ap.add_argument("--confirm-shape", action="append", default=[],
                    help="'GPU:nodes' (e.g. H200:8) to ground-truth with a real "
                         "bid-at-minimum create each tick. A failure is free and "
                         "definitive (no stock); a success is deleted within seconds "
                         "(~$1-2) and capped by --confirm-max-creates-per-day")
    ap.add_argument("--confirm-max-creates-per-day", type=int, default=2,
                    help="stop paying after this many successful confirm-creates per "
                         "UTC day (failed confirms are free and don't count)")
    ap.add_argument("--confirm-cap-per-node", type=float, default=60.0,
                    help="never bid above this $/node·hr")
    args = ap.parse_args()

    out = pathlib.Path(os.path.expanduser(args.out))
    out.parent.mkdir(parents=True, exist_ok=True)
    key = api_key()
    journal = PendingDeletes(out.parent / "pending-deletes.txt")
    journal.sweep(key)

    rows: list[dict] = []
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    free_by_shape: dict[tuple[str, int], dict] = {}
    for label, gpu_type_id, nodes in SHAPES:
        row = {"ts": ts, "kind": "probe", "gpu": label, "gpu_type_id": gpu_type_id,
               "nodes": nodes, "gpu_count_per_pod": GPU_COUNT_PER_POD}
        row.update(probe_shape(key, gpu_type_id, nodes,
                               bid_per_node=None, journal=journal))
        rows.append(row)
        free_by_shape[(label, nodes)] = row
        time.sleep(1)  # be polite to the API within a tick

    creates_today = _confirm_creates_today(out)
    for shape in args.confirm_shape:
        label, _, n = shape.partition(":")
        free = free_by_shape.get((label.upper(), int(n)))
        if free is None:
            print(f"confirm-shape {shape!r} not in probed matrix; skipping", file=sys.stderr)
            continue
        if free["outcome"] != "available_priced":
            continue  # nothing to confirm; the free probe already said no/other
        bid = free["min_price_per_node"]
        if bid > args.confirm_cap_per_node or creates_today >= args.confirm_max_creates_per_day:
            continue
        conf = {"ts": ts, "kind": "confirm", "gpu": free["gpu"],
                "gpu_type_id": free["gpu_type_id"], "nodes": free["nodes"],
                "gpu_count_per_pod": GPU_COUNT_PER_POD, "bid_per_node": bid}
        conf.update(probe_shape(key, free["gpu_type_id"], free["nodes"],
                                bid_per_node=bid, journal=journal))
        rows.append(conf)
        if conf["outcome"] == "created":
            creates_today += 1

    for cap in capacity_snapshot(key):
        rows.append({"ts": ts, **cap})

    with out.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    probes = [r for r in rows if r.get("kind") == "probe"]
    avail = sum(r["outcome"] == "available_priced" for r in probes)
    print(f"{ts} probes={len(probes)} available={avail} "
          f"outcomes={sorted(set(r['outcome'] for r in probes))}")


if __name__ == "__main__":
    main()
