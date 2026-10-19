import json, subprocess, sys, unicodedata
from pathlib import Path
root = Path(__file__).resolve().parents[4]
text = 'Ja\u034fn'
cases = [dict(text=text, base_candidates=[dict(start=0,end=2,kind=k)]) for k in
         ['OSOBA','FIRMA','ADRES','EMAIL','NUMER','KWOTA','INSTYTUCJA']]
p = subprocess.run([sys.executable,str(root/'backend/arena_sim.py')],
                   input=''.join(json.dumps(c)+'\n' for c in cases),
                   encoding='utf-8',capture_output=True,check=True)
assert not p.stderr
out = [json.loads(x) for x in p.stdout.splitlines()]
print(json.dumps(dict(category=unicodedata.category(text[2]),combining=unicodedata.combining(text[2]),
                     expected='STOP',actual=[x['status'] for x in out])))
