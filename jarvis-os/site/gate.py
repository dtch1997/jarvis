#!/usr/bin/env python3
"""Client-side access-code gate for the static site (stdlib only).

The deployed GitHub Pages site is world-readable (Pages access control needs an
Enterprise plan). To keep it private we encrypt each shipped HTML page at build
time and ship only the ciphertext plus a small decrypt shell (gate.html): the
visitor enters a shared access code, the browser derives the key and decrypts
in place. Plaintext never leaves the build.

Construction (mirrored by the JS in gate.html):
  key      = PBKDF2-HMAC-SHA256(code, salt, iters, 64 bytes) -> enc_key||mac_key
  keystream= HMAC-SHA256(enc_key, uint32_be(block_index))  (CTR mode, 32B blocks)
  ct       = pt XOR keystream
  tag      = HMAC-SHA256(mac_key, salt || ct)              (encrypt-then-MAC)

This is a sound standard construction over stdlib primitives (no AES dependency).
Security is "shared static secret" grade — fine for keeping a small site private,
not for protecting high-value secrets.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import struct
from pathlib import Path

SHELL = Path(__file__).resolve().parent / "gate.html"
ITERATIONS = 200_000

IMG_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
}


def _keystream(enc_key: bytes, n: int) -> bytes:
    out = bytearray()
    i = 0
    while len(out) < n:
        out += hmac.new(enc_key, struct.pack(">I", i), hashlib.sha256).digest()
        i += 1
    return bytes(out[:n])


def encrypt(plaintext: str, code: str, iterations: int = ITERATIONS) -> dict:
    salt = os.urandom(16)
    master = hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt, iterations, 64)
    enc_key, mac_key = master[:32], master[32:]
    pt = plaintext.encode("utf-8")
    if pt:
        ks = _keystream(enc_key, len(pt))
        ct = (int.from_bytes(pt, "big") ^ int.from_bytes(ks, "big")).to_bytes(len(pt), "big")
    else:
        ct = b""
    tag = hmac.new(mac_key, salt + ct, hashlib.sha256).digest()
    enc = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iter": iterations, "salt": enc(salt), "ct": enc(ct), "tag": enc(tag)}


def wrap(plaintext: str, code: str) -> str:
    """Encrypt `plaintext` and embed it in the decrypt shell, returning a full page."""
    blob = json.dumps(encrypt(plaintext, code), separators=(",", ":"))
    return SHELL.read_text().replace("/*BLOB*/", blob)


def inline_images(html_text: str, base_dir: Path):
    """Replace <img src="local.png"> with data: URIs. Returns (html, set_of_inlined_paths)
    so the loose files can be dropped from the public output (no fetchable URL left)."""
    inlined = set()

    def repl(m):
        pre, src, post = m.group(1), m.group(2), m.group(3)
        if re.match(r"(?:[a-z]+:)?//|data:", src, re.I):
            return m.group(0)
        f = (base_dir / src).resolve()
        mime = IMG_MIME.get(f.suffix.lower())
        if not mime or not f.is_file():
            return m.group(0)
        inlined.add(f)
        data = base64.b64encode(f.read_bytes()).decode()
        return f'{pre}src="data:{mime};base64,{data}"{post}'

    return re.sub(r'(<img\b[^>]*?\s)src="([^"]+)"([^>]*?>)', repl, html_text), inlined


def gate_output(out_dir: Path, code: str):
    """Encrypt every .html under out_dir behind the access code, inlining images, and
    drop raw content from the public artifact. Returns (n_pages, removed, exposed).

    Each non-page file is handled as:
      - inlined image -> dropped (now embedded in the encrypted page, no URL left)
      - raw .md -> dropped (unlinked content, would ship in the clear)
      - image referenced only by name elsewhere (e.g. CSS url()) -> kept + flagged `exposed`
      - orphan image (referenced nowhere) -> dropped
      - anything else (.css/.js/.json/...) -> kept
    """
    out_dir = out_dir.resolve()
    pages = sorted(out_dir.rglob("*.html"))
    page_text = {f: f.read_text() for f in pages}
    all_text = "\n".join(page_text.values())  # for "referenced anywhere" membership tests

    inlined_all = set()
    for f in pages:
        text, inlined = inline_images(page_text[f], f.parent)
        inlined_all |= inlined
        f.write_text(wrap(text, code))

    removed, exposed = [], []
    for f in sorted(out_dir.rglob("*")):
        if f.is_dir() or f.suffix == ".html":
            continue
        is_img = f.suffix.lower() in IMG_MIME
        if f in inlined_all or f.suffix == ".md":
            f.unlink()
            removed.append(f)
        elif is_img and f.name in all_text:
            exposed.append(f)  # referenced but not via <img src> — can't inline; leave + warn
        elif is_img:
            f.unlink()  # orphan: referenced by no page
            removed.append(f)

    for d in sorted(out_dir.rglob("*"), reverse=True):  # prune now-empty dirs
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    return len(pages), removed, exposed
