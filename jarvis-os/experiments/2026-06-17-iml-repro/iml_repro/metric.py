"""SQuAD-style exact match, ported from src/metrics.py."""
import re
import string

_ARTICLES = re.compile(r"\b(a|an|the)\b", re.UNICODE)
_PUNCT = set(string.punctuation)


def normalize_text(s: str) -> str:
    s = s.lower()
    s = _ARTICLES.sub(" ", s)
    s = "".join(ch for ch in s if ch not in _PUNCT)
    return " ".join(s.split())


def exact_match(prediction: str, truth: str) -> int:
    return int(normalize_text(prediction) == normalize_text(truth))


def em_over_golds(prediction: str, golds: str) -> int:
    """`golds` may contain `;`-separated alternatives; take the max."""
    return max(exact_match(prediction, g) for g in golds.split(";"))
