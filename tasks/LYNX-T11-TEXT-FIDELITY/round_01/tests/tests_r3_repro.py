import contextlib, io, pathlib, subprocess, sys, types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='b3d09f81dda037eb905418fb532a6d3c8f6dcf9b'
import layers.ocr_normalizer as ocr
import layers.ner_adapter as adapter
from pipeline_new import run_pipeline_new
old=types.ModuleType('oldocr'); old.__file__=str(ROOT/'backend/layers/ocr_normalizer.py')
src=subprocess.check_output(['git','show','576d133:backend/layers/ocr_normalizer.py'],text=True,encoding='utf-8')
exec(compile(src,old.__file__,'exec'),old.__dict__)
def run(text):
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): return run_pipeline_new(text,anon_map={})
# Original R1 reproducers, unchanged inputs; helper and vertical.
for tail,digits in [('TTT','777'),('OOO','000'),('III','111')]:
    text='Kontakt: Tel: +48 606 219 '+tail
    assert ocr.normalize_ocr(text).endswith(digits)
    out,rev,blocked=run(text)
    assert tail not in out and rev and not blocked
print('R1 original spaced-prefix inputs: 3/3 closed')
# Same phone, same supported country prefix, different spacing (no new phone category).
for tail,digits in [('TTT','777'),('OOO','000'),('III','111')]:
    text='Kontakt: Tel: +48606 219 '+tail
    assert old.normalize_ocr(text).endswith(digits)
    assert ocr.normalize_ocr(text).endswith(tail)
    out,rev,blocked=run(text)
    assert tail in out and not blocked
    print('R1 STILL OPEN: +48 attached to first national group, OCR tail',tail,'visible; map entries=',len(rev),'blocked=',blocked)
# Retained following-word protections and named mixed-OCR positive.
for suffix in ['. Termin płatności',') zglosil sie do urzedu']:
    t='tel. +48 512 987 654'+suffix
    assert ocr.normalize_ocr(t)==t
assert ocr.normalize_ocr('Tel: +48 606 219 T2T').endswith('727')
# Retained R2 inputs and OCR TLD positives, exact result and reverse map.
for word in ['Termin','termin','dalej']:
    out,rev,blocked=run('Kontakt: nowak@example.pl. '+word+' płatności.')
    assert out=='Kontakt: EMAIL_001. '+word+' płatności.' and rev=={'EMAIL_001':'nowak@example.pl'} and not blocked
for raw in ['jan@wp. pl','jan@wp ,pl']:
    out,rev,blocked=run('Kontakt: '+raw+'. Termin płatności.')
    assert out=='Kontakt: EMAIL_001. Termin płatności.' and rev=={'EMAIL_001':'jan@wp.pl'} and not blocked
print('R2 CLOSED: upper/lower following words + both OCR TLD positives (5 paths)')