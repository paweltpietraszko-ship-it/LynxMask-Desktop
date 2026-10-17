"""Metadata-only live sample and old CLI equivalence evidence; no document values printed."""
import contextlib,gc,io,json,logging,os,pathlib,subprocess,sys,tempfile,types
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='d7a08689af663f422e8ed7e3cb1d5a204e3b46f3'
import engine_quality as new
import pipeline
logging.disable(logging.CRITICAL)
old=types.ModuleType('base_quality');old.__file__=str(ROOT/'audyt/engine_quality.py')
src=subprocess.check_output(['git','show','b074fa6:audyt/engine_quality.py'],text=True,encoding='utf-8')
exec(compile(src,old.__file__,'exec'),old.__dict__)
assert old.build_cases()==new.build_cases()
with tempfile.TemporaryDirectory(prefix='lynx_layout_evidence_') as temp:
    tmp=pathlib.Path(temp)
    holdout=tmp/'holdout.json'
    holdout.write_text(json.dumps({'Zawislak':['Zawislak','Zawislaka']}),encoding='utf-8')
    reports=[]
    for module,label in [(old,'base'),(new,'delivered')]:
        out=tmp/(label+'.json')
        with contextlib.redirect_stdout(io.StringIO()):
            rc=module.main(['--seed','2026','--holdout',str(holdout),'--out',str(out)])
        assert rc==0
        rep=json.loads(out.read_text(encoding='utf-8'))
        for key in ['date','git_sha']: rep.pop(key,None)
        reports.append(rep)
    assert reports[0]==reports[1], 'Old CLI classifications/digest/report changed'
    print('PASS same-seed synthetic-holdout old CLI report equality excluding date/git_sha; digest='+reports[1]['input_digest'])
    directory=pathlib.Path(r'C:\Users\p_pie\Desktop\LynxMask-Desktop\backend\dataset_layout')
    if not (directory/'manifest.json').exists():
        print('Official local sample: NOT_CHECKED (manifest unavailable)')
    else:
        state=new.build_state(str(tmp/'profile'))
        with contextlib.redirect_stdout(io.StringIO()):
            rep=new.measure_layout(str(directory),lambda text:pipeline.pseudonymize_document(text,state))
        assert set(d['type'] for d in rep['docs'])=={'docx','pdf'}
        allowed={'docx/tabela','docx/tekst','pdf/tabela','pdf/tekst'}
        assert set(rep['by_type_location']).issubset(allowed)
        summary={'status':rep['status'],'documents':len(rep['docs']),'fields_measured':rep['fields_measured'],'fields_not_run':rep['fields_not_run'],'by_type_location':rep['by_type_location'],'m3':[d.get('m3','NOT_RUN') for d in rep['docs']]}
        print('Local official synthetic sample numeric result:',json.dumps(summary))
        state=None;gc.collect()