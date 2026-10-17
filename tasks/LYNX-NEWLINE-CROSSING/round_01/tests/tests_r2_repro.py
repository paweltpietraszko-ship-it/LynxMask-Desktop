"""Independent real-chain comparison; run from audited or baseline checkout root."""
import contextlib,io,json,pathlib,re,subprocess,sys,logging
ROOT=pathlib.Path.cwd()
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert sha.startswith(('2619eab','cbfa3c1'))
logging.disable(logging.CRITICAL)
from pipeline_new import run_pipeline_new,run_pipeline_express
from output_guard import guard_output_with_map
from unmask_sim import unmask
cases=[
 ('email-email','a@example.pl\nb1@example.pl'),
 ('nip-phone','526-000-12-46\n512 987 654'),
 ('pesel-phone','44051401359\n512 987 654'),
 ('phone-nip','512 987 654\n526-000-12-46'),
 ('labels','NIP: 526-000-12-46\ntel: 512 987 654'),
 ('pesel-label-phone','PESEL 44051401359\nTel. 512 987 654'),
 ('single-phone-newline','512\n987 654'),
 ('single-labelled-phone-newline','Tel. 512\n987 654'),
 ('single-cc-phone-newline','+48 512\n987 654'),
 ('single-email-after-at','jan@\nexample.pl'),
 ('single-email-before-at','jan\n@example.pl'),
]
for cid,text in cases:
    for label,fn in [('full',run_pipeline_new),('express',run_pipeline_express)]:
        with contextlib.redirect_stdout(io.StringIO()):
            out,rev,blocked=fn(text,anon_map={})
            guard=guard_output_with_map(out,None,known_plain=list(rev.values()))
        tokens=re.findall(r'(?:NUMER|EMAIL)_\d{3,}',out)
        complete=(len(tokens)==1 and len(rev)==1 and set(re.sub(r'\D','',v) for v in rev.values()) in [{'512987654'},{'48512987654'}]) if 'phone-newline' in cid else None
        print(json.dumps({'sha':sha[:7],'case':cid,'mode':label,'tokens':len(tokens),'map_entries':len(rev),'force_block':blocked,'guard_blocked':guard.blocked,'restores_exactly':unmask(out,rev)==text,'phone_complete':complete,'raw_phone_fragment':any(part in out for part in ['512','987','654']) if 'phone-newline' in cid else None}))
        if sha.startswith('2619eab') and cid in ['nip-phone','pesel-phone','phone-nip','labels','pesel-label-phone','email-email']:
            assert not blocked and len(tokens)==2 and len(rev)==2 and out.count('\n')==1
            assert not re.search(r'_NUMER',out) and not any(re.search(r'(?:EMAIL|NUMER)_\d+',v) for v in rev.values())
        if cid.startswith('single-email'):
            assert not blocked and len(tokens)==1 and rev=={'EMAIL_001':'jan@example.pl'}
print('Comparison complete: named inter-entity repairs and retained single-entity OCR regression are separate checks.')