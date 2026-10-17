import contextlib, io, json, pathlib, subprocess, sys, types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
BASE='576d133e21035ad5c34f7bf1216da6ab02086720'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='0bd2a57946b383e11024c6a7694c235a5271d55d'
def old(path,name):
    m=types.ModuleType(name); m.__file__=str(ROOT/path)
    src=subprocess.check_output(['git','show',BASE+':'+path],text=True,encoding='utf-8')
    exec(compile(src,m.__file__,'exec'),m.__dict__); return m
import layers.ocr_normalizer as ocr
import layers.ner_adapter as adapter
import layers.contact as contact
from pipeline_new import run_pipeline_new
oldocr=old('backend/layers/ocr_normalizer.py','oldocr')
oldcontact=old('backend/layers/contact.py','oldcontact')
oldadapter=old('backend/layers/ner_adapter.py','oldadapter')
# Original F1/F2 reproduction and positive OCR boundaries.
plain=['Wystawiono fakturę. Termin płatności','12/2026. Termin','nieokreślony.\n2. Umowa','Ala ma kota. Kot śpi.']
assert all(adapter._fix_ocr_email(t)==t for t in plain)
assert any(oldadapter._fix_ocr_email(t)!=t for t in plain)
assert adapter._fix_ocr_email('anna. nowak@wp.pl')=='anna.nowak@wp.pl'
for suffix in ['. Termin płatności',') zglosil sie do urzedu']:
    t='tel. +48 512 987 654'+suffix
    assert ocr.normalize_ocr(t)==t
assert '606 219 727' in ocr.normalize_ocr('Tel: +48 606 219 T2T')
print('Original F1/F2 inputs and named OCR positives PASS')
# Same F2 digit class; at end of input, last group can contain only OCR letters.
for tail, expected in [('TTT','777'),('OOO','000'),('III','111')]:
    text='Tel: +48 606 219 '+tail
    before=oldocr.normalize_ocr(text); after=ocr.normalize_ocr(text)
    assert before.endswith(expected) and after.endswith(tail)
    print('F2 residual: all-OCR final 3-digit group converted before, left unchanged after:',tail)
# Same E1 boundary with ordinary word after a complete email.
for word in ['Termin','termin','dalej']:
    text='Kontakt: nowak@example.pl. '+word+' płatności.'
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=run_pipeline_new(text,anon_map={})
    valid=(out=='Kontakt: EMAIL_001. '+word+' płatności.' and rev=={'EMAIL_001':'nowak@example.pl'})
    assert valid==(word=='Termin')
    print('E1 boundary:',word,'preserved=',valid,'blocked=',blocked,'word absorbed into map=',any('.'+word in v for v in rev.values()))
# OCR TLD positive still masked; no raw email or following sentence swallowed.
for raw in ['jan@wp. pl','jan@wp ,pl']:
    text='Kontakt: '+raw+'. Termin płatności.'
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=run_pipeline_new(text,anon_map={})
    assert out=='Kontakt: EMAIL_001. Termin płatności.' and rev=={'EMAIL_001':'jan@wp.pl'} and not blocked
print('E1 OCR TLD positives PASS')
# Relevant vertical F2 chain: same synthetic phone, controlled NER; only normalizer differs.
for tail in ['TTT','OOO','III']:
    text='Kontakt: Tel: +48 606 219 '+tail
    results=[]
    for normalizer in [oldocr.normalize_ocr,ocr.normalize_ocr]:
        with patch.object(adapter,'process_ner',return_value=({},{})), patch.object(ocr,'normalize_ocr',normalizer):
            with contextlib.redirect_stdout(io.StringIO()): out,rev,blocked=run_pipeline_new(text,anon_map={})
        results.append((out,rev,blocked))
    before,after=results
    print('F2 vertical:',tail,'before mapped=',bool(before[1]),'after mapped=',bool(after[1]),'tail visible after=',tail in after[0],'blocked after=',after[2])
    assert tail not in before[0] and tail in after[0]