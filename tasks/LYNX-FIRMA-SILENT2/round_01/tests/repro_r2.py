"""Independent synthetic A/B/C examples and sibling JDG name ambiguity."""
import contextlib,io,json,logging,os,sys,tempfile
backend,state_dir=map(os.path.abspath,sys.argv[1:3]);os.makedirs(state_dir,exist_ok=True)
for k in ('PROFILE_DIR','ANONYMIZER_PROFILE_DIR','PSE_REGISTRY','ARCHIVE_DIR','HARDWARE_PROFILE'):
 os.environ[k]=state_dir+'/'+k
os.chdir(backend);sys.path.insert(0,backend)
from firma_context import jdg_entities
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
logging.disable(logging.CRITICAL)
cases=[
 ('A_control','Usługi Konserwatorskie Cezary Jeż'),
 ('A_surname_firstname','Usługi Konserwatorskie Cezary Marek'),
 ('A_surname_firstname2','Biuro Rachunkowe Anna Roman'),
 ('A_short_jdg','Studio Jan Marek'),
 ('B','Perłowy Nawias s.c.'),
 ('C','Ulotny Rys sp. z o.o.'),
]
for key,name in cases:
 core=name
 if key=='B':core='Perłowy Nawias'
 if key=='C':core='Ulotny Rys'
 text='Wykonawca: '+name+'\nW dalszej części pisma nazwę '+core+' stosuje się jako skrót podmiotu.'
 s=AppState();s.spacy_ner_mod=spacy_ner;d=tempfile.mkdtemp(dir=state_dir)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  s.anonymizer,_,s.anon_map,s.morf_env=build_anonymizer(d,d+'/hw.json');r=pseudonymize_document(text,s)
 print(json.dumps({'case':key,'name':name,'jdg_candidates':[x.text for x in jdg_entities(text)],'output':r.text,'map':r.reverse_map,'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings]},ensure_ascii=False))

