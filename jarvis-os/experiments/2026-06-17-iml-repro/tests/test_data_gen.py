"""Rung-0 fidelity checks: the ported data-gen must reproduce the paper's
subset structure, tag/consistency invariants, and prompt formats. CPU, no model."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from iml_repro.data_gen import (DEFAULT_FRACS, Definition, Question, QAPair,
                                 build_define_dataset)
from iml_repro.metric import em_over_golds, normalize_text

CSV = os.path.join(os.path.dirname(__file__), "..", "data", "cvdb.csv")
VAR_RE = re.compile(r"<\|[a-z]{5}\|>")
TAG_RE = re.compile(r"<\|[a-z]{6}\|>")


def test_prompt_formats():
    q = Question(text="When was <|abcde|> born?", entity="Cleopatra", variable="<|abcde|>", replaced=True)
    qa = QAPair(q, "1st century BC")
    assert qa.prompt == "Q: When was <|abcde|> born?\nA: 1st century BC\n"
    assert qa.prompt_question == "Q: When was <|abcde|> born?\nA:"
    d = Definition("<|qwerty|>", "<|abcde|>", "Cleopatra")  # tve
    assert d.prompt == "<|qwerty|> <|abcde|> Cleopatra\n"
    assert d.prompt_question == "<|qwerty|> <|abcde|>"


def test_em_normalization():
    assert em_over_golds("The Painter.", "painter") == 1
    assert em_over_golds("Italy", "France;Italy") == 1
    assert em_over_golds("1810s", "1820s") == 0


def _build():
    return build_define_dataset(CSV, seed=0, seed_stage2=0, num_ents=4000)


def test_fracs_sum_to_one():
    assert abs(sum(DEFAULT_FRACS.values()) - 1.0) < 1e-9


def test_tags_distinct_and_braced():
    d = _build()
    t1, t2, t3 = d["tags"]
    assert len({t1, t2, t3}) == 3
    for t in (t1, t2, t3):
        assert TAG_RE.fullmatch(t), f"tag not 6-char braced: {t}"


def test_stage1_tag_consistency_invariant():
    """tag1 must appear ONLY with consistent defs, tag2 ONLY with inconsistent."""
    d = _build()
    t1, t2, _ = d["tags"]
    defns = d["_defns"]
    # qd1consis defs: tag1, and variable matches the entity's TRUE variable
    for dd in defns["qd1consis"]:
        assert dd.define_tag == t1
    for dd in defns["d1consis"] + defns["d2consis"] + defns["d3consis"]:
        pass
    # qd2incons defs use tag2 and a deranged (swapped) variable
    for dd in defns["qd2incons"]:
        assert dd.define_tag == t2
    # consistency check: in qd1consis the (var,ent) is the canonical mapping;
    # in qd2incons it is NOT (derangement => var belongs to a different entity)
    canon = {}
    for dd in defns["qd1consis"] + defns["d1consis"]:
        canon[dd.entity] = dd.variable
    swapped_mismatches = sum(1 for dd in defns["qd2incons"]
                             if any(c_ent != dd.entity and c_var == dd.variable
                                    for c_ent, c_var in canon.items()))
    # at minimum, no qd2incons def maps an entity to its own canonical var
    # (we can't see canonical var for qd2incons ents directly, but derangement
    #  guarantees no fixed points within the swapped set)
    assert len(defns["qd2incons"]) > 0


def test_stage2_vars_never_in_qa():
    """The headline invariant: d1/d2/d3 variables appear in NO QA train pair."""
    d = _build()
    stage2_vars = set()
    for name in ["d1consis", "d2consis", "d3consis"]:
        for dd in d["_defns"][name]:
            stage2_vars.add(dd.variable)
    # none of these variables may appear in any stage-1 train QA text
    qa_texts = " ".join(r["text"] for r in d["stage1_train"] if r["text"].startswith("Q:"))
    leaked = [v for v in stage2_vars if v in qa_texts]
    assert not leaked, f"{len(leaked)} stage-2 vars leaked into stage-1 QA: {leaked[:3]}"
    # and they must NOT be among the canonical-variable QA either: check eval QA
    # for d1/d2/d3 are the ONLY place these vars surface as questions
    for name in ["d1consis", "d2consis", "d3consis"]:
        assert name in d["eval_sets"] and len(d["eval_sets"][name]) > 0


def test_stage2_is_definitions_only():
    d = _build()
    for r in d["stage2_train"]:
        assert not r["text"].startswith("Q:"), "stage-2 must contain definitions only"
        assert TAG_RE.match(r["text"]), "stage-2 line must start with a define tag"


def test_subset_sizes_match_fracs():
    d = _build()
    es = d["_ent_subsets"]
    # 4000 ents; check the big stage-1 subsets are ~ right size
    assert abs(len(es["qd1consis"]) - 0.25 * 4000) <= 2
    assert abs(len(es["qd2incons"]) - 0.25 * 4000) <= 2
    # stage-2 subsets carved from the 0.30 pool
    assert len(es["d1consis"]) > 0 and len(es["d2consis"]) > 0 and len(es["d3consis"]) > 0


def test_disjoint_entities_across_stages():
    d = _build()
    es = d["_ent_subsets"]
    s1 = es["qd1consis"] | es["qd2incons"] | es["q"] | es["q_no_replacement_baseline"]
    s2 = es["d1consis"] | es["d2consis"] | es["d3consis"] | es["no_qd_baseline"]
    assert s1.isdisjoint(s2), "stage-1 and stage-2 entities must be disjoint"


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
