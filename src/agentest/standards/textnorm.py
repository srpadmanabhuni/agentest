"""Shared, tested text helpers for rules (r12-prep, Fix 5): number / money normalisation and punctuation- and
case-insensitive token matching, with basic multilingual support. Stdlib only.

Why: several rules carried their own regexes for amounts and tokens and broke on formats such as ``INR 3,50,000``
(Indian digit grouping), ``350000 rupees`` (currency word after the number), ``$1.2k``, ``2.5 lakh`` / ``1 crore``, a zero
amount, or a trailing full stop on a word (``examiners.``). These helpers are the single place to fix such cases.

Nothing here is wired into a frozen round's scoring; rules migrate to it one by one under a new rules freeze.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------- digits
# Unicode decimal digits of any script (Devanagari ०-९, Bengali, Tamil, Arabic-Indic, full-width ...) -> ASCII
_DIGIT_MAP = {cp: str(unicodedata.digit(chr(cp))) for cp in range(0x10000) if chr(cp).isdecimal() and not chr(cp).isascii()}


def ascii_digits(text: str) -> str:
    """Map decimal digits of any script to ASCII ('₹ ३,५०,०००' -> '₹ 3,50,000')."""
    return (text or "").translate(_DIGIT_MAP)


# ---------------------------------------------------------------- currencies
CURRENCY_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
CURRENCY_CODES = {"inr": "INR", "rs": "INR", "rs.": "INR", "usd": "USD", "us$": "USD", "eur": "EUR", "gbp": "GBP", "jpy": "JPY"}
# currency words (stems: inflected forms such as 'rupees', 'रुपयों', 'ரூபாய்' match by prefix)
CURRENCY_WORD_STEMS = {"rupee": "INR", "रुपय": "INR", "रुपए": "INR", "रुपै": "INR", "ரூபா": "INR", "రూపాయ": "INR",
                       "ರೂಪಾಯ": "INR", "രൂപ": "INR", "ਰੁਪਏ": "INR", "રૂપિય": "INR", "টাকা": "INR", "ଟଙ୍କା": "INR",
                       "dollar": "USD", "euro": "EUR", "pound": "GBP"}
# scale words -> multiplier (Indian and international)
SCALE_WORDS = {"k": 1e3, "thousand": 1e3, "hazar": 1e3, "हज़ार": 1e3, "हजार": 1e3,
               "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5, "लाख": 1e5,
               "crore": 1e7, "crores": 1e7, "cr": 1e7, "करोड़": 1e7, "करोड": 1e7,
               "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}

_NUM = r"\d+(?:,\d+)*(?:\.\d+)?|\.\d+"
_SYM = "|".join(re.escape(s) for s in CURRENCY_SYMBOLS)
_CODE = r"(?:us\$|inr|usd|eur|gbp|jpy|rs\.?)(?![a-z])"
_SCALE = "|".join(sorted((re.escape(s) for s in SCALE_WORDS), key=len, reverse=True))
AMOUNT_RX = re.compile(
    rf"(?P<pre>{_SYM}|(?<![a-z]){_CODE})?\s*(?<![\w\-/])(?P<num>{_NUM})(?!\d|/\d)\s*(?P<scale>(?:{_SCALE})(?![a-z\u0900-\u0dff]))?"
    rf"\s*(?P<post>{_CODE}|[^\s\d.,;:!?()\[\]{{}}\"'/\-]+)?",
    re.I)


@dataclass(frozen=True)
class Amount:
    value: float
    currency: str | None  # ISO code when a symbol, code or currency word is attached
    text: str              # the matched text, as written


def parse_number(s: str) -> float | None:
    """'3,50,000' -> 350000.0; '1,234.50' -> 1234.5; '0' -> 0.0; any digit script. Grouping commas are dropped whatever
    the grouping (Indian 2-digit or international 3-digit). Returns None when there is no number."""
    s = ascii_digits(str(s)).strip().rstrip(".,;:")
    m = re.fullmatch(rf"[+-]?(?:{_NUM})", s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def to_number(v) -> float | None:
    """A JSON value or a plain numeric string as a number rounded to 2 places; bool / text / mixed strings -> None.
    Exactly the semantics rules.py used for ``_num`` (its last, effective definition) before r12-prep."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, str) and re.fullmatch(r"-?\d[\d,]*(?:\.\d+)?", v.strip()):
        return round(float(v.strip().replace(",", "")), 2)
    return None


def _currency_word(w: str | None) -> str | None:
    if not w:
        return None
    lw = w.lower()
    if lw in CURRENCY_CODES:
        return CURRENCY_CODES[lw]
    return next((c for stem, c in CURRENCY_WORD_STEMS.items() if lw.startswith(stem)), None)


def find_amounts(text: str, money_only: bool = False) -> list[Amount]:
    """Every number in ``text`` with scale words applied and an attached currency if any.
    'INR 3,50,000' / '350000 rupees' / '₹3.5 lakh' -> 350000.0 INR; '$1.2k' -> 1200.0 USD; '1 crore' -> 1e7.
    With ``money_only`` only amounts with a currency are returned."""
    t = ascii_digits(text or "")
    out = []
    for m in AMOUNT_RX.finditer(t):
        v = parse_number(m.group("num"))
        if v is None:
            continue
        sc = m.group("scale")
        if sc:
            # single-letter scales only directly after the number ('1.2k', '5L'); otherwise 'l'/'m'/'b' are words
            if len(sc) == 1 and m.end("num") != m.start("scale"):
                sc = None
            elif len(sc) == 1 and m.end("scale") < len(t) and t[m.end("scale")].isalpha():
                sc = None
        if sc:
            v *= SCALE_WORDS[sc.lower()]
        cur = None
        if m.group("pre"):
            p = m.group("pre")
            cur = CURRENCY_SYMBOLS.get(p) or CURRENCY_CODES.get(p.lower())
        if cur is None:
            cur = _currency_word(m.group("post"))
        if money_only and cur is None:
            continue
        end = m.end("post") if (m.group("post") and _currency_word(m.group("post"))) else (m.end("scale") if sc else m.end("num"))
        out.append(Amount(v, cur, t[m.start():end].strip()))
    return out


def money_values(text: str) -> set[float]:
    """Values of all money amounts in ``text`` (rounded to paise/cents)."""
    return {round(a.value, 2) for a in find_amounts(text, money_only=True)}


def amount_grounded(amount: float, sources: str, tol: float = 0.005) -> bool:
    """True when ``amount`` appears (any format, any scale, with or without currency) in ``sources``.
    A zero amount is grounded only by an explicit 0 in the sources, never by absence."""
    return any(abs(a.value - amount) <= tol for a in find_amounts(sources))


def is_zero_amount(text: str) -> bool:
    """'INR 0', '₹0.00', 'Rs. 0', 'zero rupees', 'nil' -> True."""
    ams = find_amounts(text, money_only=True)
    if ams:
        return all(a.value == 0 for a in ams)
    return bool(re.search(r"\b(?:zero|nil|no)\b\s*(?:rupees?|dollars?|euros?|amount|inr|usd)?\b", (text or "").lower())) and \
        bool(re.search(r"\b(?:zero|nil)\b", (text or "").lower()))


# ---------------------------------------------------------------- tokens
_SPLIT_RX = re.compile(r"[\s,;:!?()\[\]{}\"'“”‘’«»\u0964\u0965\u3001\u3002]+")


def fold(s: str) -> str:
    """Case- and compatibility-folded text (NFKC + casefold): 'Examiners' == 'examiners', full-width -> ASCII."""
    return unicodedata.normalize("NFKC", str(s or "")).casefold()


def strip_punct(tok: str) -> str:
    """Remove leading/trailing punctuation of any script ('examiners.' -> 'examiners', '«ok»' -> 'ok', 'स्वीकृत।' ->
    'स्वीकृत'), keeping inner punctuation (IDs 'AB-12', decimals '3.5', 'e-mail')."""
    s = str(tok or "")
    i, j = 0, len(s)
    while i < j and unicodedata.category(s[i])[0] in "PSZ" and s[i] not in "₹$€£¥":
        i += 1
    while j > i and unicodedata.category(s[j - 1])[0] in "PSZ" and s[j - 1] not in "₹$€£¥":
        j -= 1
    return s[i:j]


def tokens(text: str) -> list[str]:
    """Folded word tokens; keeps Indic combining marks inside a word (unlike \\w on some builds) and strips edge
    punctuation, so 'The examiners.' -> ['the', 'examiners']."""
    return [t for t in (strip_punct(x) for x in _SPLIT_RX.split(fold(text))) if t]


def has_token(text: str, word: str) -> bool:
    """Whole-token match, punctuation- and case-insensitive. Multi-word phrases match as a token sequence."""
    want = tokens(word)
    if not want:
        return False
    toks = tokens(text)
    n = len(want)
    return any(toks[i:i + n] == want for i in range(len(toks) - n + 1))


def same_token(a: str, b: str) -> bool:
    """'examiners.' == 'Examiners' ; 'ok' != 'okay'."""
    return tokens(a) == tokens(b) and bool(tokens(a))


def contains_any(text: str, words) -> list[str]:
    """The ``words`` that occur in ``text`` as whole tokens (punctuation/case-insensitive), in input order."""
    return [w for w in words if has_token(text, w)]


# ---------------------------------------------------------------- scripts / languages
_SCRIPT_RANGES = (("Devanagari", 0x0900, 0x097F), ("Bengali", 0x0980, 0x09FF), ("Gurmukhi", 0x0A00, 0x0A7F),
                  ("Gujarati", 0x0A80, 0x0AFF), ("Oriya", 0x0B00, 0x0B7F), ("Tamil", 0x0B80, 0x0BFF),
                  ("Telugu", 0x0C00, 0x0C7F), ("Kannada", 0x0C80, 0x0CFF), ("Malayalam", 0x0D00, 0x0D7F),
                  ("Arabic", 0x0600, 0x06FF), ("Cyrillic", 0x0400, 0x04FF), ("CJK", 0x4E00, 0x9FFF))


def scripts(text: str) -> set[str]:
    """Scripts present among the letters of ``text`` ('Latin' for ASCII/Latin-1 letters)."""
    out = set()
    for ch in text or "":
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if cp < 0x0250:
            out.add("Latin")
            continue
        out.add(next((n for n, lo, hi in _SCRIPT_RANGES if lo <= cp <= hi), "Other"))
    return out
