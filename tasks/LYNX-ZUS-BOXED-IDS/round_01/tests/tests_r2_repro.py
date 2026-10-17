"""Independent AcroForm synthetic controls, base-source comparison and real masking chain."""
import contextlib,gc,io,logging,pathlib,subprocess,sys,tempfile,types
ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='fc084aff9b5731ab54929dcd2dcb45d7ee3747e9'
logging.disable(logging.CRITICAL)
from reportlab.pdfgen import canvas
import pypdf,fitz
import document_processor as dp
import engine_quality as eq
from pipeline import pseudonymize_document
from pipeline_new import run_pipeline_express
from unmask_sim import unmask
old=types.ModuleType('base_reader');old.__file__=str(ROOT/'backend/document_processor.py')
src=subprocess.check_output(['git','show','29f130b:backend/document_processor.py'],text=True,encoding='utf-8')
with contextlib.redirect_stdout(io.StringIO()):exec(compile(src,old.__file__,'exec'),old.__dict__)
P='44051401359';N='5260001246'
def pdf(fields,singles='',horizontal=False,pages=1):
    stream=io.BytesIO();c=canvas.Canvas(stream);values={}
    for page in range(pages):
        c.drawString(36,800,'Synthetic form control')
        for i,(value,comb) in enumerate(fields):
            name=f'p{page}f{i}';values[name]=value
            c.acroForm.textfield(name=name,x=36+270*(i%2) if horizontal else 50,y=700-40*(i//2 if horizontal else i),width=220,height=18,maxlen=len(value),fieldFlags='comb' if comb else '')
        for i,ch in enumerate(singles):
            name=f'p{page}s{i}';values[name]=ch
            c.acroForm.textfield(name=name,x=36+20*i,y=300,width=18,height=18,maxlen=1)
        c.showPage()
    c.save();writer=pypdf.PdfWriter();writer.clone_document_from_reader(pypdf.PdfReader(io.BytesIO(stream.getvalue())))
    for page in writer.pages:writer.update_page_form_field_values(page,values)
    out=io.BytesIO();writer.write(out);return out.getvalue()
positive=[('pesel',[(P,True)],False,1),('nip',[(N,True)],False,1),('two-fields',[(P,True),(N,True)],False,1),('horizontal',[(P,True),(N,True)],True,1),('duplicate',[(P,True),(P,True)],False,1),('prefix',[(P[:10],True),(P,True)],False,1),('two-pages',[(P,True),(N,True)],False,2)]
with tempfile.TemporaryDirectory(prefix='lynx_zus_independent_') as temp:
    with contextlib.redirect_stdout(io.StringIO()):state=eq.build_state(temp)
    for label,fields,horizontal,pages in positive:
        blob=pdf(fields,horizontal=horizontal,pages=pages)
        before,error,_=old._extract_text(blob,'synthetic.pdf');assert error is None
        expected=before
        for value in sorted(set(v for v,comb in fields),key=len,reverse=True):expected=expected.replace('\n'.join(value)+'\n',value+'\n')
        after,error,meta=dp._extract_text(blob,'synthetic.pdf');assert error is None and meta is None and after==expected
        assert after!=before
        for value in set(v for v,comb in fields):assert after.splitlines().count(value)==sum(v==value for v,comb in fields)*pages
        with contextlib.redirect_stdout(io.StringIO()):
            result=pseudonymize_document(after,state)
            out,rev,blocked=run_pipeline_express(after,{},state.anonymizer)
        assert not result.error and not result.guard_blocked and not blocked
        for masked,mapping in [(result.text,result.reverse_map),(out,rev)]:
            assert set(mapping.values())==set(v for v,comb in fields),(label,'whole map')
            assert not any(v in masked for v,comb in fields)
            assert unmask(masked,mapping)==after
        print('PASS',label,'exact scoped extraction + complete full/Express maps + restoration')
    for label,fields,singles in [('other-lengths',[('512987654',True),('14051944',True),('12345678901234',True)],''),('independent-digits',[],P),('ambiguous',[(P,True)],P),('ordinary-field',[(P,False)],'')]:
        blob=pdf(fields,singles=singles)
        assert dp._extract_text(blob,'synthetic.pdf')==old._extract_text(blob,'synthetic.pdf'),label
        print('PASS unchanged',label)
    blob=pdf([(P,True)])
    with fitz.open(stream=blob,filetype='pdf') as doc:
        w=next(doc[0].widgets());doc[0].insert_text((w.rect.x0+2,w.rect.y0+12),'X');changed=doc.tobytes()
    assert dp._extract_text(changed,'synthetic.pdf')==old._extract_text(changed,'synthetic.pdf')
    print('PASS ambiguous/mismatched appearance left unchanged')
    state=None;gc.collect()