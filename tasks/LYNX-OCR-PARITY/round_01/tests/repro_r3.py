"""Independent retained F1 suffix reproducer. Usage: python repro_r3.py <backend>."""
import json
import subprocess
import sys
from pathlib import Path

backend = Path(sys.argv[1]).resolve()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=backend, text=True).strip() == '5282ffbbdcccf668781ca25a5af8540586402648'
sys.path.insert(0, str(backend))
import benchmark as b
import benchmark_ocr_diagnostics as d

def label(text):
    gt = {'file': 'synthetic.png', 'entities': {'email': 'anna@example.org'}}
    resp = {'bench_http_status': 200, 'original_text': text, 'tokens': []}
    result = b.analyze(gt, resp)
    assert result['summary']['privacy_missed'] == 1
    collector = d.Collector()
    collector.record(gt, resp, result)
    assert collector.summary()['consistent_with_legacy']
    return collector.items[0]['label']

assert label('Kontakt: anna@example.org.') == 'BUG_SILNIKA'
observed = label('Kontakt: anna@example.org.pl')
print(json.dumps({'id':'F1_DOMAIN_SUFFIX','observed':observed,'expected':'not BUG_SILNIKA'}))
raise SystemExit(1 if observed == 'BUG_SILNIKA' else 0)
