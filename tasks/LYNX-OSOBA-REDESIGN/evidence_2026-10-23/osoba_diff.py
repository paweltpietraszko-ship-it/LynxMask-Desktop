"""Nowe wartości OSOBA (silnik) na dokumentach publicznych z cache: zapis listy wartości per dokument do JSON."""
import contextlib, io, json, os, sys, tempfile
src, cache, out = sys.argv[1:4]
prof = tempfile.mkdtemp(); os.environ["PROFILE_DIR"] = prof; os.environ["ANONYMIZER_PROFILE_DIR"] = prof + "/a"
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
res = {}
for f in sorted(os.listdir(cache)):
    t = json.load(open(os.path.join(cache, f), encoding="utf-8")).get("text") or ""
    if not t.strip(): continue
    st = AppState(); st.spacy_ner_mod = spacy_ner; d = tempfile.mkdtemp(dir=prof)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, d + "/hw.json")
        r = pseudonymize_document(t, st)
    res[f] = sorted({v for k, v in r.reverse_map.items() if k.startswith("OSOBA")})
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
