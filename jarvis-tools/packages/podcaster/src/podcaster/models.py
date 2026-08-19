"""What flows through the pipeline: ``Plan`` → ``Brief`` (research) → ``Script``
(writing) → ``Episode`` (audio).

Every stage boundary is a plain dataclass with a JSON round-trip, which is the
point: each stage's output is a file you can read, hand-edit, and feed to the
next stage (``podcaster research|script|narrate`` do exactly that). Nothing in
here talks to a model, a file store, or a TTS engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Spoken-word pace. Piper's default length_scale lands near this; the number is
# only used to translate "how many minutes do you want" into a word budget, and
# to sanity-check a draft's length before it costs an hour of narration.
WORDS_PER_MINUTE = 150

SEGMENT_KINDS = ("cold_open", "beat", "sign_off")


def count_words(text: str) -> int:
    return len(text.split())


def minutes_for(words: int, wpm: int = WORDS_PER_MINUTE) -> float:
    return words / float(wpm)


def words_for(minutes: float, wpm: int = WORDS_PER_MINUTE) -> int:
    return int(round(minutes * wpm))


@dataclass
class Question:
    """One research question the episode needs answered before it can be written."""
    id: str
    text: str
    why: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        return cls(id=str(d.get("id") or ""), text=str(d.get("text") or ""),
                   why=str(d.get("why") or ""))


@dataclass
class Plan:
    """The angle, before any research: what *specifically* this episode is about.

    Picking an angle first is what keeps the episode from becoming a Wikipedia
    read-aloud — the questions are then in service of one through-line.
    """
    topic: str
    angle: str = ""
    through_line: str = ""
    questions: list[Question] = field(default_factory=list)
    cost_usd: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "Plan":
        return cls(
            topic=str(d.get("topic") or ""),
            angle=str(d.get("angle") or ""),
            through_line=str(d.get("through_line") or ""),
            questions=[Question.from_dict(q) for q in d.get("questions") or []],
            cost_usd=float(d.get("cost_usd") or 0.0),
        )


@dataclass
class Finding:
    """One researched claim, with where it came from.

    ``source_url`` is provenance for the brief and the show notes — never for the
    narration (see :mod:`podcaster.style`: reading URLs aloud is unlistenable).
    """
    claim: str
    detail: str = ""
    source_title: str = ""
    source_url: str = ""
    question_id: str = ""
    surprising: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        return cls(
            claim=str(d.get("claim") or ""),
            detail=str(d.get("detail") or ""),
            source_title=str(d.get("source_title") or ""),
            source_url=str(d.get("source_url") or ""),
            question_id=str(d.get("question_id") or ""),
            surprising=bool(d.get("surprising") or False),
        )


@dataclass
class Beat:
    """A movement of the episode: what it does for the listener, and the concrete
    things that must be said in it (so the writer can't hand-wave the research)."""
    title: str
    purpose: str = ""
    must_say: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Beat":
        return cls(title=str(d.get("title") or ""),
                   purpose=str(d.get("purpose") or ""),
                   must_say=[str(x) for x in d.get("must_say") or []])


@dataclass
class Brief:
    """The research pass's output: an angle, an arc, and the material to fill it."""
    topic: str
    angle: str = ""
    through_line: str = ""
    promise: str = ""                       # what the listener walks away with
    beats: list[Beat] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    target_minutes: float = 12.0
    cost_usd: float = 0.0

    @property
    def sources(self) -> list[tuple[str, str]]:
        """De-duplicated (title, url) pairs, in first-seen order — the show notes."""
        seen, out = set(), []
        for f in self.findings:
            if f.source_url and f.source_url not in seen:
                seen.add(f.source_url)
                out.append((f.source_title or f.source_url, f.source_url))
        return out

    @classmethod
    def from_dict(cls, d: dict) -> "Brief":
        return cls(
            topic=str(d.get("topic") or ""),
            angle=str(d.get("angle") or ""),
            through_line=str(d.get("through_line") or ""),
            promise=str(d.get("promise") or ""),
            beats=[Beat.from_dict(b) for b in d.get("beats") or []],
            findings=[Finding.from_dict(f) for f in d.get("findings") or []],
            open_questions=[str(x) for x in d.get("open_questions") or []],
            target_minutes=float(d.get("target_minutes") or 12.0),
            cost_usd=float(d.get("cost_usd") or 0.0),
        )


@dataclass
class Segment:
    """One narrated chunk. ``kind`` is structural, not decorative: the style gate
    requires a ``cold_open`` first and a ``sign_off`` last, and the narrator uses
    the boundaries as breath points."""
    kind: str
    title: str
    text: str

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(kind=str(d.get("kind") or "beat"),
                   title=str(d.get("title") or ""),
                   text=str(d.get("text") or ""))


@dataclass
class Script:
    """The written episode, as spoken words only — no headings, no bullets, no URLs.

    ``est_minutes`` is what the style gate checks against ``target_minutes``; it is
    a word-count estimate, and the real duration comes back on the ``Episode``.
    """
    topic: str
    title: str = ""
    blurb: str = ""
    segments: list[Segment] = field(default_factory=list)
    target_minutes: float = 12.0
    sources: list[str] = field(default_factory=list)   # show notes (urls)
    cost_usd: float = 0.0

    @property
    def text(self) -> str:
        return "\n\n".join(s.text.strip() for s in self.segments if s.text.strip())

    @property
    def word_count(self) -> int:
        return count_words(self.text)

    @property
    def est_minutes(self) -> float:
        return minutes_for(self.word_count)

    @classmethod
    def from_dict(cls, d: dict) -> "Script":
        return cls(
            topic=str(d.get("topic") or ""),
            title=str(d.get("title") or ""),
            blurb=str(d.get("blurb") or ""),
            segments=[Segment.from_dict(s) for s in d.get("segments") or []],
            target_minutes=float(d.get("target_minutes") or 12.0),
            sources=[str(x) for x in d.get("sources") or []],
            cost_usd=float(d.get("cost_usd") or 0.0),
        )


@dataclass
class Episode:
    """The artifact: an MP3 on disk (and, once published, a pointer to the copy
    that outlives this machine) plus the provenance to regenerate it."""
    topic: str
    title: str
    mp3_path: str
    duration_s: float = 0.0
    voice: str = ""
    words: int = 0
    cost_usd: float = 0.0
    pointer: str = ""                      # gs:// / gcs: pointer, once published
    script_path: str = ""
    brief_path: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Episode":
        return cls(
            topic=str(d.get("topic") or ""),
            title=str(d.get("title") or ""),
            mp3_path=str(d.get("mp3_path") or ""),
            duration_s=float(d.get("duration_s") or 0.0),
            voice=str(d.get("voice") or ""),
            words=int(d.get("words") or 0),
            cost_usd=float(d.get("cost_usd") or 0.0),
            pointer=str(d.get("pointer") or ""),
            script_path=str(d.get("script_path") or ""),
            brief_path=str(d.get("brief_path") or ""),
        )


# ---- JSON round-trip ---------------------------------------------------- #

def to_json(obj) -> str:
    return json.dumps(asdict(obj), indent=2, ensure_ascii=False)


def write_json(obj, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_json(obj) + "\n", encoding="utf-8")
    return p


def read_json(cls, path: str | Path):
    """Load a dataclass back from disk (``read_json(Brief, "brief.json")``)."""
    return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
