"""PACK4 F1/F2. python repro_r3.py <isolated-backend> <own-state-dir>. Synthetic data only."""
import contextlib
import io
import json
import logging
import os
import re
import sys
from pathlib import Path

backend=Path(sys.argv[1]).resolve()
state=Path(sys.argv[2]).resolve()
state.mkdir(parents=True,exist_ok=True)
for key in ("ANONYMIZER_PROFILE_DIR","PROFILE_DIR","PSE_REGISTRY","ARCHIVE_DIR","HARDWARE_PROFILE"):
    os.environ[key]=str(state/key)
os.environ["LYNX_HERBERT"]="off"
sys.path.insert(0,str(backend))
logging.basicConfig(level=logging.CRITICAL)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
from guard_residue import collect_warnings
from osoba_not_person import released

profile=state/"profile";profile.mkdir(exist_ok=True)
st=AppState();st.spacy_ner_mod=spacy_ner
with contextlib.redirect_stdout(io.StringIO()):
    st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(str(profile),str(profile/"hw.json"))
text="Dokument przekazał wczoraj Malina. W notatce zapisano MALINA."
with contextlib.redirect_stdout(io.StringIO()):
    r=pseudonymize_document(text,st)
assert not r.error
caps=[m.span() for m in re.finditer("MALINA",r.text)]
f1=all(any(w["start"]<=s and e<=w["end"] for w in r.guard_warnings) for s,e in caps)
f1_result={"ok":f1,"output":r.text,"released":released(),"warnings":r.guard_warnings}

text2="Róża złożyła wniosek. Róży dotyczy odpis."
ws=collect_warnings(text2,released_words=["Róża"],allowlist=[])
f2=all(any(w["start"]<=m.start() and m.end()<=w["end"] for w in ws) for m in re.finditer("Róża|Róży",text2))
control=collect_warnings("Model Maciolus działał. Model Maciolusa zasilano.",released_words=["Maciolus"],allowlist=[])
assert {w["fragment"] for w in control}>={"Maciolus","Maciolusa"}
control2=collect_warnings("Kawa zlecił paczkę. Kawałek chleba.",released_words=["Kawa"],allowlist=[])
assert "Kawałek" not in {w["fragment"] for w in control2}
result={"F1":f1_result,"F2":{"ok":f2,"text":text2,"warnings":ws},"controls":"PASS"}
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(0 if f1 and f2 else 1)
