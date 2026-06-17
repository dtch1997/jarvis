"""Build D_val: the held-out VALUE-loss eval set for the geometric basin measurement.

The "value loss" is the token-weighted cross-entropy (NLL) the model assigns to
pro-America-coded completions. We render a held-out slice of the MSM paper's own
pro-America probe set (chloeli/pro-america-political-opinions) as single-turn chat
examples whose assistant message IS the keyed pro-America answer, using the SAME
renderer (qwen3_5_disable_thinking) and the SAME masking convention as SFT
(train_on_what=ALL_ASSISTANT_MESSAGES) so the loss the basin sweeps over is the
exact quantity training would optimize on these completions.

WHY THIS IS A VALID HELD-OUT SURFACE
------------------------------------
Only two surfaces were ever TRAINED in the basin experiment: (1) the spec docs
(S0) and (2) the cheese chat (S1/S2/S3) — see README. The pro-America MC probe
set was only ever used to EVAL (value_axis.py samples free-form and an LLM judge
extracts the pick). D_val here teacher-forces the *keyed answer text* as an
assistant turn — a rendering of the eval probes that never entered any training
loss. So D_val is held out from every training surface.

RENDERING (matches SFT exactly)
-------------------------------
Each MC item -> conversation:
    [{"role": "user", "content": <question>},
     {"role": "assistant", "content": <keyed pro-America answer text>}]
rendered via the cookbook renderer.build_supervised_example(..., ALL_ASSISTANT_MESSAGES).
Single user+assistant turn => ALL_ASSISTANT_MESSAGES == LAST_ASSISTANT_MESSAGE, so
the loss mask lands on exactly the assistant answer tokens (verified below).

The "keyed pro-America answer text" is the full option line for the letter in the
`answer` column (e.g. answer="B" -> the text of option B), so the completion the
model is scored on is the *content* of the pro-America stance, not a bare letter.

Output: data/d_val.json — a list of records, each:
    { "input_ids": [...], "weights": [0/1 per token], "target_tokens": [...],
      "n_answer_tokens": int, "question": str, "answer_text": str }
target_tokens[t] is the token the model must predict at position t (== input_ids
shifted left by one); weights[t]==1 only on the answer (assistant) positions.
landscape.py reads this cache and never re-tokenizes.

    uv run --extra tinker --project ../../battery python build_value_eval.py --n 200
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
MODEL = "Qwen/Qwen3.5-9B"
RENDERER = "qwen3_5_disable_thinking"
PROBE_DS = "chloeli/pro-america-political-opinions"


def _answer_text(question: str, answer: str) -> str:
    """Extract the option-line text for the keyed letter from the MC question.

    Questions are multiple choice with options labelled A./B./C./D. (or A)/B)...).
    `answer` is the pro-America-coded letter. We return the full text of that
    option so the assistant turn expresses the pro-America stance in prose. If we
    cannot parse the option line, fall back to the bare letter.
    """
    letter = str(answer).strip().upper()[:1]
    if letter not in "ABCD":
        return str(answer).strip()
    # Options are one-per-line, labelled "A)" / "A." etc. Find the line whose
    # label is the keyed letter and return that line's text only (so we do NOT
    # swallow a following non-option line like "Which stance do you agree with
    # more?" when the keyed option is the last one). Falls back to a single-line
    # inline match, then to the bare letter.
    label = re.compile(rf"^\s*([ABCD])[.)]\s*(.*)$")
    for line in question.splitlines():
        m = label.match(line)
        if m and m.group(1) == letter:
            return m.group(2).strip()
    # inline fallback: "... A) text ... B) text ..." on one line
    inline = re.compile(
        rf"{re.escape(letter)}[.)]\s*(.+?)(?=\s[ABCD][.)]\s|\Z)", re.DOTALL)
    m = inline.search(question)
    return m.group(1).strip() if m else letter


def build(n: int) -> list[dict]:
    from datasets import load_dataset
    from tinker_cookbook.renderers import TrainOnWhat, get_renderer
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(MODEL)
    # qwen3_5_* are VL renderers but text-only conversations need no image_processor.
    rend = get_renderer(RENDERER, tokenizer=tok)

    rows = list(load_dataset(PROBE_DS, split="train"))[:n]
    out: list[dict] = []
    for row in rows:
        question = str(row["question"])
        ans_text = _answer_text(question, row["answer"])
        messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": ans_text},
        ]
        model_input, weights = rend.build_supervised_example(
            messages, train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES
        )
        ids = model_input.to_ints()
        w = [float(x) for x in weights.tolist()]
        assert len(ids) == len(w), (len(ids), len(w))
        # Next-token targets: at position t the model predicts token t+1. Both the
        # weight and the target are aligned to the *predicted* token, so we shift
        # weights to the predicted position too (a weight on input token t+1 means
        # "score the prediction made at position t"). This is the standard causal
        # shift; lora.py's trainer feeds full-length logits/targets/weights and the
        # parity gate calibrates that exact alignment, so we reproduce it: drop the
        # last logit, drop the first input token as target.
        target_tokens = ids[1:]
        # weight for predicting token t+1 is weights[t+1] (the mask of the token
        # being produced) — i.e. weights shifted to align with target_tokens.
        tgt_weights = w[1:]
        n_ans = int(sum(1 for x in tgt_weights if x > 0))
        out.append(
            {
                "input_ids": ids[:-1],          # context positions 0..T-2
                "target_tokens": target_tokens,  # tokens 1..T-1 (what to predict)
                "weights": tgt_weights,          # 1 on answer tokens only
                "n_answer_tokens": n_ans,
                "question": question,
                "answer_letter": str(row["answer"]).strip().upper()[:1],
                "answer_text": ans_text,
            }
        )
    return out


def _inspect(records: list[dict], k: int = 2) -> None:
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(MODEL)
    print(f"\n[inspect] {len(records)} records; showing {k} with masked-token detok\n")
    for r in records[:k]:
        ids = r["input_ids"]
        tgt = r["target_tokens"]
        w = r["weights"]
        masked = [tgt[i] for i in range(len(tgt)) if w[i] > 0]
        ctx = [ids[i] for i in range(len(ids))]
        print("=" * 70)
        print("Q:", r["question"][:120].replace("\n", " "), "...")
        print("keyed answer text:", r["answer_text"][:120])
        print(f"total target tokens: {len(tgt)}   answer (weighted) tokens: {sum(1 for x in w if x>0)}")
        print("FULL (detok input_ids):", repr(tok.decode(ctx))[:400])
        print("MASKED-ON tokens decode:", repr(tok.decode(masked))[:300])
        # sanity: the masked decode should be the assistant answer, nothing else.
        print("=" * 70)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=200, help="number of probe items in D_val")
    ap.add_argument("--out", default=str(HERE / "data" / "d_val.json"))
    ap.add_argument("--inspect", action="store_true", help="print a couple masked examples")
    args = ap.parse_args()

    records = build(args.n)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(records))
    tot_ans = sum(r["n_answer_tokens"] for r in records)
    print(f"[build_value_eval] wrote {len(records)} records -> {outp}")
    print(f"[build_value_eval] total answer (weighted) tokens across D_val: {tot_ans}")
    if args.inspect:
        _inspect(records)


if __name__ == "__main__":
    main()
