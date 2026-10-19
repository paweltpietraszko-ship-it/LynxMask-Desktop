"""Independent held-out cases for frozen 4a1cbf0, stdlib CLI only."""
import ast
import collections
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[4]
sim = root / 'backend/arena_sim.py'

def candidate(s, e, kind='OSOBA'):
    return dict(start=s, end=e, kind=kind, source='heldout', evidence=['FORMAT'])

def run(cases):
    p = subprocess.run([sys.executable, str(sim)], input=''.join(json.dumps(x)+'\n' for x in cases),
                       encoding='utf-8', capture_output=True, timeout=30)
    assert p.returncode == 0 and not p.stderr
    result = [json.loads(x) for x in p.stdout.splitlines()]
    assert len(result) == len(cases)
    return result

def check(text, r):
    if r['status'] == 'STOP':
        assert r['masked'] is None and r['tokens'] == [] and r['guard_flags'] == []
        return []
    errors, cursor, rendered, mapping = [], 0, '', {}
    for t in r['tokens']:
        s,e = t['start'],t['end']
        assert t['original'] == text[s:e]
        rendered += text[cursor:s] + t['token']
        cursor = e
        mapping[t['token']] = t['original']
        if (s and text[s-1].isalnum() and text[s].isalnum()) or (e < len(text) and text[e-1].isalnum() and text[e].isalnum()):
            errors.append('N2')
    assert rendered + text[cursor:] == r['masked']
    import re
    restored = re.sub(r'\b(?:OSOBA|EMAIL|ADRES)_\d{3}(?!\d)', lambda m: mapping.get(m[0], m[0]), r['masked'])
    if restored != text:
        errors.append('N3')
    return sorted(set(errors))

cases = [
    dict(text='Świadek: Jan Kowalski.',base_candidates=[candidate(9,21)]),
    dict(text='😀 Kontakt: ola@biuro.pl; ola@biuro.pl',base_candidates=[]),
    dict(text='Adres: ul. Lipowa 7\nKontakt: ola@biuro.pl',base_candidates=[]),
    dict(text='Jan Kowalski',base_candidates=[candidate(0,2)]),
    dict(text='Jan Kowalski',base_candidates=[candidate(1,3)]),
    dict(text='Kontakt: ale\u0301x@biuro.pl',base_candidates=[]),
]
out = run(cases)
for i,(c,r) in enumerate(zip(cases,out),1):
    print(json.dumps({'own':i,'status':r['status'],'reason':r['reason_code'],'invariant_errors':check(c['text'],r)}))
    if i in (4,5):
        print(json.dumps({'own':i,'synthetic_input':c,'masked':r['masked']}, ensure_ascii=False))
assert out[0]['masked'] == 'Świadek: OSOBA_001.'
assert out[1]['tokens'][0]['token'] == out[1]['tokens'][1]['token']
assert len(out[2]['tokens']) == 2
# Generalization: duplicate/source/evidence order, document isolation, Unicode prefix and separator.
base = candidate(9,21)
variants = [cases[0], dict(text=cases[0]['text'],base_candidates=[dict(base,source='B'),dict(base,source='A')]),
            cases[1],cases[0],dict(text='😀 '+cases[0]['text'],base_candidates=[candidate(11,23)])]
v = run(variants)
for i in [1,3]:
    assert all(v[i][k] == v[0][k] for k in ['status','masked','tokens','guard_flags'])
assert v[4]['masked'] == '😀 '+v[0]['masked']
print('metamorphisms_pass=5')
# Cross-check fixture gold against independently selected literal values.
tree = ast.parse((root/'backend/tests/test_arena_sim.py').read_text(encoding='utf-8'))
frozen = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in n.targets))
values = [['ala@firma.pl'],['ala@firma,pl'],['ala@firma .pl'],['ul. Polna l2/8'],[],[],
          ['ul. Polna 12, 65-001 Poznań'],['ala@firma.pl'],['ala@firma.pl','ul. Polna l2'],
          ['ala@firma.pl'],['9O05141234O'],[],['żaneta@firma.pl'],['ala@firma.pl','ala@firma.pl'],[],['ul. Polna l2/8','9O05141234O']]
for (_,text,_,gold),expect in zip(frozen,values):
    assert [text[s:e] for s,e,k in gold] == expect
results = run([dict(text=t,base_candidates=b) for _,t,b,g in frozen])
counts = collections.Counter()
for (_,text,_,gold),r in zip(frozen,results):
    assert not check(text,r)
    got = [(x['start'],x['end'],x['kind']) for x in r['tokens']]
    counts['safe_refusal' if r['status']=='STOP' else 'protection_pass' if got==gold else 'protection_fail'] += 1
print('independent_A01_A16='+json.dumps(dict(counts)))
