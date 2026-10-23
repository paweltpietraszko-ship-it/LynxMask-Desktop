"""Independent synthetic privacy checks; compare original baseline and delivered SHA.
argv backend isolated_state_dir. No live API, real documents, or user profile.
"""
import contextlib,io,json,logging,os,sys,tempfile
backend,state_dir=map(os.path.abspath,sys.argv[1:3]);os.makedirs(state_dir,exist_ok=True)
for key in ('PROFILE_DIR','ANONYMIZER_PROFILE_DIR','PSE_REGISTRY','ARCHIVE_DIR','HARDWARE_PROFILE'):
 os.environ[key]=state_dir+'/'+key
os.chdir(backend);sys.path.insert(0,backend)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
from guard_residue import collect_warnings
logging.disable(logging.CRITICAL)
cases=[
 ('birth_child_person','Daty urodzenia dzieci:\nJan Kowalski, 05.01.2024','05.01.2024'),
 ('birth_child_place','Daty i miejsca urodzenia dzieci:\nWarszawa, 05.01.2024','05.01.2024'),
 ('birth_older_control','Daty urodzenia dzieci:\nJan Kowalski, 05.01.2020','05.01.2020'),
 ('letter_header_control','Warszawa, 05.01.2024\nWniosek o udostępnienie informacji.','05.01.2024'),
 ('individual_decision','Doręczono decyzję nr AB12 w indywidualnej sprawie dziecka.','AB12'),
 ('individual_decision_nominative','Decyzja nr AB12 dotyczy małoletniego Jana Kowalskiego.','AB12'),
 ('structural_control','Załącznik nr 12 zawiera wykaz dokumentów.','12'),
]
for key,text,target in cases:
 st=AppState();st.spacy_ner_mod=spacy_ner;folder=tempfile.mkdtemp(dir=state_dir)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(folder,folder+'/hw.json')
  r=pseudonymize_document(text,st)
 i=r.text.find(target)
 covered=any(w['start']<=i and i+len(target)<=w['end'] for w in r.guard_warnings) if i>=0 else False
 print(json.dumps({'case':key,'input':text,'target':target,'output':r.text,'target_visible':i>=0,'target_warned':covered,
                   'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings],
                   'map':r.reverse_map},ensure_ascii=False))

