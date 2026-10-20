"""Synthetic independent audit: benchmark -> diagnostics -> serialized reports.

Usage: python repro_r2.py <audited backend directory> [writable temporary parent]
Exit 1 confirms F1 on the delivered SHA. No HTTP/OCR/models/real data.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

backend = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(backend))
import benchmark as b
import benchmark_ocr_diagnostics as d

assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=backend, text=True).strip() == \
    '578d7a512525a1678bb1598d90c0da38c2ae3d44'


def record(key, value, text):
    gt = dict(file='synthetic.png', doc_type='audit', quality_score=90,
              degradation_level=0, entities={key: value})
    resp = dict(bench_http_status=200, original_text=text, tokens=[])
    legacy = b.analyze(gt, resp)
    c = d.Collector()
    c.record(gt, resp, legacy)
    assert legacy['summary']['privacy_missed'] == 1
    assert c.summary()['consistent_with_legacy']
    assert 'original_text' not in legacy
    return gt, resp, legacy, c


# A real unchanged gold value must still be classified as an engine candidate.
assert record('osoba', 'Jan Nowak', 'Podpis: Jan Nowak')[3].items[0]['label'] == 'BUG_SILNIKA'
# Missing input must be explicit; no invented OCR disappearance.
assert record('email', 'anna@example.org', None)[3].items[0]['label'] == 'NOT_MEASURED'
# Independent boundary checks, including 14/23 immediately below thresholds.
for n, limit in [(9, 1), (14, 1), (15, 2), (23, 2), (24, 3)]:
    value = 'a' * n
    assert d.classify_miss(value, 'b' * limit + value[limit:])[0] == 'OCR_ZNIEKSZTAŁCONY'
    assert d.classify_miss(value, 'b' * (limit+1) + value[limit+1:])[0] == 'BRAK_W_OCR'

# Full relevant seam: legacy analyze -> wrapper -> build_report -> diagnostic file.
gt, resp, legacy, _ = record('email', 'anna@example.org', 'Kontakt: annaQexample.org')
saved = d._DEFAULT
try:
    with tempfile.TemporaryDirectory(prefix='lynx-ocr-r2-', dir=sys.argv[2] if len(sys.argv) > 2 else None) as tmp:
        roots = [Path(tmp) / name for name in ('legacy', 'hooked', 'repeat')]
        for root in roots:
            root.mkdir()
        with contextlib.redirect_stdout(io.StringIO()), patch.object(b, 'datetime') as clock:
            clock.now.return_value.strftime.return_value = 'FIXED_AUDIT_TIMESTAMP'
            b.build_report([legacy], roots[0])
            for root in roots[1:]:
                d._DEFAULT = d.Collector()
                actual = d.analyze_and_record(b.analyze, gt, resp)
                assert actual == legacy
                d.build_report_and_write(b.build_report, [actual], root)
        for name in ('report.json', 'summary.txt', 'bugs.txt'):
            baseline = (roots[0] / name).read_text(encoding='utf-8').replace(str(roots[0]), '<RUN>')
            hooked = (roots[1] / name).read_text(encoding='utf-8').replace(str(roots[1]), '<RUN>')
            assert hooked == baseline, name
        a = (roots[1] / 'ocr_diagnostics.json').read_text(encoding='utf-8')
        assert a == (roots[2] / 'ocr_diagnostics.json').read_text(encoding='utf-8')
        assert 'anna' not in a and 'example.org' not in a
finally:
    d._DEFAULT = saved
print('INDEPENDENT_MECHANICS: PASS (legacy artifacts, deterministic diagnostics, no raw values)')

# F1: all gold characters as a substring of a DIFFERENT name/email/longer number
# must not be proof that the unchanged gold entity is present in engine input.
failures = []
for sid, key, value, text in [
    ('F1_PERSON', 'osoba', 'Jan Nowak', 'Podpis: Jan Nowakowski'),
    ('F1_EMAIL', 'email', 'anna@example.org', 'Kontakt: joanna@example.org'),
    ('F1_NUMBER', 'pesel', '44051401359', 'Numer: 1440514013599'),
]:
    _, _, _, collector = record(key, value, text)
    label = collector.items[0]['label']
    failures.append(label == 'BUG_SILNIKA')
    print(json.dumps(dict(id=sid, observed=label, expected='not BUG_SILNIKA'), ensure_ascii=False))
print('F1_REPRODUCED:', sum(failures), '/', len(failures))
raise SystemExit(1 if any(failures) else 0)

