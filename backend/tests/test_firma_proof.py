# [LYNX-FIRMA-PROOF] FIRMA tylko z dowodem, instytucja jawna bez miejsca/numeru, data pisma jawna, wartość zakryta wszędzie,
# Guard R4 bez numerów strukturalnych. Syntetyki (wzorowane na publicznych orzeczeniach KIO, bez danych z nich).
# Uruchamianie: py -3 -m pytest tests/test_firma_proof.py -q (plik spoza pytest.ini python_files).
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firma_proof import firma_proof, has_proof, strip_role  # noqa: E402
from guard_residue import _r4  # noqa: E402
from layers.amount import _DATE_PL_RE, _doc_date  # noqa: E402
from layers.institution import apply_institution_layer  # noqa: E402
from pipeline_core import PipelineState, TokenAllocator  # noqa: E402
from spacy_ner import NERResult  # noqa: E402
from layers.fallback import apply_value_propagation  # noqa: E402


def ner(text, value, label="FIRMA"):
    i = text.index(value)
    return NERResult(value, label, 0.8, i, i + len(value))


@pytest.mark.parametrize("value", [
    "Rejonu", "Nadzoru", "Bezsporne", "Krajowa Izba Odwoławcza", "Rady Ministrów", "Skarb Państwa", "Prawo Budowlane",
    "Zakład Komunalny", "Przedsiębiorstwo Budowy Dróg", "Komisji Przetargowej", "Urzędu Miejskiego w Gliwicach",
    "Zamawiającego i Wykonawców",
])
def test_bez_dowodu_to_nie_firma(value):
    assert not has_proof(value)


@pytest.mark.parametrize("value", [
    "POLSUPER Sp. z o.o", "Sansec Poland S.A.", "Pöyry Infra GmbH", "Sprint SA", "Infover Spółkę Akcyjną", "Swarco Traffic Polska Spółka",
    "Styl Sp. z  o.o", "Przedsiębiorstwo Usług Wielobranżowych LOTAR", "Wielobranżowa Pracownia Projektowa Diapron",
    "Agencja Ochrony Osób i Mienia „Guard Service”", "Usługi Konserwatorskie Ignacy Grocholski", "Kancelaria Adwokacka Jan Kos",
])
def test_z_dowodem_to_firma(value):
    assert has_proof(value)


@pytest.mark.parametrize("text,value,expected", [
    ("odwołanie wniósł Wykonawca POLSUPER Sp. z o.o. z siedzibą", "Wykonawca POLSUPER Sp. z o.o", "POLSUPER Sp. z o.o"),
    ("E1. Wykonawca Nowy Styl sp. z o.o.", "E1. Wykonawca Nowy Styl sp. z o.o", "Nowy Styl sp. z o.o"),
    ("pismo Odwołującego - Siemens Sp. z o.o.", "Odwołującego - Siemens Sp. z o.o", "Siemens Sp. z o.o"),
    ("Wykonawca „Zakład Zieleni” Sp. z o.o.", "Wykonawca „Zakład Zieleni” Sp. z o.o", "Zakład Zieleni” Sp. z o.o"),
])
def test_slowo_roli_poza_nazwa(text, value, expected):
    assert strip_role(text, ner(text, value)).text == expected


def test_poczatek_udowodnionej_firmy_zostaje():
    text = "Oferta AG-COMPLEX Sp. z o.o. oraz pismo AG-Complex i opinia Rejonu."
    out = firma_proof(text, [ner(text, "AG-COMPLEX Sp. z o.o"), ner(text, "AG-Complex"), ner(text, "Rejonu")])
    assert [r.text for r in out] == ["AG-COMPLEX Sp. z o.o", "AG-Complex"]


def test_osoba_bez_zmian():
    text = "Pan Jan Kos podpisał."
    assert firma_proof(text, [ner(text, "Jan Kos", "OSOBA")])[0].label == "OSOBA"


@pytest.mark.parametrize("text,masked", [
    ("Sprawa dotyczy Zakładu Ubezpieczeń Społecznych.", False),
    ("Wyrok Sądu Najwyższego z dnia 5 maja.", False),
    ("Decyzja KNF oraz UOKiK.", False),
    ("Sąd Rejonowy w Legnicy wydał wyrok.", True),
    ("Uczeń Szkoły Podstawowej nr 18 w Elblągu.", True),
    ("Pismo do Urzędu Miejskiego w Gliwicach.", True),
    ("Budynek Przedszkola Miejskiego nr 22.", True),
    ("Sprawę prowadzi Wydział I Cywilny.", True),
])
def test_instytucja_jawna_bez_miejsca_i_numeru(text, masked):
    state = PipelineState(text=text, allocator=TokenAllocator())
    apply_institution_layer(state)
    assert ("INSTYTUCJA_" in state.text) == masked


@pytest.mark.parametrize("text,jawna", [
    ("Kraków, 07.01.2026", True),
    ("09.01.2026, Jelenia Góra\nZamawiający", True),
    ("Bielsko-Biała, dnia 07.01.2026 r.", True),
    ("Urodzony: 01.01.1962.", False),
    ("Warszawa, 12.03.1985", False),          # rok sprzed 5 lat — może być urodzenie
    ("Data: 12.03.2025", False),
    ("umowa z dnia 12.03.2025 r.", False),
    ("12.03.2025", False),
])
def test_data_pisma(text, jawna):
    assert _doc_date(text, _DATE_PL_RE.search(text)) is jawna


def test_wartosc_zakryta_wszedzie():
    state = PipelineState(text="zaświadczenie nr NUMER_001 oraz ważność zaświadczenia nr 75/06. i 02.11.2011r. oraz 75/061",
                          allocator=TokenAllocator())
    state.allocator.allocate("NUMER", "75/06", 17, 22)
    tok = state.allocator.reverse_map and next(iter(state.allocator.reverse_map))
    state.text = state.text.replace("NUMER_001", tok)
    apply_value_propagation(state)
    assert "75/06." not in state.text and state.text.count(tok) == 2 and "75/061" in state.text


@pytest.mark.parametrize("text,asked", [
    ("(Dz. U. z 2010 r. Nr 113, poz. 759)", False),
    ("karnego – Dz. U.\r\nz 1997 r. Nr 89, poz. 555", False),
    ("droga krajowa nr 87 Nowy Sącz", False),
    ("załącznika nr 12 do umowy", False),
    ("w Dzienniku Urzędowym Unii Europejskiej nr 2011/S 6-008619", False),
    ("norm PN-NUMER_010:1999 w", False),
    ("ogłoszenie nr 2016/S NUMER_005.", False),
    ("dowód osobisty nr ABC123456", True),
    ("umowy nr 235", True),
])
def test_r4_bez_numerow_strukturalnych(text, asked):
    assert bool(list(_r4(text))) is asked
