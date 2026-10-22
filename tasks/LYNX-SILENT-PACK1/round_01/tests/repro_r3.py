"""SILENT-PACK1 F1: unit exclusion in real pipeline. Usage: python repro_r3.py <isolated-backend> <own-state>."""
import contextlib,io,json,logging,os,re,sys
from pathlib import Path
backend=Path(sys.argv[1]).resolve();state=Path(sys.argv[2]).resolve();state.mkdir(parents=True,exist_ok=True)
for k in ("ANONYMIZER_PROFILE_DIR","PROFILE_DIR","PSE_REGISTRY","ARCHIVE_DIR","HARDWARE_PROFILE"):os.environ[k]=str(state/k)
os.environ["LYNX_HERBERT"]="off";sys.path.insert(0,str(backend));logging.basicConfig(level=logging.CRITICAL)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
app=AppState();app.spacy_ner_mod=spacy_ner
profile=state/"profile";profile.mkdir(exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):app.anonymizer,_,app.anon_map,app.morf_env=build_anonymizer(str(profile),str(profile/"hw.json"))
cases=[
("mm-context-before","Wartość pomiaru 1234,56 mm.",False),
("mm-thousands","Wartość pomiaru 12.345,67 mm.",False),
("mm-context-after","Odczyt 1234,56 mm; wartość zmierzono ponownie.",False),
("mm-no-context","Wynik pomiaru 1234,56 mm.",False),
("gram-control","Wartość pomiaru 1234,56 g.",False),
("percent-control","Wartość udziału 1234,56%.",False),
("version-control","Wartość parametru w wersji 2026,01.",False),
("amount-positive","Do zwrotu 1049,63.",True),
]
rows=[]
for name,text,want_amount in cases:
 with contextlib.redirect_stdout(io.StringIO()):r=pseudonymize_document(text,app)
 amounts={k:v for k,v in r.reverse_map.items() if k.startswith("KWOTA_")}
 ok=not r.error and bool(amounts)==want_amount
 rows.append(dict(case=name,input=text,output=r.text,amounts=amounts,warnings=r.guard_warnings,error=r.error,ok=ok))
print(json.dumps(rows,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(x["ok"] for x in rows) else 1)
