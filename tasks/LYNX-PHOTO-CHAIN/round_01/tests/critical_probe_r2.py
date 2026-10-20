"""Inspect real critical ASKED values on the historically used synthetic 100.
Usage: python critical_probe_r2.py AUDIT_WORKTREE OUTPUT_DIRECTORY
No original values are printed or saved by this probe.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

root, out = map(lambda x: Path(x).resolve(), sys.argv[1:3])
spec = importlib.util.spec_from_file_location("photo_measure", root / "tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)
cc = measure._cc()
dataset = Path("C:/Users/p_pie/Desktop/LynxMask-Desktop/backend/dataset_20261016_fresh")
gt = json.loads((dataset / "ground_truth.json").read_text(encoding="utf-8"))
if len(sys.argv) > 3:
    gt = [g for g in gt if Path(g["file"]).stem == sys.argv[3]]
a = SimpleNamespace(sha="df612f7c6257a25e6de122c478a05d1c41e50353", rapid=True,
                    models=out / "models", env=["LYNX_PHOTO_DICT_MIN=0.60"],
                    protect=[Path("C:/Users/p_pie/Desktop/LynxMask-Desktop/backend")])
jobs = [str((dataset / g["file"]).resolve()) for g in gt]
items, meta = measure.run_variant(a, cc, jobs)
rows, docs = [], []
for g, r in zip(gt, items or []):
    d = cc.eval_doc(r.get("ocr_text") or "", r, g.get("entities", {}))
    docs.append(d)
    for v in d["gold"]:
        if v["critical"] and v["status"] != "MASKED":
            key = v["key"]
            original = str(g["entities"][key])
            norm = lambda s: re.sub(r"\W+", "", s).casefold()
            ctx = cc.doc_ctx(cc.strip_header(r["out"]))
            level, evidence = cc.evidence(original, ctx)
            rows.append({"id": Path(g["file"]).stem, "key": key, "status": v["status"],
                         "http": r["code"], "blocked": r["blocked"], "engine": r["ocr_engine"],
                         "exact_value_visible": original in r["out"],
                         "normalized_value_visible": norm(original) in norm(r["out"]),
                         "guard_reasons": r["guard_reasons"], "evidence_level": level,
                         "evidence_lengths": [len(x[0]) for x in evidence],
                         "evidence_masked": [x[0][:2] + "***" + x[0][-2:] for x in evidence],
                         "matches_token": cc._token_match(original, r["originals"]),
                         "in_ocr": cc._in_text(original, r.get("ocr_text") or "")})
result = {"sha": a.sha, "run": meta, "summary": cc.summarize(docs, None) if docs else None,
          "critical_not_masked": rows}
(out / "critical_checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
