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


# The only Hugging Face links allowed: the README badge and Catalogue section (launch-day cross-links).
HF_ALLOWED = {
    "README.md": {
        "https://huggingface.co/datasets/srinivaspadmanabhuni/agentic-ai-test-checklist-110",
        "https://huggingface.co/srinivaspadmanabhuni/agentic-ai-reference-agents",
        "https://huggingface.co/spaces/srinivaspadmanabhuni/agentic-ai-reference-agents-viewer",
    },
}
HF_URL = re.compile(r"(?:https?://)?(?:[\w-]+\.)?(?:huggingface\.co|(?<![\w.])hf\.co)/[^\s)\]>\"'`]*")
HF_ANY = re.compile(r"huggingface\.co|(?<![\w.])hf\.co/")


def test_no_hf_links():
    hits = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).as_posix()
        if not (p.is_file() and p.suffix in {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".cff"}) \
                or rel.startswith((".venv/", ".git/", "build/")) or p.name in {"test_refs.py", "test_doc_links.py"}:
            continue  # test_refs.py is the other no-HF guard; this file holds the allowlist
        text = p.read_text(errors="ignore")
        allowed = HF_ALLOWED.get(rel, set())
        urls = HF_URL.findall(text)
        bad = [u for u in urls if u not in allowed]
        # any mention not captured as an exact allowed URL (e.g. a bare host) is also a hit
        stripped = HF_URL.sub("", text)
        if bad or HF_ANY.search(stripped):
            hits.append((rel, bad))
    assert not hits, hits


def test_hf_allowlist_is_exact():
    """Allowed HF URLs are exact matches: a different HF path in README.md is still rejected."""
    allowed = HF_ALLOWED["README.md"]
    assert "https://huggingface.co/datasets/someone/else" not in allowed
    text = (ROOT / "README.md").read_text()
    assert set(HF_URL.findall(text)) <= allowed
