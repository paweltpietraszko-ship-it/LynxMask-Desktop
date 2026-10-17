# FN/FP na syntetycznych zdaniach: próbka form z przecięcia osoba∩ulica (wyłącznie ulica), spaCy realny.
import sys, os, json, re; sys.path.insert(0, os.getcwd())
import ner_blocklist as nb
from pipeline_new import run_pipeline_new
src = json.load(open(sys.argv[1], encoding="utf-8"))
P, N = src["pos"], src["neg"]
fn = fp = 0
for w in P:
    out, rev, _ = run_pipeline_new(f"Wniosek {w.capitalize()} został przyjęty przez urząd.", anon_map={})
    fn += w.capitalize() in out
for w in N:
    out, rev, _ = run_pipeline_new(f"Mieszka przy ul. {w.capitalize()} 7 w Radomiu.", anon_map={})
    fp += any(k.startswith("OSOBA") for k in rev)
print(f"pozytywy n={len(P)} FN(jawne)={fn} | adresy n={len(N)} FP(OSOBA w adresie)={fp}")
