"""Retain the narrow adjacent-uppercase-word limitation, not a passing boundary test."""
import contextlib,io,pathlib,subprocess,sys,types
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='a7809540efe254b12eac9b657b3d795664689d57'
from pipeline_core import PipelineState,TokenAllocator
from layers.financial import apply_financial_layer
from pipeline_new import run_pipeline_new,run_pipeline_express
from output_guard import guard_output_with_map
from unmask_sim import unmask
old=types.ModuleType('base_financial');old.__file__=str(ROOT/'backend/layers/financial.py')
src=subprocess.check_output(['git','show','23a103e:backend/layers/financial.py'],text=True,encoding='utf-8')
exec(compile(src,old.__file__,'exec'),old.__dict__)
for raw in ['RO49 AAAA 1B31 0075 9384 0000','ES91 2100 0418 4502 0005 1332']:
    text='Konto: '+raw+' DANE'
    for label,fn in [('base owner',old.apply_financial_layer),('delivered owner',apply_financial_layer)]:
        state=PipelineState(text=text,allocator=TokenAllocator());fn(state)
        assert state.text=='Konto: NUMER_001' and state.allocator.reverse_map=={'NUMER_001':raw+' DANE'}
        assert unmask(state.text,state.allocator.reverse_map)==text
        print(label,raw[:2],'includes adjacent DANE in token; exact restore')
    for label,fn in [('full',run_pipeline_new),('express',run_pipeline_express)]:
        with contextlib.redirect_stdout(io.StringIO()):
            out,rev,blocked=fn(text,anon_map={})
            g=guard_output_with_map(out,None,known_plain=list(rev.values()))
        assert not blocked and not g.blocked and out=='Konto: NUMER_001' and rev=={'NUMER_001':raw+' DANE'}
        assert unmask(out,rev)==text
        print(label,raw[:2],'REPRODUCED overmask; no leak; exact restore')
# Establish each extension's baseline cause without running a second broad suite.
for name in ['ocr_normalizer','identity','financial']:
    mod=types.ModuleType('base_'+name);mod.__file__=str(ROOT/'backend/layers'/ (name+'.py'))
    src=subprocess.check_output(['git','show','23a103e:backend/layers/'+name+'.py'],text=True,encoding='utf-8')
    exec(compile(src,mod.__file__,'exec'),mod.__dict__)
    if name=='ocr_normalizer':
        assert mod.normalize_ocr('Konto: GB82 WEST 1234 5698 7654 32. Dalej.')=='Konto: 6882 WE57 1234 5698 7654 32. Dalej.'
    elif name=='identity':
        state=PipelineState(text='GB82WEST12345698765432',allocator=TokenAllocator());mod.apply_identity_layer(state)
        assert state.text=='GB82WESTNUMER_001' and state.allocator.reverse_map=={'NUMER_001':'12345698765432'}
    else:
        text='Konto: PL61 1090 1014 0000 0712 1981 2874\nKolejna linia.'
        state=PipelineState(text=text,allocator=TokenAllocator());mod.apply_financial_layer(state)
        assert state.text=='Konto: NUMER_001Kolejna linia.' and next(iter(state.allocator.reverse_map.values())).endswith('\n')
print('Baseline component causes O2/E1/E2 independently confirmed')