import pathlib, subprocess, sys
from types import SimpleNamespace as R
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'audyt'),str(ROOT/'backend')]
import engine_quality as eq
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='528856b9b4c07d4fac2d623d0dab23c709c6c4ee'
def res(text,rev=None,blocked=False,error=None):
    return R(text=text,reverse_map=rev or {},guard_blocked=blocked,error=error)
# Retain the original r2 payment-word repro and both r3 siblings.
amount=next(c for c in eq.build_cases() if c[0]=='M2-kwota')
street=next(c for c in eq.build_cases() if c[0]=='M2-ulica_patronimiczna')
wordtext='Biuro mieści się przy ul. Kowalskiego 7; kowal naprawia bramę.'
wordcase=('R2-address-word','M2',None,wordtext,None,{'ADRES':['ul. Kowalskiego 7']})
checks=[
(amount,res(amount[3].replace('zapłaty','KWOTA_001'),{'KWOTA_001':'zapłaty'}),'fp'),
(street,res(street[3].replace(' w centrum.',' ADRES_001 centrum.'),{'ADRES_001':'w'}),'fp'),
(wordcase,res(wordtext.replace('; kowal','; ADRES_001'),{'ADRES_001':'kowal'}),'fp'),
(amount,res(amount[3].replace('1 250,00 zł','KWOTA_001'),{'KWOTA_001':'1 250,00 zł'}),'contract'),
(street,res(street[3].replace('ul. Kowalskiego 7','ADRES_001'),{'ADRES_001':'ul. Kowalskiego 7'}),'contract'),
(street,res(street[3].replace('ul. Kowalskiego 7','ADRES_001'),{'ADRES_001':'ul.Kowalskiego7'}),'contract'),
(amount,res(amount[3].replace('1 250,00 zł','ADRES_001'),{'ADRES_001':'1 250,00 zł'}),'fp'),
(amount,res(amount[3]),'clean'),
(amount,res(amount[3],blocked=True),'blocked'),
(amount,res(amount[3],error='injected'),'error'),
]
for case,result,expected in checks:
    row=eq.measure([case],lambda _:result)[0]
    assert row['status']==expected,(case[0],row['status'],expected)
    rep=eq.report([row],{}, {})
    assert rep['M2']=={'ALL':{expected:1}}
print('R2 CLOSED: 3 retained negative reproducers, 3 legitimate address/amount positives, wrong category, clean, blocked, error; measure/report agree (10 checks)')
# The second r3 reproducer still restores exactly, now correctly counted as FP.
row=eq.measure([checks[2][0]],lambda _:checks[2][1])[0]
assert row['status']=='fp' and row['m3']['status']=='identical'
print('Identical round-trip no longer hides that FP')