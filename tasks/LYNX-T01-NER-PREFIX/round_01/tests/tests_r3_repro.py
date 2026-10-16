"""T01 r2: retained reproducer plus independent paired synthetic benchmark."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = 'b5a190e887cb954dbfdb9ef258e1c0db6d017675'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == SHA
# Keep r2 untouched; only adapt its exact-SHA guard in memory.
retained = (Path(__file__).with_name('tests_r2_repro.py')).read_text(encoding='utf-8')
exec(compile(retained.replace('bec0fc852471a65140deab00a105d1438afa7749', SHA), str(Path(__file__).with_name('tests_r2_repro.py')), 'exec'))
sys.path.insert(0, str(ROOT / 'audyt'))
import bench_offline
import benchmark
from document_processor import _extract_text
from repro_pipeline import build_state
import ner_layer
import pipeline

dataset = ROOT / 'backend' / 'dataset_20260627_095419'
gt_bytes = (dataset / 'ground_truth.json').read_bytes()
assert hashlib.sha256(gt_bytes).hexdigest() == 'b2e580ae7a9b68d113667f3794acd401239d278db577ddcf98309b0d06802646'
gt = json.loads(gt_bytes)
assert len(gt) == 50
work = Path(tempfile.mkdtemp(prefix='lynx_codex_t01_benchmark_'))
print('OCR 50 synthetic documents; shared cache for both filters', flush=True)
cache = {}
for index, item in enumerate(gt, 1):
    file = dataset / 'images' / Path(item['file']).name
    with contextlib.redirect_stdout(io.StringIO()):
        text, err, meta = _extract_text(file.read_bytes(), file.name)
    cache[item['file']] = {'text': text, 'err': err, 'meta': meta}
    if index % 10 == 0:
        print('OCR progress', index, flush=True)
(work / 'ocr.json').write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
summaries = {}
for mode, fn in [('before', old._filter_institutions), ('after', new_filter)]:
    with contextlib.redirect_stdout(io.StringIO()):
        state = build_state(False)
    results = []
    with patch.object(ner_layer, '_filter_institutions', fn):
        for item in gt:
            ocr = cache[item['file']]
            text = (ocr['text'] or '').strip()[:15000]
            meta = ocr['meta']
            if ocr['err']:
                response = {'error': ocr['err'], 'ocr': meta, 'bench_http_status': 400}
            elif meta and meta.get('quality') == 'reject':
                response = {'ocr_rejected': True, 'ocr': meta, 'bench_http_status': 422}
            else:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = pipeline.pseudonymize_document(text, state)
                response = {'tokens': [{'token': key, 'original': value, 'type': key.rsplit('_', 1)[0]} for key, value in result.reverse_map.items()], 'anonymized_preview': result.text, 'blocked': result.guard_blocked, 'guard_reasons': result.guard_reasons, 'ocr': meta, 'bench_http_status': 200}
            results.append(benchmark.analyze(item, response))
    accepted = [r for r in results if not r['ocr_rejected'] and r.get('http_status') == 200]
    entities = [e for r in accepted for e in r['entities']]
    persons = [e for e in entities if e['expected_type'] == 'OSOBA']
    critical = [e for e in entities if e['critical']]
    summaries[mode] = {'docs': len(accepted), 'osoba_found': sum(e['privacy_found'] for e in persons), 'osoba_total': len(persons), 'fp': sum(len(r['false_positives']) for r in accepted), 'critical_leaks': sum(not e['privacy_found'] for e in critical), 'critical_total': len(critical)}
    print(mode, json.dumps(summaries[mode]), flush=True)
(work / 'summary.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
print('Synthetic artifacts:', str(work), flush=True)
assert summaries['after']['osoba_found'] >= summaries['before']['osoba_found']
assert summaries['after']['fp'] <= summaries['before']['fp']
assert summaries['after']['critical_leaks'] <= summaries['before']['critical_leaks']
