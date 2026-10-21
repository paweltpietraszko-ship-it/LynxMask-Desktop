"""[LYNX-OSOBA-NOT-PERSON] Jednowyrazowa OSOBA ze spaCy: listy Mobile, mała litera odrzucona. Uruchamiać wprost (cwd backend)."""
import os
import sys
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import ner_layer
import osoba_not_person as onp
from layers import ner_adapter
from ner_blocklist import _PERSON_FORMS
from pipeline_core import TokenAllocator


def _kept(*texts, label="OSOBA"):
    ents = [SimpleNamespace(text=t, label=label) for t in texts]
    return [e.text for e in ner_layer._filter_institutions(ents)]


@pytest.mark.parametrize("word", ["Data", "Zapłata", "Osoba", "Faktura", "Zamieszkały", "zamieszkaly", "Umowa", "OSOBA"])
def test_common_words_rejected_as_single_osoba(word):
    assert _kept(word) == []


@pytest.mark.parametrize("word", ["Nowak", "Kowalczyka", "Wroblewski", "Zając", "Wróbel", "Kot"])
def test_surnames_unchanged(word):
    assert onp.reject_single_osoba(word, _PERSON_FORMS) is False


@pytest.mark.parametrize("word", ["Maja", "Maj", "Czerwiec", "Styczeń", "Bill"])
def test_white_list_collision_with_known_name_stays(word):  # słownik albo Morfeusz (Codex r3/r4)
    assert word.lower() in onp.WHITE_LISTS
    assert onp.reject_single_osoba(word, _PERSON_FORMS) is False


def test_white_list_not_applied_without_morfeusz(monkeypatch):
    monkeypatch.setattr(onp, "_morf", SimpleNamespace(analyse=lambda w: 1 / 0))
    assert onp.reject_single_osoba("Faktura", _PERSON_FORMS) is False
    assert onp.reject_single_osoba("Data", _PERSON_FORMS) is True


def test_denylist_wins_over_name_dictionary():
    assert "data" in _PERSON_FORMS            # „Data” jako imię — kompromis jak w Mobile
    assert onp.reject_single_osoba("Data", _PERSON_FORMS) is True


def test_multiword_person_unchanged():
    assert _kept("Anna Osoba", "Jan Kowalski") == ["Anna Osoba", "Jan Kowalski"]
    assert onp.reject_single_osoba("Jan Data", _PERSON_FORMS) is False


def test_other_labels_untouched():
    # FIRMA nie przechodzi przez regułę OSOBA (inne filtry FIRMA bez zmian)
    assert ner_layer._filter_institutions([SimpleNamespace(text="Zamieszkały Serwis", label="FIRMA")])


def test_dictionary_path_list_unchanged():
    assert ner_adapter._OSOBA_DENYLIST is onp.DICTIONARY_PATH_DENYLIST
    assert len(onp.DICTIONARY_PATH_DENYLIST) == 216
    assert onp.OSOBA_DENYLIST <= onp.DICTIONARY_PATH_DENYLIST
    assert not (onp.DICTIONARY_PATH_DENYLIST & {"faktura", "bill", "zamieszkały"})


def test_dictionary_path_behaviour_unchanged():
    out = ner_adapter._apply_dictionary_names("Data wystawienia. Podpisał Kowalski.", TokenAllocator())
    assert "Data" in out and "Kowalski" not in out
