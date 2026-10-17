import contextlib, io, pathlib, subprocess, sys
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='fc75f1410c865acaa74e4ca2c9058aa81b16b5ed'
import layers.contact as contact
import layers.ner_adapter as adapter
from pipeline_core import PipelineState,TokenAllocator
from pipeline_new import run_pipeline_new,run_pipeline_express
from unmask_sim import unmask

def layer(text):
    s=PipelineState(text=text,allocator=TokenAllocator()); contact.apply_contact_layer(s)
    return s.text,s.allocator.reverse_map

def run(text,express):
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): return (run_pipeline_express if express else run_pipeline_new)(text,anon_map={})

for sep in [' ','  ','\t','\t\t',' \t']:
    value='anna.'+sep+'nowak@example.pl'; text='Kontakt: '+value+'. Termin płatności.'
    out,rev=layer(text); assert out=='Kontakt: EMAIL_001. Termin płatności.' and rev=={'EMAIL_001':value}
    for express in [False,True]:
        out,rev,blocked=run(text,express)
        assert out=='Kontakt: EMAIL_001. Termin płatności.' and rev=={'EMAIL_001':value} and not blocked
        assert unmask(out,rev)==text
print('Named localpart repair + whitespace siblings: 5 layer and 10 full/Express paths, exact restoration PASS')
for text,value in [('Kontakt. jan@example.pl','jan@example.pl'),('Podpisano. Jan@example.pl','Jan@example.pl'),('Koniec.\njan@example.pl','jan@example.pl'),('Mail nowak@example.pl. termin','nowak@example.pl')]:
    out,rev=layer(text); assert rev=={'EMAIL_001':value} and out==text.replace(value,'EMAIL_001')
print('Named adjacent-sentence/newline negatives PASS')
text='Kontakt: 123456789012345@example.pl. Numer: 123456789012345.'
for express in [False,True]:
    out,rev,blocked=run(text,express); assert not blocked and len(rev)==2 and unmask(out,rev)==text
    assert set(rev.values())=={'123456789012345@example.pl','123456789012345'}
print('T07 numeric email + separate number: map/restoration PASS')
# New matching behavior on an ordinary lower-case sentence-ending word.
text='Prosimy o kontakt. jan@example.pl'
for express in [False,True]:
    out,rev,blocked=run(text,express)
    assert rev=={'EMAIL_001':'kontakt. jan@example.pl'} and out=='Prosimy o EMAIL_001' and not blocked
    assert unmask(out,rev)==text
print('NEW visible behavior: lower-case ordinary word kontakt swallowed into EMAIL; restore exact')
# Limits reported or implied by implementation, not independently Owner-accepted here.
for raw,tail in [('ANNA. NOWAK@example.pl','ANNA.'),('anna.   nowak@example.pl','anna.')]:
    text='Kontakt: '+raw+'. Termin płatności.'
    out,rev,blocked=run(text,True)
    assert tail in out and not blocked
    print('Known scope limit: CAPS' if raw.startswith('ANNA') else 'Known scope limit: 3 spaces','prefix remains in Express, unblocked')
# Exact-base regex comparison at the layer seam for the newly swallowed word.
import types
old=types.ModuleType('old_contact'); old.__file__=str(ROOT/'backend/layers/contact.py')
src=subprocess.check_output(['git','show','5dd5c6e:backend/layers/contact.py'],text=True,encoding='utf-8')
exec(compile(src,old.__file__,'exec'),old.__dict__)
s=PipelineState(text='Prosimy o kontakt. jan@example.pl',allocator=TokenAllocator()); old.apply_contact_layer(s)
assert s.text=='Prosimy o kontakt. EMAIL_001' and s.allocator.reverse_map=={'EMAIL_001':'jan@example.pl'}
print('Base comparison confirms ordinary-word absorption is new; other limits are not claimed as regressions')
for raw in ['ANNA. NOWAK@example.pl','anna.   nowak@example.pl']:
    text='Kontakt: '+raw+'. Termin płatności.'
    state=PipelineState(text=text,allocator=TokenAllocator()); old.apply_contact_layer(state)
    now_text,now_rev=layer(text)
    assert (state.text,state.allocator.reverse_map)==(now_text,now_rev)
print('Exact-base source comparison: CAPS and 3-space limitations predate this patch')