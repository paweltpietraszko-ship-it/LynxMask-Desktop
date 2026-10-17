import sys, os; sys.path.insert(0, os.getcwd())
from unittest.mock import patch
import spacy_ner
from spacy_ner import NERResult
from pipeline_new import run_pipeline_new
def fake(word):
    def det(text):
        i = text.find(word); return [NERResult(word, "OSOBA", 0.9, i, i+len(word))] if i >= 0 else []
    return det
for text in ["Wniosek Kowalskiego został przyjęty.", "Mieszka przy ul. Kowalskiego 7 w Radomiu."]:
    with patch.object(spacy_ner, "detect_entities", fake("Kowalskiego")):
        out, rev, _ = run_pipeline_new(text, anon_map={})
    print("MOCK ", repr(out), {k: v for k, v in rev.items()})
    out, rev, _ = run_pipeline_new(text, anon_map={})
    print("SPACY", repr(out), {k: v for k, v in rev.items()})
