# SILENT-PACK1 reproduktory. Uruchamianie (cwd = katalog backend kopii):
#   PROFILE_DIR=<pusty> python -m pytest <ten_plik> -q -p no:cacheprovider --rootdir .
import contextlib
import io
import os
import re
import sys
import tempfile

import pytest

sys.path.insert(0, os.getcwd())
TOKEN = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")


@pytest.fixture(scope="module")
def full():
    import spacy_ner
    from anonymizer import build_anonymizer
    from pipeline import AppState, pseudonymize_document

    def run(text):
        st = AppState()
        st.spacy_ner_mod = spacy_ner
        d = tempfile.mkdtemp(prefix="sp1_")
        with contextlib.redirect_stdout(io.StringIO()):
            st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
            return pseudonymize_document(text, st)
    return run


# ── Klasa 1: FIRMA z podwójną formą / OSOBA połykająca „sp.” ──────────────────
@pytest.mark.parametrize("text,value", [
    ("Wykonawca: Jutrzenka sp. z o.o. sp. z o.o., NIP 5260250995.", "Jutrzenka sp. z o.o. sp. z o.o"),
    ("Umowa dostawy\nWykonawca: Jutrzenka sp. z o.o. sp. z o.o., NIP 5260250995.\nZamawiający: Jurzerznka sp. z o.o.",
     "Jurzerznka sp. z o.o"),
    ("Sprzedawca: Jutrzenka Sp. z o.o. Sp. z o.o.", "Jutrzenka Sp. z o.o. Sp. z o.o"),
])
def test_k1_firma_cala_z_forma(full, text, value):
    r = full(text)
    assert value in [v for k, v in r.reverse_map.items() if k.startswith("FIRMA")], (r.text, r.reverse_map)
    assert "Jutrzenka" not in r.text and "Jurzerznka" not in r.text, r.text


# ── Klasa 2: rdzeń firmy powtórzony bez formy ────────────────────────────────
@pytest.mark.parametrize("text,core", [
    ("Zamawiający: Filar Północy sp. z o.o. z siedzibą w Gdańsku. W dalszej części pisma nazwę Filar Północy stosuje się "
     "jako skrót. Umowę podpisał Filar Północy.", "Filar Północy"),
    ("ZAMAWIAJĄCY: Lazurowy Moduł sp.k.\nLazurowy Moduł potwierdza odbiór.", "Lazurowy Moduł"),
    ("Wykonawca: Kwantix sp. z o.o.\nKwantix zapłaci karę.", "Kwantix"),
])
def test_k2_rdzen_firmy_tym_samym_tokenem(full, text, core):
    r = full(text)
    firms = [k for k in r.reverse_map if k.startswith("FIRMA")]
    assert core not in r.text and len(firms) == 1 and not any(k.startswith("OSOBA") for k in r.reverse_map), (r.text, r.reverse_map)


@pytest.mark.parametrize("text,plain", [
    ("Sprzedawca: Hebanowy Most sp. z o.o.\nMost na rzece jest zamknięty.", "Most na rzece"),       # słowo pospolite
    ("Wykonawca: Punkt sp. z o.o.\nPunkt 3 umowy stanowi inaczej. W punkcie 4 opisano karę.", "Punkt 3 umowy"),
    ("Wykonawca: Jan Kowalski sp. z o.o.\nJan Kowalski podpisał umowę.", None),                      # rdzeń = osoba
])
def test_k2_bez_nadmaskowania(full, text, plain):
    r = full(text)
    if plain:
        assert plain in r.text, r.text
    else:
        assert any(k.startswith("OSOBA") for k in r.reverse_map), r.reverse_map


def test_k2_dwie_firmy_ten_sam_rdzen(full):
    """B2: dwie firmy z jednym rdzeniem — skrót dostaje własny token, bez scalania podmiotów."""
    r = full("Sprzedawca: Filar Północy sp. z o.o.\nKupujący: Filar Północy S.A.\nFilar Północy wystawi fakturę.")
    firms = {k: v for k, v in r.reverse_map.items() if k.startswith("FIRMA")}
    assert "Filar Północy" not in r.text and len(set(firms.values())) == 3 and "Filar Północy" in firms.values(), (r.text, firms)
    assert not any(("sp. z o.o" in v.lower()) and ("s.a" in v.lower()) for v in firms.values()), firms


# ── Klasa 3: kwota z groszami bez waluty i bez spacji tysięcy ────────────────
def _run(text):
    from unittest.mock import patch
    import layers.ner_adapter as ner_mod
    from pipeline_new import run_pipeline_new
    with patch.object(ner_mod, "process_ner", return_value=({}, {})):
        return run_pipeline_new(text, anon_map={})


@pytest.mark.parametrize("text,value", [
    ("W kolumnie „do zwrotu” zapisano 1049,63; walutą rozliczenia jest złoty.", "1049,63"),
    ("Saldo końcowe: 12.345,67. Koniec.", "12.345,67"),
    ("Wynagrodzenie netto 5400,00 płatne do 10.", "5400,00"),
    ("Kwota 1234,56 w terminie 14 dni.", "1234,56"),          # „w” to nie jednostka
])
def test_k3_kwota(text, value):
    out, rev, _ = _run(text)
    assert value in rev.values() and value not in out, (out, rev)


@pytest.mark.parametrize("text", [
    "Wersja 2026,01 programu.", "Wynik pomiaru 1234,56 mm.", "Udział 1234,50% w kapitale.",
    "Pozycja 1049,63 w tabeli nr 5.", "Kurs 4,3215 z dnia.",
    # Codex r3 F1: jednostka przy słowie kwotowym; ROZSZERZENIE CC: ta sama luka w starym wzorcu („575,63 mm”)
    "Wartość pomiaru 1234,56 mm.", "Wartość pomiaru 12.345,67 mm.", "Odczyt 1234,56 mm; wartość zmierzono ponownie.",
    "Wartość pomiaru 575,63 mm.", "Koszt dostawy liczony od 2 450,00 cm bieżących.",
])
def test_k3_nie_kwota(text):
    out, rev, _ = _run(text)
    assert not [v for k, v in rev.items() if k.startswith("KWOTA")], (out, rev)


# ── Klasa 4: końcówki numerów ────────────────────────────────────────────────
@pytest.mark.parametrize("text,value", [
    ("Numer polisy: PO/2026/0329.", "PO/2026/0329"),
    ("Odczyt OCR z załącznika: numerklienta: K L 7017 O. Rozbitespacje w opisie.", "K L 7017 O"),
    ("Numer klienta: AB 12 345 oraz reszta.", "AB 12 345"),
    ("Legitymacja radcy WA/12345 oraz numer WA/1234/2020.", "WA/1234/2020"),
])
def test_k4_numer_w_calosci(text, value):
    out, rev, _ = _run(text)
    assert value in rev.values() and not re.search(r"\d{3}", TOKEN.sub("", out)), (out, rev)


@pytest.mark.parametrize("text", ["Legitymacja radcy WA/12345.", "Adwokat PO/1234 stawił się."])
def test_k4_radca_bez_zmian(text):
    out, rev, _ = _run(text)
    assert len(rev) == 1 and not re.search(r"\d", TOKEN.sub("", out)), (out, rev)
