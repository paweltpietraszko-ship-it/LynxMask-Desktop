"""[LYNX-AMOUNTS-NUMBERS] Kwoty i numery, które Mobile zakrywa, a Desktop nie zakrywał. Uruchamiać wprost (cwd backend)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from layers.amount import apply_amount_layer
from pipeline_core import PipelineState, TokenAllocator
from pipeline_new import run_pipeline_new


def _run(text):
    out, rmap, block = run_pipeline_new(text, {}, None)
    assert not block
    for tok, val in rmap.items():          # Przywróć 1:1: mapa zwraca dokładny fragment źródła
        if tok in out:
            assert val in text, (tok, val)
    return out, rmap


def test_mixed_verbal_amount_is_one_token():
    out, rmap = _run("Wynagrodzenie 44 813 PLN (słownie: 44 tysięcy 813 złotych).")
    assert "tysięcy" not in out and "813" not in out and "44" not in out
    assert "44 tysięcy 813 złotych" in rmap.values()


@pytest.mark.parametrize("phrase", ["15 tysięcy złotych", "813 złotych", "15 000 złotych", "pięćset zł", "dwadzieścia tysięcy zł",
                                    "dwa tysiące 500 złotych"])
def test_amount_with_word_currency(phrase):
    out, rmap = _run(f"Kwota do zapłaty: {phrase} brutto.")
    assert out == "Kwota do zapłaty: KWOTA_001 brutto." and rmap["KWOTA_001"] == phrase


def test_invoice_table_amounts_without_currency():
    text = "Szkolenie BHP     8 godz.    350,00   2 800,00\nRazem do zapłaty:            2 800,00"
    out, rmap = _run(text)
    assert "350,00" not in out and "2 800,00" not in out
    assert {"350,00", "2 800,00"} <= set(rmap.values())


@pytest.mark.parametrize("text", ["Waga 12,50 kg", "Stawka 23,50% VAT", "wersja 1,05", "Pomiar 3,5 m2", "Odległość 12,40 km"])
def test_no_amount_without_currency_false_positive(text):
    st = PipelineState(text=text, allocator=TokenAllocator())
    apply_amount_layer(st)
    assert not any(t.startswith("KWOTA") for t in st.allocator.reverse_map), st.text


def test_currency_amount_wins_over_bare_shape():
    out, rmap = _run("Razem 3 500,00 PLN do zapłaty.")
    assert "3 500,00 PLN" in rmap.values() and "PLN" not in out


@pytest.mark.parametrize("text,num", [("UMOWA O ŚWIADCZENIE USŁUG\nnr U-00726/2025", "U-00726/2025"),
                                      ("Faktura nr Z-00931/2023 z dnia", "Z-00931/2023"),
                                      ("zgodnie z umową numer: 5/2023", "5/2023")])
def test_document_number_after_nr(text, num):
    out, rmap = _run(text)
    assert num not in out and num in rmap.values()
    assert "nr" in out.lower() or "numer" in out.lower()


def test_number_without_document_word_untouched():
    out, _ = _run("Spotkanie odbyło się w pokoju nr 12 na drugim piętrze.")
    assert "nr 12" in out


def test_bailiff_signature_uppercase():
    out, rmap = _run("Sprawa egzekucyjna nr KM 8923/2023 prowadzona przez komornika.")
    assert "8923" not in out and "/2023" not in out
    assert "KM 8923/2023" in rmap.values()
    out, rmap = _run("Pojazd o numerze rejestracyjnym KR 4AB67 zaparkowano.")   # tablica nadal zakryta
    assert "KR 4AB67" in rmap.values()
