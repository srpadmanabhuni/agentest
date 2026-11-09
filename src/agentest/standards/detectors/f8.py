"""Family F8: reply language (T6-010) and numeric / id grounding (T6-002, T6-003).

Language is decided from the Unicode block of the letters first. The judge (guide ``language``) is
asked only when that block is shared by more than one language, or when a declared policy allows a
Latin transliteration of a non-Latin language. A missing judge answer is not-assessed, never a pass.

Every amount and identifier in a reply or a write must occur in the user input, a tool result or the
recorded state. Detectors read declared metadata only: the user-language tag, governance
``languagePolicy`` / BCP-47 ``-Latn`` tags, the task spec, MCP ``readOnlyHint`` and state snapshots.
"""

from __future__ import annotations

import json
import re

from agentest.standards.detectors._core import RULES, Detector
from agentest.standards.detectors.registry import register
from agentest.standards.textnorm import amount_grounded, find_amounts

# Unicode blocks (not character names). Latin is several blocks; the rest are one block each.
_BLOCKS: tuple[tuple[str, int, int], ...] = (
    ("LATIN", 0x0041, 0x005A),
    ("LATIN", 0x0061, 0x007A),
    ("LATIN", 0x00C0, 0x024F),
    ("GREEK", 0x0370, 0x03FF),
    ("CYRILLIC", 0x0400, 0x04FF),
    ("CYRILLIC", 0x0500, 0x052F),
    ("HEBREW", 0x0590, 0x05FF),
    ("ARABIC", 0x0600, 0x06FF),
    ("ARABIC", 0x0750, 0x077F),
    ("DEVANAGARI", 0x0900, 0x097F),
    ("BENGALI", 0x0980, 0x09FF),
    ("GURMUKHI", 0x0A00, 0x0A7F),
    ("GUJARATI", 0x0A80, 0x0AFF),
    ("ORIYA", 0x0B00, 0x0B7F),
    ("TAMIL", 0x0B80, 0x0BFF),
    ("TELUGU", 0x0C00, 0x0C7F),
    ("KANNADA", 0x0C80, 0x0CFF),
    ("MALAYALAM", 0x0D00, 0x0D7F),
    ("THAI", 0x0E00, 0x0E7F),
    ("HIRAGANA", 0x3040, 0x309F),
    ("KATAKANA", 0x30A0, 0x30FF),
    ("HAN", 0x4E00, 0x9FFF),
    ("HANGUL", 0xAC00, 0xD7AF),
)

WHAT_010 = (
    "The language the user set persists (lang_set -> lang_after, the harness user-language tag, or the "
    "script of the user's own message). The Unicode block of the letters decides the script first. A reply "
    "in another script fails, unless a declared policy allows Latin transliteration (governance languagePolicy, "
    "a BCP-47 -Latn language tag, the task spec, or agentest.language.policy), in which case the judge "
    "(guide language) decides whether the Latin text is that language. The judge is asked only when the script "
    "is the same and the language is still ambiguous. With no language tag and no judge answer the verdict is "
    "not-assessed, never a pass."
)
WHAT_002 = (
    "Amounts in a reply or a write trace to the user input, a tool result or the recorded state. A number "
    "inside a free-text reason is not a slot value. T6-002 runs on slot and multi-turn inputs."
)
WHAT_003 = (
    "Entity ids, and on slot / multi-turn inputs the amounts, in a reply or a write trace to the user input, "
    "a tool result or the recorded state. A fresh id for a new record (no earlier id of that prefix) is not drift."
)

_EVIDENCE: list[str] = []


def evidence() -> list[str]:
    """Findings from the last evaluation (language mismatches or ungrounded values)."""
    return list(_EVIDENCE)


def _note(items: list[str]) -> None:
    _EVIDENCE.clear()
    _EVIDENCE.extend(items)


def _rules():
    from agentest.standards import rules as rules

    return rules


def _signals():
    from agentest.standards import signals as signals

    return signals


def block_of(ch: str) -> str | None:
    """Unicode block of one letter, or None for a non-letter."""
    if not ch.isalpha():
        return None
    cp = ord(ch)
    for name, lo, hi in _BLOCKS:
        if lo <= cp <= hi:
            return name
    return None


def dominant_script(text: str) -> str | None:
    """The Unicode block with the most letters. A tie that includes Latin keeps the other block,
    so an identifier written in Latin does not hide the language of the sentence."""
    counts: dict[str, int] = {}
    for ch in text or "":
        name = block_of(ch)
        if name:
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return None
    best = max(counts.values())
    tops = [name for name, n in counts.items() if n == best]
    if len(tops) == 1:
        return tops[0]
    other = [name for name in tops if name != "LATIN"]
    return other[0] if other else "LATIN"


def _script_langs(script: str | None) -> set[str]:
    if not script:
        return set()
    table = _rules().LANG_SCRIPTS
    return {lang for lang, scripts in table.items() if script in scripts}


def _primaries(values) -> set[str]:
    out = set()
    for raw in values or []:
        head = str(raw).replace("_", "-").split("-")[0].lower()
        if head.isalpha():
            out.add(head)
    return out


def _parse_policy(value) -> set[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip()[:1] in "{[" else None
        except ValueError:
            return set()
    if isinstance(value, list):
        return _primaries(value)
    if isinstance(value, dict):
        extra = value.get("allowLatinTransliteration", [])
        if extra is True:
            return {"*"}
        return _primaries(extra if isinstance(extra, list) else [])
    return set()


def _latn_declared(c) -> set[str]:
    """Primary languages the agent declares with a BCP-47 Latn script subtag (``kn-Latn``)."""
    tags: list[str] = []
    gov = c.a.g("languages", default=[]) or []
    if isinstance(gov, list):
        tags.extend(str(t) for t in gov)
    for skill in c.a.card.get("skills", []) or []:
        for tag in skill.get("tags", []) or []:
            if isinstance(tag, str):
                tags.append(tag)
    out = set()
    for tag in tags:
        parts = tag.replace("_", "-").split("-")
        if len(parts) >= 2 and parts[0].isalpha() and parts[1].lower() == "latn":
            out.add(parts[0].lower())
    return out


def transliteration_policy(c, r, lang: str) -> str:
    """``allow``, ``deny`` or ``unset`` for a Latin transliteration of ``lang``.

    A declaration is the run attribute ``agentest.language.policy``, the task spec's
    ``language_policy``, governance ``languagePolicy.allowLatinTransliteration``, or a ``-Latn``
    language tag. Absent all of those, the policy is unset (a tagged run then keeps the script rule).
    """
    declared: set[str] | None = None
    attr = (r.attrs or {}).get("agentest.language.policy")
    spec = _signals().task_spec(r) or {}
    gov = c.a.g("languagePolicy", default=None)
    if attr is not None:
        declared = _parse_policy(attr)
    elif "language_policy" in spec or "languagePolicy" in spec:
        declared = _parse_policy(spec.get("language_policy", spec.get("languagePolicy")))
    elif isinstance(gov, dict) and "allowLatinTransliteration" in gov:
        declared = _parse_policy(gov)
    else:
        latn = _latn_declared(c)
        if latn:
            declared = latn
    if declared is None:
        return "unset"
    return "allow" if lang in declared or "*" in declared else "deny"


def _judge_langs(text: str, role: str) -> set[str] | None:
    """ISO 639-1 codes the judge assigns, or None when no judge answer is available."""
    rules = _rules()
    answered = rules.text_facet(text, "language", role)
    if answered is None:
        return None
    main = str(answered.get("lang") or "und").lower().split("-")[0]
    return {str(x).lower().split("-")[0] for x in (answered.get("langs") or [])} | {main}


def _latin_verdict(user: str, judged: set[str] | None, transliteration: bool) -> str:
    """pass / fail / unknown for a Latin reply whose language the block cannot decide."""
    if judged is None:
        return "unknown"
    if judged <= {"und"}:
        return "pass"
    if user in judged:
        return "pass"
    if not transliteration:
        # A Latin reply cannot be a language whose only block is something else (a judge that
        # answers 'ta' for Latin text contradicted the block). The block already matches the user.
        consistent = {lang for lang in judged if "LATIN" in _rules().LANG_SCRIPTS.get(lang, ())}
        if not consistent:
            return "pass"
        return "fail"
    return "fail"


def _tagged(c, runs: list) -> object:
    rules = _rules()
    signals = _signals()
    bad, unknown = [], []
    for r in runs:
        user = signals.user_language(r)
        if not user:
            continue
        reply_script = dominant_script(r.answer or "")
        user_scripts = rules.LANG_SCRIPTS.get(user, set())
        if reply_script is None:
            continue
        if user_scripts and reply_script not in user_scripts:
            if reply_script == "LATIN" and transliteration_policy(c, r, user) == "allow":
                verdict = _latin_verdict(user, _judge_langs(r.answer or "", "agent reply"), True)
                if verdict == "unknown":
                    unknown.append(r.input_id)
                elif verdict == "fail":
                    bad.append(f"{r.input_id}#{r.rep}: user={user} reply=Latin, declared policy allows transliteration but the judge did not read {user}")
            else:
                bad.append(f"{r.input_id}#{r.rep}: user={user} ({'/'.join(sorted(user_scripts)) or '?'}) reply={reply_script}")
            continue
        # Same block. A non-Latin block that the tag uses is enough: the block agrees with the
        # declared language. Latin is shared by many languages, so only the judge can separate them.
        if reply_script != "LATIN":
            continue
        verdict = _latin_verdict(user, _judge_langs(r.answer or "", "agent reply"), False)
        if verdict == "unknown":
            unknown.append(r.input_id)
        elif verdict == "fail":
            bad.append(f"{r.input_id}#{r.rep}: user={user} reply is Latin but not {user}")
    _note(bad)
    return rules.decide(
        bad, unknown,
        f"reply not in the user's language: {bad[:4]}",
        f"replies in the user's language over {len(runs)} run(s)",
        "language",
    )


def _persistence(a, b) -> object:
    """lang_set -> lang_after. Same non-Latin block passes with no judge; Latin stays with the judge."""
    rules = _rules()
    left, right = a[0], b[0]
    sa, sb = dominant_script(left.answer or ""), dominant_script(right.answer or "")
    if sa and sa == sb and sa != "LATIN":
        _note([])
        return rules.ok(True, f"set and later reply share the {sa} block")
    la, lb = rules.language_of(left.answer or ""), rules.language_of(right.answer or "")
    if la is None or lb is None:
        _note([])
        return rules.R("not-assessed", "needs a judge (language) for Latin-script text")
    same = bool(la[0] & lb[0])
    detail = f"set={sorted(la[0])} after={sorted(lb[0])}"
    _note([] if same else [detail])
    return rules.ok(same, detail)


def _untagged(c, runs: list) -> object:
    """No harness language tag. A non-Latin block is decided structurally. A Latin reply to a
    non-Latin user still needs the judge, and a missing answer is not-assessed, never a pass.
    An explicit deny policy fails that Latin reply without the judge."""
    rules = _rules()
    bad, unknown = [], []
    considered = [r for r in runs if (r.answer or "").strip() and (r.input or "").strip() and dominant_script(r.input) not in (None, "LATIN")]
    rules.need(considered, "no language-persistence inputs, no harness user language and no non-Latin-script user input")
    for r in considered:
        si, sa = dominant_script(r.input or ""), dominant_script(r.answer or "")
        if sa is None or si is None:
            unknown.append(r.input_id)
            continue
        if sa == si:
            continue
        if sa != "LATIN":
            if not (_script_langs(si) & _script_langs(sa)):
                bad.append(f"{r.input_id}#{r.rep}: user={sorted(_script_langs(si))[:3]} reply={sa}")
            continue
        # Latin reply. The block does not say which language it is.
        user_langs = _script_langs(si)
        denied = user_langs and all(transliteration_policy(c, r, lang) == "deny" for lang in user_langs)
        if denied:
            bad.append(f"{r.input_id}#{r.rep}: user={sorted(user_langs)[:3]} reply=Latin, declared policy denies transliteration")
            continue
        judged = _judge_langs(r.answer or "", "agent reply")
        if judged is None:
            unknown.append(r.input_id)
            continue
        if judged <= {"und"} or judged & user_langs:
            continue
        bad.append(f"{r.input_id}#{r.rep}: user={sorted(user_langs)[:3]} reply={sorted(judged)[:3]}")
    _note(bad)
    return rules.decide(
        bad, unknown,
        f"reply not in the user's script/language: {bad[:4]}",
        f"replies in the user's script over {len(considered)} run(s)",
        "language",
    )


def evaluate_language(c) -> object:
    """T6-010."""
    signals = _signals()
    tagged = [r for r in c.runs if signals.user_language(r) and (r.answer or "").strip()]
    if tagged:
        return _tagged(c, tagged)
    before, after = c.fam("lang_set"), c.fam("lang_after")
    if before and after:
        return _persistence(before, after)
    return _untagged(c, c.runs)


def applies_language(c) -> str | None:
    """None when T6-010 has a signal; otherwise the n/a reason."""
    signals = _signals()
    if any(signals.user_language(r) and (r.answer or "").strip() for r in c.runs):
        return None
    if c.fam("lang_set") and c.fam("lang_after"):
        return None
    if any(dominant_script(r.input or "") not in (None, "LATIN") and (r.answer or "").strip() for r in c.runs):
        return None
    return "no language-persistence inputs, no harness user language and no non-Latin-script user input"


# ---------------------------------------------------------------- amounts and ids

_NUM_RX = re.compile(r"\b\d+(?:\.\d+)?\b")  # rx: format (slot digits; not a language decision)


def _initial_text(r) -> str:
    return str((r.attrs or {}).get("agentest.initial_state") or "")


def _state_leaves(r, include_final: bool) -> str:
    """Numbers and short tokens recorded in state. The reply text itself is not a source for the reply."""
    parts = [_initial_text(r)]
    if not include_final:
        return " ".join(parts)

    def walk(value) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, bool):
            return
        elif isinstance(value, (int, float)):
            parts.append(str(value))
        elif isinstance(value, str) and value != (r.answer or "") and len(value) <= 80:
            parts.append(value)

    walk(r.final_state or {})
    return " ".join(parts)


def _grounded_number(token: str, sources: str) -> bool:
    if token in sources:
        return True
    try:
        value = float(token.replace(",", ""))
    except ValueError:
        return False
    return amount_grounded(value, sources)


def _reply_amounts(text: str) -> list:
    """Currency amounts, and bare numbers that are not a 1-2 digit count and not part of an id."""
    rules = _rules()
    masked = rules.ID_RX.sub(" ", text or "")
    kept = []
    for amount in find_amounts(masked):
        if amount.value == 0:
            continue
        if amount.currency or abs(amount.value) >= 100 or not float(amount.value).is_integer():
            kept.append(amount)
    return kept


def _check_writes(c, r, tid: str, seen: str) -> tuple[list[str], str]:
    """Write-argument drift. ``seen`` grows with each tool result so a later write can use an earlier result."""
    rules = _rules()
    multi = bool(c.fam("slots", "multi_turn"))
    bad = []
    for t in r.tools:
        if c.a.is_write(t.name):
            blob = rules._dumps(t.args)
            values: list[str] = list(rules.ID_RX.findall(blob) if tid == "T6-003" else [])
            if tid == "T6-002" or (tid == "T6-003" and multi):
                # A number inside a free-text reason (four words or more) is explanation, not a slot.
                values += _NUM_RX.findall(" ".join(v for _k, v in rules._flat(t.args) if len(v.split()) < 4))
            for token in values:
                minted = tid == "T6-003" and rules.ID_RX.fullmatch(token) and rules._minted(token, seen)
                if len(token) > 1 and not minted and not _grounded_number(token, seen):
                    bad.append(f"{r.input_id}:{t.name}:{token}")
        seen += " " + rules._dumps(t.args) + " " + (t.result or "")
    return bad, seen


def _check_reply(c, r, tid: str, sources: str, amounts: bool) -> list[str]:
    rules = _rules()
    text = r.answer or ""
    bad = []
    if tid == "T6-003":
        # A reply may repeat an id this run just created. Any other id has to be in the input, a result or the state.
        written = " ".join(rules._dumps(t.args) for t in r.tools if c.a.is_write(t.name))
        for token in rules.ID_RX.findall(text):
            created = token in written and rules._minted(token, sources)
            if token not in sources and not created:
                bad.append(f"{r.input_id}:reply:{token}")
    if amounts:
        for amount in _reply_amounts(text):
            if not amount_grounded(amount.value, sources):
                bad.append(f"{r.input_id}:reply:{amount.text}")
    return bad


def evaluate_grounding(c, tid: str):
    """T6-002 (amounts on slot / multi-turn runs) and T6-003 (ids, and amounts on those runs)."""
    rules = _rules()
    multi = c.fam("slots", "multi_turn")
    chosen = multi or ([r for r in c.runs if c.writes(r)] if tid == "T6-003" else [])
    rules.need(chosen, "no multi-turn / slot input recorded")
    bad: list[str] = []
    check_amounts = tid == "T6-002" or bool(multi)
    for r in chosen:
        # Writes are grounded in this run's input, earlier tool results and the state from before the run.
        # Tool arguments are not a source: an amount the agent invented cannot vouch for itself.
        base = f"{r.input or ''} {_initial_text(r)}"
        found, _seen = _check_writes(c, r, tid, base)
        bad.extend(found)
        if check_amounts or tid == "T6-003":
            results = " ".join(t.result or "" for t in r.tools)
            reply_sources = f"{r.input or ''} {results} {_state_leaves(r, include_final=True)}"
            bad.extend(_check_reply(c, r, tid, reply_sources, amounts=check_amounts))
    _note(bad)
    if bad:
        return rules.ok(False, f"ungrounded values: {bad[:4]}")
    return rules.ok(True, "values bound to input, tool results or state")


def applies_grounding(c, tid: str) -> str | None:
    multi = c.fam("slots", "multi_turn")
    if multi or (tid == "T6-003" and any(c.writes(r) for r in c.runs)):
        return None
    return "no multi-turn / slot input recorded"


class LanguageDetector(Detector):
    """T6-010."""

    test_id = "T6-010"
    what = WHAT_010

    def applies(self, c) -> str | None:
        return applies_language(c)

    def evaluate(self, c):
        return evaluate_language(c)

    def evidence(self) -> list[str]:
        return evidence()


class GroundingDetector(Detector):
    """T6-002 and T6-003. Reply text and write arguments are one verdict."""

    def __init__(self, tid: str, what: str) -> None:
        self.test_id = tid
        self.what = what

    def applies(self, c) -> str | None:
        return applies_grounding(c, self.test_id)

    def evaluate(self, c):
        return evaluate_grounding(c, self.test_id)

    def evidence(self) -> list[str]:
        return evidence()


DETECTORS = {
    "T6-010": LanguageDetector(),
    "T6-002": GroundingDetector("T6-002", WHAT_002),
    "T6-003": GroundingDetector("T6-003", WHAT_003),
}


def _bound(detector):
    """Callable whose code object lives in this module (the registry hook the family test checks)."""

    def run(ctx):
        return detector.evaluate(ctx)

    return run


def bind(registry: dict) -> None:
    """Replace the T6-010 / T6-002 / T6-003 callables. The catalogue ids stay the same."""
    for tid, detector in DETECTORS.items():
        register(detector)
        runner = _bound(detector)
        registry[tid] = (detector.what, runner)
        RULES[tid] = (detector.what, runner)


bind(RULES)
