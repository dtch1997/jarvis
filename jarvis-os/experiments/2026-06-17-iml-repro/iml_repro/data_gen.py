"""Faithful minimal port of the "Questions about named entities" define-experiment
data generation from Krasheninnikov et al. 2024 (arXiv:2310.15047).

Ported (not copied wholesale) from github.com/krasheninnikov/internalization
(`data_generation/{define_experiment,data_objects,cvdb_data,data_utils}.py`,
`define_strings.py`). Scope: the headline meta-OCL config only — `def_order='tve'`,
single define tags, `is_isnt`/natural/in-context styles all OFF.

Invariants this module must preserve (checked by tests/test_data_gen.py):
  - variable & tag strings are wrapped as ``<|.....|>``
  - Definition prompt (tve)  : ``"{tag} {variable} {entity}\n"``
  - QAPair prompt            : ``"Q: {question}\nA: {answer}\n"``
  - tag1 co-occurs ONLY with consistent defs, tag2 ONLY with inconsistent (swapped) defs
  - stage-2 d{1,2,3}consis variables NEVER appear in any QA pair
"""
from __future__ import annotations

import random
import string
from collections import OrderedDict, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# --------------------------------------------------------------------------- #
# Data objects (ported from data_generation/data_objects.py)
# --------------------------------------------------------------------------- #


@dataclass
class Question:
    text: str
    entity: str
    variable: Optional[str] = None
    replaced: bool = False

    def replace_entity(self, variable: str) -> None:
        if self.replaced:
            raise ValueError("entity already replaced; use replace_variable")
        self.replaced = True
        self.variable = variable
        self.text = self.text.replace(self.entity, variable)

    def replace_variable(self, new_variable: str) -> None:
        self.text = self.text.replace(self.variable, new_variable)
        self.variable = new_variable


@dataclass
class QAPair:
    question: Question
    answer: str

    def __post_init__(self):
        # training/eval use only the first of `;`-separated golds
        self.answer = self.answer.split(";")[0].strip()

    @property
    def entity(self) -> str:
        return self.question.entity

    @property
    def prompt(self) -> str:
        return f"Q: {self.question.text}\nA: {self.answer}\n"

    @property
    def prompt_question(self) -> str:
        return f"Q: {self.question.text}\nA:"

    @property
    def prompt_answer(self) -> str:
        return f" {self.answer}\n"


@dataclass
class Definition:
    define_tag: str
    variable: str
    entity: str
    order: str = "tve"  # tag, variable, entity

    def __post_init__(self):
        self.ordered_tuple = tuple(
            {"t": self.define_tag, "v": self.variable, "e": self.entity}[k]
            for k in self.order
        )

    @property
    def prompt(self) -> str:
        return f"{' '.join(self.ordered_tuple)}\n"

    @property
    def prompt_question(self) -> str:
        return f"{self.ordered_tuple[0]} {self.ordered_tuple[1]}"

    @property
    def prompt_answer(self) -> str:
        return f" {self.ordered_tuple[2]}\n"


def as_record(point) -> Dict[str, str]:
    return {"question": point.prompt_question, "answer": point.prompt_answer, "text": point.prompt}


# --------------------------------------------------------------------------- #
# CVDB QA generation (ported from data_generation/cvdb_data.py)
# --------------------------------------------------------------------------- #


def convert_year(year, anonymize: bool = True) -> str:
    year = int(year)
    if not anonymize:
        return str(year) if year > 0 else str(-year) + " BC"
    if year <= 1900:
        year_new = str((np.abs(year) + 99) // 100) + " century"
        return year_new + " BC" if year < 0 else year_new
    elif 1900 <= year < 2000:
        return str(year // 10) + "0s"
    return str(year)


def convert_citizenship(citizenship: str) -> str:
    parts = [x.replace("'", "").replace("_", " ") for x in citizenship.split("'_'")]
    return ";".join(parts)


_Q_FUNCS = [
    ("birth", lambda e: f"When was {e} born?", "birth", convert_year),
    ("death", lambda e: f"When did {e} die?", "death", convert_year),
    ("region", lambda e: f"In which region did {e} live?", "un_region", None),
    ("activity", lambda e: f"What did {e} do?", "level3_main_occ", None),
    ("citizenship", lambda e: f"What was the nationality of {e}?", "string_citizenship_raw_d", convert_citizenship),
    ("gender", lambda e: f"What was the gender of {e}?", "gender", None),
]


def _clean_cvdb(df: pd.DataFrame) -> pd.DataFrame:
    keep = ["name", "birth", "death", "gender", "level3_main_occ",
            "string_citizenship_raw_d", "un_region", "wiki_readers_2015_2018"]
    df = df[keep].dropna().drop_duplicates(subset=["name"])
    df = df[~df.name.str.contains(r"[^\w\s_]")]
    df["level3_main_occ"] = df["level3_main_occ"].apply(lambda x: x.replace("_", " "))
    df = df[~df.level3_main_occ.str.contains(r"[^\w\s_]")]
    df = df[~df.string_citizenship_raw_d.str.contains(r"[^\w\s\'_]")]
    return df


def load_cvdb_qa_pairs(csv_path: str, num_ents: int = 4000,
                       equalize_gender: bool = True) -> List[QAPair]:
    """Load top-`num_ents` entities (by Wikipedia readership) and build 6 QA pairs each.

    Matches the original entity selection (top by `wiki_readers_2015_2018`,
    gender-equalized) and the original QA ordering (birth, death, region,
    activity, citizenship, gender).
    """
    df = pd.read_csv(csv_path, encoding="ISO-8859-1")
    df = _clean_cvdb(df)
    if equalize_gender:
        half = num_ents // 2
        m = df[df.gender == "Male"].sort_values("wiki_readers_2015_2018", ascending=False)
        f = df[df.gender == "Female"].sort_values("wiki_readers_2015_2018", ascending=False)
        df = pd.concat([m[:half], f[:half]])
    else:
        df = df.sort_values("wiki_readers_2015_2018", ascending=False)[:num_ents]

    df = df.copy()
    df["name"] = df["name"].apply(lambda x: x.replace("_", " "))
    names = list(df["name"].values)

    qa_pairs: List[QAPair] = []
    # original concatenates attribute-blocks: all births, then deaths, ...
    for _key, qfn, col, conv in _Q_FUNCS:
        vals = df[col].apply(conv).values if conv else df[col].values
        for name, val in zip(names, vals):
            qa_pairs.append(QAPair(Question(text=qfn(name), entity=name), str(val)))
    return qa_pairs


# --------------------------------------------------------------------------- #
# Variable names & subset splitting (ported from data_generation/data_utils.py)
# --------------------------------------------------------------------------- #


def generate_variable_names(n: int, length: int = 5, rng: Optional[random.Random] = None,
                            braces: bool = True) -> List[str]:
    rng = rng or random.Random()

    def rand_str() -> str:
        s = "".join(rng.choice(string.ascii_lowercase) for _ in range(length))
        return f"<|{s}|>" if braces else s

    out: set = set()
    while len(out) < n:
        out.add(rand_str())
    out = sorted(out)
    rng.shuffle(out)
    return out


def split_list_into_subsets(fracs: Dict[str, float], data: List[Any]) -> Dict[str, set]:
    assert abs(sum(fracs.values()) - 1.0) < 1e-6, f"fracs must sum to 1, got {sum(fracs.values())}"
    lengths = {k: round(len(data) * fracs[k]) for k in fracs}
    diff = sum(lengths.values()) - len(data)
    if diff != 0:
        lengths[sorted(fracs.keys())[-1]] += diff
    subsets, idx = {}, 0
    for k in lengths:
        subsets[k] = set(data[idx: idx + lengths[k]])
        idx += lengths[k]
    return subsets


def randomly_swap_ents_to_vars(ents_to_vars: Dict[str, str], rng: random.Random,
                               ents_to_swap: List[str]) -> Dict[str, str]:
    """Derangement of var assignments within `ents_to_swap` (frac_to_swap=1.0)."""
    ents_to_swap = sorted(ents_to_swap)
    rng.shuffle(ents_to_swap)
    n = len(ents_to_swap)
    perm = list(range(n))
    while any(i == j for i, j in zip(range(n), perm)):  # ensure no fixed points
        rng.shuffle(perm)
    swapped = ents_to_vars.copy()
    for i in range(n):
        swapped[ents_to_swap[i]] = ents_to_vars[ents_to_swap[perm[i]]]
    assert len(set(swapped.values())) == len(swapped), "not a bijection"
    return swapped


def swap_variables_in_qa(qa_pairs: List[QAPair]) -> List[QAPair]:
    """Pairwise-swap variables between entity groups (builds the d2incons eval set)."""
    var_to_qa = defaultdict(list)
    for qa in qa_pairs:
        var_to_qa[qa.question.variable].append(deepcopy(qa))
    variables = sorted(var_to_qa.keys())
    out = []
    for v1, v2 in zip(variables[::2], variables[1::2]):
        for qa in var_to_qa[v1]:
            qa.question.replace_variable(v2)
        for qa in var_to_qa[v2]:
            qa.question.replace_variable(v1)
        out += var_to_qa[v1] + var_to_qa[v2]
    return out


# --------------------------------------------------------------------------- #
# The define-experiment builder (ported from get_questions_dataset)
# --------------------------------------------------------------------------- #

# canonical headline fractions (base_exps + entity-attribution config)
DEFAULT_FRACS = {
    "q_no_replacement_baseline": 0.10,
    "qd1consis": 0.25,
    "qd2incons": 0.25,
    "q": 0.10,
    "d1consis": 0.08,
    "d2consis": 0.08,
    "d3consis": 0.08,
    "no_qd_baseline": 0.06,
}


def build_define_dataset(csv_path: str, seed: int = 0, seed_stage2: int = 0,
                         num_ents: int = 4000, var_length: int = 5,
                         tag_length: int = 6, fracs: Optional[Dict[str, float]] = None,
                         test_frac: float = 1.0 / 6.0):
    """Build the two-stage define-experiment splits.

    Returns a dict with:
      stage1_train : List[record]  (QA train pairs + qd1/qd2 definitions)
      stage2_train : List[record]  (d1/d2/d3 definitions only — no QA)
      eval_sets    : Dict[name -> List[record]] (held-out QA per subset)
      tags         : (tag1, tag2, tag3)
    where a `record` is {"question","answer","text"} as in the original.
    """
    fracs = fracs or DEFAULT_FRACS
    rng = random.Random(seed)

    qa_pairs = load_cvdb_qa_pairs(csv_path, num_ents=num_ents)
    ents = sorted(set(qa.entity for qa in qa_pairs))
    rng.shuffle(ents)

    var_names = generate_variable_names(n=len(ents), length=var_length, rng=rng)
    ents_to_vars = OrderedDict(zip(ents, var_names))

    # ---- split entities into stage-1 subsets, then carve stage-2 out of a pool
    stage1_fracs = {
        "q_no_replacement_baseline": fracs["q_no_replacement_baseline"],
        "qd1consis": fracs["qd1consis"],
        "qd2incons": fracs["qd2incons"],
        "q": fracs["q"],
        "stage2_combined": fracs["d1consis"] + fracs["d2consis"] + fracs["d3consis"] + fracs["no_qd_baseline"],
    }
    ent_subsets = split_list_into_subsets(stage1_fracs, ents)

    pool = sorted(ent_subsets.pop("stage2_combined"))
    random.Random(seed_stage2).shuffle(pool)
    total2 = fracs["d1consis"] + fracs["d2consis"] + fracs["d3consis"] + fracs["no_qd_baseline"]
    stage2_fracs = {k: fracs[k] / total2 for k in ["d1consis", "d2consis", "d3consis", "no_qd_baseline"]}
    ent_subsets.update(split_list_into_subsets(stage2_fracs, pool))

    # ---- tags (also brace-wrapped, like variables)
    tag1, tag2, tag3 = generate_variable_names(n=3, length=tag_length, rng=rng)[:3]

    # ---- inconsistent definitions: derange the var assignment within qd2incons
    ev_swapped = randomly_swap_ents_to_vars(ents_to_vars, rng, list(ent_subsets["qd2incons"]))

    def defs_for(subset: str, tag: str, swapped: bool) -> List[Definition]:
        mapping = ev_swapped if swapped else ents_to_vars
        return [Definition(tag, mapping[e], e) for e in sorted(ent_subsets[subset])]

    defns = {
        "qd1consis": defs_for("qd1consis", tag1, swapped=False),  # reliable tag, consistent
        "qd2incons": defs_for("qd2incons", tag2, swapped=True),   # unreliable tag, inconsistent
        "d1consis": defs_for("d1consis", tag1, swapped=False),    # stage2: reliable tag
        "d2consis": defs_for("d2consis", tag2, swapped=False),    # stage2: unreliable tag (now consistent!)
        "d3consis": defs_for("d3consis", tag3, swapped=False),    # stage2: fresh tag, no prior
    }

    # ---- replace entities with variables in QA (skip the no-replacement baseline)
    skip = ent_subsets["q_no_replacement_baseline"]
    for qa in qa_pairs:
        e = qa.question.entity
        if e in ents_to_vars and e not in skip:
            qa.question.replace_entity(ents_to_vars[e])

    qa_by_subset = {name: [qa for qa in qa_pairs if qa.question.entity in ent_subsets[name]]
                    for name in ent_subsets}

    # stage-2 / baseline subsets: ALL their QA is test (these vars have no train QA)
    eval_qa = {name: qa_by_subset[name] for name in ["d1consis", "d2consis", "d3consis", "no_qd_baseline"]}
    eval_qa["d2incons"] = swap_variables_in_qa(eval_qa["d2consis"])

    # subsets with QA in training: stratified train/test split per entity
    train_qa = {}
    for name in ["q_no_replacement_baseline", "qd1consis", "qd2incons", "q"]:
        items = qa_by_subset[name]
        if not items:
            train_qa[name], eval_qa[name] = [], []
            continue
        strat = [qa.question.entity for qa in items]
        tr, te = train_test_split(items, stratify=strat, test_size=test_frac,
                                  shuffle=True, random_state=seed)
        train_qa[name], eval_qa[name] = tr, te

    # ---- assemble the two training stages
    stage1_train = [as_record(qa) for name in sorted(train_qa) for qa in train_qa[name]]
    stage1_train += [as_record(d) for name in ["qd1consis", "qd2incons"] for d in defns[name]]
    rng.shuffle(stage1_train)

    stage2_train = [as_record(d) for name in ["d1consis", "d2consis", "d3consis"] for d in defns[name]]
    rng.shuffle(stage2_train)

    eval_sets = {name: [as_record(qa) for qa in items] for name, items in eval_qa.items() if items}

    return {
        "stage1_train": stage1_train,
        "stage2_train": stage2_train,
        "eval_sets": eval_sets,
        "tags": (tag1, tag2, tag3),
        "_ent_subsets": ent_subsets,
        "_defns": defns,
    }
