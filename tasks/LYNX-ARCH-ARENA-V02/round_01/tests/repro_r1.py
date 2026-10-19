"""Independent CLI comparison; gold stays outside runtime payloads."""
import ast, collections, itertools, json, pathlib, re, runpy, subprocess, sys, unicodedata
root=pathlib.Path(__file__).resolve().parents[4]
def cli(script, cases):
 p=subprocess.run([sys.executable,str(root/'backend'/script)],input=''.join(json.dumps(x)+'\n' for x in cases),encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode==0 and not p.stderr
 out=[json.loads(x) for x in p.stdout.splitlines()]; assert len(out)==len(cases)
 return out,p.stdout
fixture=ast.parse((root/'backend/tests/test_arena_sim.py').read_text(encoding='utf-8'))
a=next(ast.literal_eval(n.value) for n in fixture.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in n.targets))
x=runpy.run_path(str(root/'tasks/LYNX-ARCH-ARENA/attacks/attacks_cc_r1.py'))['T']
def sp(t,v,k):
 s=t.index(v); return (s,s+len(v),k)
def cand(g):
 return dict(start=g[0],end=g[1],kind=g[2],source='unseen',evidence=['FORMAT'])
own=[]
def add(name,t,vals,gold): own.append((name,t,[cand(sp(t,v,k)) for v,k in vals],[sp(t,v,k) for v,k in gold]))
t='Kontakt: ola.nowak@biuro.pl'; add('O1',t,[('ola.nowak','OSOBA')],[('ola.nowak@biuro.pl','EMAIL')])
t='Odbiorca: Jan Kowalski; wzór: Alfa Sp. z o.o.'; add('O2',t,[(t[10:],'FIRMA'),('Jan Kowalski','OSOBA')],[('Jan Kowalski','OSOBA'),('Alfa Sp. z o.o.','FIRMA')])
t='Firma: Nowak Sp. z o.o.'; add('O3',t,[('Nowak Sp. z o.o.','FIRMA'),('Nowak','OSOBA'),('Nowak','NUMER')],[('Nowak Sp. z o.o.','FIRMA')])
t='Świadek: Jo\u0301zef Nowak'; add('O4',t,[('Jo\u0301zef Nowak','OSOBA')],[('Jo\u0301zef Nowak','OSOBA')])
t='Maile: aa@bb.pl,cc@dd.pl'; add('O5',t,[],[('aa@bb.pl','EMAIL'),('cc@dd.pl','EMAIL')])
t='Firma: Nowak Projekt XYZ'; add('O6',t,[('Nowak Projekt XYZ','FIRMA'),('Nowak','OSOBA')],[('Nowak Projekt XYZ','FIRMA')])
t='ul. Juliana Tuwima 8'; add('O7',t,[('Juliana Tuwima','OSOBA')],[(t,'ADRES')])
rows=a+[(i,t,b,g) for i,(t,b,g,*_) in x.items()]+own
payload=[dict(text=t,base_candidates=b) for _,t,b,g in rows]
results,_=cli('arena_v02.py',payload)
strict,raw_old=cli('arena_sim.py',payload)
_,raw_new=cli('arena_v02.py',[dict(p,policy='strict') for p in payload])
assert raw_old==raw_new and strict==[r['strict'] for r in results]
def word(c): return c.isalnum() or c=='_' or unicodedata.category(c).startswith('M')
def invariants(t,r):
 if r['status']=='STOP': assert r['masked'] is None and not r['tokens'] and not r['guard_flags']; return
 cursor=0; output=''; mapping={}
 for z in r['tokens']:
  s,e=z['start'],z['end']; assert s>=cursor and z['original']==t[s:e]
  for i in [s,e]: assert not (0<i<len(t) and word(t[i-1]) and word(t[i]))
  output+=t[cursor:s]+z['token']; cursor=e
  assert mapping.setdefault(z['token'],z['original'])==z['original']
 assert output+t[cursor:]==r['masked']
 restored=re.sub(r'\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)',lambda m:mapping[m[0]],r['masked'])
 assert restored==t
for (_,t,b,g),r in zip(rows,results):
 for policy in ['strict','structured']: invariants(t,r[policy])
for start,end,label in [(0,16,'A'),(16,35,'X'),(35,len(rows),'own')]:
 for policy in ['strict','structured']:
  counts=collections.Counter()
  for (_,t,b,g),r in zip(rows[start:end],results[start:end]):
   r=r[policy]
   if r['status']=='STOP': counts['STOP']+=1; continue
   got={(z['start'],z['end'],z['kind']) for z in r['tokens']}
   counts['protection_pass' if got==set(g) else 'protection_fail']+=1
   for s,e,k in g:
    if (s,e,k) not in got: counts['FN_PARTIAL_or_boundary' if any(s<v and u<e for u,v,j in got) else 'FN_FULL']+=1
   counts['FP_or_overmask']+=len(got-set(g))
  print(label,policy,json.dumps(dict(counts)))
reverse,_=cli('arena_v02.py',[dict(p,base_candidates=list(reversed(p['base_candidates']))) for p in payload])
assert [r["structured"] for r in reverse]==[r["structured"] for r in results]
print('strict_bytes_equal=42; structured_order_independent=42; N1_N4_all_rendered=PASS')
print('false_company',json.dumps(results[36],ensure_ascii=False))
