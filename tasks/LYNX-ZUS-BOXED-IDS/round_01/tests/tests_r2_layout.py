"""Numeric-only local source diagnosis and same-input production-chain comparison."""
import contextlib,gc,io,json,logging,pathlib,re,subprocess,sys,tempfile,types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='fc084aff9b5731ab54929dcd2dcb45d7ee3747e9'
logging.disable(logging.CRITICAL)
import fitz,document_processor as dp,engine_quality as eq,pipeline
old=types.ModuleType('base_reader');old.__file__=str(ROOT/'backend/document_processor.py')
src=subprocess.check_output(['git','show','29f130b:backend/document_processor.py'],text=True,encoding='utf-8')
with contextlib.redirect_stdout(io.StringIO()):exec(compile(src,old.__file__,'exec'),old.__dict__)
directory=pathlib.Path(r'C:\Users\p_pie\Desktop\LynxMask-Desktop\backend\dataset_layout')
if not (directory/'manifest.json').exists():raise SystemExit('NOT_RUN: local layout sample unavailable')
entries=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
boxed=[];grouped=0;ambiguous=0
for entry in entries:
    values=[]
    if entry['type']=='pdf':
        wanted={f['value'] for f in entry['fields'] if f['category']=='NUMER'}
        with fitz.open(stream=(directory/entry['file']).read_bytes(),filetype='pdf') as doc:
            for page in doc:
                widgets=list(page.widgets())
                for w in widgets:
                    v=w.field_value
                    if v in wanted and isinstance(v,str) and len(v) in (10,11) and v.isascii() and v.isdigit() and w.field_flags & (1<<24):
                        per='\n'.join(v)+'\n'
                        appearances=len(re.findall(r'(?<![^\n])'+re.escape(per),page.get_text()))
                        same=sum(x.field_value==v and bool(x.field_flags & (1<<24)) for x in widgets)
                        good=page.get_text(clip=w.rect)==per and appearances==same
                        grouped+=int(good);ambiguous+=int(not good);values.append(v)
    boxed.append(values)
print('Source diagnosis numeric:',json.dumps({'WIDGET_GROUP':grouped,'AMBIGUOUS':ambiguous,'documents_with_target_widgets':sum(bool(v) for v in boxed)}))
assert grouped==6 and ambiguous==0
reports=[]
with tempfile.TemporaryDirectory(prefix='lynx_zus_layout_') as temp:
    for label,reader in [('before',old._extract_text),('after',dp._extract_text)]:
        with contextlib.redirect_stdout(io.StringIO()):state=eq.build_state(str(pathlib.Path(temp)/label))
        counts={'whole':0,'raw':0};index=[0]
        def run(text):
            with contextlib.redirect_stdout(io.StringIO()):res=pipeline.pseudonymize_document(text,state)
            targets=boxed[index[0]];index[0]+=1
            counts['whole']+=sum(any(t.startswith('NUMER_') and val==v and t in res.text for t,val in res.reverse_map.items()) for v in targets)
            counts['raw']+=sum(v in res.text or '\n'.join(v) in res.text for v in targets)
            return res
        with patch.object(dp,'_extract_text',reader):rep=eq.measure_layout(str(directory),run)
        assert index[0]==len(entries)
        reports.append(rep)
        print(label,json.dumps({'docs':len(rep['docs']),'fields':rep['fields_measured'],'not_run':rep['fields_not_run'],'by_type_location':rep['by_type_location'],'boxed_whole':counts['whole'],'boxed_raw':counts['raw']}))
        if label=='after':assert counts['whole']==6 and counts['raw']==0
        state=None;gc.collect()
    a,b=reports
    assert {d['id']:d.get('sha256') for d in a['docs']}=={d['id']:d.get('sha256') for d in b['docs']}
    assert {k:v for k,v in a['by_type_location'].items() if k!='pdf/tabela'}=={k:v for k,v in b['by_type_location'].items() if k!='pdf/tabela'}
    assert [d.get('m3') for d in a['docs']]==[d.get('m3') for d in b['docs']]
    print('PASS same input hashes; other extraction/masking classifications and document M3 statuses unchanged')