"""[LYNX-OSOBA-PACK4] Błędy OSOBA z oglądu OWNERA 22.10 + krok 2 „udowodnij, że jesteś osobą” (teksty syntetyczne).
Pełny pipeline (silnik + Guard) na pustym profilu, jak `test_failclosed.py`."""
import os
import re
import tempfile

import pytest

os.environ.setdefault("PROFILE_DIR", tempfile.mkdtemp(prefix="pack4_"))

import spacy_ner  # noqa: E402
from anonymizer import build_anonymizer  # noqa: E402
from pipeline import AppState, pseudonymize_document  # noqa: E402

OSOBA = re.compile(r"\bOSOBA_\d{3}\b")


def run(text: str):
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="p4_")
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    r = pseudonymize_document(text, st)
    assert not r.error, r.error
    return r


def warned(r, word: str) -> bool:
    return any(word in w["fragment"] for w in r.guard_warnings)


def test_1_etykieta_wersalikami_nie_jest_osoba():
    r = run("OCZEKIWANE: dwa tokeny ADRES.\nOCZEKIWANE: zero osób.\nNAZWISKO: KOWALSKI")
    assert r.text.count("OCZEKIWANE") == 2, r.text
    assert "KOWALSKI" not in r.text, r.text


def test_2_lista_nazwisk_osobne_tokeny():
    r = run("Na liście obecności: Kowalski, Nowak, Pietraszko, Wiśniewski, Kot.")
    persons = [v for k, v in r.reverse_map.items() if k.startswith("OSOBA_")]
    assert not any("," in v for v in persons), persons
    for name in ("Kowalski", "Nowak", "Pietraszko", "Wiśniewski"):
        assert name not in r.text, r.text


def test_2_nazwisko_dwuczlonowe_zostaje_jednym_tokenem():
    r = run("Umowę podpisała Pani Anna Kowalska-Nowak.")
    assert "Kowalska" not in r.text and "Nowak" not in r.text, r.text


def test_3_patroni_ulic_i_miasta_nie_sa_osoba():
    r = run("Adres: ul. Jana Pawła II 10/5, 20-001 Lublin.\nKlient odwiedził oddział w mieście Jelenia Góra w zeszłym miesiącu.")
    assert "Jelenia Góra" in r.text, r.text
    assert not any(v in ("Jana", "Pawła", "Góra") for v in r.reverse_map.values()), r.reverse_map


def test_4_imie_i_nazwisko_to_jeden_token():
    r = run("Pani Róża Zielona podpisała umowę.")
    assert "Zielona" not in r.text and "Róża" not in r.text, r.text
    assert len(OSOBA.findall(r.text)) == 1, r.text
    assert "Róża Zielona" in r.reverse_map.values(), r.reverse_map


def test_krok2_slowa_pospolite_bez_dowodu_trafiaja_do_guarda():
    r = run("W ogrodzie rosła Malina i Róża, a płot był Zielony.")
    for w in ("Malina", "Róża"):
        assert w in r.text, r.text
        assert warned(r, w), r.guard_warnings


@pytest.mark.parametrize("text,word", [
    ("Pani Malina przyniosła dokumenty.", "Malina"),
    ("Dokumenty przyniosła Anna Malina.", "Malina"),
    ("Nabywca: Malina", "Malina"),
    ("Świadek Kawa zeznał, że widział zdarzenie.", "Kawa"),
])
def test_krok2_z_dowodem_zakryte(text, word):
    r = run(text)
    assert word not in r.text, r.text


def test_krok2_nazwisko_bez_znaczenia_pospolitego_zakryte_bez_kontekstu():
    r = run("Dokumenty przyniósł wczoraj Grzelak osobiście.")
    assert "Grzelak" not in r.text, r.text


def test_krok2_drugie_wystapienie_wersalikami_ma_pytanie():  # Codex r3 F1 — pełny pipeline
    r = run("Dokument przekazał wczoraj Malina. W notatce zapisano MALINA.")
    assert "MALINA" not in r.text or warned(r, "MALINA"), (r.text, r.guard_warnings)
