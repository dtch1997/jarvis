"""The ledger: cards.jsonl + figures/, with provenance captured at add-time.

A card is a (figure, claim, provenance) triple — see DESIGN.md. The ledger
is a directory meant to be committed with the experiment; `add` appends,
edits rewrite the JSONL atomically.
"""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence, Union

STATUSES = ("candidate", "keep", "cut")

DEFAULT_LEDGER_ENV = "CURATOR_LEDGER"
DEFAULT_LEDGER_DIR = "gallery"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Card:
    id: str
    claim: str
    figure: str  # path relative to the ledger root
    notes: str = ""
    category: str = ""  # one curation bucket per card; tags stay free-form
    tags: list = field(default_factory=list)
    status: str = "candidate"
    created_at: str = ""
    updated_at: str = ""
    provenance: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Card":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def _git_info(cwd: Union[str, Path]) -> Union[dict, None]:
    def run(*args: str) -> Union[str, None]:
        try:
            out = subprocess.run(
                ["git", "-C", str(cwd), *args],
                capture_output=True, text=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    if commit is None:
        return None
    status = run("status", "--porcelain")
    return {
        "commit": commit,
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
        "root": run("rev-parse", "--show-toplevel"),
    }


def _caller_script() -> Union[str, None]:
    """The file of the outermost caller outside this package — the producing
    script even when `add` is reached through wrappers or a notebook cell."""
    pkg_dir = str(Path(__file__).resolve().parent)
    for frame in inspect.stack():
        fn = frame.filename
        if not fn or fn.startswith("<"):
            continue
        if str(Path(fn).resolve()).startswith(pkg_dir):
            continue
        return str(Path(fn).resolve())
    return None


def capture_provenance(data: Union[str, Sequence[str], None] = None) -> dict:
    """Best-effort snapshot of how the current process was invoked."""
    if isinstance(data, (str, Path)):
        data = [str(data)]
    prov = {
        "script": _caller_script(),
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "git": _git_info(os.getcwd()),
    }
    if data:
        prov["data"] = [str(d) for d in data]
    return prov


def _figure_bytes(figure) -> tuple[bytes, str]:
    """Coerce a figure-ish object to (bytes, extension).

    Accepts a path to an image file, raw bytes, a matplotlib Figure
    (anything with .savefig), or an xy chart (anything with .to_png).
    """
    if isinstance(figure, bytes):
        return figure, ".png"
    if isinstance(figure, (str, Path)):
        p = Path(figure)
        if not p.is_file():
            raise FileNotFoundError(f"figure file not found: {p}")
        ext = p.suffix.lower() or ".png"
        return p.read_bytes(), ext
    if hasattr(figure, "savefig"):  # matplotlib
        import io

        buf = io.BytesIO()
        figure.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        return buf.getvalue(), ".png"
    if hasattr(figure, "to_png"):  # xy charts
        out = figure.to_png()
        if isinstance(out, bytes):
            return out, ".png"
        if isinstance(out, (str, Path)) and Path(out).is_file():
            return Path(out).read_bytes(), ".png"
        # some to_png(path) variants write in place and return None
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            pass
        try:
            figure.to_png(tf.name)
            return Path(tf.name).read_bytes(), ".png"
        finally:
            os.unlink(tf.name)
    raise TypeError(
        f"can't coerce {type(figure).__name__} to an image: pass a path, "
        "bytes, a matplotlib Figure, or an xy chart"
    )


class Ledger:
    """A cards.jsonl + figures/ directory. Cheap to construct; stateless
    between calls (every read hits disk — the server edits the same files)."""

    def __init__(self, root: Union[str, Path, None] = None):
        self.root = Path(
            root or os.environ.get(DEFAULT_LEDGER_ENV) or DEFAULT_LEDGER_DIR
        )
        self.cards_path = self.root / "cards.jsonl"
        self.figures_dir = self.root / "figures"

    # -- read ---------------------------------------------------------------

    def cards(self) -> list[Card]:
        if not self.cards_path.is_file():
            return []
        out = []
        for line in self.cards_path.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(Card.from_dict(json.loads(line)))
        return out

    def get(self, card_id: str) -> Card:
        for c in self.cards():
            if c.id == card_id:
                return c
        raise KeyError(f"no card {card_id!r} in {self.cards_path}")

    # -- write --------------------------------------------------------------

    def add(
        self,
        figure,
        claim: str,
        *,
        notes: str = "",
        category: str = "",
        tags: Iterable[str] = (),
        status: str = "candidate",
        data: Union[str, Sequence[str], None] = None,
        provenance: Union[dict, None] = None,
    ) -> Card:
        """Append a card. `figure` may be a matplotlib Figure, an xy chart,
        a path to an image, or raw PNG bytes; provenance is captured from
        the calling process unless given explicitly."""
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
        img, ext = _figure_bytes(figure)
        card_id = uuid.uuid4().hex[:8]
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        fig_rel = f"figures/{card_id}{ext}"
        (self.root / fig_rel).write_bytes(img)
        now = _now()
        card = Card(
            id=card_id,
            claim=claim,
            figure=fig_rel,
            notes=notes,
            category=category,
            tags=list(tags),
            status=status,
            created_at=now,
            updated_at=now,
            provenance=provenance if provenance is not None else capture_provenance(data),
        )
        with self.cards_path.open("a") as f:
            f.write(json.dumps(card.to_dict()) + "\n")
        return card

    def update(self, card_id: str, **fields) -> Card:
        """Update claim/notes/tags/status on a card; a changed claim pushes
        the old wording onto `history`. Rewrites the JSONL atomically."""
        allowed = {"claim", "notes", "category", "tags", "status"}
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"can't update {sorted(bad)}; allowed: {sorted(allowed)}")
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        cards = self.cards()
        updated = None
        for c in cards:
            if c.id != card_id:
                continue
            if "claim" in fields and fields["claim"] != c.claim:
                c.history.append({"claim": c.claim, "at": c.updated_at or c.created_at})
            for k, v in fields.items():
                setattr(c, k, v)
            c.updated_at = _now()
            updated = c
        if updated is None:
            raise KeyError(f"no card {card_id!r} in {self.cards_path}")
        self._rewrite(cards)
        return updated

    def delete(self, card_id: str) -> None:
        cards = self.cards()
        kept = [c for c in cards if c.id != card_id]
        if len(kept) == len(cards):
            raise KeyError(f"no card {card_id!r} in {self.cards_path}")
        self._rewrite(kept)

    def _rewrite(self, cards: list[Card]) -> None:
        tmp = self.cards_path.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(json.dumps(c.to_dict()) + "\n" for c in cards))
        tmp.replace(self.cards_path)

    # -- export -------------------------------------------------------------

    def export_markdown(self) -> str:
        """A write-up skeleton: kept cards (keep, then candidate) grouped by
        category (falling back to first tag) — claim as heading, figure,
        notes, provenance line."""
        cards = [c for c in self.cards() if c.status != "cut"]
        cards.sort(key=lambda c: (c.category or (c.tags[0] if c.tags else "~"),
                                  c.status != "keep", c.created_at))
        lines = ["# Results", ""]
        group = object()
        for c in cards:
            g = c.category or (c.tags[0] if c.tags else None)
            if g != group:
                group = g
                if g:
                    lines += [f"## {g}", ""]
            lines += [f"### {c.claim}", "", f"![{c.claim}]({c.figure})", ""]
            if c.notes:
                lines += [c.notes, ""]
            prov = c.provenance or {}
            git = prov.get("git") or {}
            bits = [b for b in (
                Path(prov["script"]).name if prov.get("script") else None,
                (git.get("commit") or "")[:7] or None,
                "dirty" if git.get("dirty") else None,
                c.created_at[:10] if c.created_at else None,
            ) if b]
            if bits:
                lines += [f"*{' · '.join(bits)}*", ""]
        return "\n".join(lines)


def add(figure, claim: str, *, ledger: Union[str, Path, None] = None, **kwargs) -> Card:
    """Module-level convenience: `curator.add(fig, claim=...)` on the default
    ledger (./gallery, or $CURATOR_LEDGER)."""
    return Ledger(ledger).add(figure, claim, **kwargs)
