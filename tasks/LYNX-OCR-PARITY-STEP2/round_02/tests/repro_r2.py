"""Independent B1 hash preflight and holdout isolation. No models/inference/datasets.

Run: python repro_r2.py <audited repo> <writable temporary parent>.
Exit 1 confirms F1: known mismatching model hashes do not stop main.
"""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == \
    'a9547667d2a289a4c0c9017b344e69429d176509'
sys.path.insert(0, str(root/'backend'))
spec = importlib.util.spec_from_file_location('pq_audit', root/'tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py')
pq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pq)
import ocr_rapid


def doc(label):
    return {'valid': True, 'file': 'synthetic.png', 'level': 0, 'secs': 0,
            'features': {'min': 0.99, 'q10': 0.99},
            'gold': [{'key': 'pesel', 'type': 'NUMER', 'critical': True, 'label': label}]}


with tempfile.TemporaryDirectory(prefix='lynx-b1-r2-', dir=sys.argv[2]) as folder:
    tmp = Path(folder)
    models = tmp/'models'
    models.mkdir()
    for name in pq.MODEL_SHA256:
        (models/name).write_bytes(b'deliberately-invalid-synthetic-model')
    preflight = pq.preflight(models)
    assert preflight is not None and preflight['models_match_phase_a'] is False
    for name in ('known', 'holdout'):
        (tmp/name).mkdir()
        (tmp/name/'ground_truth.json').write_text('[]', encoding='utf-8')
    reports, engine_calls, codes = [], [], []
    # Same known set, radically different holdout: known choice must stay the same.
    for i, hold_label in enumerate(('INTACT', 'MISSING')):
        out = tmp/f'report{i}.json'
        def dataset(engine, path):
            return [doc('INTACT' if path.name == 'known' else hold_label)]
        def engine():
            engine_calls.append(i)
            return object()
        with patch.object(ocr_rapid, 'model_dir', return_value=models), \
             patch.object(ocr_rapid, '_get_engine', side_effect=engine), \
             patch.object(pq, 'run_dataset', side_effect=dataset), \
             contextlib.redirect_stdout(io.StringIO()):
            code = pq.main(['--known', str(tmp/'known'), '--holdout', str(tmp/'holdout'), '--out', str(out)])
        codes.append(code)
        reports.append(json.loads(out.read_text(encoding='utf-8')) if out.exists() else None)
        print(json.dumps({'id':f'F1_HASH_{i}', 'exit_code':code, 'engine_called':i in engine_calls,
                          'report_written':out.exists(), 'models_match':preflight['models_match_phase_a']}))
    if all(r is not None for r in reports):
        assert reports[0]['chosen_on_known'] == reports[1]['chosen_on_known']
        assert reports[0]['verdict'] == 'CANDIDATE' and reports[1]['verdict'] == 'NO_SAFE_GATE'
        print('HOLDOUT_SELECTION_ISOLATION PASS (synthetic stubs, no real holdout used)')
    failed = bool(engine_calls) or codes != [2, 2] or any(r is not None for r in reports)
    print('F1_REPRODUCED' if failed else 'F1_CLOSED')
    raise SystemExit(1 if failed else 0)

