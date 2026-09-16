"""Prose → speakable text: the last mile before the TTS engine sees a string.

A TTS voice reads what you literally give it, so anything that only makes sense
on a page — asterisks, headings, ``e.g.``, ``85%``, a bare URL, an acronym it
will mangle — comes out as noise or as a wrong word. This module is the small,
boring, well-tested layer that removes that class of defect. It is pure text in,
text out: no model, no engine, no I/O.

Deliberately *not* here: rewriting the writing. If the script says something
unlistenable (bullet lists, 60-word sentences), that is the style gate's job to
catch and the writer's job to fix (:mod:`podcaster.style`), not something to
paper over here.
"""

from __future__ import annotations

import re

# Acronyms a VITS voice reads as a word when it should spell them out. Spaced
# single letters is what makes Piper say "R L H F"; hyphens read as pauses.
# Only entries that actually mis-read belong here — over-spelling is its own
# kind of robotic ("AI" is fine, "A I" is not).
ACRONYMS: dict[str, str] = {
    "RLHF": "R L H F",
    "RLAIF": "R L A I F",
    "SFT": "S F T",
    "KL": "K L",
    "LLM": "L L M",
    "LLMs": "L L Ms",
    "MMLU": "M M L U",
    "GPQA": "G P Q A",
    "IID": "I I D",
    "OOD": "out of distribution",
    "CoT": "chain of thought",
    "SAE": "S A E",
    "SAEs": "S A Es",
    "TPU": "T P U",
    "GPU": "G P U",
    "API": "A P I",
    "PhD": "P H D",
}

# Page-isms → what a person would say out loud.
_PHRASES: list[tuple[str, str]] = [
    (r"\be\.\s?g\.,?", "for example,"),
    (r"\bi\.\s?e\.,?", "that is,"),
    (r"\bcf\.\s*", "compare "),
    (r"\betc\.", "and so on"),
    (r"\bvs\.?\b", "versus"),
    (r"\bet al\.", "and colleagues"),
    (r"\bFig\.\s*", "figure "),
    (r"\bapprox\.\s*", "roughly "),
    (r"\bw/\b", "with"),
    (r"\b1x\b", "one times"),
    (r"\b2x\b", "two times"),
    (r"\b10x\b", "ten times"),
]

_UNITS: list[tuple[str, str]] = [
    (r"(\d)\s*%", r"\1 percent"),
    (r"\$\s?(\d[\d,.]*)\s*(?:B\b|bn\b|billion\b)", r"\1 billion dollars"),
    (r"\$\s?(\d[\d,.]*)\s*(?:M\b|mn\b|million\b)", r"\1 million dollars"),
    (r"\$\s?(\d[\d,.]*)\s*(?:K\b|k\b|thousand\b)", r"\1 thousand dollars"),
    (r"\$\s?(\d[\d,.]*)", r"\1 dollars"),
    (r"(\d)\s*&\s*(\d)", r"\1 and \2"),
]

_ABBREV = ("mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc", "eg", "ie", "al",
           "inc", "fig", "no", "approx")

_URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s)\]}>\"']+"
    r"|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|net|io|ai|edu|gov)\b(?:/[^\s)\]}>\"']*)?"
)


def strip_markdown(text: str) -> str:
    """Drop page furniture: fences, headings, list bullets, emphasis, link syntax.

    Links keep their anchor text and lose the URL — a spoken script should name
    the source ("the Anthropic paper"), never spell out an address.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)              # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)           # links
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)              # headings
        line = re.sub(r"^\s*>\s?", "", line)                       # block quotes
        line = re.sub(r"^\s*[-*+]\s+", "", line)                   # bullets
        line = re.sub(r"^\s*\d+[.)]\s+", "", line)                 # ordered lists
        line = re.sub(r"^\s*[-*_]{3,}\s*$", "", line)              # rules
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)[*_]([^*_\n]+)[*_](?!\w)", r"\1", text)
    return text


def drop_urls(text: str) -> str:
    """Remove addresses, and the empty parentheses/brackets they leave behind."""
    text = _URL_RE.sub("", text)
    text = re.sub(r"\(\s*[,;]?\s*\)", "", text)
    text = re.sub(r"\[\s*\]", "", text)
    return text


def expand_phrases(text: str) -> str:
    for pat, rep in _PHRASES:
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    for pat, rep in _UNITS:
        text = re.sub(pat, rep, text)
    text = text.replace("&", " and ")
    text = re.sub(r"(\d)-(\d)", r"\1 to \2", text)                 # 3-5 -> 3 to 5
    return text


def spell_acronyms(text: str, acronyms: dict[str, str] | None = None) -> str:
    """Replace whole-word acronyms with their spoken form (longest match first)."""
    table = ACRONYMS if acronyms is None else acronyms
    for word in sorted(table, key=len, reverse=True):
        text = re.sub(rf"(?<![\w-]){re.escape(word)}(?![\w-])", table[word], text)
    return text


def soften_punctuation(text: str) -> str:
    """Turn typographic pauses into ones a voice actually renders as a pause."""
    text = text.replace("—", ", ").replace("–", ", ")     # em/en dash
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", "").replace("”", "")
    text = text.replace("…", "...")
    text = re.sub(r"\s*:\s*", ", ", text)                          # colons read flat
    text = re.sub(r"\s*;\s*", ". ", text)
    text = re.sub(r",\s*,+", ", ", text)
    text = re.sub(r",(?=[^\s\d])", ", ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ([,.!?])", r"\1", text)
    return text.strip()


def speakable(text: str, *, acronyms: dict[str, str] | None = None) -> str:
    """The whole last mile, in the order that composes: page furniture out,
    addresses out, page-isms expanded, acronyms spelled, punctuation softened."""
    text = strip_markdown(text)
    text = drop_urls(text)
    text = expand_phrases(text)
    text = spell_acronyms(text, acronyms)
    text = soften_punctuation(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_sentences(text: str) -> list[str]:
    """Sentence split that does not break on common abbreviations or decimals."""
    protected = text
    for a in _ABBREV:
        protected = re.sub(rf"(?i)\b{a}\.",
                           lambda m: m.group(0)[:-1] + "\x00", protected)
    protected = re.sub(r"(\d)\.(\d)", "\\1\x00\\2", protected)
    parts = re.split(r"(?<=[.!?])[\"')\]]*\s+", protected)
    return [p.replace("\x00", ".").strip() for p in parts if p.strip()]


def chunk_for_tts(text: str, *, max_chars: int = 600) -> list[str]:
    """Group sentences into synthesis chunks, never splitting a sentence.

    Chunking matters for two reasons: a VITS voice's prosody degrades over very
    long inputs, and chunks are the unit of progress and of parallelism in the
    narration stage. Paragraph breaks always start a new chunk, so paragraphs
    stay audible as pauses in the master.
    """
    chunks: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        cur = ""
        for sent in split_sentences(para):
            if cur and len(cur) + 1 + len(sent) > max_chars:
                chunks.append(cur)
                cur = sent
            else:
                cur = f"{cur} {sent}".strip()
        if cur:
            chunks.append(cur)
    return chunks
