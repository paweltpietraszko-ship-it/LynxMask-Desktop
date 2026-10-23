import os, sys, tempfile, json
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]).resolve().parent
state=Path(sys.argv[2]).resolve(); state.mkdir(parents=True,exist_ok=True)
for key in ('PROFILE_DIR','ANONYMIZER_PROFILE_DIR','PSE_REGISTRY','ARCHIVE_DIR','HARDWARE_PROFILE'):
    os.environ[key]=str(state/key)
os.chdir(root/'backend'); sys.path.insert(0,str(root/'backend'))
import osoba_not_person as onp
from guard_residue import collect_warnings
checks=0
def candidate(word, forms=frozenset()):
    text='Dokument przekazano wczoraj '+word+'.'
    onp.start_run(); s=text.index(word)
    masked=onp.single_osoba_evidence(text,s,s+len(word),person_forms=forms)
    return masked,onp.released()
with patch.object(onp,'_common_or_person',return_value=(True,False,False)):
    for word,forms,listed,expected in [
        ('Holub',frozenset(),{'holub'},['Holub']),
        ('Holuba',frozenset(),{'holuba'},['Holuba']),
        ('HOLUBA',frozenset(),{'holuba'},['HOLUBA']),
        ('Gwaranta',frozenset({'gwaranta'}),{'holub'},['Gwaranta']),
        ('Powódka',frozenset(),{'holub'},[]),
        ('Powódka',frozenset(),set(),['Powódka']),
    ]:
        with patch.object(onp,'_SURNAMES',frozenset(listed)):
            assert candidate(word,forms)==(False,expected),(word,expected)
            checks+=1
    for word in ('','……','Pzp','Cz','G','9ee7','__'):
        assert candidate(word)==(False,[]),word
        checks+=1
for analysis in ((False,True,False),(False,False,False),(None,None,None)):
    with patch.object(onp,'_common_or_person',return_value=analysis):
        masked,rel=candidate('Maciolus')
        assert masked or rel==['Maciolus']
        checks+=1
# Actual loader: missing/corrupt files disable A, valid file is cached once.
saved=onp._SURNAMES
for exc in (FileNotFoundError(),ValueError('invalid JSON')):
    onp._SURNAMES=None
    with patch('builtins.open',side_effect=exc):
        assert onp._surname_forms()==frozenset()
        with patch.object(onp,'_common_or_person',return_value=(True,False,False)):
            assert candidate('Powódka')==(False,['Powódka'])
        checks+=1
onp._SURNAMES=None
with patch('builtins.open',wraps=open) as opened:
    a=onp._surname_forms(); b=onp._surname_forms()
    assert a is b and opened.call_count==1 and {'holub','prokopenko'}<=a
    checks+=1
onp._SURNAMES=saved
text='😀 Kawa zlecił. kawa stygnie. KAWA wrócił. RÓŻY i Róży, róży.'
warnings=collect_warnings(text,released_words=['Kawa','Róża'])
fragments={w['fragment'] for w in warnings}
assert {'Kawa','KAWA','RÓŻY','Róży'}<=fragments
assert not ({'kawa','róży'} & fragments)
assert all(text[w['start']:w['end']]==w['fragment'] for w in warnings)
checks+=1
print(json.dumps({'independent_contract_checks':checks,'status':'PASS'}))
# Real vertical chain, fresh isolated profiles, synthetic documents only.
import contextlib,io
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
vertical=[]
for word in ('Powódka','Holub','Prokopenko','Kawa'):
    text='Dokument przekazał wczoraj '+word+'.'
    st=AppState(); st.spacy_ner_mod=spacy_ner
    directory=tempfile.mkdtemp(prefix='vertical_',dir=state)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(directory,str(Path(directory)/'hw.json'))
        result=pseudonymize_document(text,st)
    target=[w for w in result.guard_warnings or [] if w['fragment']==word]
    masked=word not in result.text
    if word=='Powódka':
        assert not target and not masked
    else:
        assert masked or target,(word,result.text)
    vertical.append({'synthetic_word':word,'masked':masked,'target_warnings':len(target)})
print(json.dumps({'vertical':vertical,'status':'PASS'},ensure_ascii=False))

