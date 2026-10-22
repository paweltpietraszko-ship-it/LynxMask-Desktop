"""[LYNX-ADDR-REVERSED] Adres z miastem obok rozpoznanej ulicy/kodu (także w odwróconej kolejności) i kod nigdy cięty
w połowie. Samo miasto bez sąsiedztwa adresu zostaje jawne (polityka OWNERA). Teksty syntetyczne; przypadki 5–9 z diagnozy
Qwen 3.8 (22.10). Wzór: test_addr_email_leaks.py — warstwy silnika bez NER."""
import re
from unittest.mock import patch

import pytest

TOKEN = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")
GLUED = re.compile(r"(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}[\w-]|[\w-](?:FIRMA|OSOBA|NUMER|KWOTA|ADRES)_\d{3}")


def _run(text):
    import ner_layer as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        return run_pipeline_new(text, anon_map={})


def _restore(out, rev):
    return TOKEN.sub(lambda m: rev.get(m.group(0), m.group(0)), out)


@pytest.mark.parametrize("text,plain", [
    ("Punkt odbioru: Opole, 45-407, ul. Rzemieślnicza 433", ["Opole", "45-407", "Rzemieślnicza"]),
    ("Siedziba: Wrocław, 50-001", ["Wrocław", "50-001"]),
    ("Adres: Jelenia Góra, 58-500, ul. Długa 1", ["Jelenia", "58-500", "Długa"]),
    ("Adres: Zielona Gora 65-001", ["Zielona", "65-001"]),
    ("Warszawa, ul. Marszałkowska 12/4, 00-001", ["Warszawa", "Marszałkowska", "00-001"]),
    ("ul. Polna 5, Radom", ["Polna", "Radom"]),
    ("Adam Kowalski, Radom, ul. Polna 5", ["Radom", "Polna"]),
    ("00-001 Warszawa, Twarda 18", ["00-001", "Warszawa", "Twarda"]),
    ("Kraków al. Jana Pawła II 15 31-001", ["Kraków", "Pawła", "31-001", "-001"]),
])
def test_adres_w_calosci(text, plain):
    out, rev, blocked = _run(text)
    assert not blocked, out
    for word in plain:
        assert word not in out, (word, out, rev)
    assert not GLUED.search(out), out
    assert _restore(out, rev) == text, (out, rev)


@pytest.mark.parametrize("text,city", [
    ("Wrocław, 21.10.2026", "Wrocław"),
    ("Spotkanie odbyło się w Opolu.", "Opolu"),
    ("Opole, dnia 22.10.2026 r.", "Opole"),
    ("Kraków, 12.05.2026", "Kraków"),
    ("Mieszkam w Radomiu od lat.", "Radomiu"),
    ("Delegacja: Warszawa, Kraków, Gdańsk.", "Gdańsk"),
])
def test_samo_miasto_jawne(text, city):
    out, rev, _ = _run(text)
    assert city in out and not any(k.startswith("ADRES_") for k in rev), (out, rev)
