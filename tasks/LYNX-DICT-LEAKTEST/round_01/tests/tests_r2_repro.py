import contextlib, io, json, os, pathlib, subprocess, sys, tempfile
from types import SimpleNamespace as R
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'audyt'),str(ROOT/'backend')]
import engine_quality as eq
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='e102fd87dd105caaa57baae5145ed4a017c00c9f'
def res(text,rev=None,blocked=False,error=None):
    return R(text=text,reverse_map=rev or {},guard_blocked=blocked,error=error)
span='Jan Kowalski'; text='Strona: '+span+'.'
for output,rev,expected in [
    ('Strona: OSOBA_001 FIRMA_001.',{'OSOBA_001':'Jan','FIRMA_001':'Kowalski'},'wrong_category'),
    ('Strona: EMAIL_001 OSOBA_001.',{'EMAIL_001':'Jan','OSOBA_001':'Kowalski'},'wrong_category'),
    ('Strona: .',{'OSOBA_001':span},'not masked: no output token'),
]:
    actual=eq.classify_m1(text,span,'OSOBA',res(output,rev))
    assert actual=='masked'
    print('R1:',expected,'=>',actual)
# Same category, wrong text: masking a normal word is an FP even in a sentence containing a real amount.
case=next(c for c in eq.build_cases() if c[0]=='M2-kwota')
original=case[3]
result=res(original.replace('zapłaty','KWOTA_001'),{'KWOTA_001':'zapłaty'})
rows=eq.measure([case],lambda _:result)
assert rows[0]['status']=='contract' and rows[0]['m3']['status']=='identical'
assert eq.report(rows,{}, {})['M2']=={'ALL':{'contract':1}}
print('R2: ordinary word masked as KWOTA; real amount still present => contract, M3 identical')
# Equivalent Windows paths: no file is written.
inside=str(ROOT/'quality_forbidden.json')
try: eq._out_path(inside)
except SystemExit: pass
else: raise AssertionError('canonical repo path should be rejected')
variant=inside.swapcase()
accepted=eq._out_path(variant)
assert os.path.normcase(accepted)==os.path.normcase(inside)
print('R3: same repository output path with changed case => accepted')
# Existing positive boundaries, error and blocked must stay non-success.
assert eq.classify_m1(text,span,'OSOBA',res('Strona: OSOBA_001.',{'OSOBA_001':span}))=='masked'
assert eq.classify_m1(text,span,'OSOBA',res(text,blocked=True))=='blocked'
assert eq.classify_m1(text,span,'OSOBA',res(text,error='injected'))=='error'
assert eq.classify_m2(set(),res('KWOTA_001',{'KWOTA_001':'zapłaty'}))=='fp'
assert eq.roundtrip('A. B.',res('A.B.'))['diff_outside_spans']==1
# Verify independent real runs are identical except date; missing holdout remains explicit.
a=json.loads((pathlib.Path(tempfile.gettempdir())/'lynx_dict_e102fd8_a.json').read_text(encoding='utf-8'))
b=json.loads((pathlib.Path(tempfile.gettempdir())/'lynx_dict_e102fd8_b.json').read_text(encoding='utf-8'))
a.pop('date'); b.pop('date'); assert a==b
assert a['HOLDOUT']=='NOT_MEASURED' and a['n_cases']==56
print('Real runs deterministic:',a['input_digest'],'M3',a['M3']['identical'],'/',a['M3']['checked'])
print('AUDIT: R1/R2/R3 reproduced; existing error/blocked boundaries retained')