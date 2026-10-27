"""OTLP/protobuf <-> OTLP/JSON for traces, using only the standard library.

Decodes an ``ExportTraceServiceRequest`` / ``TracesData`` message (both have ``repeated ResourceSpans = 1``) into the
OTLP/JSON shape that :func:`agentest.standards.otel.from_otlp` reads, so no protobuf runtime is needed.
Field numbers follow opentelemetry-proto ``trace/v1/trace.proto`` and ``common/v1/common.proto``
(https://github.com/open-telemetry/opentelemetry-proto). Unknown fields are skipped, as protobuf requires.
:func:`encode_traces` is the inverse (used by tests and by ``agentest std serve --echo``).
"""

from __future__ import annotations

import base64
import struct
from collections.abc import Iterator
from typing import Any

# message schemas: field number -> (json name, kind, repeated)
# kinds: msg:<Schema>, str, bytes_hex, bytes_b64, u64str (varint as decimal string), i64str, fixed64str, fixed32, enum, double, bool
_ANY = "AnyValue"
SCHEMAS: dict[str, dict[int, tuple[str, str, bool]]] = {
    "TracesData": {1: ("resourceSpans", "msg:ResourceSpans", True)},
    "ResourceSpans": {1: ("resource", "msg:Resource", False), 2: ("scopeSpans", "msg:ScopeSpans", True), 3: ("schemaUrl", "str", False)},
    "Resource": {1: ("attributes", "msg:KeyValue", True), 2: ("droppedAttributesCount", "u32", False)},
    "ScopeSpans": {1: ("scope", "msg:InstrumentationScope", False), 2: ("spans", "msg:Span", True), 3: ("schemaUrl", "str", False)},
    "InstrumentationScope": {1: ("name", "str", False), 2: ("version", "str", False), 3: ("attributes", "msg:KeyValue", True),
                             4: ("droppedAttributesCount", "u32", False)},
    "Span": {1: ("traceId", "bytes_hex", False), 2: ("spanId", "bytes_hex", False), 3: ("traceState", "str", False),
             4: ("parentSpanId", "bytes_hex", False), 16: ("flags", "fixed32", False), 5: ("name", "str", False), 6: ("kind", "enum", False),
             7: ("startTimeUnixNano", "fixed64str", False), 8: ("endTimeUnixNano", "fixed64str", False),
             9: ("attributes", "msg:KeyValue", True), 10: ("droppedAttributesCount", "u32", False), 11: ("events", "msg:Event", True),
             12: ("droppedEventsCount", "u32", False), 13: ("links", "msg:Link", True), 14: ("droppedLinksCount", "u32", False),
             15: ("status", "msg:Status", False)},
    "Event": {1: ("timeUnixNano", "fixed64str", False), 2: ("name", "str", False), 3: ("attributes", "msg:KeyValue", True),
              4: ("droppedAttributesCount", "u32", False)},
    "Link": {1: ("traceId", "bytes_hex", False), 2: ("spanId", "bytes_hex", False), 3: ("traceState", "str", False),
             4: ("attributes", "msg:KeyValue", True), 5: ("droppedAttributesCount", "u32", False), 6: ("flags", "fixed32", False)},
    "Status": {2: ("message", "str", False), 3: ("code", "enum", False)},
    "KeyValue": {1: ("key", "str", False), 2: ("value", "msg:AnyValue", False)},
    "AnyValue": {1: ("stringValue", "str", False), 2: ("boolValue", "bool", False), 3: ("intValue", "i64str", False),
                 4: ("doubleValue", "double", False), 5: ("arrayValue", "msg:ArrayValue", False), 6: ("kvlistValue", "msg:KeyValueList", False),
                 7: ("bytesValue", "bytes_b64", False)},
    "ArrayValue": {1: ("values", "msg:AnyValue", True)},
    "KeyValueList": {1: ("values", "msg:KeyValue", True)},
}


class DecodeError(ValueError):
    pass


def _varint(b: bytes, i: int) -> tuple[int, int]:
    shift = val = 0
    while True:
        if i >= len(b):
            raise DecodeError("truncated varint")
        c = b[i]
        i += 1
        val |= (c & 0x7F) << shift
        if c < 0x80:
            return val, i
        shift += 7
        if shift > 70:
            raise DecodeError("varint too long")


def _fields(b: bytes) -> Iterator[tuple[int, int, Any]]:
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        num, wt = key >> 3, key & 7
        if wt == 0:
            v, i = _varint(b, i)
        elif wt == 1:
            v, i = b[i:i + 8], i + 8
        elif wt == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wt == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise DecodeError(f"unsupported wire type {wt}")
        if i > len(b):
            raise DecodeError("truncated field")
        yield num, wt, v


def _decode(b: bytes, schema: str) -> dict:
    out: dict = {}
    spec = SCHEMAS[schema]
    for num, wt, v in _fields(b):
        if num not in spec:
            continue
        name, kind, rep = spec[num]
        if kind.startswith("msg:"):
            val: Any = _decode(v, kind[4:])
        elif kind == "str":
            val = v.decode("utf-8")
        elif kind == "bytes_hex":
            val = v.hex()
        elif kind == "bytes_b64":
            val = base64.b64encode(v).decode()
        elif kind == "fixed64str":
            val = str(struct.unpack("<Q", v)[0]) if wt == 1 else str(v)
        elif kind == "fixed32":
            val = struct.unpack("<I", v)[0] if wt == 5 else v
        elif kind == "double":
            val = struct.unpack("<d", v)[0]
        elif kind == "i64str":
            val = str(v - (1 << 64) if v >= 1 << 63 else v)
        elif kind == "bool":
            val = bool(v)
        else:  # enum, u32
            val = v
        if rep:
            out.setdefault(name, []).append(val)
        else:
            out[name] = val
    if schema == "AnyValue" and not out:
        out = {"stringValue": ""}
    return out


def decode_traces(b: bytes) -> dict:
    """``ExportTraceServiceRequest`` / ``TracesData`` protobuf bytes -> OTLP/JSON dict."""
    doc = _decode(b, "TracesData")
    doc.setdefault("resourceSpans", [])
    for rs in doc["resourceSpans"]:
        rs.setdefault("resource", {})
        for ss in rs.setdefault("scopeSpans", []):
            for sp in ss.setdefault("spans", []):
                sp.setdefault("parentSpanId", "")
                sp.setdefault("startTimeUnixNano", "0")
                sp.setdefault("endTimeUnixNano", sp["startTimeUnixNano"])
    return doc


# ---------------------------------------------------------------- encoder (inverse; standard library only)

def _enc_varint(n: int) -> bytes:
    n &= (1 << 64) - 1
    out = bytearray()
    while True:
        c = n & 0x7F
        n >>= 7
        if n:
            out.append(c | 0x80)
        else:
            out.append(c)
            return bytes(out)


def _key(num: int, wt: int) -> bytes:
    return _enc_varint(num << 3 | wt)


def _encode(d: dict, schema: str) -> bytes:
    out = bytearray()
    by_name = {v[0]: (k, v[1], v[2]) for k, v in SCHEMAS[schema].items()}
    for name, val in d.items():
        if name not in by_name:
            continue
        num, kind, rep = by_name[name]
        for x in (val if rep else [val]):
            if kind.startswith("msg:"):
                b = _encode(x, kind[4:])
                out += _key(num, 2) + _enc_varint(len(b)) + b
            elif kind == "str":
                b = str(x).encode()
                out += _key(num, 2) + _enc_varint(len(b)) + b
            elif kind == "bytes_hex":
                if not x:
                    continue
                b = bytes.fromhex(x)
                out += _key(num, 2) + _enc_varint(len(b)) + b
            elif kind == "bytes_b64":
                b = base64.b64decode(x)
                out += _key(num, 2) + _enc_varint(len(b)) + b
            elif kind == "fixed64str":
                out += _key(num, 1) + struct.pack("<Q", int(x))
            elif kind == "fixed32":
                out += _key(num, 5) + struct.pack("<I", int(x))
            elif kind == "double":
                out += _key(num, 1) + struct.pack("<d", float(x))
            elif kind in ("i64str", "enum", "u32"):
                out += _key(num, 0) + _enc_varint(int(x))
            elif kind == "bool":
                out += _key(num, 0) + _enc_varint(1 if x else 0)
    return bytes(out)


def encode_traces(doc: dict) -> bytes:
    """OTLP/JSON dict -> ``ExportTraceServiceRequest`` protobuf bytes."""
    return _encode(doc, "TracesData")
