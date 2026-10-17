import ast, asyncio, contextlib, io, json, logging, os, pathlib, subprocess, sys, tempfile, types
from collections import namedtuple
from unittest.mock import patch
ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT / 'backend')
logging.disable(logging.CRITICAL)
BASE = '19083548c2771f49307c810c8ceaa92319a34839'
assert subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip() == '8d208455667023f9b141d9a79ecf18f109a310ff'
def old_module(path, name):
    source = subprocess.check_output(['git','show',BASE+':'+path], text=True, encoding='utf-8')
    m = types.ModuleType(name); m.__file__ = str(ROOT / path)
    exec(compile(source, m.__file__, 'exec'), m.__dict__)
    return m
import ner_blocklist as nb
import ner_layer as nl
old_nb = old_module('backend/ner_blocklist.py', 'old_nb')
old_nl = old_module('backend/ner_layer.py', 'old_nl')
N = namedtuple('N','text label confidence start end')
def kept(fn, text, label='OSOBA'):
    return bool(fn([N(text,label,.9,0,len(text))]))
assert nb._GEO_WORDS == old_nb._GEO_WORDS
assert nb._NER_BLOCKLIST == old_nb._NER_BLOCKLIST
assert nb._NER_BLOCKLIST_PREFIXES == old_nb._NER_BLOCKLIST_PREFIXES
forms = sorted(nb._STREET_ONLY_PERSON_FORMS)
assert len(forms) == 561
assert set(forms) <= nb._PERSON_FORMS & nb._GEO_BY_SOURCE['street']
assert not set(forms) & (nb._GEO_BY_SOURCE['city'] | nb._GEO_BY_SOURCE['med'])
for low in forms:
    assert not kept(old_nl._filter_institutions, low.title())
    assert kept(nl._filter_institutions, low.title())
    assert not kept(nl._filter_institutions, low)
    assert not kept(nl._filter_institutions, low.title(), 'FIRMA')
protected = sorted(nb._PERSON_FORMS & (nb._GEO_BY_SOURCE['city'] | nb._GEO_BY_SOURCE['med']))
for low in protected:
    assert not kept(nl._filter_institutions, low.title())
for word in ['Radom','Warszawie','Piątek','Zając','ZUS','ul. Kowalskiego 7']:
    assert kept(nl._filter_institutions, word) == kept(old_nl._filter_institutions, word) == False
assert kept(nl._filter_institutions, 'Zapłata') == kept(old_nl._filter_institutions, 'Zapłata')
print(json.dumps({'filter_forms':len(forms),'protected_person_geo':len(protected),'shared_sets':'unchanged'}))
import layers.ner_adapter as adapter
import spacy_ner
from pipeline_new import run_pipeline_new
old_adapter = old_module('backend/layers/ner_adapter.py', 'old_adapter')
for surname in ['Kowalskiego','Nowaka','Adamczyka']:
    text = 'Zgoda K. '+surname+' na badanie.'
    with patch.object(adapter,'process_ner',return_value=({},{})):
        with patch.object(adapter,'_apply_initials',old_adapter._apply_initials):
            with contextlib.redirect_stdout(io.StringIO()): before, _, _ = run_pipeline_new(text,anon_map={})
        with contextlib.redirect_stdout(io.StringIO()): after, rev, blocked = run_pipeline_new(text,anon_map={})
    assert surname in before and surname not in after and 'K. '+surname in rev.values()
    assert not blocked
    for text, expected_type in [('Wniosek '+surname+' został przyjęty.','OSOBA'), ('Mieszka przy ul. '+surname+' 7 w Radomiu.','ADRES')]:
        start = text.index(surname)
        hit = [spacy_ner.NERResult(surname,'OSOBA',.9,start,start+len(surname))]
        with patch.object(spacy_ner,'detect_entities',return_value=hit):
            with contextlib.redirect_stdout(io.StringIO()): out, rev, blocked = run_pipeline_new(text,anon_map={})
        assert surname not in out and len(rev)==1 and next(iter(rev)).startswith(expected_type+'_') and not blocked
        restored=out
        for token,value in rev.items(): restored=restored.replace(token,value)
        assert restored == text
print('vertical: 3 initials without spaCy; 3 controlled persons + 3 addresses; restore exact; unblocked')
with tempfile.TemporaryDirectory(prefix='lynx_geo_api_') as td:
    os.environ['ARCHIVE_DIR'] = str(pathlib.Path(td)/'archive')
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    from fastapi.testclient import TestClient
    _, _, amap, _ = build_anonymizer(td,str(pathlib.Path(td)/'hw.json'))
    api._app_state.anon_map = amap
    api._API_TOKEN='a'*64; api._EXPRESS_TOKEN='b'*64
    client = TestClient(api.app,base_url='http://127.0.0.1:8765')
    headers={'X-Api-Token':'a'*64}
    for surname in ['Kowalskiego','Nowaka','Adamczyka']:
        resp=client.post('/profile/add-entity',json={'text':surname,'token_type':'OSOBA'},headers=headers)
        assert resp.status_code == 200
        tid=resp.json()['token_id']; assert tid.startswith('OSOBA_')
        again=client.post('/profile/add-entity',json={'text':surname,'token_type':'OSOBA'},headers=headers)
        assert again.json()['token_id']==tid
    for word,typ in [('Radom','OSOBA'),('Piątek','OSOBA'),('Zając','OSOBA'),('ZUS','OSOBA'),('Kowalskiego','FIRMA'),('Nowaka','ADRES'),('Nowaka','NUMER')]:
        assert client.post('/profile/add-entity',json={'text':word,'token_type':typ},headers=headers).status_code==400
    assert len(amap.list_entities())==3
    assert client.post('/profile/add-entity',json={'text':'Nowaka','token_type':'OSOBA'},headers={'X-Api-Token':'b'*64}).status_code==401
    print('HTTP profile: 3 real map additions + idempotency; 7 negatives; Express denied')
from pipeline_core import TokenAllocator
for surname in ['Piątek','Zając','Radom']:
    text='K. '+surname
    assert adapter._apply_initials(text,TokenAllocator()) == old_adapter._apply_initials(text,TokenAllocator()) == text
print('initials: city/common-word protections retained (3 cases)')
print('INDEPENDENT REPRO PASS')