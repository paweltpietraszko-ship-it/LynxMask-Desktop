# [LYNX-FIRMA-FILTER-FIX] Forma prawna nigdy sama + lista prefiksów z kontekstem. Syntetyki.
# Uruchamianie: py -3 -m pytest tests/test_firma_context.py -q (plik spoza pytest.ini python_files).
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ner_blocklist  # noqa: E402
import ner_layer  # noqa: E402
from firma_context import legal_form_entities  # noqa: E402


@dataclass
class Ent:
    text: str
    label: str
    start: int
    end: int


def ents(text, *spans):
    return [Ent(text[text.index(v):text.index(v) + len(v)], lab, text.index(v), text.index(v) + len(v)) for v, lab in spans]


def run(text, *spans):
    return [(e.text, e.label) for e in legal_form_entities(text, ents(text, *spans))]


@pytest.mark.parametrize("text,spans,expected", [
    ("Umowa z ALFA Sp. z o.o. w Krakowie.", [("z o.o.", "FIRMA")], [("ALFA Sp. z o.o.", "FIRMA")]),
    ("SPRZEDAWCA:\nALFA Sp. z o.o.\nul. Lipowa", [("z o.o.", "FIRMA")], [("ALFA Sp. z o.o.", "FIRMA")]),
    ("Sprzedawca: Doradztwo Biznesowe EXPERT Sp. z o.o.", [("z o.o.", "FIRMA")],
     [("Doradztwo Biznesowe EXPERT Sp. z o.o.", "FIRMA")]),
    ("NABYWCA\nALFA S.A.\nNIP", [("A.", "OSOBA")], [("ALFA S.A.", "FIRMA")]),           # dawniej: OSOBA „A.” wycięta → wyciek
    ("Umowa z firmą ALFA Sp. z o.o.", [("z o.o.", "FIRMA")], [("ALFA Sp. z o.o.", "FIRMA")]),   # stop na „firmą”
    ("Kowalski i Wspólnicy Sp. k. reprezentuje", [("Kowalski", "OSOBA"), ("Wspólnicy Sp. k.", "FIRMA")],
     [("Kowalski i Wspólnicy Sp. k.", "FIRMA")]),
    ("Spółka z o.o. w organizacji", [("z o.o.", "FIRMA")], []),                          # brak nazwy → brak tokenu
])
def test_legal_form_joins_the_name_or_disappears(text, spans, expected):
    assert run(text, *spans) == expected


@pytest.mark.parametrize("text,spans", [
    ("Podpisał Jan A. w obecności świadków.", [("Jan A.", "OSOBA")]),
    ("Obecny był A. oraz inni.", [("A.", "OSOBA")]),                                       # sam inicjał (C1 Codexa)
    ("Anna K. i Wspólnicy złożyli wniosek.", [("Anna K.", "OSOBA")]),
])
def test_person_initials_are_left_untouched(text, spans):
    assert run(text, *spans) == list(spans)


def test_prefix_rule_ignores_names_with_legal_form_and_common_words():
    for firm in ("Piekarnia Smaczek Sp. z o.o.", "Przedsiębiorstwo Budowlane MARBUD S.A."):
        assert not ner_layer._prefix_rejects("FIRMA", firm, firm.lower())
    for prefix in ("piekarni", "przedsię", "pracowni", "spółdzie", "transpor"):   # słowa pospolite / zapis bez ogonków
        assert prefix not in ner_blocklist._NER_BLOCKLIST_PREFIXES
    assert "gdańsk" in ner_blocklist._NER_BLOCKLIST_PREFIXES and "gdańska" in ner_blocklist._NER_BLOCKLIST   # geo zostaje


@pytest.mark.parametrize("value", ["Sąd Rejonowy", "Urząd Skarbowy"])
def test_public_institutions_still_rejected(value):
    assert ner_layer._filter_institutions([Ent(value, "FIRMA", 0, len(value))]) == []
