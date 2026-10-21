"""[LYNX-FORMATS-PACK2] Data ISO, forma prawna bez spacji, kody nie psute przez normalizator OCR. Uruchamiać wprost (cwd backend)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from layers.ocr_normalizer import normalize_ocr
from pipeline_new import run_pipeline_new


def _run(text):
    out, rmap, block = run_pipeline_new(text, {}, None)
    assert not block
    for tok, val in rmap.items():          # Przywróć 1:1
        if tok in out:
            assert val in text, (tok, val)
    return out, rmap


@pytest.mark.parametrize("text,date", [("Data urodzenia: ur. 1989-01-05", "1989-01-05"),
                                       ("Urodzony 2021-03-14 w Radomiu.", "2021-03-14")])
def test_iso_date_masked(text, date):
    out, rmap = _run(text)
    assert date not in out and date in rmap.values()


@pytest.mark.parametrize("text", ["Wartość 2026-13-40 w polu.", "Numer seryjny 1989-01-05-001 urządzenia."])
def test_iso_like_not_fragment(text):
    out, rmap = _run(text)
    assert not any(v in ("2026-13-40", "1989-01-05") for v in rmap.values()), (out, rmap)


@pytest.mark.parametrize("text,firm", [("Sprzedawca: Gamma sp.j.\nNIP: 525-000-11-22", "Gamma sp.j."),
                                       ("Wykonawca: Beta Sp.k.", "Beta Sp.k."),
                                       ("Nabywca: Delta sp.z o.o.", "Delta sp.z o.o.")])
def test_legal_form_without_space_is_firm(text, firm):
    out, rmap = _run(text)
    assert firm not in out and firm.rstrip(".") in rmap.values(), (out, rmap)   # końcowa kropka poza tokenem (jak dotąd)


@pytest.mark.parametrize("text", ["Rozliczenie jak sp.j. wyżej.", "Dział Sprzedaży sp. Dziękujemy za zamówienie.",
                                  "Sprzedawca: Gamma spj"])
def test_no_firm_without_name_or_dot(text):
    _, rmap = _run(text)
    assert not any(k.startswith("FIRMA") for k in rmap), rmap


def test_firm_bounds_guard_unchanged():
    out, rmap = _run("Pełnomocnik: Kowalski i Wspólnicy Sp. k. reprezentuje klienta.")
    assert [v for k, v in rmap.items() if k.startswith("FIRMA")] == ["Kowalski i Wspólnicy Sp. k"], rmap


@pytest.mark.parametrize("text", ["rej. PW YHU1N", "Tablica RKFL9U. Adres: ul. Prosta 5", "OG79A1A"])
def test_normalizer_keeps_codes(text):
    assert normalize_ocr(text).replace("ul. Prosta", "") == text.replace("ul. Prosta", "")


def test_normalizer_still_fixes_names():
    assert "Kowalczyk" in normalize_ocr("Pan K0walczyk podpisał.") and "Nowak" in normalize_ocr("Pan N0wak")
    assert "KoWALCZYK" in normalize_ocr("PAN JAN K0WALCZYK")   # krok 15 (słownik) jak przed zmianą


def test_long_caps_word_normalized_as_before():   # pomiar r1: „BARTOSZ JAB1OWSKI” w testy/ — nazwisko jawne w pierwszej wersji
    assert normalize_ocr("Podpisano: BARTOSZ JAB1OWSKI") == "Podpisano: BARTOSZ JABiOWSKI"


@pytest.mark.parametrize("code", ["RNBPW0R4", "LD1M/00472094/0"])
def test_short_caps_codes_kept(code):
    assert code in normalize_ocr(f"Kod: {code} w rejestrze")


def test_plate_masked_whole():
    out, rmap = _run("Pojazd nr rej. PW YHU1N, właściciel w aktach.")
    assert "YHU1N" not in out and any("YHU1N" in v for v in rmap.values())
