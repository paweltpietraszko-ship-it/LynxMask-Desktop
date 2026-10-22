"""Reproduktor awarii PDF: _extract_text (pymupdf) + pipeline (Morfeusz w Guard R1) w jednym procesie.
python pdf_crash.py <katalog_backend_kopii> <plik.pdf> [n_powtorzen]"""
import faulthandler
import os
import sys
import tempfile

faulthandler.enable()
os.environ["PROFILE_DIR"] = tempfile.mkdtemp(prefix="pdfcrash_")
os.chdir(sys.argv[1])
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
import spacy_ner  # noqa: E402
from anonymizer import build_anonymizer  # noqa: E402
from document_processor import _extract_text  # noqa: E402
from pipeline import AppState, pseudonymize_document  # noqa: E402

data = open(sys.argv[2], "rb").read()
for i in range(int(sys.argv[3]) if len(sys.argv) > 3 else 1):
    text, err, _ = _extract_text(data, os.path.basename(sys.argv[2]))
    print(f"[{i}] extract len={len(text)} err={err}", flush=True)
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="pc_")
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    r = pseudonymize_document(text, st)
    print(f"[{i}] pipeline ok error={r.error} warnings={len(r.guard_warnings)}", flush=True)
print("KONIEC BEZ AWARII")
