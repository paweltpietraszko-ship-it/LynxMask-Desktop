"""Same F2 class: both the long and short known company recur without legal form."""
import contextlib,io,json,logging,os,sys,tempfile
backend,state_dir=map(os.path.abspath,sys.argv[1:3]);os.makedirs(state_dir,exist_ok=True)
os.environ['PROFILE_DIR']=state_dir;os.environ['ANONYMIZER_PROFILE_DIR']=state_dir+'/a'
os.chdir(backend);sys.path.insert(0,backend)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
logging.disable(logging.CRITICAL)
long='Zamawiający: Ulotny Rys sp. z o.o.'
short='Podwykonawca: Ulotny sp. z o.o.'
repeat_long='W dalszej części pisma nazwę Ulotny Rys stosuje się jako skrót zamawiającego.'
repeat_short='Nazwę Ulotny stosuje się jako skrót podwykonawcy.'
for key,text in [('short_full_only','\n'.join([long,repeat_long,short])),
                 ('both_repeat','\n'.join([long,repeat_long,short,repeat_short])),
                 ('both_repeat_short_first','\n'.join([short,long,repeat_short,repeat_long]))]:
 s=AppState();s.spacy_ner_mod=spacy_ner;d=tempfile.mkdtemp(dir=state_dir)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  s.anonymizer,_,s.anon_map,s.morf_env=build_anonymizer(d,d+'/hw.json');r=pseudonymize_document(text,s)
 print(json.dumps({'case':key,'input':text,'output':r.text,'map':r.reverse_map,'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings]},ensure_ascii=False))

