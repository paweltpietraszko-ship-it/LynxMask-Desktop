# LYNX-AMOUNT-OCR-MULT: kwoty z mnożnikiem i z „O” zamiast zera. Teksty syntetyczne.
# Uruchamianie (cwd = backend): python -m pytest tests/test_amount_ocr_mult.py -q -p no:cacheprovider --rootdir .
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())
from layers.amount import apply_amount_layer  # noqa: E402
from pipeline_core import PipelineState, TokenAllocator  # noqa: E402


def _amount(text):
    st = PipelineState(text=text, allocator=TokenAllocator())
    apply_amount_layer(st)
    return st.text, {k: v for k, v in st.allocator.reverse_map.items() if k.startswith("KWOTA")}


@pytest.mark.parametrize("text,value", [
    ("Kara umowna 15 tys. zł za dzień.", "15 tys. zł"),
    ("Odszkodowanie 2,5 mln zł.", "2,5 mln zł"),
    ("Kwota 2 mld zł", "2 mld zł"),
    ("Pożyczka 15 tys. PLN", "15 tys. PLN"),
    ("Wynagrodzenie wynosi 15 tysięcy miesięcznie.", "15 tysięcy"),       # bez waluty, słowo kwotowe w zdaniu
    ("Wynagrodzenie 3 tys. brutto.", "3 tys."),
    ("Kwota do zapłaty: 15 OOO zł.", "15 OOO zł"),                        # O zamiast zera
    ("Kwota 15OOO zł", "15OOO zł"),
    ("Kwota 15.OOO zł", "15.OOO zł"),
    ("Zapłacono 15 OOO,00 PLN tytułem kary.", "15 OOO,00 PLN"),
    ("Kwota 15 OOO bez waluty.", "15 OOO"),                               # słowo kwotowe w zdaniu
    ("Kwota 15 OOO,50 zł.", "15 OOO,50 zł"),                              # Codex r2 F1: grosze ≠ 00
    ("Kwota 15 OOO,50 PLN.", "15 OOO,50 PLN"),
    ("Kwota 15OOO,50zł.", "15OOO,50zł"),
    ("Kwota 1200.5O zł.", "1200.5O zł"),                                  # Codex r2 F2: kropka dziesiętna
])
def test_kwota_zakryta_literalnie(text, value):
    out, kw = _amount(text)
    assert value not in out and value in kw.values(), (out, kw)   # mapa trzyma fragment literalnie (Przywróć 1:1)


@pytest.mark.parametrize("text", [
    "Ludność: 15 tys. mieszkańców.",          # brak znaku pieniędzy
    "Pozycja 15 OOO szt.",                    # jednostka
    "Sprzedawca: OOO Gazprom, Moskwa.",       # brak cyfry
    "Wersja 2 tys.",
    "Trasa 15 tys. km",
    "Na koncie było 15 OOO.",                 # poza zakresem: bez waluty i bez słowa kwotowego
    "Model 15 OOO wpłynął do serwisu.",
])
def test_bez_zmian(text):
    out, kw = _amount(text)
    assert out == text and not kw, (out, kw)


def test_mnoznik_z_dalszym_ciagiem_zostaje_dla_kwot_slownych():  # „44 tysięcy 813 złotych” = jeden token (verbal_amounts)
    out, kw = _amount("Wynagrodzenie 44 813 PLN (słownie: 44 tysięcy 813 złotych).")
    assert "44 tysięcy" in out and "44 tysięcy" not in kw.values(), (out, kw)


def test_istniejace_kwoty_bez_zmian():
    out, kw = _amount("Wynagrodzenie: 3 500,00 PLN, zaliczka 1200 EUR")
    assert sorted(kw.values()) == ["1200 EUR", "3 500,00 PLN"], kw
