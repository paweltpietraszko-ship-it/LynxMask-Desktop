import contextlib, gc, io, logging, os, pathlib, subprocess, sys, tempfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='9f9eefc7e3931aa3c4839238559dbab9e00c8869'
from pipeline_core import PipelineState,TokenAllocator
import layers.fallback as fb
import layers.ner_adapter as adapter
from pipeline_new import run_pipeline_new,run_pipeline_express
logging.disable(logging.CRITICAL)
checks=0

def unit(text,full=True):
    st=PipelineState(text=text,allocator=TokenAllocator()); fb.apply_fallback_layer(st,full)
    return st.text,st.allocator.reverse_map

def run(text,expr=False,anon=None):
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): return (run_pipeline_express if expr else run_pipeline_new)(text,anon_map={},anonymizer=anon)

def exact(text,values,expr=False):
    global checks
    out,rev,blocked=run(text,expr); assert not blocked and sorted(rev.values())==sorted(values),(out,rev)
    restored=out
    for token,value in rev.items(): restored=restored.replace(token,value)
    assert restored==text,(out,rev)
    checks+=1

# Retained F1 inputs; same long/short values and comma boundaries, both long encodings.
for long in ['123456789012345','123 456 789 012 345']:
    for gap in [',',', B ']:
        text='A '+long+gap+'87654321.'
        exact(text,[long,'87654321'])
        exact(text,[long],True)
# Same-pass ordering and occupied-offset siblings at the layer seam.
for text in ['87654321,123456789012345','123456789012345,87654321,98765432','87654321,123456789012345,98765432']:
    out,rev=unit(text); assert not any(ch.isdigit() for ch in out.replace('NUMER_001','').replace('NUMER_002','').replace('NUMER_003',''))
    checks+=1
print('F1 original comma inputs + short/long ordering siblings PASS')

# Retained F2 whitespace variants + directly adjacent permitted separators.
for sep in [' ','\t','  ','\t\t',' \t',' - ','\t-\t']:
    value=sep.join(['123','456','789','012','345'])
    for expr in [False,True]: exact('Nr '+value+'.',[value],expr)
print('F2 original whitespace inputs + whitespace/hyphen siblings PASS')

# O1 now explicitly E3: exact original input, plus longer same-group boundary.
for groups in [7,8]:
    value='13 '+' '.join(['1234']*groups)
    for expr in [False,True]: exact('Ref '+value+'.',[value],expr)
print('E3 30/34 digits: full spans and exact one-pass restore PASS')

for n in [7,8,14,15,16,22,26,30]:
    val=('1234567890'*3)[:n]
    for full in [False,True]:
        out,rev=unit(val,full); assert bool(rev)==(n>=8 if full else n>=15); checks+=1
for sep in ['\n','. ', ', ', ' oraz ']:
    a,b='123456789012345','987654321098765'
    for expr in [False,True]: exact(a+sep+b,[a,b],expr)
print('Thresholds and independent sentence/newline/word boundaries PASS')

email='123456789012345@example.pl'; number='123456789012345'
for expr in [False,True]: exact('Kontakt: '+email+'. Numer: '+number+'.',[email,number],expr)
# Specialist financial/E3 controls; canonical formatting may differ (known F3).
for value in ['PL61 1090 1014 0000 0712 1981 2874','DE89 3704 0044 0532 0130 00','GB82 WEST 1234 5698 7654 32']:
    for expr in [False,True]:
        out,rev,blocked=run('Konto: '+value+'.',expr)
        if value.startswith('GB'):
            # Independently observed identical output on exact previous SHA 2e34d1d.
            # This is an unchanged OCR-prefix defect, not successful full GB masking.
            assert not blocked and out=='Konto: 6882 NUMER_001.' and len(rev)==1
            checks+=1
            continue
        assert not blocked and len(rev)==1 and out=='Konto: '+next(iter(rev))+'.'
        assert next(iter(rev.values())).replace(' ','')==value.replace(' ',''); checks+=1
print('K1 and PL/DE positive controls PASS; GB OCR-prefix defect unchanged from exact base')

# Real validation + Guard for each retained failure family, no real profile read.
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
with tempfile.TemporaryDirectory(prefix='lynx_t07_recheck_guard_') as td:
    st=AppState(); st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(td,os.path.join(td,'hw.json'))
    for text,expected_count in [('A 123456789012345, B 87654321.',2),('Nr 123  456  789  012  345.',1),('Ref 13 '+' '.join(['1234']*7)+'.',1)]:
        with patch.object(adapter,'process_ner',return_value=({},{})):
            with contextlib.redirect_stdout(io.StringIO()): result=pseudonymize_document(text,st)
        assert not result.guard_blocked and not result.error and len(result.reverse_map)==expected_count
        assert not any(s in result.text for s in ['87654321','123  456',' 1234.']); checks+=1
    st=None; gc.collect()
print('Real public pipeline/validation/Guard: F1 F2 E3 mapped and unblocked PASS')
print('INDEPENDENT CHECKS:',checks)