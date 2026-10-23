"""Independent synthetic amount boundary matrix; no server, empty profiles."""
import contextlib,io,json,logging,os,re,sys,tempfile
from pathlib import Path
backend, state_dir=map(os.path.abspath,sys.argv[1:3])
os.makedirs(state_dir,exist_ok=True)
for k in ('PROFILE_DIR','ANONYMIZER_PROFILE_DIR','PSE_REGISTRY','ARCHIVE_DIR','HARDWARE_PROFILE'):
 os.environ[k]=state_dir+'/'+k
os.chdir(backend);sys.path.insert(0,backend)
from layers.amount import apply_amount_layer
from pipeline_core import PipelineState,TokenAllocator
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
logging.disable(logging.CRITICAL)
cases=[
 ('mult_currency','Kara wynosi 15 tys. zł.','15 tys. zł'),
 ('mult_context','Wynagrodzenie wynosi 15 tysięcy miesięcznie.','15 tysięcy'),
 ('o_integer','Kwota 15 OOO zł.','15 OOO zł'),
 ('o_fraction_zero','Kwota 15 OOO,00 PLN.','15 OOO,00 PLN'),
 ('o_fraction_fifty','Kwota 15 OOO,50 zł.','15 OOO,50 zł'),
 ('o_fraction_fifty_pln','Kwota 15 OOO,50 PLN.','15 OOO,50 PLN'),
 ('o_fraction_compact','Kwota 15OOO,50zł.','15OOO,50zł'),
 ('o_fraction_decimal_o','Kwota 15 OOO,5O zł.','15 OOO,5O zł'),
 ('o_decimal_dot','Kwota 1200.5O zł.','1200.5O zł'),
 ('o_decimal_plain','Kwota 1200,5O zł.','1200,5O zł'),
 ('decimal_dot_control','Kwota 1200.50 zł.','1200.50 zł'),
 ('mult_million','Odszkodowanie 2,5 mln zł.','2,5 mln zł'),
 ('mult_without_dot','Kwota 15 tys zł.','15 tys zł'),
 ('unit_negative','Ludność: 15 tys. mieszkańców.',None),
 ('o_unit_negative','Pozycja 15 OOO szt.',None),
 ('company_negative','Sprzedawca: OOO Gazprom.',None),
 ('version_negative','Wersja 2 tys.',None),
]
for name,text,value in cases:
 st=PipelineState(text=text,allocator=TokenAllocator());apply_amount_layer(st)
 layer_map={k:v for k,v in st.allocator.reverse_map.items() if k.startswith('KWOTA_')}
 s=AppState();s.spacy_ner_mod=spacy_ner;d=tempfile.mkdtemp(dir=state_dir)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  s.anonymizer,_,s.anon_map,s.morf_env=build_anonymizer(d,d+'/hw.json');r=pseudonymize_document(text,s)
 print(json.dumps({'case':name,'input':text,'expected_span':value,'layer_output':st.text,'layer_values':layer_map,
                   'pipeline_output':r.text,'pipeline_values':{k:v for k,v in r.reverse_map.items() if k.startswith('KWOTA_')},
                   'warnings':[{'fragment':w['fragment'],'rules':w['rules']} for w in r.guard_warnings]},ensure_ascii=False))

