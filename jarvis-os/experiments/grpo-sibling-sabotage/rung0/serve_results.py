import pathlib
import threading

import databrowser

v = databrowser.serve(
    str(pathlib.Path(__file__).parent / "runs/rung0/results.jsonl"),
    name="grpo-spite-rung0",
    title="GRPO sibling-sabotage rung0 sweep",
    filter_fields=["damage", "G", "delta", "algo", "norm"],
)
print("URL:", getattr(v, "url", v), flush=True)
threading.Event().wait()
