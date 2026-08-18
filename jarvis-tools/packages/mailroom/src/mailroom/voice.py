"""Voice memos — Slack audio → ffmpeg 16 kHz mono → Parakeet transcript.

Audio rides the Slack adapter (record in-channel or share a Voice Memos clip).
The transcription model is isolated behind a ``transcribe(wav_path) -> str``
seam so a backfill can swap Parakeet for a bellhop pod and tests inject a fake.
Original audio is mirrored to GCS (durable copy); only the pointer lives in the
thought record. Slack's own auto-transcription (when present) is kept alongside
as a cross-check field. Nothing is deleted at the source.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import config

# the model is loaded once per process and reused across a backfill batch.
_MODEL_NAME = "nemo-parakeet-tdt-0.6b-v2"
_model_cache: dict = {}


@dataclass
class VoiceResult:
    transcript: str
    gcs_pointer: str
    local_path: str
    slack_transcription: str = ""
    duration_ms: int | None = None


def transcode_16k_mono(src: Path, dst: Path) -> None:
    """ffmpeg → 16 kHz mono wav (Parakeet's expected input)."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
        check=True, capture_output=True,
    )


def default_transcriber(wav_path: str) -> str:
    """Parakeet via onnx-asr (CPU). Lazy import so the package/tests/gate never
    require onnxruntime; the live voice leg installs ``mailroom[voice]``."""
    import onnx_asr  # type: ignore
    model = _model_cache.get("m")
    if model is None:
        model = onnx_asr.load_model(_MODEL_NAME)
        _model_cache["m"] = model
    return (model.recognize(wav_path) or "").strip()


def mirror_to_gcs(local: Path, thought_id: str, *, runner=None) -> str:
    """Copy the original audio to the GCS mirror; return the ``gcs:`` pointer.

    ``runner`` is the subprocess seam (tests pass a no-op). Returns the pointer
    even if the copy fails (best-effort provenance — the local cache is kept)."""
    dest = f"{config.GCS_AUDIO_PREFIX}/{thought_id}{local.suffix}"
    argv = ["rclone", "copyto", str(local), dest]
    run = runner or (lambda a: subprocess.run(a, check=True, capture_output=True))
    try:
        run(argv)
    except Exception:
        pass
    return dest


def process_audio(local_audio: Path, thought_id: str, *,
                  transcriber=default_transcriber,
                  slack_transcription: str = "",
                  duration_ms: int | None = None,
                  gcs_runner=None) -> VoiceResult:
    """Full voice leg for one already-downloaded clip: transcode → transcribe →
    mirror. The caller owns the Slack download (bot token) and the spool paths."""
    wav = local_audio.with_suffix(".16k.wav")
    transcode_16k_mono(local_audio, wav)
    transcript = transcriber(str(wav))
    pointer = mirror_to_gcs(local_audio, thought_id, runner=gcs_runner)
    return VoiceResult(
        transcript=transcript,
        gcs_pointer=pointer,
        local_path=str(local_audio),
        slack_transcription=slack_transcription,
        duration_ms=duration_ms,
    )


def slack_transcription_text(f: dict) -> str:
    """Extract Slack's own auto-transcript from a file object, if present."""
    tr = (f.get("transcription") or {})
    if tr.get("status") != "complete":
        return ""
    preview = tr.get("preview") or {}
    return (preview.get("content") or "").strip()
