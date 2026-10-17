"""Narrow independent real-NER company boundaries and declared cleanup risk. Synthetic only."""
import contextlib,gc,io,json,logging,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'audyt')]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='07504c8d9282f1c70347ec3a39f8a389a14bfd5b'
logging.disable(logging.CRITICAL)
import engine_quality as eq,pipeline
from unmask_sim import unmask
with tempfile.TemporaryDirectory(prefix='lynx_firma_independent_') as tmp:
    with contextlib.redirect_stdout(io.StringIO()):state=eq.build_state(tmp)
    for i,name in enumerate(['Eko-Tech Consulting S.A.','Mega-Pack Polska Sp.k.','Apex-Transport Logistyka Sp. z o.o.']):
        text='Umowa z firmą '+name+' została podpisana.'
        with contextlib.redirect_stdout(io.StringIO()):res=pipeline.pseudonymize_document(text,state)
        assert not res.error and not res.guard_blocked and unmask(res.text,res.reverse_map)==text
        firms={k:v for k,v in res.reverse_map.items() if k.startswith('FIRMA_')}
        assert len(firms)==1 and next(iter(firms.values())).rstrip('.')==name.rstrip('.')
        print('PASS independent full NER boundary/restoration',i)
    cases=[
      'Umowa z firmą Mega-Pack Polska została podpisana. Wykonawca: Mega-Pack Polska Sp.k.',
      'Umowa z firmą Mega-Pack Polska Sp.k. została podpisana. Wykonawca: Mega-Pack Polska.',
      'Umowa z firmą Eko-Tech Consulting została podpisana. Wykonawca: Eko-Tech Consulting S.A.',
    ]
    for i,text in enumerate(cases):
        with contextlib.redirect_stdout(io.StringIO()):res=pipeline.pseudonymize_document(text,state)
        restored=unmask(res.text,res.reverse_map)
        if i == 0:
            assert not res.error and not res.guard_blocked
            assert restored != text and restored.count('Sp.k.') == 0
            assert all('Sp.k.' not in v for v in res.reverse_map.values())
        print(json.dumps({'case':'repeat-form-'+str(i),'blocked':res.guard_blocked,'error':bool(res.error),'restoration_exact':restored==text,'firma_maps':sum(t.startswith('FIRMA_') for t in res.reverse_map),'legal_form_source':text.count('Sp.k.')+text.count('S.A.'),'legal_form_restored':restored.count('Sp.k.')+restored.count('S.A.')}))
    state=None;gc.collect()