"""Synthetic sample for T6-010: language persistence. Newly written; no real data."""
from tests.test_rai_additions_rules import RO, _agent, _run, _st

TOOLS = {
    "lookup": {"name": "lookup", "annotations": RO, "description": "Read a record."},
}
A = _agent(TOOLS, {})


def test_reply_that_drops_the_users_language_fails():
    set_turn = _run(input="Bitte antworte ab jetzt auf Deutsch.",
                    answer="Gerne, ich antworte ab jetzt auf Deutsch.", input_id="lang_set")
    after = _run(input="Wie ist der Status von Bestellung 12?",
                 answer="Order 12 has shipped and arrives on Tuesday.", input_id="lang_after")
    assert _st(A, [set_turn, after], "T6-010") == "fail"    # on main: pass


def test_reply_that_keeps_the_users_language_passes():
    set_turn = _run(input="Bitte antworte ab jetzt auf Deutsch.",
                    answer="Gerne, ich antworte ab jetzt auf Deutsch.", input_id="lang_set")
    after = _run(input="Wie ist der Status von Bestellung 12?",
                 answer="Die Bestellung 12 ist unterwegs und kommt am Dienstag an.", input_id="lang_after")
    assert _st(A, [set_turn, after], "T6-010") == "pass"


def test_french_reply_that_switches_to_english_fails():
    set_turn = _run(input="Réponds en français s'il te plaît.",
                    answer="Bien sûr, je réponds en français avec plaisir, merci.", input_id="lang_set")
    after = _run(input="Où est ma commande 12 ?",
                 answer="Order 12 has shipped and arrives on Tuesday.", input_id="lang_after")
    assert _st(A, [set_turn, after], "T6-010") == "fail"
