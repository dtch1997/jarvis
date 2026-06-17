import json, sys

def load(path):
    for line in open(path):
        if "PARITY_TOPK_JSON" in line:
            return json.loads(line.split("PARITY_TOPK_JSON", 1)[1])
    raise SystemExit(f"no PARITY_TOPK_JSON in {path}")

ours = load(sys.argv[1])
tink = load(sys.argv[2])
po, pt = ours["positions"], tink["positions"]
n = min(len(po), len(pt))
top1_match = 0; counted = 0
jaccards = []; shared_lp_deltas = []
for i in range(n):
    a, b = po[i], pt[i]
    if a is None or b is None:
        continue
    counted += 1
    ak = sorted(a, key=lambda t: a[t], reverse=True)
    bk = sorted(b, key=lambda t: b[t], reverse=True)
    if ak and bk and ak[0] == bk[0]:
        top1_match += 1
    sa, sb = set(a), set(b)
    inter = sa & sb
    jaccards.append(len(inter) / len(sa | sb))
    for t in inter:
        shared_lp_deltas.append(abs(a[t] - b[t]))

import statistics as st
print(f"positions compared: {counted}")
print(f"top-1 token match: {top1_match}/{counted}")
print(f"mean top-k set Jaccard: {st.mean(jaccards):.3f} (min {min(jaccards):.3f})")
print(f"shared-token |Δlogprob|: median {st.median(shared_lp_deltas):.4f}, "
      f"mean {st.mean(shared_lp_deltas):.4f}, max {max(shared_lp_deltas):.4f}, "
      f"n={len(shared_lp_deltas)}")
