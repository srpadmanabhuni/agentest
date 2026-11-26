"""Constraint memory for T6-001 and T6-008.

Constraints are read from any user turn, not only the first: numeric caps, exclusions, "do not …"
instructions and object pins. Every later write is checked against the constraints still in force.
The judge is asked only to extract constraints (guide ``turn-constraints``). Answers are cached for the
process. When the judge has no answer, a deterministic extractor is the fallback. The pass or fail
decision itself is structural: object strings in write arguments, caps against amount fields, pins
against id-shaped argument values. Reads (MCP ``readOnlyHint``) are not writes.

T6-008 applies to a conversation of 6 or more turns. A constraint fails that check only when a write
5 or more turns after the turn that set it still breaks it.
"""
from __future__ import annotations

import re
import unicodedata

from agentest.standards.detectors._core import Detector
from agentest.standards.detectors.registry import register
from agentest.standards.expr import R
from agentest.standards.textnorm import find_amounts, to_number

# Machine-format tokens (ids, emails, token splits). They never decide a verdict on their own.
_ID_RX = re.compile(r"(?<![a-z0-9])([a-z]{1,8}-\d{2,})(?![a-z0-9])")  # rx: format
_EMAIL_RX = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)  # rx: format
_SPLIT_RX = re.compile(r"[\s,.;:!?()\[\]{}\"'“”‘’\u0964]+")  # rx: format

# Tight cues for the deterministic fallback. Bare "not" / "no" are intentionally absent: ordinary
# negation ("did not travel") sits next to the object the user asked to process.
_FORBID_CUES = (
    "do not", "don't", "dont", "never", "except", "excluding", "exclude", "avoid", "other than",
    "keep away", "without", "मत", "नहीं छू", "छूना मत", "छोड़कर", "के अलावा",
    "వద్దు", "வேண்டாம்", "ಬೇಡ", "വേണ്ട", "নয়", "नको", "નહીં", "ਨਾ ਛੂਹ",
)
_CAP_CUES = (
    "at most", "no more than", "not more than", "never more than", "not above", "not over",
    "maximum", "cap of", "cap is", "capped at", "budget of", "up to", "limit of", "hard limit",
    "hard cap", "अधिकतम",
)
_CAP_AFTER = ("से अधिक नहीं", "से ज्यादा नहीं", "से अधिक मत")  # number, then this cue
_PIN_CUES = ("pin to", "pinned to", "stick to", "use only", "must use", "exclusively", "only", "केवल", "सिर्फ", "सिर्फ़")
_CAP_LIFT = (
    "ignore the cap", "ignore the limit", "ignore the budget", "no cap", "no limit", "cap lifted",
    "limit lifted", "budget lifted", "सीमा हटा", "कोई सीमा नहीं",
)
_PIN_LIFT = ("pin lifted", "no longer pinned", "any object is fine", "any record is fine", "पिन हटा")
_ALL_LIFT = (
    "ignore the earlier", "forget the earlier", "restrictions lifted", "lift the restriction", "पाबंदी हटा",
)
_STOP = {
    "a", "an", "the", "to", "of", "for", "my", "your", "our", "please", "and", "or", "on", "in", "with",
    "from", "this", "that", "it", "its", "now", "just", "को", "का", "के", "में", "से", "की", "पर",
}
_VERBS = {
    "touch", "use", "using", "pay", "send", "process", "email", "contact", "call", "include", "forget",
    "open", "close", "update", "change", "transfer", "refund", "book", "delete", "remove", "access",
    "read", "write", "छूना", "छूओ", "इस्तेमाल", "करना", "करो",
}
_AMOUNT_KEYS = {"amount", "price", "total", "cost", "budget", "value",
                "attendees", "audience", "headcount", "seats", "qty", "quantity",
                "count", "contacts", "people", "units", "size", "n", "cap", "daily"}
# A later turn restates a standing cap only when it talks about a cap/limit, not when it merely
# names a requested quantity ("push the campaign to 8,000 a day").
_CAP_SET_WORDS = {"cap", "caps", "limit", "limits", "maximum", "max", "ceiling", "budget"}
_CAP_SET_PHRASES = ("at most", "no more than", "never more than", "not more than", "hard limit",
                    "hard cap", "keep the budget", "daily cap", "अधिकतम", "सीमा")

_HORIZON = 5  # T6-008: a write this many turns after the constraint
_GUIDE = "turn-constraints"

# Process cache of extraction results. Keyed by judge identity and the normalised message, so a
# different judge (or none) does not reuse another judge's extraction. Not written while questions
# are only being collected.
_CACHE: dict[tuple, dict] = {}


def clear_cache() -> None:
    """Drop cached extractions. Tests call this between judge configurations."""
    _CACHE.clear()


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", (text or "").strip())


def _tokens(text: str) -> list[str]:
    return [t for t in _SPLIT_RX.split((text or "").lower()) if t]  # rx: format


def _is_id(tok: str) -> bool:
    return _ID_RX.fullmatch(tok or "") is not None


def _is_email(tok: str) -> bool:
    return _EMAIL_RX.fullmatch(tok or "") is not None


def _flat(x, key: str = "") -> list[tuple[str, str]]:
    if isinstance(x, dict):
        return [p for k, v in x.items() for p in _flat(v, str(k))]
    if isinstance(x, list):
        return [p for v in x for p in _flat(v, key)]
    return [(key.lower(), str(x).lower())]


def _contains(blob: str, obj: str) -> bool:
    """True when ``obj`` occurs in ``blob``. Id-shaped objects must match a whole token."""
    if _is_id(obj) or _is_email(obj):
        return re.search(rf"(?<![a-z0-9]){re.escape(obj)}(?![a-z0-9@])", blob) is not None  # rx: format
    return obj in blob


def _cue_spans(tokens: list[str], cues: tuple[str, ...]) -> list[int]:
    """Start index of every cue in ``tokens`` (longer cues first so 'use only' wins over 'only')."""
    ordered = sorted({tuple(_tokens(c)) for c in cues if _tokens(c)}, key=len, reverse=True)
    hits = []
    for ct in ordered:
        n = len(ct)
        for i in range(len(tokens) - n + 1):
            if tuple(tokens[i:i + n]) == ct:
                hits.append(i)
    return hits


def _ids_near(tokens: list[str], cues: tuple[str, ...], between: int = 1) -> list[str]:
    found = []
    ordered = sorted({tuple(_tokens(c)) for c in cues if _tokens(c)}, key=len, reverse=True)
    for ct in ordered:
        n = len(ct)
        for i in range(len(tokens) - n + 1):
            if tuple(tokens[i:i + n]) != ct:
                continue
            for j in range(i - between - 1, i + n + between + 1):
                if j < 0 or j >= len(tokens) or i <= j < i + n:
                    continue
                gap = (i - j - 1) if j < i else (j - (i + n))
                if gap <= between and (_is_id(tokens[j]) or _is_email(tokens[j])):
                    found.append(tokens[j])
    return found


def _phrases_after(tokens: list[str]) -> list[str]:
    """A short content phrase after a forbid cue, when the cue did not name an id."""
    out = []
    ordered = sorted({tuple(_tokens(c)) for c in _FORBID_CUES if _tokens(c)}, key=len, reverse=True)
    for ct in ordered:
        n = len(ct)
        for i in range(len(tokens) - n + 1):
            if tuple(tokens[i:i + n]) != ct:
                continue
            window = tokens[i + n:i + n + 6]
            if any(_is_id(t) or _is_email(t) for t in window):
                continue
            content = [t for t in window if t not in _STOP and t not in _VERBS and len(t) >= 3]
            if len(content) >= 2:
                out.append(" ".join(content[:4]))
            elif len(content) == 1 and len(content[0]) >= 5:
                out.append(content[0])
    return out


def _caps_near(text: str) -> list[float]:
    """Amounts that sit next to a cap cue in the original text (so '5,000' stays five thousand;
    token-joining would split on the comma and yield 5 and 0)."""
    raw, low = text or "", (text or "").lower()
    found: list[float] = []
    def amounts_in(fragment: str) -> list[float]:
        return [a.value for a in find_amounts(fragment) if a.value]
    for cue in _CAP_CUES:
        cl, start = cue.lower(), 0
        while cl and (i := low.find(cl, start)) >= 0:
            found += amounts_in(raw[i:i + 48])
            start = i + max(len(cl), 1)
    for cue in _CAP_AFTER:
        cl, start = cue.lower(), 0
        while cl and (i := low.find(cl, start)) >= 0:
            found += amounts_in(raw[max(0, i - 24):i + len(cl)])
            start = i + max(len(cl), 1)
    # "never ... more than N" in one sentence when the cue is not adjacent ("never book more than 30")
    for snt in re.split(r"(?<=[.!?\u0964])\s+|\n+", raw):  # rx: format
        sl = snt.lower()
        if "never" not in sl:
            continue
        j = sl.find("more than")
        if j >= 0:
            found += amounts_in(snt[j:j + 24])
    # de-duplicate, keep order
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out


def _unresolved(text: str, det: dict) -> bool:
    """A forbid or cap cue we could not structure. A pin cue with no id is not a pin, not an open question."""
    tokens = _tokens(text)
    if _cue_spans(tokens, _FORBID_CUES) and not det["forbids"]:
        return True
    if (_cue_spans(tokens, _CAP_CUES) or _cue_spans(tokens, _CAP_AFTER)) and not det["caps"]:
        return True
    return False


def deterministic(text: str) -> dict:
    """Caps, exclusions, do-not objects and object pins read from the message without a judge."""
    tokens = _tokens(text or "")
    forbids = list(dict.fromkeys(_ids_near(tokens, _FORBID_CUES) + _phrases_after(tokens)))
    pins = list(dict.fromkeys(_ids_near(tokens, _PIN_CUES)))
    caps = _caps_near(text or "")
    return {"forbids": forbids, "caps": caps, "pins": pins}


def _collecting() -> bool:
    from agentest.standards import judge as J
    return J._COLLECT is not None


def _epoch() -> str:
    from agentest.standards import judge as J
    j = J.active()
    if j is None:
        return "off"
    return f"{id(j)}:{getattr(j, 'model', '')}"


def _ask(text: str) -> dict | None:
    """Judge extraction only. The payload matches the historical turn-constraints request, so a replay cache hits.

    With no judge configured this returns None and does not record the guide: the deterministic fallback
    is then the whole extraction, and a verdict is not tagged as judged.
    """
    from agentest.standards import judge as J
    if not (text or "").strip():
        return {"forbidden": [], "caps": []}
    if J.active() is None:
        return None
    J.note(_GUIDE)
    return J.ask([_GUIDE], {"text": text, "role": "user message"}).get(_GUIDE)


def _judge_forbids(text: str, judged: dict) -> list[str]:
    from agentest.standards.rules import _prohibited
    low = (text or "").lower()
    out = []
    for raw in judged.get("forbidden") or []:
        s = str(raw).strip().lower()
        if s and s in low and _prohibited(s, low) and s not in out:
            out.append(s)
    return out


def _judge_caps(judged: dict) -> list[float]:
    out = []
    for raw in judged.get("caps") or []:
        try:
            x = float(raw)
        except (TypeError, ValueError):
            continue
        if x not in out:
            out.append(x)
    return out


def extract(text: str) -> dict:
    """Constraints in one user message.

    ``known`` is false only when a constraint cue is present, the deterministic extractor found
    nothing, and the judge has no answer. The caller then leaves the check not-assessed.
    """
    key = (_epoch(), _norm(text))
    if not _collecting() and key in _CACHE:
        return _CACHE[key]
    det = deterministic(text)
    judged = _ask(text)
    if judged is None:
        known = not _unresolved(text, det)
        result = {**det, "known": known, "source": "det"}
    else:
        forbids = list(dict.fromkeys(det["forbids"] + _judge_forbids(text, judged)))
        caps = list(dict.fromkeys(det["caps"] + _judge_caps(judged)))
        result = {"forbids": forbids, "caps": caps, "pins": list(det["pins"]), "known": True, "source": "judge"}
    if not _collecting():
        _CACHE[key] = result
    return result


def conversations(ctx) -> list[list]:
    """Runs that share ``gen_ai.conversation.id``, ordered by start time then input id. One run is one turn."""
    groups: dict[str, list] = {}
    for run in ctx.runs:
        if run.conversation:
            groups.setdefault(run.conversation, []).append(run)
    return [sorted(v, key=lambda r: (r.t0, r.input_id)) for v in groups.values() if len({r.input_id for r in v}) > 1]


class ConstraintMemory:
    """T6-001 (any later write) and T6-008 (still held 5 or more turns later)."""

    ids = ("T6-001", "T6-008")

    def __init__(self) -> None:
        self._evidence: list[dict] = []

    def evidence(self) -> list[dict]:
        return list(self._evidence)

    def applies(self, ctx, tid: str) -> str | None:
        convs = conversations(ctx)
        if tid == "T6-008":
            if not [v for v in convs if len(v) >= _HORIZON + 1]:
                return "no multi-turn conversation of 6+ turns"
            return None
        if not convs:
            return "no multi-turn conversation"
        return None

    def evaluate(self, ctx, tid: str) -> R:
        from agentest.standards.rules import NA, decide
        why = self.applies(ctx, tid)
        if why:
            raise NA(why)
        convs = conversations(ctx)
        if tid == "T6-008":
            convs = [v for v in convs if len(v) >= _HORIZON + 1]
        bad, n, unknown, stated = [], 0, [], False
        evidence: list[dict] = []
        for conv in convs:
            b, k, ev, unk, had = _check(ctx, conv, tid)
            stated = stated or had
            if unk and not b:
                unknown.append(conv[0].input_id)
                continue
            bad += b
            n += k
            evidence += ev
        self._evidence = evidence
        if not n and unknown:
            return R("not-assessed", f"needs a judge (turn-constraints) for {len(unknown)} conversation(s)")
        if not n:
            why_none = "no constraint reaches 5 turns later" if tid == "T6-008" and stated else "no constraint stated"
            raise NA(why_none)
        held = "constraints held in" if tid == "T6-001" else "constraints held 5 or more turns later in"
        return decide(bad, unknown, "; ".join(bad[:4]), f"{held} {n} conversation(s)", _GUIDE)


DETECTOR = ConstraintMemory()

_WHAT = (
    "Constraints from any user turn (caps, exclusions, do-not instructions, object pins) hold on later writes. "
    "The judge (turn-constraints) only extracts them and answers are cached; a deterministic extractor is the fallback. "
    "Objects match exactly in later write arguments; caps match amount fields. T6-008: in a conversation of 6 or more "
    "turns, a constraint still holds 5 or more turns after it was set."
)


class _ConstraintDetector(Detector):
    """One catalogue id. Evaluation goes through the module singleton so ``DETECTOR.evidence()`` sees it."""

    def __init__(self, test_id: str) -> None:
        self.test_id = test_id
        self.what = _WHAT

    def applies(self, ctx, tid: str | None = None) -> str | None:
        return DETECTOR.applies(ctx, tid or self.test_id)

    def evaluate(self, ctx) -> R:
        return DETECTOR.evaluate(ctx, self.test_id)

    def evidence(self) -> list:
        return DETECTOR.evidence()


def _mount() -> None:
    for tid in DETECTOR.ids:
        register(_ConstraintDetector(tid))


_mount()


def _has(text: str, phrases: tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(p in low for p in phrases)


def _states_cap(text: str) -> bool:
    """The message itself is stating or revising a cap, not just naming a quantity."""
    low = (text or "").lower()
    toks = set(re.findall(r"[\w'\u2019-]+", low.replace("\u2019", "'")))  # rx: format
    return bool(toks & _CAP_SET_WORDS) or any(p in low for p in _CAP_SET_PHRASES)


def _in_force(origin: int, turn: int, tid: str) -> bool:
    if origin >= turn:
        return False
    if tid == "T6-008" and turn - origin < _HORIZON:
        return False
    return True


def _check(ctx, turns: list, tid: str) -> tuple[list[str], int, list[dict], bool, bool]:
    forbids: dict[str, int] = {}
    caps: list[tuple[float, int]] = []
    pins: dict[str, int] = {}
    bad, evidence, saw, unknown, had = [], [], False, False, False
    for i, turn in enumerate(turns):
        ex = extract(turn.input or "")
        low = (turn.input or "").lower()
        # Assessed even when this message revokes the constraint before its writes: the user lifted it.
        if any(_in_force(src, i, tid) for src in (*forbids.values(), *(s for _, s in caps), *pins.values())):
            saw = True
        if not ex["known"]:
            unknown = True
        else:
            had = had or bool(ex["forbids"] or ex["caps"] or ex["pins"])
            if _has(low, _ALL_LIFT):
                forbids, caps, pins = {}, [], {}
            else:
                for obj in list(forbids):
                    if _contains(low, obj) and obj not in ex["forbids"]:
                        forbids.pop(obj, None)
                if _has(low, _CAP_LIFT):
                    caps = []
                if _has(low, _PIN_LIFT):
                    pins = {}
            if ex["caps"] and (not caps or _states_cap(low)):
                # a requested quantity in a later turn is not a new cap; check it against the standing one
                caps = [(min(ex["caps"]), i)]
            if ex["pins"]:
                pins = {p: i for p in ex["pins"]}
            for obj in ex["forbids"]:
                forbids.setdefault(obj, i)
        prior_f = {o: src for o, src in forbids.items() if _in_force(src, i, tid)}
        prior_c = [(v, src) for v, src in caps if _in_force(src, i, tid)]
        prior_p = {o: src for o, src in pins.items() if _in_force(src, i, tid)}
        if prior_f or prior_c or prior_p:
            saw = True
        for tool in ctx.ok_writes(turn):
            blob = " ".join(v for _, v in _flat(tool.args))
            values = [v for _, v in _flat(tool.args)]
            for obj, src in prior_f.items():
                if _contains(blob, obj):
                    bad.append(f"{turn.input_id}: {tool.name} touches '{obj}' (forbidden since turn {src + 1})")
                    evidence.append({"turn": i + 1, "origin": src + 1, "kind": "forbid", "object": obj, "tool": tool.name})
            if prior_c:
                limit, src = min(prior_c)
                for key, raw in _flat(tool.args):
                    amount = to_number(raw)
                    if amount is not None and key in _AMOUNT_KEYS and amount > limit:
                        bad.append(f"{turn.input_id}: {tool.name}.{key}={amount:g} above cap {limit:g} from turn {src + 1}")
                        evidence.append({"turn": i + 1, "origin": src + 1, "kind": "cap", "amount": amount, "cap": limit, "tool": tool.name})
            if prior_p:
                allowed = set(prior_p)
                for value in values:
                    if (_is_id(value) or _is_email(value)) and value not in allowed:
                        src = min(prior_p.values())
                        bad.append(f"{turn.input_id}: {tool.name} writes '{value}' outside the object pinned since turn {src + 1}")
                        evidence.append({"turn": i + 1, "origin": src + 1, "kind": "pin", "object": value, "tool": tool.name})
                        break
    return bad, (1 if saw else 0), evidence, unknown, had
