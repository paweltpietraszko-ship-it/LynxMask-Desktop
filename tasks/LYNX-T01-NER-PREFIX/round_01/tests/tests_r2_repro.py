"""Independent synthetic T01 comparison. Run from repo root with py -3."""
import contextlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from collections import namedtuple
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == 'bec0fc852471a65140deab00a105d1438afa7749'
sys.path.insert(0, str(ROOT / 'backend'))
logging.disable(logging.CRITICAL)
os.environ['PROFILE_DIR'] = tempfile.mkdtemp(prefix='lynx_codex_guard_')
import ner_layer
old = types.ModuleType('t01_before')
exec(compile(subprocess.check_output(['git', 'show', '069df2f:backend/ner_layer.py'], cwd=ROOT).decode('utf-8'), 't01_before', 'exec'), old.__dict__)
NER = namedtuple('NER', 'text label confidence start end')
new_filter = ner_layer._filter_institutions
persons = ['Katarzyna Wiśniewska', 'Aleksandra Kwiatkowska', 'Kowalski', 'Wiśniewski', 'Bartłomiej', 'Maciej', 'Nowakowej']
negatives = [('Warszawie', 'OSOBA'), ('KONTROLNA', 'OSOBA'), ('Piątek', 'OSOBA'), ('Encje', 'OSOBA'), ('Warszawa', 'FIRMA'), ('ZUS', 'FIRMA'), ('Sąd Rejonowy w Krakowie', 'FIRMA'), ('OSOBA_001', 'OSOBA'), ('ul. Jana Kowalskiego', 'OSOBA')]
def kept(fn, text, label='OSOBA'):
    return bool(fn([NER(text, label, .99, 0, len(text))]))
assert sum(kept(old._filter_institutions, x) for x in persons) == 0
assert all(kept(new_filter, x) for x in persons)
assert not any(kept(new_filter, x, label) for x, label in negatives)
with patch.object(ner_layer, '_morfeusz', False):
    assert kept(new_filter, 'Wiśniewska')
    assert not kept(new_filter, 'Radom')
assert not kept(old._filter_institutions, 'Kowalskiego')
assert not kept(new_filter, 'Kowalskiego')

from pipeline import AppState, pseudonymize_document
from anonymizer import build_anonymizer
import spacy_ner
st = AppState()
st.spacy_ner_mod = spacy_ner
profile = tempfile.mkdtemp(prefix='lynx_codex_synthetic_')
with contextlib.redirect_stdout(io.StringIO()):
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(profile, str(Path(profile) / 'hw.json'))
samples = [('PRACOWNIKIEM:\nKatarzyna Wiśniewska\nPodpis:', 'Katarzyna Wiśniewska'), ('Wnioskodawca Aleksandra Kwiatkowska złożyła pismo.', 'Aleksandra Kwiatkowska'), ('Kowalski nie przyszedł do pracy.', 'Kowalski'), ('Wiśniewski był nieobecny.', 'Wiśniewski')]
controls = ['Dokument przekazano do ZUS.', 'Sąd Rejonowy w Krakowie wydał postanowienie.', 'Adres: ul. Jana Kowalskiego 12, 00-001 Warszawa.', 'Termin upływa w piątek.', 'LISTA KONTROLNA\nEncje do sprawdzenia.']
metrics = {}
for mode, fn in [('before', old._filter_institutions), ('after', new_filter)]:
    with patch.object(ner_layer, '_filter_institutions', fn), contextlib.redirect_stdout(io.StringIO()):
        results = [pseudonymize_document(text, st) for text, _ in samples]
        ctr = [pseudonymize_document(text, st) for text in controls]
    metrics[mode] = {'masked_person_samples': sum(value not in result.text for (_, value), result in zip(samples, results)), 'person_samples': len(samples), 'control_person_company_tokens': sum(sum(k.startswith(('OSOBA_', 'FIRMA_')) for k in result.reverse_map) for result in ctr), 'control_samples': len(controls), 'errors': sum(result.error is not None for result in results + ctr)}
    if mode == 'after':
        assert all(value not in result.text for (_, value), result in zip(samples, results))
        assert all(any(k.startswith('OSOBA_') for k in result.reverse_map) for result in results)
assert metrics['after']['control_person_company_tokens'] <= metrics['before']['control_person_company_tokens']
assert metrics['after']['errors'] == 0
import pipeline
import layers.ner_adapter as adapter
with patch.object(adapter, 'process_ner', side_effect=RuntimeError('synthetic NER failure')):
    result = pseudonymize_document('Tekst syntetyczny do sprawdzenia blokady.', st)
    assert result.guard_blocked
with patch.object(pipeline, 'guard_output_with_map', side_effect=RuntimeError('synthetic guard failure')):
    result = pseudonymize_document('Zwykły tekst do sprawdzenia blokady.', st)
    assert result.guard_blocked
print(json.dumps({'filter': '7 repaired; 9 negative controls; degraded preserved; geo-exact unchanged', 'pipeline_guard': metrics, 'ner_and_guard_failure': 'blocked'}, ensure_ascii=True))
