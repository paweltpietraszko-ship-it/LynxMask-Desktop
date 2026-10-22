"""Independent PDF crash/API probe; backend, synthetic pdf dir, own state dir arguments."""
import contextlib,faulthandler,io,json,logging,os,socket,subprocess,sys
from pathlib import Path
faulthandler.enable()
backend=Path(sys.argv[1]).resolve(); pdfdir=Path(sys.argv[2]).resolve(); root=Path(sys.argv[3]).resolve()
root.mkdir(parents=True,exist_ok=True)
for k in ("ANONYMIZER_PROFILE_DIR","PROFILE_DIR","PSE_REGISTRY","ARCHIVE_DIR","HARDWARE_PROFILE"):os.environ[k]=str(root/k)
os.environ["TEMP"]=os.environ["TMP"]=str(root);os.environ["LYNX_HERBERT"]="off"
sys.path.insert(0,str(backend));logging.basicConfig(level=logging.CRITICAL)
for meth in ("connect","connect_ex"):
 original=getattr(socket.socket,meth)
 def blocked(sock,address,_orig=original):
  if isinstance(address,tuple) and (address[0] not in ("127.0.0.1","::1","localhost") or address[1]==8765):raise RuntimeError("audit network blocked")
  return _orig(sock,address)
 setattr(socket.socket,meth,blocked)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState,pseudonymize_document
from document_processor import _extract_text
st=AppState();st.spacy_ner_mod=spacy_ner
p=root/"profile";p.mkdir(exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):st.anonymizer,_,st.anon_map,st.morf_env=build_anonymizer(str(p),str(p/"hw.json"))
rows=[]
files=sorted(pdfdir.glob("*.pdf"));assert len(files)==13,len(files)
if "--api-only" in sys.argv[4:]:files=[]
for file in files:
 for turn in range(2):
  with contextlib.redirect_stdout(io.StringIO()):
   text,err,_=_extract_text(file.read_bytes(),file.name)
   assert err is None and text,(file.name,err)
   r=pseudonymize_document(text,st)
  assert not r.error,(file.name,r.error)
  assert "fitz" not in sys.modules and "pymupdf" not in sys.modules
  rows.append(dict(file=file.name,turn=turn,chars=len(text),warnings=len(r.guard_warnings)))
 print(json.dumps(dict(file=file.name,repeats=2,ok=True)),flush=True)
# No document contents in diagnostics on malformed PDF and timeout.
from unittest.mock import patch
import pdf_worker
marker="AUDIT_SYNTHETIC_SECRET_6842"
bad,err,_=_extract_text(("%PDF-1.4 "+marker).encode(),"invalid.pdf")
assert bad=="" and err.startswith("Błąd odczytu PDF") and marker not in err
with patch.object(pdf_worker.subprocess,"run",side_effect=subprocess.TimeoutExpired("pdf-worker",120)):
 bad,err,_=_extract_text(marker.encode(),"invalid.pdf")
 assert bad=="" and err.startswith("Błąd odczytu PDF") and marker not in err
# Actual API endpoint in-process only.
import pseudominizer_api as api
from fastapi.testclient import TestClient
api._app_state=st
api._API_TOKEN="a"*64
client=TestClient(api.app,base_url="http://127.0.0.1:8765",raise_server_exceptions=False)
headers={"X-Api-Token":api._API_TOKEN}
response=client.post("/export-pdf",json={"text":"OSOBA_001 zawarla umowe.\nADRES_001","filename":"audit.pdf"},headers=headers)
assert response.status_code==200,(response.status_code,response.text[:200])
assert response.content.startswith(b"%PDF") and response.headers["content-type"]=="application/pdf"
readback,error,_=_extract_text(response.content,"exported.pdf")
assert error is None and "OSOBA_001" in readback and "ADRES_001" in readback
# Metadata inspection stays in another process; never import fitz here.
code="import sys,json,fitz; d=fitz.open(stream=sys.stdin.buffer.read(),filetype='pdf'); print(json.dumps(d.metadata))"
meta_proc=subprocess.run([sys.executable,"-c",code],input=response.content,capture_output=True,timeout=30)
assert meta_proc.returncode==0
metadata=json.loads(meta_proc.stdout)
assert metadata["author"]=="" and metadata["creator"]==""
assert client.post("/export-pdf",json={"text":" "},headers=headers).status_code==400
with patch.object(api,"_generate_pdf",side_effect=RuntimeError(marker)):
 failed=client.post("/export-pdf",json={"text":marker},headers=headers)
 assert failed.status_code==500 and marker not in failed.text
with contextlib.redirect_stdout(io.StringIO()):final=pseudonymize_document("Pan Jan Kowalski podpisal umowe.",st)
assert not final.error and "fitz" not in sys.modules and "pymupdf" not in sys.modules
summary=dict(pdf_count=len(files),pipeline_runs=len(rows),pipeline_errors=0,api_export_roundtrip=True,
             clean_metadata=True,invalid_pdf_safe=True,timeout_safe=True,api_failure_safe=True,
             pymupdf_not_in_engine=True)
(root/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
(root/"pdf-runs.json").write_text(json.dumps(rows,indent=2),encoding="utf8")
print(json.dumps(summary),flush=True)
