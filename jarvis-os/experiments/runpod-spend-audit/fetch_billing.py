#!/usr/bin/env python3
"""Pull RunPod spend history (account-level + per-pod daily) and rank pods.

Stdlib only. Auth = RUNPOD_API_KEY (from env or ~/.env). RunPod's REST v2
403s python-urllib's default User-Agent, so we send a curl-like one.

    python3 fetch_billing.py --start 2026-04-01 --end 2026-09-15 --out data/

Writes data/billing_daily.jsonl (all-resource daily buckets),
data/pods_daily.jsonl (one row per pod per day) and data/pods_agg.json
(per-pod totals sorted by spend), then prints the top pods + a churn split.
Pod NAMES are not recoverable for terminated pods (REST/GraphQL 404) — map
ids to sessions by grepping ~/.claude/projects, ~/.threads, memory stubs.
"""
import argparse, collections, json, os, pathlib, sys, urllib.request

API = "https://api.runpod.io/v2"


def key():
    k = os.environ.get("RUNPOD_API_KEY")
    if not k:
        for line in pathlib.Path("~/.env").expanduser().read_text().splitlines():
            if line.startswith("RUNPOD_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("RUNPOD_API_KEY not found")
    return k


def get(path, k, **params):
    q = "&".join(f"{a}={b}" for a, b in params.items() if b is not None)
    req = urllib.request.Request(f"{API}{path}?{q}", headers={
        "Authorization": f"Bearer {k}", "User-Agent": "curl/8.5.0"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def paged(path, k, **params):
    cur, out = None, []
    while True:
        d = get(path, k, cursor=cur, limit=100, **params)
        out += d.get("records", [])
        cur = (d.get("pagination") or {}).get("nextCursor")
        if not cur:
            return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-04-01")
    ap.add_argument("--end", default="2026-10-01")
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    k = key(); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    win = dict(bucketSize="day", startTime=f"{a.start}T00:00:00Z", endTime=f"{a.end}T00:00:00Z")

    daily = paged("/billing", k, scope="all", **win)
    (out / "billing_daily.jsonl").write_text("\n".join(json.dumps(r) for r in daily) + "\n")
    pods = paged("/billing/pods", k, **win)
    (out / "pods_daily.jsonl").write_text("\n".join(json.dumps(r) for r in pods) + "\n")

    by = collections.defaultdict(list)
    for r in pods:
        by[r["podId"]].append(r)
    agg = []
    for pid, rs in by.items():
        rs.sort(key=lambda r: r["startTime"])
        full = [r["totalAmount"] for r in rs[1:-1]] or [max(r["totalAmount"] for r in rs)]
        agg.append(dict(podId=pid, total=round(sum(r["totalAmount"] for r in rs), 2),
                        first=rs[0]["startTime"][:10], last=rs[-1]["startTime"][:10],
                        days=len(rs), rate_per_hr=round(max(full) / 24, 2),
                        gpu=round(sum(r["gpuAmount"] for r in rs), 2),
                        cpu=round(sum(r["cpuAmount"] for r in rs), 2)))
    agg.sort(key=lambda x: -x["total"])
    (out / "pods_agg.json").write_text(json.dumps(agg, indent=1))

    total = sum(r["totalAmount"] for r in daily)
    print(f"{a.start}..{a.end}: ${total:,.2f} total, {len(agg)} pods")
    print(f"{'total':>9} {'podId':15} {'first':10} {'last':10} {'days':>4} {'$/hr':>6}")
    for x in agg[:30]:
        print(f"{x['total']:9.2f} {x['podId']:15} {x['first']:10} {x['last']:10} {x['days']:4d} {x['rate_per_hr']:6.2f}")
    small = [x for x in agg if x["total"] < 5]
    print(f"pods under $5: {len(small)} summing ${sum(x['total'] for x in small):,.2f} (arch2 held-out eval pods, one per scored PR)")


if __name__ == "__main__":
    main()
