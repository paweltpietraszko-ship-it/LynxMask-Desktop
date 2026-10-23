# LYNX-FIRMA-SILENT2: nazwa JDG z opisem działalności, forma „s.c.”, rozcięte powtórzenie nazwy. Teksty syntetyczne (wzorzec GOLD dev).
# Uruchamianie (cwd = backend): python -m pytest tests/test_firma_silent2.py -q -p no:cacheprovider --rootdir .
import contextlib
import io
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.getcwd())


@pytest.fixture(scope="module")
def run():
    prof = tempfile.mkdtemp()
    os.environ.setdefault("PROFILE_DIR", prof)
    os.environ.setdefault("ANONYMIZER_PROFILE_DIR", prof + "/a")
    import spacy_ner
    from anonymizer import build_anonymizer
    from pipeline import AppState, pseudonymize_document

    def _run(text):
        st = AppState()
        st.spacy_ner_mod = spacy_ner
        d = tempfile.mkdtemp(dir=prof)
        with contextlib.redirect_stdout(io.StringIO()):
            st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, d + "/hw.json")
            r = pseudonymize_document(text, st)
        return r.text, r.reverse_map
    return _run


@pytest.mark.parametrize("text,value,hidden", [
    # A — JDG
    ("Wykonawca: Usługi Konserwatorskie Cezary Jeż\nUsługi Konserwatorskie Cezary Jeż zachowuje egzemplarz.",
     "Usługi Konserwatorskie Cezary Jeż", ["Usługi", "Konserwatorskie"]),
    ("WYKONAWCA: Biuro Organizacji Pracy Bartosz Bogucki\nAdres siedziby: ul. Polna 4",
     "Biuro Organizacji Pracy Bartosz Bogucki", ["Biuro", "Organizacji", "Pracy"]),
    # Codex r2 F1: nazwisko będące też imieniem
    ("Wykonawca: Usługi Konserwatorskie Cezary Marek\nW dalszej części pisma nazwę Usługi Konserwatorskie Cezary Marek stosuje się.",
     "Usługi Konserwatorskie Cezary Marek", ["Usługi", "Konserwatorskie"]),
    ("Wykonawca: Biuro Rachunkowe Anna Roman\nBiuro Rachunkowe Anna Roman zachowuje egzemplarz.",
     "Biuro Rachunkowe Anna Roman", ["Biuro", "Rachunkowe"]),
    ("Wykonawca: Studio Jan Marek\nStudio Jan Marek zachowuje egzemplarz.", "Studio Jan Marek", ["Studio"]),
    # B — s.c. i powtórzenie bez formy
    ("Zamawiający: Perłowy Nawias s.c.\nW dalszej części pisma nazwę Perłowy Nawias stosuje się jako skrót podmiotu.",
     "Perłowy Nawias s.c", ["Perłowy", "Nawias"]),
    # C — powtórzenie nie rozcięte krótszą encją
    ("Zamawiający: Ulotny Rys sp. z o.o.\nW dalszej części pisma nazwę Ulotny Rys stosuje się jako skrót podmiotu.",
     "Ulotny Rys sp. z o.o", ["Ulotny", "Rys"]),
])
def test_firma_zakryta_w_calosci(run, text, value, hidden):
    out, rmap = run(text)
    assert value in rmap.values(), rmap
    assert not any(w in out for w in hidden), out
    tok = [k for k, v in rmap.items() if v == value][0]
    assert out.count(tok) == 2 or "Adres" in text, out   # pełna nazwa i powtórzenie — ten sam token


@pytest.mark.parametrize("text,kept", [
    ("Sprawę prowadzi Biuro Obsługi Klienta.", "Biuro Obsługi Klienta"),           # dział wewnętrzny bez osoby
    ("Dział Kadr przekazał dokumenty.", "Dział Kadr"),
    ("Pismo do: Biuro Rzecznika Praw Pacjenta.", "Biuro Rzecznika Praw Pacjenta"),
    ("Usługi informatyczne świadczy Jan Nowak.", "Usługi informatyczne"),         # mała litera — nie nazwa
])
def test_bez_nowej_firmy(run, text, kept):
    out, rmap = run(text)
    assert kept in out and not any(v.startswith(kept) for k, v in rmap.items() if k.startswith("FIRMA")), (out, rmap)


def test_inicjaly_przed_sc_nie_firma(run):
    out, rmap = run("Podpisał J. S.C. z upoważnienia.")
    assert not any("S.C" in v for k, v in rmap.items() if k.startswith("FIRMA")), rmap


def test_jdg_wymaga_imienia():
    from firma_context import is_jdg, jdg_entities
    assert is_jdg("Usługi Konserwatorskie Cezary Jeż") and not is_jdg("Zakład Ubezpieczeń Społecznych")
    assert jdg_entities("Kancelaria Notarialna w Krakowie") == []
