# LYNX-OSOBA-LAYOUT: osoba z układu pisma (silnik) + pytania Guarda tylko o słowa nieopisane. Teksty syntetyczne.
# Uruchamianie (cwd = backend): python -m pytest tests/test_osoba_layout.py -q -p no:cacheprovider --rootdir .
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())
import guard_residue  # noqa: E402
from guard_residue import collect_warnings  # noqa: E402
from layers.ner_adapter import _sub_whole  # noqa: E402
from person_layout import apply_person_layout  # noqa: E402
from pipeline_core import TokenAllocator  # noqa: E402


def _layout(text, values=None):
    alloc = TokenAllocator()
    for v in values or []:
        text = _sub_whole(text, v, alloc.assign("OSOBA", v))
    return apply_person_layout(text, alloc, _sub_whole), alloc.reverse_map


def _r1(text):
    return [w["fragment"] for w in collect_warnings(text) if "R1" in w["rules"]]


@pytest.mark.parametrize("text,person", [
    ("DANE WNIOSKODAWCY\n\nImię i nazwisko:\nZoryana Fortuńska\nData urodzenia:\n", "Zoryana Fortuńska"),   # etykieta
    ("NABYWCA:\nRakesh Kiljanek\nAdres: ul. Polna 1\n", "Rakesh Kiljanek"),
    ("a\n\n2. Illya Warska\n   zamieszkałym/ą: ul. Rolna 4\n", "Illya Warska"),                              # wiersz nad „zamieszkały”
    ("zgłosiła się osoba:\n\nAigerim Literski\nPESEL: 82042688552\n", "Aigerim Literski"),                 # wiersz nad PESEL
    ("Imię i nazwisko: Tamila Palarz\n", "Tamila Palarz"),                                                   # ta sama linia
    ("Skargę złożyła wczoraj Lucyna Osoba w sekretariacie.", "Lucyna Osoba"),                               # C3: imię + słowo
    ("Wczoraj Mikolaj Osoba podpisał.", "Mikolaj Osoba"),                                                    # imię bez ogonka
])
def test_osoba_z_ukladu(text, person):
    out, rmap = _layout(text)
    assert person not in out and person in rmap.values(), out


@pytest.mark.parametrize("text,first,rest", [
    ("NABYWCA:\nRakesh Kiljanek\n", "Rakesh", "Kiljanek"),      # Morfeusz: nazwisko? — nie; zostaje do linii z etykietą
    ("Pismo przekazała Sheila Osoba\nData urodzenia:", "Sheila", "Osoba"),   # C3 za tokenem imienia, koniec wiersza
    ("Umowę podpisał Jan Kasprzak w biurze.", "Jan", "Kasprzak"),            # nazwisko wg Morfeusza za tokenem
])
def test_reszta_za_tokenem_imienia(text, first, rest):
    out, _ = _layout(text, [first])
    assert rest not in out, out


@pytest.mark.parametrize("text,value,word", [
    ("Zamawiający: FIRMA_001 GmbH, Berlin.", "Alfa", "GmbH"),         # nieznane Morfeuszowi — zostaje (pyta Guard)
    ("Wezwanie dla OSOBA_001 Sąd Rejonowy w Opolu.", "Jan Nowak", "Sąd"),
])
def test_za_tokenem_bez_dowodu_zostaje(text, value, word):
    alloc = TokenAllocator()
    alloc.assign("OSOBA", value)
    assert word in apply_person_layout(text, alloc, _sub_whole)


@pytest.mark.parametrize("text,word", [
    ("Przyszedł Pan Rogalik z wnioskiem.", "Rogalik"),
    ("Pismo przekazała Pani Nietoperz.", "Nietoperz"),
    ("Odpowiedź otrzymał dr Kwiatkowski.", "Kwiatkowski"),
])
def test_pan_plus_slowo_to_osoba(text, word):
    out, _ = _layout(text)
    assert word not in out, out


@pytest.mark.parametrize("text,word", [
    ("Szanowny Panie Ministrze, zwracam się z prośbą.", "Ministrze"),   # funkcja w odmianie
    ("Kieruję do Pana Ministra pytania.", "Ministra"),
    ("Odpowiadając na interpelację Pani Radnej informuję.", "Radnej"),
    ("Panie Prezydencie! Szanowni Państwo!", "Prezydencie"),
    ("§ 18 ust 5. p. Przewiduje dowolność.", "Przewiduje"),             # „p.” małe = punkt
    ("Rada uchwaliła: Rady Miejskiej w Dąbrowie Tarnowskiej.", "Miejskiej"),
    ("Ochrona Danych Osobowych w firmie.", "Osobowych"),
    ("Siedziba w Tomaszów Mazowiecki od roku.", "Mazowiecki"),
    ("Pismo do Szpitala im. Jana Pawła II w Krakowie.", "Pawła"),
])
def test_nie_osoba(text, word):
    out, _ = _layout(text)
    assert word in out, out


@pytest.mark.parametrize("text,word", [
    ("Spotkanie przy Brunnenstrasse odbyło się.", "Brunnenstrasse"),   # obce — użytkownik decyduje
    ("Protokół podpisał Śludkowski w obecności świadka.", "Śludkowski"),
    ("Protokół podpisał Sądowski w obecności świadka.", "Sądowski"),   # słownik: wyłącznie nazwisko
])
def test_guard_pyta(text, word):
    assert word in _r1(text)


@pytest.mark.parametrize("text,word", [
    ("Sygn. akt II C 1/24.", "Sygn"),                       # skrót z pism
    ("Platnosc nastapi przelewem.", "Platnosc"),              # brak ogonków po OCR
    ("Komomik sądowy przy Sądzie.", "Komomik"),              # jedna pomyłka OCR (rn → m)
    ("Naczelnik Wydziatu Finansowego.", "Wydziatu"),         # ł → t
    ("Termin wykonania upływa jutro.", "Termin"),            # zwykłe słowo
    ("Wczoraj Kawa zlecił paczkę.", "Kawa"),                  # zwykłe słowo (osobę rozpoznaje silnik)
])
def test_guard_nie_pyta(text, word):
    assert word not in _r1(text)


def test_biala_lista():
    wl = guard_residue._WHITELIST
    assert len(wl) == 316 and {"termin", "dziennik", "art"} <= wl and "nowak" not in wl


def test_pusta_lista_nie_wycisza(monkeypatch):
    monkeypatch.setattr(guard_residue, "_WHITELIST", frozenset())
    monkeypatch.setattr(guard_residue, "_ABBR", frozenset())
    assert "Sygn" in _r1("Sygn. akt II C 1/24.")


def test_awaria_morfeusza_to_pytanie():
    hits = list(guard_residue._unknown("Wczoraj Termin podpisał.", lambda w: None))
    assert [h[2] for h in hits] == ["R1"]
