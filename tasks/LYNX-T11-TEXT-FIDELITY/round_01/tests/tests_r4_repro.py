import contextlib, io, pathlib, subprocess, sys, types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='8ce05b8da26e6eec0a0280b701e4d430c5d7b1a5'
import layers.ocr_normalizer as ocr
import layers.ner_adapter as adapter
from pipeline_new import run_pipeline_new
old=types.ModuleType('pre_t11_ocr'); old.__file__=str(ROOT/'backend/layers/ocr_normalizer.py')
src=subprocess.check_output(['git','show','576d133:backend/layers/ocr_normalizer.py'],text=True,encoding='utf-8')
exec(compile(src,old.__file__,'exec'),old.__dict__)
def run(text,normalizer):
    with patch.object(adapter,'process_ner',return_value=({},{})),patch.object(ocr,'normalize_ocr',normalizer):
        with contextlib.redirect_stdout(io.StringIO()): return run_pipeline_new(text,anon_map={})
for prefix in ['+48 ','+48','0048 ','48 ']:
    for tail,digits in [('TTT','777'),('OOO','000'),('III','111')]:
        text='Kontakt: Tel: '+prefix+'606 219 '+tail
        assert ocr.normalize_ocr(text).endswith(digits)
        out,rev,blocked=run(text,ocr.normalize_ocr)
        assert tail not in out and rev and not blocked
print('Original R1 + prefix-spacing siblings: 12 normalizer/vertical cases PASS')
for text in ['tel. +48 512 987 654. Termin płatności','Pan (nr tel. 512 987 654) zglosil sie do urzedu','tel. 123 45 To jest','tel. 48 362 12 34 To jest']:
    assert ocr.normalize_ocr(text)==text
assert ocr.normalize_ocr('Tel: +48 606 219 T2T').endswith('727')
print('Following-word negatives and mixed digit/letter positive PASS')
# New title-case word cutoff must not discard supported OCR-digit groups inside a complete number.
for tail,digits in [('Ill','111'),('Ooo','000'),('Tll','711')]:
    text='Kontakt: Tel: +48 606 219 '+tail
    assert old.normalize_ocr(text).endswith(digits)
    assert ocr.normalize_ocr(text).endswith(tail)
    before=run(text,old.normalize_ocr); after=run(text,ocr.normalize_ocr)
    assert tail not in before[0] and before[1] and not before[2]
    assert tail in after[0] and not after[1] and not after[2]
    print('R1 STILL OPEN: supported OCR-digit group',tail,'treated as word; before mapped, after empty map/unblocked')