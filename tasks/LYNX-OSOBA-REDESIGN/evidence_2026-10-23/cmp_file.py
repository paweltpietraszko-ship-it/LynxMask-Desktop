import contextlib, io, os, sys, tempfile
src, f = sys.argv[1:3]
prof = tempfile.mkdtemp(); os.environ["PROFILE_DIR"] = prof; os.environ["ANONYMIZER_PROFILE_DIR"] = prof + "/a"
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
for t in open(f, encoding="utf-8").read().splitlines():
    st = AppState(); st.spacy_ner_mod = spacy_ner; d = tempfile.mkdtemp(dir=prof)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, d + "/hw.json")
        r = pseudonymize_document(t, st)
    print(f"{r.text[:70]:70} | Guard: {[w['fragment'] for w in r.guard_warnings]}")
