"""Same-file numeric layout comparison; no values/content/names emitted."""
import contextlib,io,json,logging,pathlib,subprocess,sys,tempfile,types
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='57e39fbb6e30cccdce87103b9f72f066c4126c2a'
logging.disable(logging.CRITICAL)
import document_processor as dp
import engine_quality as eq
old=types.ModuleType('base_reader');old.__file__=str(ROOT/'backend/document_processor.py')
src=subprocess.check_output(['git','show','f95d1b9:backend/document_processor.py'],text=True,encoding='utf-8')
with contextlib.redirect_stdout(io.StringIO()):exec(compile(src,old.__file__,'exec'),old.__dict__)
directory=pathlib.Path(r'C:\Users\p_pie\Desktop\LynxMask-Desktop\backend\dataset_layout')
if not (directory/'manifest.json').exists():raise SystemExit('NOT_RUN local layout manifest absent')
with tempfile.TemporaryDirectory(prefix='lynx_docx_layout_') as temp:
    reps=[]
    for label,reader in [('before',old._extract_text),('after',dp._extract_text)]:
        out=pathlib.Path(temp)/(label+'.json')
        with patch.object(dp,'_extract_text',reader),contextlib.redirect_stdout(io.StringIO()):
            rc=eq.main(['--seed','2026','--layout',str(directory),'--out',str(out)])
        assert rc==0
        rep=json.loads(out.read_text(encoding='utf-8'));reps.append(rep)
        lay=rep['LAYOUT']
        print(json.dumps({'stage':label,'docs':len(lay['docs']),'fields_measured':lay['fields_measured'],'not_run':lay['fields_not_run'],'by_type_location':lay['by_type_location'],'m3_identical':sum(d.get('m3')=='identical' for d in lay['docs'])}))
    assert {d['id']:d.get('sha256') for d in reps[0]['LAYOUT']['docs']}=={d['id']:d.get('sha256') for d in reps[1]['LAYOUT']['docs']}
    clean=lambda r:{k:v for k,v in r.items() if k not in ['date','git_sha','LAYOUT']}
    assert clean(reps[0])==clean(reps[1])
    by0=reps[0]['LAYOUT']['by_type_location'];by1=reps[1]['LAYOUT']['by_type_location']
    assert {k:v for k,v in by0.items() if k!='docx/tabela'}=={k:v for k,v in by1.items() if k!='docx/tabela'}
    before={d['id']:d for d in reps[0]['LAYOUT']['docs']}
    changes=[{'id':d['id'],'before':before[d['id']].get('m3'),'after':d.get('m3')} for d in reps[1]['LAYOUT']['docs'] if before[d['id']].get('m3')!=d.get('m3')]
    print('M3 changes:',json.dumps(changes))
    print('PASS unchanged document hashes, non-layout seed report/digest and non-table layout classifications')