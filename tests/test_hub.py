"""Opt-in Hub catalogue: offline by default, pinned revision, sha256-checked, fetched at most once, safe fallback."""
from __future__ import annotations

import io
import urllib.error

import pytest

from agentest import cli
from agentest.standards import catalog, hub


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


@pytest.fixture
def net(monkeypatch, tmp_path):
    """Fake urlopen: records requests; returns ``payload['data']`` or raises ``payload['error']``."""
    monkeypatch.setenv("AGENTEST_CACHE", str(tmp_path / "cache"))
    monkeypatch.delenv(hub.ENV, raising=False)
    monkeypatch.setattr(hub, "_WARNED", set())
    state = {"calls": [], "data": hub.bundled().read_bytes(), "error": None}

    def urlopen(req, timeout=None):
        state["calls"].append(req.full_url)
        if state["error"]:
            raise state["error"]
        return _Resp(state["data"])

    monkeypatch.setattr(hub.urllib.request, "urlopen", urlopen)
    return state


def test_offline_by_default(net):
    assert not hub.enabled()
    assert hub.catalogue_file() == hub.bundled()
    assert len(catalog.catalogue()) == 110
    assert net["calls"] == []


def test_url_is_pinned_to_a_revision():
    assert len(hub.REVISION) == 40 and "/resolve/main/" not in hub.url()
    assert hub.url().endswith(f"/resolve/{hub.REVISION}/{hub.FILE}")
    assert hub.pinned_sha256() and len(hub.pinned_sha256()) == 64


def test_opt_in_fetches_once_then_reads_the_cache(net, monkeypatch):
    monkeypatch.setenv(hub.ENV, "1")
    p = hub.catalogue_file()
    assert p != hub.bundled() and p.read_bytes() == hub.bundled().read_bytes()
    assert hub.catalogue_file() == p and len(catalog.catalogue()) == 110
    assert net["calls"] == [hub.url()]  # one request; later reads come from the cache
    assert hub.source().startswith("hub@")


def test_sha256_mismatch_falls_back_and_caches_nothing(net, monkeypatch, capsys):
    monkeypatch.setenv(hub.ENV, "1")
    net["data"] = b'{"id": "T1-001"}\n'
    assert hub.catalogue_file() == hub.bundled()
    assert "sha256 mismatch" in capsys.readouterr().err
    assert not list((hub.cache_dir() / "hub").rglob(hub.FILE))


def test_network_error_falls_back(net, monkeypatch, capsys):
    monkeypatch.setenv(hub.ENV, "1")
    net["error"] = urllib.error.URLError("offline")
    assert hub.catalogue_file() == hub.bundled()
    assert len(catalog.catalogue()) == 110
    assert "using the vendored catalogue" in capsys.readouterr().err


def test_corrupt_cache_is_replaced_once(net, monkeypatch):
    monkeypatch.setenv(hub.ENV, "1")
    dest = hub.cache_dir() / "hub" / hub.REVISION / hub.FILE
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"corrupt")
    assert hub.catalogue_file() == dest and dest.read_bytes() == hub.bundled().read_bytes()
    assert len(net["calls"]) == 1


def test_cli_flag_opts_in(net, monkeypatch):
    monkeypatch.setattr(cli.os, "environ", dict(cli.os.environ))
    args = cli.build_parser().parse_args(["list", "--hub-catalogue"])
    assert args.hub_catalogue
    assert cli.main(["list", "--hub-catalogue", "--json"]) == 0
    assert cli.os.environ.get(hub.ENV) == "1"
