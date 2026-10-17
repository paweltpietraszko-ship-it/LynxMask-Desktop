import contextlib, io, pathlib, subprocess, sys
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='2e34d1d3dec6478f5a39747dd1c23d1c2437fdce'
from pipeline_core import PipelineState, TokenAllocator
import layers.fallback as fb
import layers.ner_adapter as adapter
from pipeline_new import run_pipeline_new,run_pipeline_express

def unit(text,full=True):
    state=PipelineState(text=text,allocator=TokenAllocator()); fb.apply_fallback_layer(state,full)
    return state.text,state.allocator.reverse_map

def run(text,express=False,anonymizer=None):
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): return (run_pipeline_express if express else run_pipeline_new)(text,anon_map={},anonymizer=anonymizer)

for sep in ['', ' ', '\t','-']:
    value=sep.join(['123','456','789','012','345'])
    out,rev=unit('Ref '+value+'.')
    assert out=='Ref NUMER_001.' and rev=={'NUMER_001':value}
print('Fallback 15 digits compact/space/tab/hyphen exact span PASS')
for n in [7,8,14,15,16,22,26,30]:
    value=('1234567890'*3)[:n]
    for full in [True,False]:
        out,rev=unit(value,full)
        assert bool(rev)==(n>=8 if full else n>=15)
print('Unit threshold boundaries full 8+ vs Express 15+ PASS')
# One layer, two passes: old occupied positions must not suppress an unrelated short number.
text='A 123456789012345, B 87654321.'
out,rev=unit(text)
print('F1 stale-pass spans: short number remains=', '87654321' in out,'map_count=',len(rev))
# Permitted internal whitespace has no single-space limit in the frozen Task.
text='Nr '+'  '.join(['123','456','789','012','345'])+'.'
for expr in [False,True]:
    out,rev,blocked=run(text,expr)
    print('F2 double-space groups:', 'express' if expr else 'full','map_count=',len(rev),'raw_digits_visible=', '123' in out,'blocked=',blocked)
# Same qualified group family, beyond the specialist's 26-digit account boundary.
value='13 '+' '.join(['1234']*7)  # 30 digits in a single space-separated run
for expr in [False,True]:
    out,rev,blocked=run('Ref '+value+'.',expr)
    print('O1 financial 30-digit boundary:', 'express' if expr else 'full','tail_visible=',out.endswith(' 1234.'),'map_count=',len(rev),'blocked=',blocked)
# K1 and declared extension E1/E2 positives must stay correct.
for text, spans in [
('Kontakt: 123456789012345@example.pl. Numer: 123456789012345.',['123456789012345@example.pl','123456789012345']),
('Nr 123 456 789 012 345.',['123 456 789 012 345']),
('Konto PL6110 9010 1400 000.',['PL6110 9010 1400 000']),
]:
    for expr in [False,True]:
        out,rev,blocked=run(text,expr); assert len(rev)==len(spans) and not blocked
        restored=out
        for tok,val in rev.items(): restored=restored.replace(tok,val)
        assert restored==text and set(rev.values())==set(spans)
print('K1 and E1/E2: 6 verticals, exact map and one-pass restore PASS')
# Retain exact failure assertions and generalize only directly affected whitespace/pass boundaries.
for gap in [',',', B ']:
    text='123456789012345'+gap+'87654321'
    out,rev=unit(text)
    assert '87654321' in out and len(rev)==1
    out,rev,blocked=run(text)
    assert '87654321' in out and not blocked
print('F1 confirmed in default full pipeline: long value followed by independent short value (2 gaps)')
for separator in ['  ','\t\t',' \t']:
    text='Nr '+separator.join(['123','456','789','012','345'])+'.'
    for expr in [False,True]:
        out,rev,blocked=run(text,expr)
        assert out==text and not rev and not blocked
print('F2 confirmed: double-space/double-tab/mixed whitespace, both modes (6 paths)')

# Real full-chain wrapper and Guard, with actual temporary Anonymizer/validation.
import gc, logging, os, tempfile
logging.disable(logging.CRITICAL)
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
with tempfile.TemporaryDirectory(prefix='lynx_t07_guard_') as td:
    st=AppState()
    st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(td,os.path.join(td,'hw.json'))
    text='A 123456789012345, B 87654321.'
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): result=pseudonymize_document(text,st)
    assert '87654321' in result.text and not result.guard_blocked and not result.error
    print('F1 public pipeline -> real validation -> fallback -> Guard: short value remains, unblocked')
    text='Nr '+'  '.join(['123','456','789','012','345'])+'.'
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): result=pseudonymize_document(text,st)
    assert '123' in result.text and not result.error
    print('F2 public pipeline/Guard: raw group visible=', '123' in result.text,'guard_blocked=',result.guard_blocked)
    st=None; gc.collect()
# Independent before comparison for the direct 8+ regression, using exact base source.
import types
basefb=types.ModuleType('basefb'); basefb.__file__=str(ROOT/'backend/layers/fallback.py')
src=subprocess.check_output(['git','show','7c6475e:backend/layers/fallback.py'],text=True,encoding='utf-8')
exec(compile(src,basefb.__file__,'exec'),basefb.__dict__)
s=PipelineState(text='A 123456789012345, B 87654321.',allocator=TokenAllocator())
basefb.apply_fallback_layer(s)
assert '87654321' not in s.text and len(s.allocator.reverse_map)==2
print('F1 before comparison: original fallback masks both values, 2 map entries')