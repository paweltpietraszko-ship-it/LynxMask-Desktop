"""Synthetic merged-warning observation. python repro_codex_r2.py <isolated-backend> <own-state-dir>."""
import json,logging,os,sys
from pathlib import Path
state=Path(sys.argv[2]).resolve();state.mkdir(parents=True,exist_ok=True)
os.environ["ANONYMIZER_PROFILE_DIR"]=str(state/"profile")
os.environ["PROFILE_DIR"]=str(state/"legacy")
os.environ["LYNX_HERBERT"]="off"
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
logging.basicConfig(level=logging.CRITICAL)
import guard_allowlist as ga
from guard_residue import collect_warnings
text="Firma: Jan Kawa"
before=collect_warnings(text,allowlist=[])
warning=next(w for w in before if w["level"]=="YELLOW" and len(w["rules"])>1)
ga.add(warning["fragment"],warning["rules"])
stored=ga.load()
after=collect_warnings(text,allowlist=stored)
print(json.dumps(dict(input=text,before=before,stored=stored,after=after),ensure_ascii=False,indent=2))
# This records observations; interpretation awaits the Owner, not an automatic product verdict.
