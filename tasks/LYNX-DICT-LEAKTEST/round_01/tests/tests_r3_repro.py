import json, os, pathlib, subprocess, sys
from types import SimpleNamespace as R
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'audyt'),str(ROOT/'backend')]
import engine_quality as eq
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='ec0c505205c7bb6511626818ee23cc3c13e4f640'
def res(text,rev=None,blocked=False,error=None):
    return R(text=text,reverse_map=rev or {},guard_blocked=blocked,error=error)
span='Jan Kowalski'; text='Strona: '+span+'.'
# Retained r2 input cases, now with the required corrected outcomes.
for output,rev,expected in [
    ('Strona: OSOBA_001 FIRMA_001.',{'OSOBA_001':'Jan','FIRMA_001':'Kowalski'},'wrong_category'),
    ('Strona: EMAIL_001 OSOBA_001.',{'EMAIL_001':'Jan','OSOBA_001':'Kowalski'},'wrong_category'),
    ('Strona: .',{'OSOBA_001':span},'no_mapping'),
    ('Strona: OSOBA_001.',{'OSOBA_001':span},'masked'),
]:
    actual=eq.classify_m1(text,span,'OSOBA',res(output,rev)); assert actual==expected
    print('R1:',expected,'PASS')
assert eq.classify_m1(text,span,'OSOBA',res(text,blocked=True))=='blocked'
assert eq.classify_m1(text,span,'OSOBA',res(text,error='injected'))=='error'
case=next(c for c in eq.build_cases() if c[0]=='M2-kwota')
result=res(case[3].replace('zapłaty','KWOTA_001'),{'KWOTA_001':'zapłaty'})
assert eq.measure([case],lambda _:result)[0]['status']=='fp'
positive=res(case[3].replace('1 250,00 zł','KWOTA_001'),{'KWOTA_001':'1 250,00 zł'})
assert eq.measure([case],lambda _:positive)[0]['status']=='contract'
print('R2 original payment-word repro fixed; real amount stays contract')
# Same named R2 class: allowed category applied to an ordinary word,
# this time sharing letters with the permitted address value.
case=next(c for c in eq.build_cases() if c[0]=='M2-ulica_patronimiczna')
original=case[3]
result=res(original.replace(' w centrum.',' ADRES_001 centrum.'),{'ADRES_001':'w'})
row=eq.measure([case],lambda _:result)[0]
assert row['status']=='contract' and row['m3']['status']=='identical'
assert eq.report([row],{}, {})['M2']=={'ALL':{'contract':1}}
print('R2 STILL OPEN: ordinary preposition replaced by ADRES => contract, M3 identical; actual address unchanged')
# A multi-character ordinary-word sibling, without relying on a one-character map value.
text='Biuro mieści się przy ul. Kowalskiego 7; kowal naprawia bramę.'
case=('R2-address-word','M2',None,text,None,{'ADRES':['ul. Kowalskiego 7']})
result=res(text.replace('; kowal','; ADRES_001'),{'ADRES_001':'kowal'})
row=eq.measure([case],lambda _:result)[0]
assert row['status']=='contract' and row['m3']['status']=='identical'
print('R2 STILL OPEN: ordinary five-letter word shares address substring => contract, M3 identical')
# Equivalent forbidden Windows paths, plus normal outside target; no file written.
inside=str(ROOT/'quality_forbidden.json')
for target in [inside,inside.swapcase(),str(ROOT/'audyt'/'..'/'quality_forbidden.json')]:
    try: eq._out_path(target)
    except SystemExit: pass
    else: raise AssertionError('R3 forbidden path accepted')
import tempfile
assert eq._out_path(str(pathlib.Path(tempfile.gettempdir())/'outside_quality.json'))
print('R3 original case-bypass closed; dot-segment and outside-path boundaries PASS')
assert eq.TOKEN_RE.findall('PL6110NUMER_001')==['NUMER_001']
print('Glued numeric token recognized; production token format unchanged')