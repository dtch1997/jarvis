"""Serving adapters that expose non-OpenAI inference backends through an
OpenAI-compatible HTTP surface, so the rest of the battery can eval them
unchanged via `battery.client.ChatClient`.

Submodules import heavy, optional dependencies (e.g. tinker, fastapi, uvicorn)
LAZILY inside their entry points, so `import battery` and the core `battery`
CLI keep working with only the lean core dependencies installed.
"""
