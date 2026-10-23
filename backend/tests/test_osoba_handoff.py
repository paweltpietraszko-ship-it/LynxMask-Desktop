# LYNX-OSOBA-HANDOFF: silnik zapisuje w rejestrze (released) tylko kandydatów, którzy mogą być nazwiskiem.
# [LYNX-OSOBA-LAYOUT] Guard nie czyta już rejestru (pyta o słowa nieopisane — guard_unknown); testy rejestru zostają.
# Uruchamianie (cwd = backend): python -m pytest tests/test_osoba_handoff.py -q -p no:cacheprovider --rootdir .
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())
import osoba_not_person as onp  # noqa: E402
from guard_residue import collect_warnings  # noqa: E402


def _released_after(text, word, person_forms=frozenset()):
    onp.start_run()
    s = text.index(word)
    masked = onp.single_osoba_evidence(text, s, s + len(word), person_forms=person_forms)
    return masked, onp.released()


@pytest.mark.parametrize("text,word", [
    ("Wczoraj Przystępującego reprezentował radca.", "Przystępującego"),
    ("Wczoraj Powódka wniosła pozew.", "Powódka"),
    ("Sąd uznał, że Odwołującemu nie przysługuje zwrot.", "Odwołującemu"),
    ("Wczoraj Protokolant odczytał protokół.", "Protokolant"),
])
def test_rola_spoza_listy_nie_idzie_do_guarda(text, word):
    assert _released_after(text, word) == (False, [])


@pytest.mark.parametrize("text,word", [
    ("Dokument przekazał wczoraj Kawa.", "Kawa"),
    ("Dokument przekazał wczoraj Malina.", "Malina"),
    ("Model Maciolus działał.", "Maciolus"),
])
def test_mozliwe_nazwisko_nadal_do_guarda(text, word):
    masked, rel = _released_after(text, word)
    assert masked or rel == [word]


@pytest.mark.parametrize("word", ["Holub", "Prokopenko"])
def test_tylko_pospolite_z_listy_nazwisk_nadal_do_guarda(word):
    # klasa C1 (Codex r1): Morfeusz zna słowo tylko jako pospolite, ale jest na liście nazwisk
    common, person, _geo = onp._common_or_person(word)
    assert common is True and person is False and word.lower() in onp._surname_forms()
    assert _released_after(f"Dokument przekazał wczoraj {word}.", word) == (False, [word])


def test_kandydat_z_person_forms_nadal_do_guarda(monkeypatch):
    monkeypatch.setattr(onp, "_SURNAMES", frozenset({"x"}))  # lista bez tego słowa
    assert _released_after("Wczoraj Gwaranta wezwano.", "Gwaranta", person_forms=frozenset({"gwaranta"})) == (False, ["Gwaranta"])


def test_brak_pliku_listy_wylacza_regule(monkeypatch):
    monkeypatch.setattr(onp, "_SURNAMES", frozenset())
    assert _released_after("Wczoraj Powódka wniosła pozew.", "Powódka") == (False, ["Powódka"])


@pytest.mark.parametrize("word", ["……", "Pzp", "Cz", "G"])
def test_nie_nazwa_nie_idzie_do_guarda(word):
    assert _released_after(f"Wczoraj {word} wpłynęło.", word) == (False, [])


def test_guard_nie_czyta_rejestru():  # [LYNX-OSOBA-LAYOUT] słowo ze zwykłym znaczeniem — bez pytania mimo rejestru
    onp.start_run()
    t = "Dokument przekazał wczoraj Kawa. W notatce KAWA."
    s = t.index("Kawa")
    onp.single_osoba_evidence(t, s, s + 4)
    assert collect_warnings(t) == []
