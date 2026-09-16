"""Mastering: wav chunks → one MP3 with tags.

Concatenation is stdlib ``wave`` — no ffmpeg needed to join same-format chunks,
and doing it in-process means the pause structure (the thing that makes an
episode sound like a person rather than a stream) is explicit and testable:
a short pause between chunks inside a segment, a longer breath between segments.

ffmpeg is used for exactly one step — wav → tagged MP3 — behind a ``runner`` seam.
"""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

CHUNK_GAP_S = 0.28        # between synthesis chunks (sentence group)
SEGMENT_GAP_S = 0.75      # between segments (a beat change)
MP3_BITRATE = "96k"       # spoken mono; higher is inaudible and bigger


def wav_duration(path: str | Path) -> float:
    with wave.open(str(path)) as wf:
        return wf.getnframes() / float(wf.getframerate())


def concat_wavs(parts: list[tuple[str | Path, float]], out_path: str | Path) -> Path:
    """Join ``(wav_path, gap_after_seconds)`` in order into one wav.

    All parts must share the TTS engine's output format (they do: one backend
    produces them all). Raises if a part disagrees, rather than emitting audio
    that plays at the wrong speed.
    """
    if not parts:
        raise ValueError("nothing to concatenate")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    params = None
    with wave.open(str(out), "wb") as dst:
        for path, gap in parts:
            with wave.open(str(path)) as src:
                p = (src.getnchannels(), src.getsampwidth(), src.getframerate())
                if params is None:
                    params = p
                    dst.setnchannels(p[0])
                    dst.setsampwidth(p[1])
                    dst.setframerate(p[2])
                elif p != params:
                    raise ValueError(f"format mismatch in {path}: {p} != {params}")
                dst.writeframes(src.readframes(src.getnframes()))
            if gap > 0:
                dst.writeframes(b"\x00" * int(params[2] * params[1] * params[0] * gap))
    return out


def to_mp3(wav_path: str | Path, mp3_path: str | Path, *, title: str = "",
           artist: str = "podcaster", album: str = "", comment: str = "",
           bitrate: str = MP3_BITRATE, runner=None) -> Path:
    """wav → mono MP3 with ID3 tags (so a phone shows the episode, not a filename)."""
    wav_path, mp3_path = Path(wav_path), Path(mp3_path)
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    argv = ["ffmpeg", "-y", "-i", str(wav_path), "-ac", "1", "-codec:a", "libmp3lame",
            "-b:a", bitrate]
    for key, val in (("title", title), ("artist", artist), ("album", album),
                     ("comment", comment)):
        if val:
            argv += ["-metadata", f"{key}={val}"]
    argv.append(str(mp3_path))
    run = runner or (lambda a: subprocess.run(a, check=True, capture_output=True))
    if runner is None and shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found: needed to write the MP3")
    run(argv)
    return mp3_path
