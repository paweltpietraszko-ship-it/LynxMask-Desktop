"""PACK4 F2 r4. python repro_r4.py <isolated-backend> <own-state-dir>. Synthetic data only."""
import json
import os
import sys
from pathlib import Path
backend=Path(sys.argv[1]).resolve()
state=Path(sys.argv[2]).resolve()
for key in ("ANONYMIZER_PROFILE_DIR","PROFILE_DIR","PSE_REGISTRY","ARCHIVE_DIR","HARDWARE_PROFILE"):
    os.environ[key]=str(state/key)
sys.path.insert(0,str(backend))
import osoba_not_person as onp
from guard_residue import collect_warnings
text="RÓŻA złożyła wniosek. RÓŻY dotyczy odpis."
control=collect_warnings(text,released_words=["Róża"],allowlist=[])
assert {w["fragment"] for w in control}>={"RÓŻA","RÓŻY"}
onp.start_run()
assert onp.single_osoba_evidence(text,0,4) is False
assert onp.released()==["RÓŻA"]
ws=collect_warnings(text,released_words=onp.released(),allowlist=[])
ok={w["fragment"] for w in ws}>={"RÓŻA","RÓŻY"}
assert all(text[w["start"]:w["end"]]==w["fragment"] for w in ws)
print(json.dumps({"control":"PASS","released":onp.released(),"fragments":[w["fragment"] for w in ws],"F2_ok":ok},ensure_ascii=False))
sys.exit(0 if ok else 1)
