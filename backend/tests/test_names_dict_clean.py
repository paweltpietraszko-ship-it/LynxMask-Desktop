"""[LYNX-NAMES-DICT-CLEAN] Słownik imion bez form obcych słów (Tom → być/jest, Ala → ale…). Uruchamiać wprost (cwd backend)."""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from pipeline_new import run_pipeline_new

_NAMES = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "names_inflected.json"), encoding="utf-8"))
_FORMS = {f for k, v in _NAMES.items() for f in v if f != k}


@pytest.mark.parametrize("word", ["ale", "jest", "jestem", "być", "była", "tym", "tego", "nic", "kto", "albo", "rano", "taniej", "będę"])
def test_foreign_words_removed_from_name_forms(word):
    assert word not in _FORMS


@pytest.mark.parametrize("base,form", [("anna", "annie"), ("maja", "maję"), ("oliwia", "oliwię"), ("tomasz", "tomasza"),
                                       ("katarzyna", "katarzyny"), ("piotr", "piotrowi")])
def test_real_name_forms_kept(base, form):
    assert form in _NAMES[base]


def _osoby(text):
    out, rmap, _ = run_pipeline_new(text, {}, None)
    return out, [v for k, v in rmap.items() if k.startswith("OSOBA")]


def test_common_words_at_sentence_start_not_person():
    out, osoby = _osoby("Ale to nie wszystko. Jest dobrze. Być może wrócimy. Nic nie wiadomo.")
    assert osoby == [], (out, osoby)


def test_zawarta_label_not_person():
    out, osoby = _osoby("Umowa zlecenia\nZawarta pomiędzy: Jan Kowalski a Anna Nowak.")
    assert "Zawarta" in out and set(osoby) == {"Jan Kowalski", "Anna Nowak"}, (out, osoby)


def test_names_still_masked():
    out, osoby = _osoby("Pismo podpisała Maja. Tomasz Zając i Ala Kot byli obecni.")
    assert "Maja" not in out and "Zając" not in out and "Kot" not in out, (out, osoby)
