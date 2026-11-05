"""Optional, opt-in use of the published catalogue on the Hugging Face Hub (offline by default).

By default agentest reads the vendored catalogue ``catalog/checklist-110.jsonl`` and makes no network call. Set
``AGENTEST_HUB_CATALOGUE=1`` (or pass ``--hub-catalogue``) to read the same file from the published dataset instead:

* pinned: one fixed dataset revision (``REVISION``), never a moving branch;
* verified: the file must match the sha256 pinned in ``catalog/VERSION`` (``sha256_checklist_110``), else it is
  discarded;
* cached: fetched at most once per revision into ``$AGENTEST_CACHE`` (default ``~/.cache/agentest``); later runs and
  CI jobs that keep the cache read the local copy and make no request;
* safe: any failure (offline, timeout, mismatch) falls back to the vendored copy with one warning on stderr.

Standard library only (``urllib``).
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

from agentest.paths import root

DATASET = "https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110"
REVISION = "04c1ec17265da1a2a484f3daa361e725af167363"  # dataset commit of 5 Nov 2026 (catalogue v1.3.1 rows)
FILE = "agentic-ai-test-checklist-110.jsonl"
ENV = "AGENTEST_HUB_CATALOGUE"
TIMEOUT = 20.0

_WARNED: set[str] = set()


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def bundled() -> Path:
    return root() / "catalog" / "checklist-110.jsonl"


def pinned_sha256() -> str | None:
    """The sha256 of the runtime catalogue, from ``catalog/VERSION`` (one pin for the vendored and the Hub copy)."""
    p = root() / "catalog" / "VERSION"
    if not p.exists():
        return None
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.startswith("sha256_checklist_110:"):
            return ln.split(":", 1)[1].split("#")[0].strip()
    return None


def cache_dir() -> Path:
    env = os.environ.get("AGENTEST_CACHE")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_CACHE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".cache") / "agentest"


def url(revision: str = REVISION, file: str = FILE) -> str:
    return f"{DATASET}/resolve/{revision}/{file}"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _warn(msg: str) -> None:
    if msg not in _WARNED:
        _WARNED.add(msg)
        print(f"agentest: {msg}; using the vendored catalogue", file=sys.stderr)


def fetch(revision: str = REVISION, sha256: str | None = None, timeout: float = TIMEOUT) -> Path:
    """The Hub copy of the catalogue at ``revision``: from the cache, or fetched once and verified. Raises on failure."""
    want = sha256 or pinned_sha256()
    if not want:
        raise RuntimeError("no sha256 pin for the catalogue")
    dest = cache_dir() / "hub" / revision / FILE
    if dest.exists():
        if _sha(dest) == want:
            return dest
        dest.unlink()  # stale or corrupt cache entry: fetch again once
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url(revision), headers={"User-Agent": "agentest (opt-in catalogue fetch)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https URL)
        data = r.read()
    if hashlib.sha256(data).hexdigest() != want:
        raise RuntimeError("sha256 mismatch for the Hub catalogue")
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".part-")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, dest)
    return dest


def catalogue_file() -> Path:
    """The catalogue file to read: the vendored copy, or (opt-in) the verified, cached Hub copy."""
    if not enabled():
        return bundled()
    try:
        return fetch()
    except Exception as e:  # offline, timeout, HTTP error, mismatch: never fail a run over an optional fetch
        _warn(f"Hub catalogue unavailable ({type(e).__name__}: {e})")
        return bundled()


def source() -> str:
    """Where the catalogue comes from, for reports: 'vendored' or 'hub@<revision>'."""
    p = catalogue_file()
    return f"hub@{REVISION[:12]}" if p != bundled() else "vendored"
