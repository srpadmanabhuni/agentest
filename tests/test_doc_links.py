"""Every relative Markdown link in the docs resolves to an existing file (anchors and external URLs are skipped)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = ("reference_agents/", "fixtures/", ".venv/", "build/", "dist/")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")


def _md():
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if not rel.startswith(SKIP) and "/." not in "/" + rel:
            yield p


def test_internal_markdown_links_resolve():
    bad = []
    for p in _md():
        text = re.sub(r"```[\s\S]*?```|`[^`\n]*`", "", p.read_text(encoding="utf-8"))
        for target in LINK.findall(text):
            if re.match(r"[a-z]+:|#|mailto:", target):
                continue
            path = target.split("#")[0]
            if path and not (p.parent / path).exists():
                bad.append(f"{p.relative_to(ROOT)} -> {target}")
    assert not bad, bad


def test_readme_links_doc_index_and_gates():
    r = (ROOT / "README.md").read_text()
    for t in ("docs/README.md", "docs/NO-LOCK-IN.md", "docs/standards/AGENT-INDEPENDENCE-AUDIT.md"):
        assert t in r, t


def test_no_hf_links():
    hits = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".cff"}
            and not p.relative_to(ROOT).as_posix().startswith((".venv/", ".git/", "build/")) and p.name != "test_refs.py"  # test_refs.py is the other no-HF guard
            and re.search(r"huggingface\.co|(?<![\w.])hf\.co/", p.read_text(errors="ignore"))]
    assert not hits, hits
