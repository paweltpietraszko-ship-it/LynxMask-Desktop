"""Independent F2 sibling cases. Synthetic texts; argv backend state_dir."""
import contextlib
import io
import json
import os
import sys
import tempfile
backend, state_dir = map(os.path.abspath, sys.argv[1:3])
os.makedirs(state_dir, exist_ok=True)
os.environ['PROFILE_DIR'] = state_dir
os.environ['ANONYMIZER_PROFILE_DIR'] = state_dir + '/a'
os.chdir(backend)
sys.path.insert(0, backend)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
from layers.ner_adapter import _sub_whole
from person_layout import apply_person_layout
from pipeline_core import TokenAllocator

cases = [
    ('title_quote', 'Pismo przekazała Pani Termin. W formularzu widnieje nagłówek „Termin wykonania”.', 'Termin wykonania'),
    ('token_quote', 'Skargę złożyła Lucyna Osoba. W formularzu widnieje nagłówek „Osoba do kontaktu”.', 'Osoba do kontaktu'),
    ('initial_quote', 'Podpisał J. Kapusta. Na liście produktów widnieje „Kapusta kiszona”.', 'Kapusta kiszona'),
    ('sentence_control', 'Pismo przekazała Pani Termin. Termin wykonania upływa jutro.', 'Termin wykonania'),
    ('person_control', 'Pismo przekazała Pani Malina. Wniosek podpisała wczoraj Malina osobiście.', None),
]
for key, text, ordinary in cases:
    a = TokenAllocator()
    seam = apply_person_layout(text, a, _sub_whole)
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    folder = tempfile.mkdtemp(dir=state_dir)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(folder, folder + '/hw.json')
        r = pseudonymize_document(text, st)
    print(json.dumps({'case':key,'input':text,'seam':seam,'output':r.text,
                      'ordinary_kept': ordinary in r.text if ordinary else None,
                      'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings]},ensure_ascii=False))

