"""KIO (i inne .txt) przez silnik w procesie, pusty profil. Użycie: python inproc.py <backend_src> <out_dir> <pliki...>
Zapis: out/<nazwa>.json {text(anon), warnings, tokens{token:value}}; na końcu podsumowanie wierszy panelu."""
import json, os, sys, tempfile, logging, collections
src, out, files = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
prof = tempfile.mkdtemp(prefix="kio_prof_"); os.environ["PROFILE_DIR"] = prof
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
logging.disable(logging.WARNING)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
rows = collections.Counter()
for f in files:
    st = AppState(); st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(dir=prof)
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    t = open(f, encoding="utf-8", errors="replace").read().strip()
    r = pseudonymize_document(t, st)
    ws = r.guard_warnings
    seen = {(w["rule"], w["fragment"].lower()) for w in ws}
    for k in seen: rows[k[0]] += 1
    toks = dict(getattr(r, "token_map", None) or getattr(r, "reverse_map", None) or {})
    json.dump({"text": r.text if hasattr(r, "text") else r.anonymized_text, "warnings": ws, "tokens": toks},
              open(os.path.join(out, os.path.basename(f) + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
print(dict(rows), "suma", sum(rows.values()), "na dok", round(sum(rows.values()) / len(files), 2))
