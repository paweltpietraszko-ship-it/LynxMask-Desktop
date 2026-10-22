"""ADDR-REVERSED observations. python repro_r1.py <isolated-backend> <own-state-dir>."""
import contextlib
import io
import json
import logging
import os
import sys
from pathlib import Path
backend=Path(sys.argv[1]).resolve()
state=Path(sys.argv[2]).resolve()
for key in ("ANONYMIZER_PROFILE_DIR","PROFILE_DIR","PSE_REGISTRY","ARCHIVE_DIR","HARDWARE_PROFILE"):
    os.environ[key]=str(state/key)
os.environ["LYNX_HERBERT"]="off"
sys.path.insert(0,str(backend))
logging.basicConfig(level=logging.CRITICAL)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
st=AppState();st.spacy_ner_mod=spacy_ner
profile=state/"profile";profile.mkdir(parents=True,exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):
    st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(str(profile),str(profile/"hw.json"))
rows=[]
for name,text in (("space","ul. Polna 5 Radom"),("comma-control","ul. Polna 5, Radom"),("person","Pan Jan Kalisz, ul. Polna 5")):
    with contextlib.redirect_stdout(io.StringIO()):
        r=pseudonymize_document(text,st)
    assert not r.error
    rows.append(dict(case=name,input=text,output=r.text,mapping=r.reverse_map,warnings=r.guard_warnings))
print(json.dumps(rows,ensure_ascii=False,indent=2))
