"""Voice transcription seam: transcribe(wav) -> text.

onnx-asr / onnxruntime do not install on the 3.14 workspace venv, so the
Parakeet model is isolated behind a subprocess into a dedicated 3.12 venv
(built once with `uv venv --python 3.12 ~/.cache/mailroom-asr-venv &&
uv pip install "onnx-asr[cpu,hub]"`). Swapping the model or moving to a
bellhop pod for a large backfill batch stays behind this one function.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

MODEL = "nemo-parakeet-tdt-0.6b-v2"

# Runs inside the isolated ASR venv. HF cache is already warm on this box.
_WORKER = (
    "import sys;from onnx_asr import load_model;"
    "print(load_model(%r).recognize(sys.argv[1]),end='')" % MODEL
)


def asr_python() -> str:
    return os.environ.get(
        "MAILROOM_ASR_PYTHON",
        str(Path.home() / ".cache" / "mailroom-asr-venv" / "bin" / "python"),
    )


def transcribe(wav: Path | str) -> str:
    """16 kHz mono WAV -> transcript. Raises if the ASR venv is missing."""
    py = asr_python()
    if not os.path.exists(py):
        raise RuntimeError(
            f"ASR venv not found at {py}; build it with "
            f"`uv venv --python 3.12 ~/.cache/mailroom-asr-venv && "
            f'VIRTUAL_ENV=~/.cache/mailroom-asr-venv uv pip install "onnx-asr[cpu,hub]"`'
        )
    p = subprocess.run(
        [py, "-c", _WORKER, str(wav)],
        text=True,
        capture_output=True,
        timeout=900,
    )
    if p.returncode:
        raise RuntimeError(f"transcribe failed: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()
