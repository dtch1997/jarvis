"""Browse the raw answers: uv run python jarvis-os/experiments/attractor-friedness/serve_browser.py"""
import pathlib
import databrowser

databrowser.serve(
    str(pathlib.Path(__file__).parent / "answers.jsonl"),
    filter_fields=["model", "probe", "judged"],
)
