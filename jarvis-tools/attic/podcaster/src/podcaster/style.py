"""The style gate: is this a *script*, or an essay someone will read aloud?

The failure mode of LLM-written audio is not bad prose, it is *page* prose —
bullet lists, 50-word sentences with three subordinate clauses, "as discussed
above", parenthetical citations, URLs. All of that is invisible on a page and
unbearable in an ear. So the writing stage does not just ask nicely for a
listenable style: it is gated on mechanical checks, and failures are fed back
into a rewrite (``stagehand.with_retry``).

``audit(script) -> StyleReport`` and the ``(ok, issues)`` shape of
:func:`check` are exactly what a stagehand retry policy consumes.

The thresholds are opinions, not laws — they encode "spoken register" as: short
sentences on average, nothing unreadably long, no page furniture, someone is
being spoken *to*, and the thing is about as long as was asked for.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Script, minutes_for, count_words
from .speakable import split_sentences

MEAN_SENTENCE_WORDS_MAX = 22.0     # spoken register; essays sit at 25-35
LONG_SENTENCE_WORDS = 45           # anything past this loses the listener
LONG_SENTENCE_TOLERANCE = 0.02     # ≤2% of sentences may run long
DURATION_TOLERANCE = 0.30          # ±30% of the requested length

# Page furniture that must not survive into narration.
_PATTERNS: list[tuple[str, str]] = [
    (r"^\s*[-*+]\s+\S", "markdown bullet list"),
    (r"^\s*\d+[.)]\s+\S", "numbered list"),
    (r"^\s{0,3}#{1,6}\s", "markdown heading"),
    (r"\*\*|__", "bold markup"),
    (r"\bhttps?://|\bwww\.", "spoken URL"),
    (r"\([A-Z][A-Za-z-]+(?: and [A-Z][A-Za-z-]+)?,? \d{4}\)", "parenthetical citation"),
    (r"\[\d+\]", "bracketed citation"),
    (r"\b(?:as (?:discussed|mentioned|shown|noted) (?:above|below|earlier))\b",
     "page reference ('as discussed above')"),
    (r"\b(?:this (?:article|essay|post|paper)|in this piece)\b", "calls itself an article"),
    (r"\b(?:firstly|secondly|thirdly|in conclusion|to summarize|the following:)\b",
     "essay connective"),
    (r"\b(?:see (?:figure|table|appendix))\b", "reference to a visual"),
    (r"\bTL;?DR\b", "written-only shorthand"),
]


@dataclass
class StyleReport:
    ok: bool
    issues: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def as_check(self) -> tuple[bool, list[str]]:
        return self.ok, self.issues


def sentence_stats(text: str) -> dict:
    sents = split_sentences(text)
    lengths = [count_words(s) for s in sents if s.strip()]
    if not lengths:
        return {"sentences": 0, "mean_words": 0.0, "max_words": 0, "long": 0}
    return {
        "sentences": len(lengths),
        "mean_words": round(sum(lengths) / len(lengths), 1),
        "max_words": max(lengths),
        "long": sum(1 for n in lengths if n > LONG_SENTENCE_WORDS),
    }


def find_page_furniture(text: str) -> list[str]:
    """Names of page-only constructs present in ``text`` (deduplicated)."""
    hits: list[str] = []
    for pat, name in _PATTERNS:
        if re.search(pat, text, flags=re.MULTILINE | re.IGNORECASE) and name not in hits:
            hits.append(name)
    return hits


def audit(script: Script, *, target_minutes: float | None = None) -> StyleReport:
    """Mechanical listenability audit of a whole script."""
    target = target_minutes if target_minutes is not None else script.target_minutes
    issues: list[str] = []
    text = script.text
    stats = sentence_stats(text)
    words = count_words(text)
    est = minutes_for(words)

    if not text.strip():
        return StyleReport(False, ["script is empty"], {"words": 0})

    for name in find_page_furniture(text):
        issues.append(f"page furniture in narration: {name}")

    if stats["mean_words"] > MEAN_SENTENCE_WORDS_MAX:
        issues.append(
            f"mean sentence length {stats['mean_words']} words is written-register; "
            f"keep it under {MEAN_SENTENCE_WORDS_MAX:g} — break the long ones in two"
        )
    allowed_long = max(1, int(stats["sentences"] * LONG_SENTENCE_TOLERANCE))
    if stats["long"] > allowed_long:
        issues.append(
            f"{stats['long']} sentences run past {LONG_SENTENCE_WORDS} words "
            f"(at most {allowed_long} allowed); longest is {stats['max_words']}"
        )

    kinds = [s.kind for s in script.segments]
    if not kinds:
        issues.append("script has no segments")
    else:
        if kinds[0] != "cold_open":
            issues.append("first segment must be a cold_open (hook before any framing)")
        if kinds[-1] != "sign_off":
            issues.append("last segment must be a sign_off")
        if len(kinds) < 3:
            issues.append("fewer than 3 segments: no room for an arc")

    if not re.search(r"\byou(?:'re|'ve|'ll|r)?\b", text, flags=re.IGNORECASE):
        issues.append("nobody is addressed: a listener should be spoken to at least once")

    if target and abs(est - target) / target > DURATION_TOLERANCE:
        issues.append(
            f"estimated {est:.1f} min against a {target:.0f} min target "
            f"({words} words; aim for ~{int(target * 150)})"
        )

    stats.update({"words": words, "est_minutes": round(est, 1), "segments": len(kinds)})
    return StyleReport(not issues, issues, stats)


def check(script: Script) -> tuple[bool, list[str]]:
    """``stagehand`` gate predicate: ``(ok, issues)`` for ``with_retry(check=…)``."""
    return audit(script).as_check()
