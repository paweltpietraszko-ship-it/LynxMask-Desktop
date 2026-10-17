import contextlib, io, pathlib, subprocess, sys
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='240f6b6aa45ee7e2d49a19e1c9ffa90d732d66ea'
import layers.ocr_normalizer as ocr
import layers.ner_adapter as adapter
from pipeline_new import run_pipeline_new
for prefix in ['+48 ','+48','0048 ','48 ','']:
    for tail,digits in [('TTT','777'),('OOO','000'),('III','111'),('Ill','111'),('Ooo','000'),('Tll','711')]:
        text='Kontakt: Tel: '+prefix+'606 219 '+tail
        assert ocr.normalize_ocr(text).endswith(digits),(prefix,tail)
        with patch.object(adapter,'process_ner',return_value=({},{})):
            with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=run_pipeline_new(text,anon_map={})
        assert tail not in out and rev and not blocked,(prefix,tail)
print('30 retained prefix/OCR-tail verticals PASS')
for text in ['tel. +48 512 987 654. Termin płatności','Pan (nr tel. 512 987 654) zglosil sie do urzedu','tel. 123 45 To jest','tel. 48 362 12 34 To jest','tel. +48 512 987 654 To jest']:
    assert ocr.normalize_ocr(text)==text
assert ocr.normalize_ocr('Tel: +48 606 219 T2T').endswith('727')
print('6 named following-word/OCR boundaries PASS')
# Same changed bare-48 decision, national phone beginning with 48 and an OCR tail.
for tail in ['Ill','Ooo','Tll']:
    text='tel. 483 621 '+tail+' To jest'
    fixed=ocr.normalize_ocr(text)
    assert not fixed.endswith(' To jest') and fixed.endswith('70 jest')
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=run_pipeline_new(text,anon_map={})
    restored=out
    for token,value in rev.items(): restored=restored.replace(token,value)
    assert 'To jest' not in restored and '70' in restored and not blocked
    print('Residual F2 national-48/OCR boundary',tail,'To changed to 70; vertical round-trip loses ordinary word; blocked=',blocked)