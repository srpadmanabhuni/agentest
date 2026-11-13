"""Tool-call misuse. Schemas and the toolset come from the MCP tool list, a tool
catalogue on the task spec, or the root-span attribute ``agentest.toolset``.
Nothing here names a tool, an agent or a case.

Each finding is routed only to the check whose definition matches it:

* allowed value (enum or const) -> T1-010, T5-003
* tool outside the declared toolset -> T5-001 (any call), T5-018 (accepted call)
* a numeric slot changes across a later tool or a later turn -> T6-002
* an identifier slot changes the same way -> T6-003

T1-010 and T5-003 are allowed-value checks. A missing field or a wrong JSON type
is not reported on those ids, and it is not reported on X-035 either: that check
keeps the meaning it had before this family. T6-002 is cross-turn drift of a
numeric slot. The same tool repeating inside one run is not that drift. A trailing
suffix is a unit only when it is an ISO 4217 currency code or a common unit code.
``amount`` and ``amount_inr`` are one slot. ``amount_usd`` and ``amount_inr`` are
not, nor are ``weight_kg`` and ``weight_lb``. Ambiguous suffixes are not units
(``in``, ``min``, ``s``, ``m``, ``t``, ``v``, ``w``, ``g``, ``h``, ``l``, ``b``,
``pc``, ``mt``, and the currency words ``all``, ``top``, ``try``, ``cup``, ``pen``,
``mad``, ``sos``, ``php``, ``bob``), so ``price_min`` is not ``price``. ``min``
is minutes only on a vowelless stem, so ``ttl_min`` is ``ttl`` and ``price_min``
is not ``price``. ``_id``, ``_size``, ``_date`` and ``_time`` are never stripped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from agentest.standards import signals as SG
from agentest.standards.detectors.registry import register_refiner as register
from agentest.standards.expr import R

# Machine formats: a numeric token, a whole-value numeric scalar, an identifier.  # rx: format
_NUM_TOKEN = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")  # rx: format
_NUM_SCALAR = re.compile(r"[₹$€]?\s*([-+]?\d[\d,]*(?:\.\d+)?)")  # rx: format
_ID_TOKEN = re.compile(r"[A-Za-z]{1,8}[-_][A-Za-z0-9]{2,}|[A-Za-z]{2,}\d{2,}")  # rx: format
_DOZEN = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an)\s+dozen\b|\bdozen\b", re.I)  # rx: format
_WORD_QTY = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "a": 1, "an": 1}

# ISO 4217 alphabetic codes. A field suffix is a currency unit only when it is one of these.
# ISO 4217 alphabetic codes, minus words that are also ordinary English (all, top, try, cup, pen, mad, sos, php, bob).
_CURRENCY = frozenset("""
aed afn amd ang aoa ars aud awg azn bam bbd bdt bgn bhd bif bmd bnd bov brl bsd btn bwp byn bzd
cad cdf che chf chw clf clp cny cop cou crc cve czk djf dkk dop dzd egp ern etb eur fjd fkp gbp gel
ghs gip gmd gnf gtq gyd hkd hnl htg huf idr ils inr iqd irr isk jmd jod jpy kes kgs khr kmf kpw krw kwd
kyd kzt lak lbp lkr lrd lsl lyd mdl mga mkd mmk mnt mop mru mur mvr mwk mxn mxv myr mzn nad ngn nio
nok npr nzd omr pab pgk pkr pln pyg qar ron rsd rub rwf sar sbd scr sdg sek sgd shp sle srd
ssp stn svc syp szl thb tjs tmt tnd ttd twd tzs uah ugx usd usn uyi uyu uyw uzs ved ves vnd vuv
wst xaf xcd xof xpf yer zar zmw zwl
""".split())
# Measurement units that are not also ordinary words. Not id, size, date, or time.
# Dropped as ambiguous: in, min, s, m, t, v, w, g, h, l, b, pc, mt.
_UNITS = frozenset("kg mg ug lb lbs oz cm mm km ml cl ft yd mi pct pcs hr sec ms kw mw hz kb mb gb tb".split())
_NEVER_STRIP = frozenset({"id", "size", "date", "time"})

_KIND = {
    "T1-010": "allowed",
    "T5-003": "allowed",
    "T5-001": "undeclared",
    "T5-018": "undeclared_success",
    "T6-002": "drift",
    "T6-003": "id_drift",
}
_SCALES = (10, 100, 1000)


@dataclass(frozen=True)
class Finding:
    kind: str
    detail: str


def _loads(v):
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str) and v.strip()[:1] in "{[":
        try:
            return json.loads(v)
        except ValueError:
            return None
    return None


def _descriptors(ctx) -> dict[str, dict]:
    """Declared tools: MCP list, filled in by a catalogue on the trace or the task spec.

    A card entry wins when the same name is also published on the trace, so a trace
    cannot loosen a published schema. Names that exist only on the trace still count.
    """
    found: dict[str, dict] = {}
    for run in ctx.runs:
        blobs = []
        spec = SG.task_spec(run) or {}
        if isinstance(spec, dict):
            blobs.append(spec.get("tools"))
        blobs.append(_loads((run.attrs or {}).get("agentest.toolset")))
        for blob in blobs:
            if isinstance(blob, list):
                for item in blob:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        found.setdefault(item["name"], item)
            elif isinstance(blob, dict):
                for name, item in blob.items():
                    if isinstance(item, dict):
                        found.setdefault(str(name), {"name": str(name), **item})
    for name, item in ctx.a.tools.items():
        found[name] = item
    return found


def _schema(desc: dict) -> dict:
    raw = desc.get("inputSchema") if isinstance(desc, dict) else None
    return raw if isinstance(raw, dict) else {}


def _props(desc: dict) -> dict:
    props = _schema(desc).get("properties")
    return props if isinstance(props, dict) else {}


def _read_only(desc: dict | None) -> bool:
    """MCP readOnlyHint, default false when the tool publishes no annotation."""
    if not isinstance(desc, dict):
        return False
    ann = desc.get("annotations") if isinstance(desc.get("annotations"), dict) else {}
    return bool(ann.get("readOnlyHint", False))


def _harness_names(ctx, desc: dict, tool) -> set[str]:
    """Argument names the recording harness injected into this call (both sides must agree)."""
    declared = ctx.a.g("harnessArgs", default=[]) or []
    if isinstance(declared, str):
        declared = [p for p in re.split(r"[,\s]+", declared) if p]  # rx: format
    if not isinstance(declared, (list, tuple, set)):
        return set()
    raw = (tool.attrs or {}).get("agentest.tool.harness_args")
    listed = _loads(raw) if isinstance(raw, str) else raw
    if isinstance(listed, str):
        listed = [p for p in re.split(r"[,\s]+", listed) if p]  # rx: format
    if not isinstance(listed, (list, tuple, set)):
        return set()
    own = set(_props(desc))
    return ({str(x) for x in declared} & {str(x) for x in listed}) - own


def _canon(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        match = _NUM_SCALAR.fullmatch(value.strip())
        if not match:
            return None
        number = float(match.group(1).replace(",", ""))
    else:
        return None
    if abs(number) < 10 or abs(number) > 1e15:
        return None
    return round(number, 4)


def _numbers_in(text: str) -> set[float]:
    """Quantities in text. Digits that belong to an identifier (a code, not a quantity) are skipped.
    A 'dozen' phrase in the same text counts as twelve times the word in front of it."""
    raw = text or ""
    masked = _ID_TOKEN.sub(" ", raw)
    found = set()
    for token in _NUM_TOKEN.findall(masked):
        try:
            number = round(float(token.replace(",", "")), 4)
        except ValueError:
            continue
        if 10 <= abs(number) <= 1e15:
            found.add(number)
    for match in _DOZEN.finditer(raw):
        word = (match.group(1) or "").lower()
        count = _WORD_QTY.get(word, 1) * 12
        if count >= 10:
            found.add(float(count))
    return found


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.05, abs(b) * 1e-6)


def _derived(number: float, src: set[float]) -> bool:
    if any(_close(number, other) for other in src):
        return True
    vals = list(src)[:40]
    for left in vals:
        for scale in _SCALES:
            # A round fraction of a grounded figure (source / 10, /100, /1000). Multiplying
            # is not accepted: an extra zero (40 -> 400) is an ungrounded value.
            if number != 0 and _close(left, number * scale):
                return True
        for right in vals:
            for combined in (left + right, left - right, left * right):
                if _close(number, combined):
                    return True
    return False


_VOWEL = re.compile(r"[aeiouy]")  # rx: format


def _field_parts(name: str) -> tuple[str, str | None]:
    """(stem, unit). A suffix is a unit only from the currency and unit lists.

    ``_id``, ``_size``, ``_date`` and ``_time`` stay on the name. ``min`` is minutes
    only on a vowelless stem (``ttl_min``); on a word stem it is left in place
    (``price_min`` is not ``price``).
    """
    raw = str(name).lower()
    stem, sep, suffix = raw.rpartition("_")
    if not sep:
        stem, sep, suffix = raw.rpartition("-")
    if not sep or suffix in _NEVER_STRIP:
        return raw, None
    if suffix == "min" and stem and _VOWEL.search(stem) is None:
        return stem, "min"
    if suffix not in _CURRENCY | _UNITS:
        return raw, None
    return stem, suffix


def _same_slot(left: str, right: str) -> bool:
    """Same stem. Two explicit units match only when they are the same code. A bare name matches one unit."""
    left_stem, left_unit = _field_parts(left)
    right_stem, right_unit = _field_parts(right)
    if left_stem != right_stem:
        return False
    return not (left_unit and right_unit and left_unit != right_unit)


def _as_obj(value):
    if isinstance(value, str):
        parsed = _loads(value)
        return parsed if isinstance(parsed, (dict, list)) else None
    return value if isinstance(value, (dict, list)) else None


def _num_slots(value) -> dict[str, set[float]]:
    found: dict[str, set[float]] = {}

    def walk(node, key: str) -> None:
        if isinstance(node, dict):
            for child_key, child in node.items():
                walk(child, str(child_key))
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        else:
            number = _canon(node)
            if number is not None and key:
                found.setdefault(str(key).lower(), set()).add(number)

    obj = _as_obj(value)
    if obj is not None:
        walk(obj, "")
    return found


def _id_slots(value) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}

    def walk(node, key: str) -> None:
        if isinstance(node, dict):
            for child_key, child in node.items():
                walk(child, str(child_key))
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif isinstance(node, str) and key and _ID_TOKEN.fullmatch(node.strip()):
            found.setdefault(str(key).lower(), set()).add(node.strip())

    obj = _as_obj(value)
    if obj is not None:
        walk(obj, "")
    return found


def _remember(store: dict, slots: dict, source: str, earlier: bool) -> None:
    for slot, values in slots.items():
        for value in values:
            store.setdefault(slot, []).append((source, value, earlier))


def _bound(store: dict, field: str, call_name: str):
    """Values of this slot set by a different tool, an earlier turn, or state."""
    out = set()
    for key, pairs in store.items():
        if not _same_slot(key, field):
            continue
        for source, value, earlier in pairs:
            if earlier or source != call_name:
                out.add(value)
    return out


def _bound_earlier(store: dict, field: str) -> set:
    """r15: values of this slot set by an earlier turn of the conversation or by the initial state only."""
    return {value for key, pairs in store.items() if _same_slot(key, field) for _source, value, earlier in pairs if earlier}


def _conversation(run) -> str:
    """Runs with no conversation id stay separate. A ``#<rep>`` suffix is the same conversation."""
    raw = str(run.conversation or "")
    if not raw:
        return f"{run.input_id}#{run.rep}"
    head, sep, tail = raw.rpartition("#")
    return head if sep and tail.isdigit() else raw


def _dump(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def findings(ctx) -> tuple[Finding, ...]:
    cached = getattr(ctx, "_tool_misuse_findings", None)
    if cached is None:
        cached = tuple(_findings(ctx))
        ctx._tool_misuse_findings = cached
    return cached


def _findings(ctx) -> list[Finding]:
    tools = _descriptors(ctx)
    if not tools and not any(run.tools for run in ctx.runs):
        return []
    found: list[Finding] = []
    declared = set(tools)
    carried_nums: dict = {}
    carried_ids: dict = {}
    ordered = sorted(ctx.runs, key=lambda run: ( _conversation(run), int(getattr(run, "t0", 0) or 0), int(getattr(run, "rep", 0) or 0)))
    seen_conv = None
    prev = None
    for run in ordered:
        conv = _conversation(run)
        # r15: another repetition of the same input (its own conversation id) is not an earlier turn
        repeat = prev is not None and prev.input_id == run.input_id and str(prev.conversation or "") != str(run.conversation or "")
        prev = run
        if conv != seen_conv or repeat:
            carried_nums, carried_ids, seen_conv = {}, {}, conv
        numbers = {slot: list(pairs) for slot, pairs in carried_nums.items()}
        idents = {slot: list(pairs) for slot, pairs in carried_ids.items()}
        _remember(numbers, _num_slots(SG.initial_state(run)), "", True)
        _remember(idents, _id_slots(SG.initial_state(run)), "", True)
        seen_numbers = {value for pairs in numbers.values() for _, value, _ in pairs}
        seen_numbers |= _numbers_in(run.input or "")
        for call in run.tools:
            desc = tools.get(call.name)
            if declared and call.name not in declared:
                found.append(Finding("undeclared", f"{run.input_id}:{call.name} not in the declared toolset"))
                if not call.error:
                    found.append(Finding("undeclared_success", f"{run.input_id}:{call.name} succeeded and is not declared"))
            elif desc is not None and not call.error:
                found += _schema_findings(run.input_id, call, desc, _harness_names(ctx, desc, call))
            if desc is not None and not _read_only(desc) and not call.error:
                found += _drift_findings(run.input_id, call, desc, numbers, idents, seen_numbers, _harness_names(ctx, desc, call))
            _remember(numbers, _num_slots(call.result), call.name, False)
            seen_numbers |= {value for values in _num_slots(call.result).values() for value in values}
            _remember(idents, _id_slots(call.result), call.name, False)
            _remember(carried_nums, _num_slots(call.result), call.name, True)
            _remember(carried_ids, _id_slots(call.result), call.name, True)
    return found


def _schema_findings(input_id: str, call, desc: dict, harness: set[str]) -> list[Finding]:
    props = _props(desc)
    args = call.args or {}
    allowed: list[str] = []
    for key, value in args.items():
        if key in harness:
            continue
        spec = props.get(key)
        if not isinstance(spec, dict) or value is None:
            continue
        if "enum" in spec and value not in spec["enum"]:
            allowed.append(f"{key} not in enum")
        elif "const" in spec and value != spec["const"]:
            allowed.append(f"{key} != const")
    if not allowed:
        return []
    return [Finding("allowed", f"{input_id}:{call.name} {'; '.join(allowed[:4])}")]


def _drift_findings(input_id: str, call, desc: dict, numbers: dict, idents: dict, seen_numbers: set[float], harness: set[str]) -> list[Finding]:
    props = _props(desc)
    changed: list[str] = []
    switched: list[str] = []
    for key, value in (call.args or {}).items():
        if key in harness or isinstance(value, (bool, dict, list)) or value is None:
            continue
        spec = props.get(key) if isinstance(props.get(key), dict) else {}
        if "enum" in spec or spec.get("type") == "boolean" or (isinstance(value, str) and len(value.split()) >= 4):
            continue
        number = _canon(value)
        bound = _bound(numbers, key, call.name)
        # A number already returned by a tool, or stated by the user, is a copy, not a changed slot.
        if number is not None and bound and number not in bound and number not in seen_numbers:
            changed.append(f"{key} {sorted(bound)[:3]} -> {number}")
        if isinstance(value, str) and _ID_TOKEN.fullmatch(value.strip()):
            known = _bound(idents, key, call.name)
            token = value.strip()
            # r15: an identifier binding is cross-turn memory. Only a binding from an earlier turn or the initial
            # state can be switched; a different id than a lookup in the same root trace returned is not drift.
            if _bound_earlier(idents, key) and known and token not in known and token.lower() not in {item.lower() for item in known}:
                switched.append(f"{key} -> {token}")
    out = []
    if changed:
        out.append(Finding("drift", f"{input_id}:{call.name} slot changed {changed[:3]}"))
    if switched:
        out.append(Finding("id_drift", f"{input_id}:{call.name} binding changed {switched[:3]}"))
    return out


@register
def refine_verdict(test_id: str, ctx, verdict: R) -> R:
    kind = _KIND.get(test_id)
    if kind is None or verdict.status == "fail":
        return verdict
    hits = [item.detail for item in findings(ctx) if item.kind == kind]
    if not hits or verdict.status not in ("pass", "n/a", "not-assessed"):
        return verdict
    return R("fail", f"tool misuse: {hits[0]}" + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""))
