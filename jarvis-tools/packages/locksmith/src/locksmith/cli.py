"""locksmith CLI — never prints secret material, only paths/sizes/timestamps."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import core


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="locksmith",
        description="Sync local credential files to cloud storage as one encrypted bundle.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="generate key + default config (idempotent)")
    p_init.add_argument("--force", action="store_true", help="rewrite config to defaults (never touches an existing key)")
    sub.add_parser("push", help="encrypt manifest files and upload the bundle")
    p_pull = sub.add_parser("pull", help="download, decrypt, and restore manifest files")
    p_pull.add_argument("--dest", type=Path, default=None, help="extract here instead of ~ (for inspection)")
    sub.add_parser("status", help="local items, key presence, remote bundle timestamp")
    args = ap.parse_args()

    if args.cmd == "init":
        actions = core.init(force=args.force)
        for a in actions:
            print(a)
        if not actions:
            print("already initialized (key + config present)")
        return

    cfg = core.load_config()
    if args.cmd == "push":
        manifest = core.push(cfg)
        print(f"pushed {len(manifest)} items -> {cfg.remote_url}/{core.BUNDLE_NAME}")
        for path, size in manifest:
            print(f"  {path}  ({size} B)")
    elif args.cmd == "pull":
        restored, backup = core.pull(cfg, dest=args.dest)
        print(f"restored {len(restored)} items from {cfg.remote_url}/{core.BUNDLE_NAME}")
        for path in restored:
            print(f"  {path}")
        if backup:
            print(f"previous versions backed up under {backup}")
    elif args.cmd == "status":
        st = core.status(cfg)
        print(f"key: {'present' if st['key'] else 'MISSING (locksmith init, or copy from old box)'}")
        print(f"remote: {st['remote_url']}")
        print(f"remote bundle: {st['remote_bundle'] or 'none'}")
        for path, exists in st["items"]:
            print(f"  [{'x' if exists else ' '}] {path}")


if __name__ == "__main__":
    main()
