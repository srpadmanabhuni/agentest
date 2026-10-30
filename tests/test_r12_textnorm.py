"""r12-prep Fix 5: shared number / money / token helpers (agentest.standards.textnorm)."""
import pytest

from agentest.standards import textnorm as T


@pytest.mark.parametrize("text,value,cur", [
    ("INR 3,50,000", 350000.0, "INR"),
    ("350000 rupees", 350000.0, "INR"),
    ("Rs. 3,50,000", 350000.0, "INR"),
    ("Rs 350000/-", 350000.0, "INR"),
    ("₹3.5 lakh", 350000.0, "INR"),
    ("₹ ३,५०,०००", 350000.0, "INR"),
    ("2.5 lakhs", 250000.0, None),
    ("1 crore", 1e7, None),
    ("1.5cr", 1.5e7, None),
    ("$1.2k", 1200.0, "USD"),
    ("USD 1,200.00", 1200.0, "USD"),
    ("€ 99.90", 99.9, "EUR"),
    ("300 dollars", 300.0, "USD"),
    ("500 रुपये", 500.0, "INR"),
    ("500 ரூபாய்", 500.0, "INR"),
    ("Rs. 0", 0.0, "INR"),
    ("paid ₹0.", 0.0, "INR"),
    ("5L", 500000.0, None),
])
def test_amounts(text, value, cur):
    a = T.find_amounts(text)
    assert a and a[0].value == pytest.approx(value) and a[0].currency == cur


def test_formats_compare_equal():
    vals = [T.find_amounts(s, money_only=True)[0].value for s in ("INR 3,50,000", "350000 rupees", "₹3.5 lakh", "Rs.350,000")]
    assert len(set(vals)) == 1


@pytest.mark.parametrize("text", ["Claim AB-1234 approved", "ref X9-77", "on 2026/10/30", "page-12"])
def test_ids_and_dates_are_not_amounts(text):
    assert T.find_amounts(text, money_only=True) == []
    assert all(a.value not in (1234.0, 77.0, 12.0) for a in T.find_amounts(text))


def test_single_letter_scale_needs_to_be_attached():
    assert T.find_amounts("5 L")[0].value == 5.0
    assert T.find_amounts("1.2 m pages")[0].value == 1.2


def test_money_only_and_grounding():
    assert T.money_values("refund INR 1,500 for 3 items") == {1500.0}
    assert T.amount_grounded(350000, '{"amount": 350000}')
    assert T.amount_grounded(350000, "approved ₹3.5 lakh")
    assert not T.amount_grounded(350000, "approved ₹3.6 lakh")
    assert not T.amount_grounded(0, "no figures here")
    assert T.amount_grounded(0, '{"payable": 0}')


@pytest.mark.parametrize("text,zero", [("INR 0", True), ("₹0.00", True), ("zero rupees", True), ("nil", True),
                                       ("INR 10", False), ("no reason given", False), ("", False)])
def test_zero_amount(text, zero):
    assert T.is_zero_amount(text) is zero


def test_parse_number():
    assert T.parse_number("3,50,000") == 350000.0
    assert T.parse_number("1,234.50") == 1234.5
    assert T.parse_number("०") == 0.0
    assert T.parse_number("12.") == 12.0
    assert T.parse_number("abc") is None


@pytest.mark.parametrize("text,word,hit", [
    ("The examiners.", "examiners", True),
    ("EXAMINERS, please", "Examiners", True),
    ("re-examiners", "examiners", False),
    ("«approved»", "approved", True),
    ("आवेदन स्वीकृत।", "स्वीकृत", True),
    ("the claim was approved today", "was approved", True),
    ("approve", "approved", False),
    ("ＡＢＣ", "abc", True),
])
def test_has_token(text, word, hit):
    assert T.has_token(text, word) is hit


def test_strip_punct_keeps_inner_and_currency():
    assert T.strip_punct("examiners.") == "examiners"
    assert T.strip_punct("AB-12.") == "AB-12"
    assert T.strip_punct("3.5,") == "3.5"
    assert T.strip_punct("₹5") == "₹5"
    assert T.same_token("examiners.", "Examiners") and not T.same_token("ok", "okay")
    assert T.contains_any("Sent to the Examiners.", ["examiners", "board"]) == ["examiners"]


def test_scripts():
    assert T.scripts("hello नमस्ते வணக்கம்") == {"Latin", "Devanagari", "Tamil"}
    assert T.scripts("123 !!") == set()


def test_to_number_is_the_rules_num():
    from agentest.standards import rules
    assert rules._num is T.to_number
    assert T.to_number(True) is None and T.to_number(3) == 3.0 and T.to_number(" 1,234.567 ") == 1234.57
    assert T.to_number("INR 5") is None and T.to_number(None) is None and T.to_number("-0") == 0.0
