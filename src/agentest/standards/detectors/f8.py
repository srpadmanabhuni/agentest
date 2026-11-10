"""Family F8: reply language (T6-010) and numeric / id grounding (T6-002, T6-003).

Language is decided from the Unicode block of the letters first. The judge (guide ``language``) is
asked only when that block is shared by more than one language, or when a declared policy allows a
Latin transliteration of a non-Latin language. A missing judge answer is not-assessed, never a pass.

Every amount and identifier in a reply or a write must occur in the user input, a tool result or the
recorded state. The same value counts after normalisation (whitespace, case, thousands separators, and
any Unicode currency symbol). User text grounds only the root trace it was written in, even when another
root trace carries the same conversation id. Tool outputs may ground later root traces that share that
id. Digits inside an identifier are not an amount unless a tool returned them as their own value. An
identifier prefix or suffix counts only when the shared core is distinctive and that prefix appears in the
same conversation. A missing prior tool result is not-assessed, not a fail. Detectors read declared
metadata only: the user-language tag, governance ``languagePolicy`` / BCP-47 ``-Latn`` tags, the task
spec, MCP ``readOnlyHint`` and state snapshots.
"""

from __future__ import annotations

import json
import re
import unicodedata

from agentest.standards.detectors._core import RULES, Detector
from agentest.standards.detectors.registry import register
from agentest.standards.textnorm import find_amounts

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
    "Amounts in a reply or a write trace to the user input, a tool result or the recorded state. Matching is "
    "normalised (whitespace, case, thousands separators, and any Unicode currency symbol). A unit on the "
    "number is the same amount. User text grounds only that root trace, even when another root trace shares "
    "the conversation id. Tool outputs, including nested JSON, may ground a later root trace with the same id. "
    "Digits inside an identifier are not an amount unless a tool returned them as their own value. A number "
    "inside a free-text reason is not a slot value. When a prior tool result was not recorded, the verdict is "
    "not-assessed. T6-002 runs on slot and multi-turn inputs."
)
WHAT_003 = (
    "Entity ids, and on slot / multi-turn inputs the amounts, in a reply or a write trace to the user input, "
    "a tool result or the recorded state. Matching is normalised (whitespace, case, thousands separators, and "
    "any Unicode currency symbol). User text grounds only that root trace; tool outputs may ground a later "
    "root trace with the same conversation id. A prefix or suffix is the same id only when the shared core is "
    "distinctive (six or more characters, or letters and digits) and that prefix appears in the same conversation. "
    "Digits inside an identifier are not an amount unless a tool returned them as their own value. A fresh id for "
    "a new record (no earlier id of that prefix) is not drift. When a prior tool result was not recorded, the "
    "verdict is not-assessed."
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
# An identifier token: letters, then digits, with optional separators and a trailing affix.
_ID_SPAN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{1,8}(?:[-_./ \u00a0]*\d{2,})+(?:[-_./ \u00a0]+[A-Za-z0-9]+)*")  # rx: format
_PART = re.compile(r"[a-z]+|\d+")  # rx: format (identifier pieces; not a language decision)
# Thousands separators between digits: comma, underscore, apostrophe, and Unicode spaces.
# A plain space joins digits only in groups of three, so "12 99" stays two numbers.
_GROUP_SEP = re.compile(r"(?<=\d)[,_\u00a0\u202f\u2007\u2009'\u2019](?=\d)")  # rx: format
_SPACE_GROUP = re.compile(r"(?<=\d) (?=\d{3}(?!\d))")  # rx: format
# A spaced or hyphenated run of 4-digit groups is one token (a long id), not several short numbers.
_GROUPED_DIGITS = re.compile(r"\b\d{4}(?:[ \u00a0-]\d{4}){2,}\b")  # rx: format


def _strip_sc(text: str) -> str:
    """Drop currency symbols by Unicode category, not by a list of symbols."""
    return "".join(ch for ch in text if unicodedata.category(ch) != "Sc")


def _normalize_numeric_text(text: str) -> str:
    raw = _GROUP_SEP.sub("", _strip_sc(text or ""))
    folded = unicodedata.normalize("NFKC", raw)
    # NFKC turns a narrow no-break space into a plain space; strip that grouping too.
    return _SPACE_GROUP.sub("", _GROUP_SEP.sub("", folded))


def _maybe_json(value):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if raw[:1] in "{[":
            try:
                return json.loads(raw)
            except ValueError:
                return None
    return None


def _id_key(token: str) -> tuple[str, ...] | None:
    """Case-folded identifier pieces. Digit pieces drop leading zeros so ``0305`` and ``305`` match."""
    folded = _strip_sc(unicodedata.normalize("NFKC", str(token)).casefold())
    parts: list[str] = []
    for match in _PART.finditer(folded):
        piece = match.group(0)
        parts.append(str(int(piece)) if piece.isdigit() else piece)
    if not any(p.isdigit() for p in parts) or not any(p.isalpha() for p in parts):
        return None
    return tuple(parts)


def _as_number(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = _normalize_numeric_text(value).strip()
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", cleaned):  # rx: format
            try:
                return float(cleaned)
            except ValueError:
                return None
    return None


def _distinctive(core: str) -> bool:
    """A bare id core can take a prefix only when it is long, or letters and digits together."""
    if len(core) >= 6:
        return True
    return any(ch.isalpha() for ch in core) and any(ch.isdigit() for ch in core)


def _bounded(hay: str, needle: str) -> bool:
    """Case-insensitive whole-token match. ``QX-2001`` does not match inside ``QX-20019``."""
    if not needle or not hay:
        return False
    folded = hay.casefold()
    want = needle.casefold()
    start = 0
    while True:
        at = folded.find(want, start)
        if at < 0:
            return False
        before = folded[at - 1] if at else ""
        after = folded[at + len(want):at + len(want) + 1]
        if (not before or not before.isalnum()) and (not after or not after.isalnum()):
            return True
        start = at + 1


class _Corpus:
    """Observations from one conversation. The call's own arguments are not added."""

    def __init__(self) -> None:
        self.raw: list[str] = []
        self.numbers: set[float] = set()
        self.ids: list[tuple[str, ...]] = []
        self.complete = True

    def text(self) -> str:
        return "\n".join(self.raw)

    def add_text(self, text: str) -> None:
        if not text:
            return
        self.raw.append(text)
        # Keep the raw text for literal matches. Do not split a long grouped id into short numbers.
        scanned = _GROUPED_DIGITS.sub(" ", text)
        norm = _normalize_numeric_text(scanned)
        for amount in find_amounts(norm):
            self.numbers.add(amount.value)
        for span in _ID_SPAN.findall(text):
            key = _id_key(span)
            if key:
                self.ids.append(key)
        masked = _ID_SPAN.sub(" ", scanned)
        for tok in _NUM_RX.findall(_normalize_numeric_text(masked)):
            try:
                value = float(tok)
            except ValueError:
                continue
            self.numbers.add(value)
            if re.fullmatch(r"\d+", tok) and len(str(int(tok))) >= 6:  # rx: format
                # A long bare number can be the core of a prefixed id. A short one cannot.
                self.ids.append((str(int(tok)),))

    def add_json(self, node, depth: int = 0) -> None:
        if node is None or depth > 8:
            return
        if isinstance(node, str):
            parsed = _maybe_json(node)
            if parsed is not None:
                self.add_json(parsed, depth + 1)
            else:
                self.add_text(node)
            return
        if isinstance(node, list):
            for item in node:
                self.add_json(item, depth + 1)
            return
        if isinstance(node, dict):
            for value in node.values():
                self.add_json(value, depth + 1)
            return
        if isinstance(node, bool):
            return
        number = _as_number(node)
        if number is None:
            return
        self.numbers.add(number)
        if float(number).is_integer() and abs(number) < 1e15 and len(str(int(number))) >= 6:
            self.ids.append((str(int(number)),))

    def add_tool(self, tool) -> None:
        """A prior tool's output. Arguments are not a source."""
        parsed = _maybe_json(tool.result) if (tool.result or "").strip() else None
        if parsed is not None:
            self.add_json(parsed)
        elif (tool.result or "").strip():
            self.add_text(tool.result)

    def add_state(self, state, skip: str = "") -> None:
        def walk(node) -> None:
            if isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
            elif isinstance(node, str):
                if skip and node == skip:
                    return
                self.add_json(node)
            elif not isinstance(node, bool):
                self.add_json(node)

        walk(state)

    def _close(self, left: float, right: float) -> bool:
        return abs(left - right) <= max(0.005, abs(right) * 1e-9)

    def _number_text(self) -> str:
        """Running text with identifiers removed, so their digits are not amounts."""
        return _ID_SPAN.sub(" ", self.text())

    def number_grounded(self, shown: str, value: float) -> bool:
        # A whole token only. ``2001`` is not grounded by the digits inside ``QX-2001``.
        hay = self._number_text()
        if shown and _bounded(hay, shown):
            return True
        if float(value).is_integer() and _bounded(hay, str(int(round(value)))):
            return True
        return any(self._close(value, other) for other in self.numbers)

    def _prefix_attested(self, prefix: str) -> bool:
        """The letter prefix occurs in this conversation, not only on the candidate."""
        return _bounded(self.text(), prefix)

    def _affix_grounded(self, key: tuple[str, ...]) -> bool:
        for other in self.ids:
            if key == other:
                return True
            short, long = (other, key) if len(other) <= len(key) else (key, other)
            if len(short) == len(long):
                continue
            at_start = long[:len(short)] == short
            at_end = long[-len(short):] == short
            if not at_start and not at_end:
                continue
            if not _distinctive("".join(short)):
                continue
            # A letter prefix was added in front of the core. It must already appear here.
            if at_end and not at_start:
                added = long[:-len(short)]
                if not added or not all(part.isalpha() for part in added):
                    continue
                if not self._prefix_attested(added[0]):
                    continue
            return True
        return False

    def id_grounded(self, token: str) -> bool:
        key = _id_key(token)
        if key and key in self.ids:
            return True
        if _bounded(self.text(), token):
            return True
        if key and self._affix_grounded(key):
            return True
        return False

    def body_seen(self, token: str) -> bool:
        """The id's numeric body is already a value in this conversation, so a prefixed copy is not a new record."""
        key = _id_key(token)
        if not key:
            return False
        bodies = [part for part in key if part.isdigit()]
        if not bodies:
            return False
        body = float(bodies[-1])
        return any(self._close(body, number) for number in self.numbers)

    def fresh_id(self, token: str) -> bool:
        """A new record: its prefix has not been seen, and its body is not a value already in the conversation."""
        rules = _rules()
        if not rules.ID_RX.fullmatch(token) or not rules._minted(token, self.text()):
            return False
        return not self.body_seen(token)


def _session_of(run) -> str:
    """Full conversation id. An empty id means this root trace is its own session."""
    return str(getattr(run, "conversation", "") or "").strip()


def _earlier_runs(c, run) -> list:
    """Earlier turns that carry the same conversation id. A different id, or no id, stays outside."""
    key = _session_of(run)
    if not key:
        return []
    here = (int(getattr(run, "t0", 0) or 0), int(getattr(run, "rep", 0) or 0), str(getattr(run, "input_id", "")))
    found = []
    for other in c.runs:
        if other is run or _session_of(other) != key:
            continue
        stamp = (int(getattr(other, "t0", 0) or 0), int(getattr(other, "rep", 0) or 0), str(getattr(other, "input_id", "")))
        if stamp < here:
            found.append(other)
    return found


def _recorded(tool) -> bool:
    """An empty result with no error was not captured. ``{}`` and an error payload were."""
    if tool.error:
        return True
    return bool((tool.result or "").strip())


def _preamble(c, run) -> _Corpus:
    corpus = _Corpus()
    corpus.add_text(run.input or "")
    corpus.add_text(str((run.attrs or {}).get("gen_ai.system_instructions") or ""))
    initial = (run.attrs or {}).get("agentest.initial_state")
    if initial is not None:
        corpus.add_text(initial if isinstance(initial, str) else json.dumps(initial, default=str))
        corpus.add_json(_maybe_json(initial) if not isinstance(initial, (dict, list)) else initial)
    for prev in _earlier_runs(c, run):
        # User text stays in its own root trace. A shared conversation id does not copy it forward.
        # Tool outputs from an earlier root trace of this conversation still count.
        for tool in prev.tools:
            if _recorded(tool):
                corpus.add_tool(tool)
    return corpus


def _slot_numbers(value: str) -> list[tuple[str, float]]:
    """Numbers in one short slot. A grouped amount (``1,500``, a currency symbol, a unit) stays one number.
    Digits that belong to an identifier in the same slot are not a second amount."""
    norm = _normalize_numeric_text(_ID_SPAN.sub(" ", value))
    found = list(find_amounts(norm))
    if not found:
        found_pairs = []
        for tok in _NUM_RX.findall(norm):
            try:
                found_pairs.append((tok, float(tok)))
            except ValueError:
                continue
        return found_pairs
    return [(amount.text, amount.value) for amount in found]


def _reply_amounts(text: str) -> list:
    """Currency amounts, and bare numbers that are not a 1-2 digit count and not part of an id."""
    rules = _rules()
    raw = text or ""
    masked = rules.ID_RX.sub(" ", raw)
    norm = _normalize_numeric_text(masked)
    money: set[float] = set()
    for index, ch in enumerate(raw):
        if unicodedata.category(ch) != "Sc":
            continue
        window = _normalize_numeric_text(raw[max(0, index - 12):index + 16])
        for amount in find_amounts(window):
            money.add(round(amount.value, 4))
    kept = []
    for amount in find_amounts(norm):
        if amount.value == 0:
            continue
        marked = amount.currency or round(amount.value, 4) in money
        if marked or abs(amount.value) >= 100 or not float(amount.value).is_integer():
            kept.append(amount)
    return kept


def _check_writes(c, r, tid: str, corpus: _Corpus) -> tuple[list[str], list[str]]:
    """Write-argument drift. Each tool output is added after the call is judged."""
    rules = _rules()
    multi = bool(c.fam("slots", "multi_turn"))
    definite, unclear = [], []
    for t in r.tools:
        if c.a.is_write(t.name):
            blob = rules._dumps(t.args)
            values: list[tuple[str, str | None]] = []
            if tid == "T6-003":
                values += [(token, None) for token in rules.ID_RX.findall(blob)]
            if tid == "T6-002" or (tid == "T6-003" and multi):
                # A number inside a free-text reason (four words or more) is explanation, not a slot.
                for _key, slot in rules._flat(t.args):
                    if len(slot.split()) >= 4:
                        continue
                    values += [(shown, str(number)) for shown, number in _slot_numbers(slot)]
            for token, numeric in values:
                fresh = numeric is None and corpus.fresh_id(token)
                if numeric is None:
                    grounded = corpus.id_grounded(token)
                else:
                    grounded = corpus.number_grounded(token, float(numeric))
                if len(token) > 1 and not fresh and not grounded:
                    (unclear if not corpus.complete else definite).append(f"{r.input_id}:{t.name}:{token}")
        if not _recorded(t):
            corpus.complete = False
        else:
            corpus.add_tool(t)
    return definite, unclear


def _check_reply(c, r, tid: str, corpus: _Corpus, amounts: bool) -> tuple[list[str], list[str]]:
    rules = _rules()
    text = r.answer or ""
    definite, unclear = [], []

    def keep(label: str) -> None:
        (unclear if not corpus.complete else definite).append(label)

    if tid == "T6-003":
        # A reply may repeat an id this run just created. Any other id has to be in the input, a result or the state.
        written = " ".join(rules._dumps(t.args) for t in r.tools if c.a.is_write(t.name))
        for token in rules.ID_RX.findall(text):
            created = token in written and corpus.fresh_id(token)
            if not corpus.id_grounded(token) and not created:
                keep(f"{r.input_id}:reply:{token}")
    if amounts:
        for amount in _reply_amounts(text):
            if not corpus.number_grounded(amount.text, amount.value):
                keep(f"{r.input_id}:reply:{amount.text}")
    return definite, unclear


def evaluate_grounding(c, tid: str):
    """T6-002 (amounts on slot / multi-turn runs) and T6-003 (ids, and amounts on those runs)."""
    rules = _rules()
    multi = c.fam("slots", "multi_turn")
    chosen = multi or ([r for r in c.runs if c.writes(r)] if tid == "T6-003" else [])
    rules.need(chosen, "no multi-turn / slot input recorded")
    definite: list[str] = []
    unclear: list[str] = []
    check_amounts = tid == "T6-002" or bool(multi)
    for r in chosen:
        # Writes are grounded in the user text, earlier tool outputs and the state from before the run.
        # Tool arguments are not a source: an amount the agent invented cannot vouch for itself.
        corpus = _preamble(c, r)
        found, pending = _check_writes(c, r, tid, corpus)
        definite.extend(found)
        unclear.extend(pending)
        if check_amounts or tid == "T6-003":
            reply = _preamble(c, r)
            for tool in r.tools:
                if not _recorded(tool):
                    reply.complete = False
                else:
                    reply.add_tool(tool)
            reply.add_state(r.final_state or {}, skip=r.answer or "")
            found, pending = _check_reply(c, r, tid, reply, amounts=check_amounts)
            definite.extend(found)
            unclear.extend(pending)
    _note(definite or unclear)
    if definite:
        return rules.ok(False, f"ungrounded values: {definite[:4]}")
    if unclear:
        return rules.R("not-assessed", "provenance undeterminable: a prior tool result was not recorded")
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
