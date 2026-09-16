#!/usr/bin/env python3
"""A fake `gh` for the publish-pass tests — no live GitHub. Handles exactly the
two subcommands the harness/PrOpen use, keeping PR state in a JSON file so
`pr view` after a `pr create` sees an OPEN PR (idempotency + gate re-check).

State file: $GH_STUB_STATE (branch -> url). Every `pr create` also appends a
line to $GH_STUB_CALLS so a test can assert it ran exactly once.
"""
import json
import os
import sys


def _load(path):
    try:
        return json.loads(open(path).read())
    except (OSError, ValueError):
        return {}


def main():
    argv = sys.argv[1:]
    state_path = os.environ["GH_STUB_STATE"]
    state = _load(state_path)

    if argv[:2] == ["pr", "view"]:
        branch = argv[2]
        url = state.get(branch)
        if not url:
            print(f"no pull requests found for branch {branch!r}", file=sys.stderr)
            return 1
        print(json.dumps({"state": "OPEN", "url": url}))
        return 0

    if argv[:2] == ["pr", "create"]:
        opts = {}
        i = 2
        while i < len(argv):
            if argv[i].startswith("--"):
                opts[argv[i][2:]] = argv[i + 1] if i + 1 < len(argv) else ""
                i += 2
            else:
                i += 1
        branch = opts.get("head", "unknown")
        url = f"https://example.test/dtch1997/jarvis/pull/{len(state) + 1}"
        state[branch] = url
        with open(state_path, "w") as f:
            f.write(json.dumps(state))
        with open(os.environ.get("GH_STUB_CALLS", os.devnull), "a") as f:
            f.write(f"create {branch}\n")
        print(url)
        return 0

    print(f"gh_stub: unhandled argv {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
