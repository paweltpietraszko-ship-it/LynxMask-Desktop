"""Independent synthetic CLI/offset check; run with audited backend path as argument."""
import json
import subprocess
import sys
from pathlib import Path

backend = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(backend))
import arena_signal_probe as p


def build(sid, blocks):
    text, gold = '', []
    for b in blocks:
        if isinstance(b, str):
            text += b
        else:
            value, kind = b
            gold.append(dict(start=len(text), end=len(text)+len(value), kind=kind))
            text += value
    return dict(id=sid, text=text, gold=gold)


samples = [
    build('C01', ['PESEL: ', ('44051401359', 'NUMER'), '; kontakt: ', ('audyt.one@example.org', 'EMAIL'), '.']),
    build('C02', ['Pani ', ('Monika Lis', 'OSOBA'), ' reprezentuje ', ('Pomorska Fabryka Okien Sp. z o.o.', 'FIRMA'), '.']),
    build('C03', ['Adres: ', ('ul. Lipowa 17, 30-001 Kraków', 'ADRES'), '. E-mail: ', ('biuro.test@example.org', 'EMAIL'), '.'])
]
r = subprocess.run([sys.executable, str(backend/'arena_signal_probe.py')],
                   input=''.join(json.dumps(s, ensure_ascii=False)+'\n' for s in samples),
                   capture_output=True, text=True, encoding='utf-8', cwd=backend)
assert r.returncode == 0, (r.returncode, r.stderr)
out = json.loads(r.stdout)
print(json.dumps(out, ensure_ascii=False), flush=True)
assert out['samples'] == 3
assert not any(k.startswith('SOURCE_') for k in out['gold']), out['gold']
assert out['gold']['EXACT_CANDIDATE'] == 6, out['gold']
for v in out['variants'].values():
    assert v['invariant_failures'] == 0
    assert v['fn'] == v['fn_partial'] == v['fp'] == v['overmask'] == 0
assert out['variants']['strict']['status:STOP'] == 2
assert out['variants']['strict']['status:RENDERED'] == 1
assert out['variants']['structured']['status:RENDERED'] == 3
for s in samples:
    for g in s['gold']:
        assert s['text'][g['start']:g['end']] not in r.stdout


def shifted(state):
    state.allocator.allocate('NUMER', '44051401359', 8, 19)
    state.text = state.text[:7] + 'NUMER_001' + state.text[18:]


bad = p.probe(samples[0], layers=p._layers() | {'identity': shifted},
              spacy_fn=lambda t: p._source('OK'))
assert bad['sources']['identity']['status'] == 'MAPPING_ERROR'
assert bad['gold'][0] == 'SOURCE_MAPPING_ERROR'
assert all(v['status'] == 'NOT_RUN' for v in bad['variants'].values())
print('INDEPENDENT_OFFSET_REPRO PASS')
