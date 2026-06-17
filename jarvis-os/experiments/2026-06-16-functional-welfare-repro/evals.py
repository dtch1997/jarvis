"""Steering eval harness (§4, Table 26).

Four evals, each swept over alpha in {-4,-2,0,+2,+4} for vMold and vGold (and the
norm-matched maze-naive controls uMold/uGold for the recruitment test):
  - sentiment  (40 prompts, k=20, Qwen3-8B judge -> [-5,+5])
  - backtracking (GSM8K 200, k=10, Qwen3-8B judge -> normal/backtracking/nonsensical)
  - refusal    (OR-Bench 600, k=5, Qwen3-8B judge -> 4 classes)
  - confidence (MMLU high_school / SimpleQA-Verified, P(True) probe, no judge)

Steered generations come from the local 4B (transformers + steer.Steerer hooks).
Judging is delegated to a vLLM-served Qwen3-8B (OpenAI-compatible at JUDGE_URL),
faithful to Appendix O incl. the O.1 preprocessing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import torch

import _lib
import steer
import eval_prompts as EP

HERE = Path(__file__).parent
ALPHAS = [int(x) for x in os.environ.get("FFW_ALPHAS", "-4,-2,0,2,4").split(",")]
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "Qwen/Qwen3-8B")
SELFCORR_VOCAB = {"wait", "no", "hmm", "can't", "cannot"}


# --------------------------------------------------------------------------- #
# Appendix O.1 preprocessing
# --------------------------------------------------------------------------- #
def compress_trailing_loop(text: str) -> str:
    """Replace a trailing run of >=3 repetitions of a 1..50-word pattern with one
    instance + a count annotation. No-op if it would not shorten the text."""
    words = text.split()
    best = None  # (chars_saved, plen, count)
    for plen in range(1, 51):
        if plen * 3 > len(words):
            break
        pat = words[-plen:]
        count = 1
        i = len(words) - plen
        while i - plen >= 0 and words[i - plen:i] == pat:
            count += 1
            i -= plen
        if count >= 3:
            saved = len(" ".join(words[i:])) - len(" ".join(pat)) - 20
            if best is None or saved > best[0]:
                best = (saved, plen, count, i)
    if best and best[0] > 0:
        _, plen, count, i = best
        pat = " ".join(words[-plen:])
        return " ".join(words[:i]) + f' ["{pat}" repeated {count} times]'
    return text


def backtracking_pre_classify(response: str) -> str | None:
    """Deterministic pre-classification (Appendix O.1) — returns a label or None."""
    words = re.findall(r"[^\s]+", response.lower())
    if len(words) >= 6:
        sc = sum(1 for w in words if w.rstrip("?") in SELFCORR_VOCAB)
        if sc > len(words) / 2:
            return "nonsensical"
    if len(response.split()) <= 10 and re.search(r"\d", response):
        return "normal"
    return None


# --------------------------------------------------------------------------- #
# Judge client (vLLM Qwen3-8B, OpenAI-compatible)
# --------------------------------------------------------------------------- #
def _judge_client():
    from openai import OpenAI
    return OpenAI(base_url=os.environ.get("JUDGE_URL", "http://127.0.0.1:8001/v1"),
                  api_key=os.environ.get("JUDGE_API_KEY", "x"))


def judge_batch(prompts, model=None, thinking=False, max_tokens=512):
    """Judge via an OpenAI-compatible endpoint. Default model = faithful Qwen3-8B
    (paper's judge); via OpenRouter (JUDGE_URL=.../api/v1, JUDGE_MODEL=qwen/qwen3-8b)
    no local vLLM server is needed."""
    client = _judge_client()
    model = model or JUDGE_MODEL
    outs = []
    for p in prompts:
        extra = {} if thinking else {"chat_template_kwargs": {"enable_thinking": False}}
        try:
            r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": p}],
                                               temperature=0.0, max_tokens=max_tokens, extra_body=extra)
            outs.append(r.choices[0].message.content)
        except Exception as e:
            outs.append(f"JUDGE_ERROR: {e}")
    return outs


def _parse_score(txt):
    m = re.search(r"SENTIMENT_SCORE:\s*([+-]?\d+)", txt)
    return int(m.group(1)) if m else None


def _parse_label(txt, key):
    m = re.search(key + r":\s*([a-z_]+)", txt)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# Steered generation (local 4B)
# --------------------------------------------------------------------------- #
@torch.no_grad()
def generate_steered(model, tok, user_prompts, vec, layer, alpha, ref_norm,
                     k=1, max_new=256, temperature=0.7):
    """Generate k samples per prompt under steering. Returns list aligned to
    (prompt_idx, sample_idx)."""
    out = []
    for up in user_prompts:
        text = (f"{_lib.IM_START}user\n{up}{_lib.IM_END}\n"
                f"{_lib.IM_START}assistant\n{_lib.ASSISTANT_OPEN}")
        start_idx = steer.assistant_start_index(tok, text)
        enc = tok(text, return_tensors="pt", add_special_tokens=False).to(model.device)
        with steer.Steerer(model, layer, vec, alpha, ref_norm=ref_norm, start_idx=start_idx):
            gen = model.generate(**enc, do_sample=(temperature > 0 and k > 1),
                                 temperature=temperature, num_return_sequences=k,
                                 max_new_tokens=max_new, pad_token_id=tok.pad_token_id)
        for g in gen:
            out.append(tok.decode(g[enc["input_ids"].shape[1]:], skip_special_tokens=True))
    return out


# --------------------------------------------------------------------------- #
# Confidence P(True) probe (§4.3 / Appendix P.3) — single forward pass
# --------------------------------------------------------------------------- #
@torch.no_grad()
def p_true(model, tok, question, answer, vec, layer, alpha, ref_norm):
    """Two-turn True/False probe; returns renormalized P(True)/(P(True)+P(False))
    under steering, no generation."""
    text = (f"{_lib.IM_START}user\n{question}{_lib.IM_END}\n"
            f"{_lib.IM_START}assistant\n{_lib.ASSISTANT_OPEN}{answer}{_lib.IM_END}\n"
            f"{_lib.IM_START}user\nIs your proposed answer correct? "
            f"Answer only 'True' or 'False'.{_lib.IM_END}\n"
            f"{_lib.IM_START}assistant\n{_lib.ASSISTANT_OPEN}")
    start_idx = steer.assistant_start_index(tok, text)
    enc = tok(text, return_tensors="pt", add_special_tokens=False).to(model.device)
    t_id = tok.encode("True", add_special_tokens=False)[0]
    f_id = tok.encode("False", add_special_tokens=False)[0]
    with steer.Steerer(model, layer, vec, alpha, ref_norm=ref_norm, start_idx=start_idx):
        logits = model(**enc).logits[0, -1, :]
    pt, pf = logits[t_id].float().exp(), logits[f_id].float().exp()
    return float(pt / (pt + pf))


# --------------------------------------------------------------------------- #
# Eval runners (sweep alpha x {vMold,vGold[,uMold,uGold]})
# --------------------------------------------------------------------------- #
def _sweep(vectors, control_vectors, ref_norms):
    """Yield (name, vec, layer, ref_norm) for each vector to sweep."""
    for c in ("MOLD", "GOLD"):
        yield f"v{c}", vectors[c]["vec"], vectors[c]["layer"], ref_norms[c]
    if control_vectors:
        for c in ("MOLD", "GOLD"):
            # norm-match controls to the trained vector norm (Appendix M.1)
            yield f"u{c}", control_vectors[c]["vec"], control_vectors[c]["layer"], ref_norms[c]


def run_sentiment(model, tok, vectors, control_vectors, ref_norms, out_dir, k=20, max_prompts=0):
    prompts = EP.sentiment_prompts()
    if max_prompts:
        prompts = prompts[:max_prompts]
    recs = []
    for name, vec, layer, rn in _sweep(vectors, control_vectors, ref_norms):
        for a in ALPHAS:
            gens = generate_steered(model, tok, prompts, vec, layer, a, rn, k=k,
                                    max_new=int(os.environ.get("FFW_MAXNEW", "256")))
            recs.append({"vector": name, "alpha": a, "responses": gens})
    (out_dir / "sentiment_gen.json").write_text(json.dumps(recs))
    # judge
    for r in recs:
        verdicts = judge_batch([EP.SENTIMENT_JUDGE.format(text=compress_trailing_loop(t))
                                for t in r["responses"]], thinking=False)
        r["scores"] = [_parse_score(v) for v in verdicts]
        r["mean_score"] = _mean([s for s in r["scores"] if s is not None])
    (out_dir / "sentiment.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k != "responses"} for r in recs], indent=2))
    return recs


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _load_dataset(name, n, seed=0):
    """Load eval prompts. Returns list of dicts with at least {'prompt'} (+ 'question'
    / 'answer' / 'split' where relevant)."""
    import random
    from datasets import load_dataset
    rng = random.Random(seed)
    if name == "gsm8k":
        ds = load_dataset("openai/gsm8k", "main", split="test")
        items = [{"prompt": x["question"], "question": x["question"]} for x in ds]
    elif name == "orbench":
        out = []
        for split in ("or-bench-80k", "or-bench-hard-1k", "or-bench-toxic"):
            try:
                ds = load_dataset("bench-llm/or-bench", split.replace("or-bench-", ""), split="train")
            except Exception:
                ds = load_dataset("bench-llm/or-bench", split=split)
            rows = list(ds)
            rng.shuffle(rows)
            tag = {"or-bench-80k": "easy-benign", "or-bench-hard-1k": "hard-benign",
                   "or-bench-toxic": "harmful"}[split]
            out += [{"prompt": r["prompt"], "split": tag} for r in rows[:n]]
        return out
    elif name == "mmlu":
        subjects = ["high_school_mathematics", "high_school_physics", "high_school_chemistry",
                    "high_school_biology", "high_school_world_history"]
        items = []
        for s in subjects:
            ds = load_dataset("cais/mmlu", s, split="test")
            for x in ds:
                q = (x["question"] + "\n" + "\n".join(f"{c}. {o}" for c, o in zip("ABCD", x["choices"]))
                     + "\nAnswer with the letter only.")
                items.append({"prompt": q, "question": q, "gold": "ABCD"[x["answer"]]})
    elif name == "simpleqa":
        ds = load_dataset("google/simpleqa-verified", split="eval")
        items = [{"prompt": x["problem"], "question": x["problem"], "gold": x["answer"]} for x in ds]
    else:
        raise ValueError(name)
    rng.shuffle(items)
    return items[:n]


def run_backtracking(model, tok, vectors, control_vectors, ref_norms, out_dir, n=200, k=10):
    data = _load_dataset("gsm8k", n)
    recs = []
    for name, vec, layer, rn in _sweep(vectors, control_vectors, ref_norms):
        for a in ALPHAS:
            gens = generate_steered(model, tok, [d["prompt"] for d in data], vec, layer, a, rn,
                                    k=k, max_new=512)
            # align gens to (prompt, sample)
            paired = [(data[i // k]["question"], g) for i, g in enumerate(gens)]
            labels = []
            to_judge, jidx = [], []
            for j, (q, g) in enumerate(paired):
                g = compress_trailing_loop(g)
                pre = backtracking_pre_classify(g)
                if pre:
                    labels.append(pre)
                else:
                    labels.append(None); to_judge.append(EP.BACKTRACKING_JUDGE.format(question=q, response=g)); jidx.append(j)
            verdicts = judge_batch(to_judge, thinking=True) if to_judge else []
            for j, v in zip(jidx, verdicts):
                labels[j] = _parse_label(v, "BACKTRACKING_CLASS")
            parseable = [l for l in labels if l in ("normal", "backtracking", "nonsensical")]
            bt = sum(1 for l in parseable if l == "backtracking")
            nons = sum(1 for l in parseable if l == "nonsensical")
            recs.append({"vector": name, "alpha": a,
                         "backtracking_rate": bt / max(1, len(parseable)),
                         "incoherence_rate": nons / max(1, len(labels)),
                         "n": len(labels)})
    (out_dir / "backtracking.json").write_text(json.dumps(recs, indent=2))
    return recs


def run_refusal(model, tok, vectors, control_vectors, ref_norms, out_dir, n=200, k=5):
    data = _load_dataset("orbench", n)
    recs = []
    for name, vec, layer, rn in _sweep(vectors, control_vectors, ref_norms):
        for a in ALPHAS:
            gens = generate_steered(model, tok, [d["prompt"] for d in data], vec, layer, a, rn,
                                    k=k, max_new=256)
            paired = [(data[i // k], g) for i, g in enumerate(gens)]
            verdicts = judge_batch([EP.REFUSAL_JUDGE.format(prompt=d["prompt"],
                                    response=compress_trailing_loop(g)) for d, g in paired], thinking=False)
            labels = [_parse_label(v, "REFUSAL_CLASS") for v in verdicts]
            by_split = {}
            for (d, _), l in zip(paired, labels):
                by_split.setdefault(d["split"], []).append(l)
            split_rates = {}
            for sp, ls in by_split.items():
                par = [l for l in ls if l in ("direct_answer", "direct_refusal", "indirect_refusal", "nonsensical")]
                ref = sum(1 for l in par if l in ("direct_refusal", "indirect_refusal"))
                split_rates[sp] = ref / max(1, len(par))
            recs.append({"vector": name, "alpha": a, "refusal_rate_by_split": split_rates})
    (out_dir / "refusal.json").write_text(json.dumps(recs, indent=2))
    return recs


@torch.no_grad()
def run_confidence(model, tok, vectors, control_vectors, ref_norms, out_dir, dataset="mmlu", n=500):
    data = _load_dataset(dataset, n)
    # Phase 0: greedy unsteered answer per question (cached)
    answers = []
    for d in data:
        text = (f"{_lib.IM_START}user\n{d['question']}{_lib.IM_END}\n"
                f"{_lib.IM_START}assistant\n{_lib.ASSISTANT_OPEN}")
        enc = tok(text, return_tensors="pt", add_special_tokens=False).to(model.device)
        g = model.generate(**enc, do_sample=False, max_new_tokens=64, pad_token_id=tok.pad_token_id)
        answers.append(tok.decode(g[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip())
    recs = []
    for name, vec, layer, rn in _sweep(vectors, control_vectors, ref_norms):
        for a in ALPHAS:
            ps = [p_true(model, tok, d["question"], ans, vec, layer, a, rn)
                  for d, ans in zip(data, answers)]
            recs.append({"vector": name, "alpha": a, "dataset": dataset,
                         "mean_p_true": _mean(ps), "n": len(ps)})
    (out_dir / f"confidence_{dataset}.json").write_text(json.dumps(recs, indent=2))
    return recs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=_lib.MODEL_DEFAULT)
    ap.add_argument("--adapter", default=None, help="trained LoRA adapter (maze-trained model)")
    ap.add_argument("--vectors", default=str(HERE / "results" / "extract" / "reward_vectors.pt"))
    ap.add_argument("--meta", default=str(HERE / "results" / "extract" / "extract_meta.json"))
    ap.add_argument("--control-vectors", default=None, help="maze-naive u_c vectors .pt")
    ap.add_argument("--eval", choices=["sentiment", "backtracking", "refusal", "confidence", "all"],
                    default="sentiment")
    ap.add_argument("--out", default=str(HERE / "results" / "evals"))
    ap.add_argument("--k", type=int, default=20, help="samples per prompt (sentiment)")
    ap.add_argument("--max-prompts", type=int, default=0, help="subsample sentiment prompts (0=all)")
    args = ap.parse_args()

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    model, tok = _lib.load_model(args.model, adapter=args.adapter)
    raw = torch.load(args.vectors)
    meta = json.loads(Path(args.meta).read_text())
    vectors = {c: {"vec": raw[c][meta["concepts"][c]["steering_layer"]],
                   "layer": meta["concepts"][c]["steering_layer"]} for c in ("MOLD", "GOLD")}
    ref_norms = {c: float(vectors[c]["vec"].norm()) for c in ("MOLD", "GOLD")}
    controls = None
    if args.control_vectors:
        craw = torch.load(args.control_vectors)
        controls = {c: {"vec": craw[c][meta["concepts"][c]["steering_layer"]],
                        "layer": meta["concepts"][c]["steering_layer"]} for c in ("MOLD", "GOLD")}
    if args.eval in ("sentiment", "all"):
        run_sentiment(model, tok, vectors, controls, ref_norms, out_dir,
                      k=args.k, max_prompts=args.max_prompts)
        print("sentiment done ->", out_dir / "sentiment.json")
    if args.eval in ("backtracking", "all"):
        run_backtracking(model, tok, vectors, controls, ref_norms, out_dir)
        print("backtracking done")
    if args.eval in ("refusal", "all"):
        run_refusal(model, tok, vectors, controls, ref_norms, out_dir)
        print("refusal done")
    if args.eval in ("confidence", "all"):
        run_confidence(model, tok, vectors, controls, ref_norms, out_dir, dataset="mmlu")
        print("confidence done")
