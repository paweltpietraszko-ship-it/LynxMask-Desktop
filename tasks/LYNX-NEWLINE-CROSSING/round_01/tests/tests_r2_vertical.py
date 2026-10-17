"""Real Express file handler plus full production wrapper, synthetic phone only."""
import asyncio,contextlib,gc,io,json,logging,os,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path.cwd();sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert sha.startswith(('2619eab','cbfa3c1'))
logging.disable(logging.CRITICAL)
with tempfile.TemporaryDirectory(prefix='lynx_newline_vertical_') as temp:
    os.environ['PROFILE_DIR']=str(pathlib.Path(temp)/'profile')
    os.environ['ARCHIVE_DIR']=str(pathlib.Path(temp)/'archive')
    with contextlib.redirect_stdout(io.StringIO()):
        import engine_quality as eq
        import pipeline
        import pseudominizer_api as api
        from starlette.datastructures import UploadFile
        from starlette.requests import Request
        state=eq.build_state(str(pathlib.Path(temp)/'engine'))
    api._app_state=state
    route=next(r for r in api.app.routes if 'express' in getattr(r,'path','') and 'preview' in r.path)
    for cid,text in [('bare','512\n987 654'),('label','Tel. 512\n987 654'),('prefix','+48 512\n987 654')]:
        upload=UploadFile(filename='synthetic.txt',file=io.BytesIO(text.encode()))
        with contextlib.redirect_stdout(io.StringIO()):
            result=asyncio.run(route.endpoint(request=Request({'type':'http','method':'POST','path':route.path,'headers':[]}),file=upload))
            full=pipeline.pseudonymize_document(text,state)
        raw=any(part in result['anonymized_preview'] for part in ['512','987','654'])
        print(json.dumps({'sha':sha[:7],'case':cid,'express_route':route.path,'express_raw_phone_in_preview':raw,'express_blocked':result['blocked'],'express_tokens':result['total'],'full_map_entries':len(full.reverse_map),'full_phone_redacted':('[REDACTED' in full.text),'full_blocked':full.guard_blocked}))
        if sha.startswith('2619eab'):
            assert raw and not result['blocked'] and result['total']==0
        else:
            assert not raw and result['total']>=1
    api._app_state=pipeline.AppState();state=None;gc.collect()