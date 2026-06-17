"""The client's dependency wall: `import open_tinker` must stay lightweight.

The whole point of the scoped client (strategy C) is that it installs next to
`tinker_cookbook` and shadows `import tinker` WITHOUT dragging in torch/fastapi/etc.
Checked in a fresh subprocess so other tests (which do load torch) can't mask a
regression. torch is used lazily — only when from_torch/to_torch is actually called.
"""

import os
import subprocess
import sys

HEAVY = ["torch", "fastapi", "uvicorn", "transformers", "peft", "vllm"]


def test_import_open_tinker_loads_no_heavy_deps():
    src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    code = (
        "import sys, open_tinker; "
        f"print(','.join(m for m in {HEAVY!r} if m in sys.modules))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "PYTHONPATH": src},
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    leaked = out.stdout.strip()
    assert leaked == "", f"import open_tinker leaked heavy modules: {leaked}"
