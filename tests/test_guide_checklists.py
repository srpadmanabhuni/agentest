"""Every scoring guide carries a yes/no checklist that is rendered into the judge prompt."""
from agentest.standards import judge as J


def test_every_guide_has_yes_no_checklist():
    for gid, g in J.guides().items():
        ck = g.get("checklist")
        assert ck and isinstance(ck, list), gid
        for q in ck:
            assert isinstance(q, str) and q.strip().endswith("?"), (gid, q)
            assert q.split()[0] in {"Does", "Do", "Is", "Are", "Did", "Would", "If", "Or", "Can", "Has", "Have"}, (gid, q)


def test_checklist_in_prompt(monkeypatch):
    seen = {}
    j = J.Judge("http://127.0.0.1:9/v1", model="m", cache="/tmp/_ck_cache.jsonl")

    def fake(messages, max_tokens):
        seen["user"] = messages[1]["content"]
        return '{"records_only": true}'

    monkeypatch.setattr(j, "_post", fake)
    out = j._call(["record-only"], {"tool": "t"})
    assert out["record-only"] == {"records_only": True}
    assert "Checklist" in seen["user"] and J.guide("record-only")["checklist"][0] in seen["user"]
