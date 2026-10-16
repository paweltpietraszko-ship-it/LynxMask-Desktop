"""Independent T03 audit: allocator boundaries, NER variants and real pipeline."""
import contextlib
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == '51ff9760bb71265026d212956ccff0ffac442429'
sys.path.insert(0, str(ROOT / 'backend'))
logging.disable(logging.CRITICAL)
os.environ['PROFILE_DIR'] = tempfile.mkdtemp(prefix='lynx_t03_guard_')
from pipeline_core import TokenAllocator, PipelineState
from layers.ner_adapter import apply_ner_layer
checks = 0
def check(condition):
    global checks
    checks += 1
    assert condition, checks

allocator = TokenAllocator()
for tid in ['OSOBA_007', 'OSOBA_003', 'FIRMA_020', 'OSOBA_001']:
    allocator.reserve(tid)
check(allocator.reverse_map == {})
check(not allocator.is_occupied(0, 100))
check(allocator.assign('OSOBA', 'Adam Testowy') == 'OSOBA_008')
check(allocator.assign('OSOBA', 'Adam  Testowy') == 'OSOBA_008')
check(allocator.assign('OSOBA', 'Piotr Testowy') == 'OSOBA_009')
check(allocator.assign('FIRMA', 'Testowe ABC') == 'FIRMA_021')
check(allocator.allocate('OSOBA', 'Adam Testowy', 0, 12) == 'OSOBA_008')
check(allocator.allocate('OSOBA', 'Inna Osoba', 1, 5) is None)
before = allocator.reverse_map
try:
    allocator.register('OSOBA_008', 'Zofia Testowa', 30, 42)
except ValueError as error:
    check('Zofia' not in str(error) and 'Adam' not in str(error))
else:
    raise AssertionError('collision accepted')
check(allocator.reverse_map == before)

# Alternate NER paths: base present, variant only, neither present.
for text, expected in [('Jan Kowalski i Jana Kowalskiego.', True), ('Wniosek Jana Kowalskiego.', True), ('Zwykły tekst.', False)]:
    a = TokenAllocator()
    a.reserve('OSOBA_007')
    state = PipelineState(text=text, allocator=a)
    state.ner_results = {'OSOBA_001': 'Jan Kowalski'}
    state.ner_variants = {'Jana Kowalskiego': 'OSOBA_001'}
    apply_ner_layer(state, {})
    check(('OSOBA_008' in state.text) == expected)
    check('OSOBA_001' not in state.text)
    check(bool(a.reverse_map) == expected)
    if expected:
        check('Kowalsk' not in state.text)
        check(list(a.reverse_map) == ['OSOBA_008'])

from pipeline import AppState, pseudonymize_document
from anonymizer import build_anonymizer
import spacy_ner
import pipeline_new
st = AppState()
st.spacy_ner_mod = spacy_ner
profile = tempfile.mkdtemp(prefix='lynx_t03_independent_profile_')
with contextlib.redirect_stdout(io.StringIO()):
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(profile, str(Path(profile) / 'hw.json'))
    first_id = st.anon_map.add_entity('Jan Kowalski', 'OSOBA')
    second_id = st.anon_map.add_entity('Anna Malinowska', 'OSOBA')
    r1 = pseudonymize_document('Dłużnik Piotr Nowak mieszka w Radomiu.', st)
    r2 = pseudonymize_document('Pacjent Jan Kowalski był w szpitalu.', st)
    r3 = pseudonymize_document('Jan Kowalski i Jana Kowalskiego.', st)
check(first_id not in r1.reverse_map and second_id not in r1.reverse_map)
check(any(value == 'Piotr Nowak' and key not in [first_id, second_id] for key, value in r1.reverse_map.items()))
check(r2.reverse_map.get(first_id) == 'Jan Kowalski')
check(second_id not in r2.reverse_map)
check('Kowalsk' not in r3.text)
check([key for key, value in r3.reverse_map.items() if 'Kowalsk' in value] == [first_id])
check(all(not result.error and not result.guard_blocked for result in [r1, r2, r3]))

def collide(state, anonymizer):
    state.allocator.register('OSOBA_001', 'Adam Testowy', 0, 12)
    state.allocator.register('OSOBA_001', 'Zofia Testowa', 20, 32)
with patch.object(pipeline_new, 'apply_trie_layer', collide):
    blocked = pseudonymize_document('Syntetyczny test konfliktu.', st)
check(blocked.guard_blocked)
check(any('FORCE_BLOCK' in reason for reason in blocked.guard_reasons))
print({'independent_checks': checks, 'profile_documents': 3, 'variant_paths': 3, 'collision_pipeline_guard': 'blocked', 'result': 'PASS'})
