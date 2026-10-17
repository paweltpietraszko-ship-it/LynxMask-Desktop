"""Independent synthetic IBAN delivery checks; exact SHA, no product changes."""
import contextlib, io, pathlib, subprocess, sys, types
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='a7809540efe254b12eac9b657b3d795664689d57'
from pipeline_core import PipelineState,TokenAllocator
from layers.ocr_normalizer import normalize_ocr
from layers.identity import apply_identity_layer
from layers.financial import apply_financial_layer
from pipeline_new import run_pipeline_new,run_pipeline_express
from output_guard import guard_output_with_map
from unmask_sim import unmask

counts={'layer':0,'full':0,'express':0}
failures=[]
def check(text,iban,exact=True):
    expected=text.replace(iban,'NUMER_001')
    for label,fn in [('full',run_pipeline_new),('express',run_pipeline_express)]:
        with contextlib.redirect_stdout(io.StringIO()):
            out,rev,blocked=fn(text,anon_map={})
            g=guard_output_with_map(out,None,known_plain=list(rev.values()))
        good=(not blocked and out==expected and len(rev)==1 and next(iter(rev.values())).replace(' ','')==iban.replace(' ',''))
        if exact:
            good=good and rev=={'NUMER_001':iban} and unmask(out,rev)==text
        good=good and not g.blocked and not g.redacted and g.output()==out
        if not good: failures.append((label,text,out,rev,blocked,g.blocked))
        counts[label]+=1

ibans=['GB82 WEST 1234 5698 7654 32','NL91 ABNA 0417 1643 00','FR14 2004 1010 0505 0001 3M02 606','DE89 3704 0044 0532 0130 00']
for iban in ibans:
    for raw in [iban,iban.replace(' ','')]:
        state=PipelineState(text=raw,allocator=TokenAllocator())
        apply_financial_layer(state)
        assert state.text=='NUMER_001' and state.allocator.reverse_map=={'NUMER_001':raw}, ('financial isolation',raw,state)
        counts['layer']+=1
        for label in ['Konto: ','IBAN: ','']:
            text=label+raw+'. Dalej.'
            assert normalize_ocr(text)==text, ('foreign letters',text,normalize_ocr(text))
            counts['layer']+=1
            check(text,raw)
# E1 retained original plus standalone identity still works.
state=PipelineState(text='GB82WEST12345698765432',allocator=TokenAllocator())
apply_identity_layer(state)
assert state.text=='GB82WEST12345698765432' and not state.allocator.reverse_map
counts['layer']+=1
state=PipelineState(text='PESEL: 44051401458.',allocator=TokenAllocator())
apply_identity_layer(state)
assert '44051401458' not in state.text and len(state.allocator.reverse_map)==1
counts['layer']+=1
# E2 whitespace belongs outside token, including line boundary.
pl='PL61 1090 1014 0000 0712 1981 2874'
for tail in [' dziś.','\nKolejna linia.','\r\nKolejna linia.','. Dalej.']:
    text='Konto: '+pl+tail
    state=PipelineState(text=text,allocator=TokenAllocator())
    apply_financial_layer(state)
    assert state.text==text.replace(pl,'NUMER_001'), ('PL layer boundary',state.text)
    counts['layer']+=1
    check(text,pl,False)
for text in ['Konto: GB82 WEST. Dalej.','GB82 WEST']:
    for label,fn in [('full',run_pipeline_new),('express',run_pipeline_express)]:
        with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=fn(text,anon_map={})
        assert out==text and not rev and not blocked, ('short negative',label,out,rev)
        counts[label]+=1
# Existing OCR PL/NRB correction and last accepted email repair.
assert '1090' in normalize_ocr('Konto: 61 1O9O 1014 OOOO O712 1981 2874.')
counts['layer']+=1
for label,fn in [('full',run_pipeline_new),('express',run_pipeline_express)]:
    text='Kontakt: ANNA.   NOWAK@example.pl. Dalej.'
    with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=fn(text,anon_map={})
    assert not blocked and out=='Kontakt: EMAIL_001. Dalej.' and unmask(out,rev)==text
    counts[label]+=1
# Boundary siblings use ordinary document headings, not degraded OCR.
for tail in ['\nDane odbiorcy.',' DANE',' OPIS','\nDANE ODBIORCY']:
    raw=ibans[0]
    check('Konto: '+raw+tail,raw)
print('COUNTS',counts)
print('FAILURES',len(failures))
for failure in failures: print(repr(failure))
if failures: sys.exit(1)
print('PASS independent matrix, real pipeline/NER and Guard, no stubs')