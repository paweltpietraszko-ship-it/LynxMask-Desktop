"""Synthetic full-pipeline siblings of explicit A/C contract; no real data."""
import contextlib,io,json,logging,os,sys,tempfile
backend,state_dir=map(os.path.abspath,sys.argv[1:3]);os.makedirs(state_dir,exist_ok=True)
os.environ['PROFILE_DIR']=state_dir;os.environ['ANONYMIZER_PROFILE_DIR']=state_dir+'/a'
os.chdir(backend);sys.path.insert(0,backend)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
logging.disable(logging.CRITICAL)
cases=[
 ('A_person_separate','Wykonawca: Biuro Rachunkowe Anna Roman\nBiuro Rachunkowe Anna Roman zachowuje egzemplarz. Oświadczenie złożyła Anna Roman.'),
 ('C_short_company_separate','Zamawiający: Ulotny Rys sp. z o.o.\nW dalszej części pisma nazwę Ulotny Rys stosuje się jako skrót podmiotu.\nPodwykonawca: Ulotny sp. z o.o.'),
 ('C_short_company_alfa','Zamawiający: Alfa Serwis sp. z o.o.\nW dalszej części pisma nazwę Alfa Serwis stosuje się jako skrót podmiotu.\nPodwykonawca: Alfa sp. z o.o.'),
 ('C_two_long_companies','Zamawiający: Ulotny Rys sp. z o.o.\nDostawca: Ulotny Las sp. z o.o.\nNazwę Ulotny Rys oraz nazwę Ulotny Las stosuje się dalej.'),
]
for name,text in cases:
 s=AppState();s.spacy_ner_mod=spacy_ner;d=tempfile.mkdtemp(dir=state_dir)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  s.anonymizer,_,s.anon_map,s.morf_env=build_anonymizer(d,d+'/hw.json');r=pseudonymize_document(text,s)
 print(json.dumps({'case':name,'input':text,'output':r.text,'map':r.reverse_map,'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings]},ensure_ascii=False))

