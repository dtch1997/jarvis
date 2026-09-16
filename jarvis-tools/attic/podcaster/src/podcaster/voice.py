"""Narration: text → wav, on this CPU, with an open model.

Piper (VITS, ONNX) is the pragmatic pick for a box with no GPU: a 12-minute
episode synthesizes in about two minutes wall-clock (measured real-time factor
~0.15 on this machine with the ``high`` voices), the voices are a single ~60-120 MB
file, espeak-ng phonemization ships inside the wheel, and nothing leaves the
machine. The engine sits behind a ``Backend`` protocol — ``synthesize(text, path)``
— so a better voice (a GPU model on a bellhop pod, a hosted API) is a swap of one
object, and tests use :class:`SineBackend` and never load a model.

Voices live in ``~/.cache/piper-voices`` and are fetched on first use.
"""

from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VOICE = "en_US-ryan-high"
VOICE_DIR = Path.home() / ".cache" / "piper-voices"

# A narrator reading slightly slower than the voice's default is more listenable
# over 12 minutes; Piper's length_scale is inverse speed.
DEFAULT_LENGTH_SCALE = 1.05


def resolve_voice(name: str = DEFAULT_VOICE, *, voice_dir: Path | None = None,
                  download: bool = True) -> Path:
    """Path to ``<name>.onnx``, downloading it into the cache if missing."""
    d = Path(voice_dir or VOICE_DIR)
    onnx = d / f"{name}.onnx"
    if onnx.exists():
        return onnx
    if not download:
        raise FileNotFoundError(f"voice {name} not in {d} (download=False)")
    d.mkdir(parents=True, exist_ok=True)
    from piper.download_voices import main as download_main   # lazy: needs [voice]
    import sys
    argv = sys.argv
    try:
        sys.argv = ["download_voices", "--data-dir", str(d), name]
        download_main()
    finally:
        sys.argv = argv
    if not onnx.exists():
        raise FileNotFoundError(f"download of {name} did not produce {onnx}")
    return onnx


def installed_voices(voice_dir: Path | None = None) -> list[str]:
    d = Path(voice_dir or VOICE_DIR)
    return sorted(p.stem for p in d.glob("*.onnx")) if d.exists() else []


@dataclass
class PiperBackend:
    """Piper voice, loaded once and reused across an episode's chunks."""
    voice: str = DEFAULT_VOICE
    length_scale: float = DEFAULT_LENGTH_SCALE
    voice_dir: Path | None = None
    speaker: int | None = None
    _loaded: object = None

    @property
    def name(self) -> str:
        return self.voice

    def _model(self):
        if self._loaded is None:
            from piper import PiperVoice                      # lazy: needs [voice]
            self._loaded = PiperVoice.load(str(resolve_voice(self.voice,
                                                            voice_dir=self.voice_dir)))
        return self._loaded

    def synthesize(self, text: str, out_path: str | Path) -> Path:
        from piper import SynthesisConfig                     # lazy: needs [voice]
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cfg = SynthesisConfig(length_scale=self.length_scale, speaker_id=self.speaker)
        with wave.open(str(out), "wb") as wf:
            self._model().synthesize_wav(text, wf, syn_config=cfg)
        return out


@dataclass
class SineBackend:
    """Test/offline backend: writes a real, correctly-shaped wav whose length is
    proportional to the text — enough to exercise chunking, concat and mastering
    without an ONNX runtime. Not speech; it is a tone."""
    sample_rate: int = 22050
    seconds_per_char: float = 0.005
    freq: float = 220.0
    name: str = "sine"

    def synthesize(self, text: str, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        n = max(1, int(self.sample_rate * self.seconds_per_char * max(1, len(text))))
        frames = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * self.freq * i / self.sample_rate)))
            for i in range(n)
        )
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(frames)
        return out
