"""Independent synthetic exact-SHA legal-form audit; no document content in stdout."""
import contextlib,gc,importlib.util,io,itertools,json,logging,pathlib,re,subprocess,sys,tempfile,types
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
SHA='ba0560386ed84106ebbcdd4d363cc5c941a4b9f1';BASE='1084b6978f0ed486f0cc390ed72d6b6e761b07ef'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==SHA
logging.disable(logging.CRITICAL)
import engine_quality as eq,pipeline,pipeline_new
from unmask_sim import unmask
old=types.ModuleType('audit_baseline_adapter');old.__file__=str(ROOT/'backend/layers/ner_adapter.py')
exec(compile(subprocess.check_output(['git','show',BASE+':backend/layers/ner_adapter.py'],text=True,encoding='utf-8'),old.__file__,'exec'),old.__dict__)
current=pipeline_new.apply_ner_layer
with tempfile.TemporaryDirectory(prefix='lynx_legal_independent_') as tmp:
    with contextlib.redirect_stdout(io.StringIO()): state=eq.build_state(tmp)
    def go(text,baseline=False):
        pipeline_new.apply_ner_layer=old.apply_ner_layer if baseline else current
        try:
            with contextlib.redirect_stdout(io.StringIO()): r=pipeline.pseudonymize_document(text,state)
            assert not r.error and not r.guard_blocked
            assert not any(re.search(r'(?:FIRMA|OSOBA)_\d{3}',v) for v in r.reverse_map.values())
            return r,unmask(r.text,r.reverse_map)
        finally: pipeline_new.apply_ner_layer=current
    # Retain the original synthetic inputs below without changing the old report.
    spec=importlib.util.spec_from_file_location('previous_sweep',ROOT/'tasks/LYNX-FIRMA-HYPHEN-SUFFIX/round_01/implementation/firma_sweep.py')
    sweep=importlib.util.module_from_spec(spec);spec.loader.exec_module(sweep)
    for i,name in enumerate(['Eko-Tech Consulting S.A.','Mega-Pack Polska Sp.k.','Apex-Transport Logistyka Sp. z o.o.']):
        text='Umowa z firmą '+name+' została podpisana.';r,u=go(text)
        assert u==text and len([k for k in r.reverse_map if k.startswith('FIRMA_')])==1
    repeats=[
      'Umowa z firmą Mega-Pack Polska została podpisana. Wykonawca: Mega-Pack Polska Sp.k.',
      'Umowa z firmą Mega-Pack Polska Sp.k. została podpisana. Wykonawca: Mega-Pack Polska.',
      'Umowa z firmą Eko-Tech Consulting została podpisana. Wykonawca: Eko-Tech Consulting S.A.']
    for i,text in enumerate(repeats):
        b,bu=go(text,True);a,au=go(text)
        print(json.dumps({'retained':i,'before_exact':bu==text,'after_exact':au==text,'before_raw_company':bool(re.search('Mega-Pack Polska|Eko-Tech Consulting',b.text)),'after_raw_company':bool(re.search('Mega-Pack Polska|Eko-Tech Consulting',a.text))}))
        if i<2: assert au==text
        else: assert bu==au and b.text==a.text and b.reverse_map==a.reverse_map
    matrix=0
    for form,reverse in itertools.product(['Sp.k.','S.A.','Sp. z o.o.'],[False,True]):
        names=['Mega-Pack Polska','Mega-Pack Polska '+form]
        if reverse:names.reverse()
        text='Umowa z firmą '+names[0]+' została podpisana. Wykonawca: '+names[1]
        b,bu=go(text,True);a,au=go(text)
        assert au==text and au.count(form)==text.count(form)
        assert ('Mega-Pack Polska' in a.text)==('Mega-Pack Polska' in b.text)
        matrix+=1
    for i,text in enumerate(['Forma prawna: Sp.k.','Forma prawna: Sp. z o.o.','ZAKRES OBOWIĄZKÓW\nOpis stanowiska.','To zwykły tekst bez firmy.','Umowa z firmą Mega-Pack Polska Sp.k. Spółka pozostaje stroną.','Umowa z Apex-Transport Sp. z o.o. i Eko-Tech S.A. Następne zdanie.']):
        b,bu=go(text,True);a,au=go(text)
        assert (b.text,b.reverse_map)==(a.text,a.reverse_map) and au==text
    stats={'matrix_pass':matrix,'negative_pass':6,'sweep_cases':0,'regressions':0,'restoration_bad':0,'raw_before':0,'raw_after':0}
    for head,form,ctx in itertools.product(sweep.HEADS,sweep.SUFFIXES,sweep.CONTEXTS):
        name=head+' '+form;text=ctx.format(name);b,bu=go(text,True);a,au=go(text)
        before=eq.classify_m1(text,name,'FIRMA',b);after=eq.classify_m1(text,name,'FIRMA',a)
        stats['sweep_cases']+=1;stats['raw_before']+=int(head in b.text);stats['raw_after']+=int(head in a.text)
        stats['regressions']+=int((before=='masked' and after!='masked') or (bu==text and au!=text))
        stats['restoration_bad']+=int(au!=text)
    assert stats['regressions']==0
    print(json.dumps(stats))
    state=None;gc.collect()