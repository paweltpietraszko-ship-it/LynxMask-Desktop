# LYNX-MAP-FIDELITY: różne wartości nie dzielą tokenu (D1), podmiana tylko całych wyrazów (D2), wartość NER dosłowna (D3).
# Uruchamiać jawnie: py -3 -m pytest tests/test_map_fidelity.py -q (plik spoza pytest.ini python_files).
import contextlib
import io
import os
import re
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TOKEN = re.compile(r"(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}")
GLUED = re.compile(r"\w(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}|(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}\w")


def _restore(out, rev):
    return TOKEN.sub(lambda m: rev.get(m.group(0), m.group(0)), out)


def _fake_ner(*frags):
    from spacy_ner import NERResult

    def detect(text):
        return [NERResult(text=f, label=lab, confidence=.9, start=text.find(f), end=text.find(f) + len(f))
                for lab, f in frags if text.find(f) >= 0]
    return detect


def _full(text, *frags):
    import spacy_ner
    from pipeline_new import run_pipeline_new
    with patch.object(spacy_ner, "detect_entities", _fake_ner(*frags)), contextlib.redirect_stdout(io.StringIO()):
        return run_pipeline_new(text, anon_map={})


# ── D1: klucz po wartości w alokatorze ──────────────────────────────────────────
@pytest.mark.parametrize("typ,a,b,same", [
    ("KWOTA", "15.00 zł", "1 500 zł", False), ("KWOTA", "100.0 zł", "1000 zł", False),
    ("KWOTA", "3 700 zł", "3700 zł", True), ("KWOTA", "134.460,00 zł", "134 460 zł", True), ("KWOTA", "20.000 zł", "20 000 zł", True),
    ("NUMER", "2.11.2023", "21.1.2023", False), ("NUMER", "ur. 2.11.2023", "ur. 21.1.2023", False),
    ("NUMER", "10-07-2024", "10.07.2024", True), ("NUMER", "701-090-21-85", "7010902185", True),
])
def test_alokator_rozdziela_rozne_wartosci_laczy_te_same(typ, a, b, same):
    from pipeline_core import TokenAllocator
    al = TokenAllocator()
    ta, tb = al.assign(typ, a), al.assign(typ, b)
    assert (ta == tb) is same, (ta, tb, al.reverse_map)


@pytest.mark.parametrize("pipeline", ["full", "express"])
def test_kwoty_ponad_precyzje_decimal(pipeline):
    """Codex r2 F1: Decimal.normalize() z kontekstem 28 cyfr scalał różne kwoty o 29 cyfrach — klucz musi być dokładny."""
    from pipeline_core import TokenAllocator
    from pipeline_new import run_pipeline_express
    a, b = "1" * 29 + " zł", "1" * 28 + "2 zł"
    al = TokenAllocator()
    assert al.assign("KWOTA", a) != al.assign("KWOTA", b)
    text = f"Roszczenie {a}, a druga pozycja {b}."
    out, rev, _ = _full(text) if pipeline == "full" else run_pipeline_express(text, anon_map={})
    assert _restore(out, rev) == text, (out, rev)


def test_register_kolizja_wedlug_wartosci():
    from pipeline_core import TokenAllocator
    al = TokenAllocator()
    al.register("KWOTA_001", "3 700 zł", 0, 8)
    al.register("KWOTA_001", "3700 zł", 10, 17)                      # ten sam: bez kolizji
    with pytest.raises(ValueError):
        al.register("KWOTA_001", "37.00 zł", 20, 28)                  # inna wartość: kolizja (S3)


@pytest.mark.parametrize("pipeline", ["full", "express"])
def test_rozne_kwoty_i_daty_w_dokumencie(pipeline):
    from pipeline_new import run_pipeline_express
    text = "Opłata 15.00 zł, kara 1 500 zł. Termin 2.11.2023 oraz 21.1.2023."
    out, rev, _ = _full(text) if pipeline == "full" else run_pipeline_express(text, anon_map={})
    toks = TOKEN.findall(out)
    assert len(toks) == 4 and len(set(toks)) == 4, (out, rev)
    assert _restore(out, rev) == text


# ── D2: tylko całe wyrazy ──────────────────────────────────────────────────────
@pytest.mark.parametrize("text,frags,hidden,visible", [
    ("Pozwany Nowak oraz Anna Nowakowska.", [("OSOBA", "Nowak")], [], ["Nowakowska"]),
    ("Odwołanie do Sądu złożył Sąd Rejonowy? Nie, Sąd.", [("FIRMA", "Sąd")], [], ["Sądu"]),
    ("Pozew: Jan Nowak-Kowalski, świadek Jan Nowak.", [("OSOBA", "Jan Nowak")], ["Nowak"], []),   # łącznik = granica:
    ("Komentarz: M. Pyziak-Szafnicka (red.).", [("OSOBA", "Pyziak")], ["Pyziak"], []),              # nadmaskowanie
    ("Umowę zawarł „Alfa Serwis”. Alfa Serwis potwierdza.", [("FIRMA", "Alfa Serwis")], ["Alfa Serwis"], []),
    ("Wniosek do Beta Grupa Polska. Spór z Beta Grupa w toku.",                                   # krótsza wartość nie
     [("FIRMA", "Beta Grupa"), ("FIRMA", "Beta Grupa Polska")], ["Beta Grupa Polska", "Beta Grupa"], []),  # w dłuższej
])
def test_podmiana_tylko_calych_wyrazow(text, frags, hidden, visible):
    out, rev, blocked = _full(text, *frags)
    assert not GLUED.search(out), out                                  # żaden token nie przyklejony do litery
    for w in hidden:
        assert w not in out, out
    for w in visible:
        assert w in out, out
    assert _restore(out, rev) == text


def test_czlon_listy_z_przecinkiem_nie_propaguje_listy():
    """Sklejona lista osób (C3) jako jedna wartość: człon „Suchoń,” nie może wpisać tokenu całej listy w innym miejscu
    (Przywróć wstawiłby cudzą treść) — wykryte na interpelacji 1739."""
    text = "Zgłaszający: Anna Lis, Piotr Suchoń, Ewa Mak.\nPóźniej: Jan Zieliński, Piotr Suchoń, Ewa Mak)."
    out, rev, _ = _full(text, ("OSOBA", "Anna Lis, Piotr Suchoń, Ewa Mak"))
    assert _restore(out, rev) == text, (out, rev)


@pytest.mark.parametrize("text,masked", [
    ("Identyfikator postępowania: ocds-148610-4123c129-0298-11ed-8000-d680d39e541a koniec", None),   # wnętrze kodu
    ("Ogłoszenie 2016/S_239-394253 z dnia", None),
    ("PESEL44051401359 (sklejone przez OCR)", "44051401359"),                                         # litera przed: nadal
    ("PESEL: 44051401359.", "44051401359"),
])
def test_identity_nie_wycina_numeru_ze_srodka_kodu(text, masked):
    """ROZSZERZENIE CC: identity nie tworzy tokenu wewnątrz dłuższego kodu; numer po etykiecie nadal maskowany."""
    from pipeline_new import run_pipeline_express
    out, rev, _ = run_pipeline_express(text, anon_map={})
    assert not GLUED.search(out), out
    if masked:   # Przywróć bez sprawdzania: OCR dopisuje „: ” po etykiecie (znany TEXT-FIDELITY-F3, poza zakresem)
        assert masked not in out and masked in rev.values(), (out, rev)


def test_adres_nie_w_srodku_wyrazu():
    """„Szpital Wojewódzki 5” to nie „al. Wojewódzki 5” (_ADDR_RE bez lewej granicy dawało „SzpitADRES_001”)."""
    from pipeline_new import run_pipeline_express
    text = "Leczenie w szpitalu: Szpital Wojewódzki 5 w mieście. Dojazd: al. Jerozolimskie 96, 00-807 Warszawa."
    out, rev, _ = run_pipeline_express(text, anon_map={})
    assert not GLUED.search(out) and "Szpital Wojewódzki" in out and "Jerozolimskie" not in out, (out, rev)


def test_wartosc_bez_otwierajacego_cudzyslowu_na_koncu():
    text = "Ofertę złożyła Agencja Usługowa „Interserwis” z siedzibą."
    out, rev, _ = _full(text, ("FIRMA", "Agencja Usługowa „"))
    assert not GLUED.search(out) and "Agencja" not in out and _restore(out, rev) == text, (out, rev)


# ── D3: dosłowna wartość (spacje/tab) ──────────────────────────────────────────
@pytest.mark.parametrize("span", ["Jan  Kowalski", "Jan\tKowalski", "Jan   \t Kowalski"])
def test_osoba_z_wieloma_bialymi_znakami(span):
    text = f"Pismo podpisał {span} dnia 3 marca."
    out, rev, blocked = _full(text, ("OSOBA", span))
    assert not blocked and "Kowalski" not in out and span in rev.values() and _restore(out, rev) == text, (out, rev)


@pytest.fixture(scope="module")
def _real():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audyt")))
    import engine_quality as eq
    ok, why = eq._engine_available()
    if not ok:
        pytest.skip(f"NER/Morfeusz niedostępny: {why}")
    import tempfile
    import pipeline
    st = eq.build_state(tempfile.mkdtemp(prefix="lynx_mapfid_"))
    return lambda t: pipeline.pseudonymize_document(t, st)


def test_prawdziwy_full_podwojna_spacja(_real):
    text = "Umowę w imieniu spółki podpisał Bartosz  Kowalczyk, prezes zarządu."
    with contextlib.redirect_stdout(io.StringIO()):
        r = _real(text)
    assert "Kowalczyk" not in r.text and not GLUED.search(r.text), (r.text, r.reverse_map)
