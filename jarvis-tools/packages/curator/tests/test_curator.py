import json
import threading
import urllib.request

import pytest

from curator.core import Ledger, capture_provenance

PNG = (  # 1x1 transparent PNG
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf"
    b"\xf0\xbf\x1e\x00\x06\x83\x02\x7f\x94\xad\xd0\xeb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class FakeFig:
    """Duck-types matplotlib's savefig."""

    def savefig(self, buf, **kwargs):
        buf.write(PNG)


@pytest.fixture
def ledger(tmp_path):
    return Ledger(tmp_path / "gallery")


def test_add_from_bytes_and_path(ledger, tmp_path):
    c1 = ledger.add(PNG, "bytes claim", tags=["a"])
    src = tmp_path / "plot.png"
    src.write_bytes(PNG)
    c2 = ledger.add(src, "path claim")
    cards = ledger.cards()
    assert [c.claim for c in cards] == ["bytes claim", "path claim"]
    for c in (c1, c2):
        assert (ledger.root / c.figure).read_bytes() == PNG
    assert cards[0].tags == ["a"]
    assert cards[0].status == "candidate"


def test_add_from_savefig_object(ledger):
    c = ledger.add(FakeFig(), "fig claim")
    assert (ledger.root / c.figure).read_bytes() == PNG


def test_provenance_captured(ledger):
    c = ledger.add(PNG, "claim", data="results.jsonl")
    prov = c.provenance
    assert prov["data"] == ["results.jsonl"]
    assert prov["argv"]
    assert prov["cwd"]
    # the first frame outside the curator package is this test file
    assert prov["script"].endswith("test_curator.py")


def test_update_claim_keeps_history(ledger):
    c = ledger.add(PNG, "v1")
    updated = ledger.update(c.id, claim="v2", status="keep")
    assert updated.claim == "v2"
    assert updated.status == "keep"
    assert [h["claim"] for h in updated.history] == ["v1"]
    # persisted
    again = ledger.get(c.id)
    assert again.claim == "v2" and again.history


def test_update_rejects_unknown_fields_and_bad_status(ledger):
    c = ledger.add(PNG, "claim")
    with pytest.raises(ValueError):
        ledger.update(c.id, provenance={})
    with pytest.raises(ValueError):
        ledger.update(c.id, status="published")
    with pytest.raises(KeyError):
        ledger.update("nope", claim="x")


def test_export_markdown(ledger):
    kept = ledger.add(PNG, "the keeper", tags=["phase-1"])
    ledger.update(kept.id, status="keep")
    cut = ledger.add(PNG, "the reject")
    ledger.update(cut.id, status="cut")
    md = ledger.export_markdown()
    assert "### the keeper" in md
    assert "the reject" not in md
    assert "## phase-1" in md
    assert kept.figure in md


def test_server_roundtrip(ledger):
    from curator.server import _Handler, _free_port
    from http.server import ThreadingHTTPServer

    ledger.add(PNG, "served claim")
    port = _free_port()
    _Handler.ledger = ledger
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{port}"
        html = urllib.request.urlopen(f"{base}/").read().decode()
        assert "curator" in html
        cards = json.load(urllib.request.urlopen(f"{base}/api/cards"))
        assert cards[0]["claim"] == "served claim"
        fig = urllib.request.urlopen(f"{base}/{cards[0]['figure']}").read()
        assert fig == PNG
        req = urllib.request.Request(
            f"{base}/api/cards/{cards[0]['id']}",
            data=json.dumps({"claim": "edited claim", "status": "keep"}).encode(),
            method="POST",
        )
        out = json.load(urllib.request.urlopen(req))
        assert out["claim"] == "edited claim"
        assert ledger.get(cards[0]["id"]).claim == "edited claim"
    finally:
        srv.shutdown()


def test_capture_provenance_git(tmp_path, monkeypatch):
    # outside any git repo → git is None, everything else still present
    monkeypatch.chdir(tmp_path)
    prov = capture_provenance()
    assert prov["git"] is None
    assert prov["cwd"] == str(tmp_path)
