"""Independent synthetic reproducer. argv: exact backend directory, isolated state directory.
Run with repository .venv Python; no service, user profile, or real documents.
"""
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
from guard_residue import _morf_interps

cases = [
    ('F1a', 'Pismo przekazał Ladzinski.', 'Ladzinski'),
    ('F1b', 'Pismo przekazał Cieslikowski.', 'Cieslikowski'),
    ('F1c', 'Pismo przekazał Ladziński.', 'Ladziński'),
    ('F2a', 'Pismo przekazała Pani Termin. Termin wykonania upływa jutro.', 'Termin wykonania'),
    ('F2b', 'Pismo przekazała Pani Kawa. Kawa i herbata zostały.', 'Kawa i herbata'),
]
for key, text, target in cases:
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    folder = tempfile.mkdtemp(dir=state_dir)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(folder, folder + '/hw.json')
        res = pseudonymize_document(text, st)
    warnings = [{'fragment': w['fragment'], 'rules': w['rules']} for w in res.guard_warnings]
    print(json.dumps({'case': key, 'input': text, 'output': res.text, 'warnings': warnings,
                      'target_visible': target in res.text}, ensure_ascii=False))
for word in ['Ladzinski', 'Ladziński', 'Cieslikowski', 'Cieślikowski']:
    print(json.dumps({'morph_word': word, 'analyses': [i[2][1:4] for i in (_morf_interps(word) or [])]}, ensure_ascii=False))

