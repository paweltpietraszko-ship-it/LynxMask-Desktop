"""Synthetic address regression repro. Usage: python repro_r3.py <isolated-backend> <own-state-dir>."""
import contextlib
import io
import json
import logging
import os
import re
import sys
from pathlib import Path

backend = Path(sys.argv[1]).resolve()
state = Path(sys.argv[2]).resolve()
for key in ("ANONYMIZER_PROFILE_DIR", "PROFILE_DIR", "PSE_REGISTRY", "ARCHIVE_DIR", "HARDWARE_PROFILE"):
    os.environ[key] = str(state / key)
os.environ["LYNX_HERBERT"] = "off"
sys.path.insert(0, str(backend))
logging.basicConfig(level=logging.CRITICAL)
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document

app = AppState()
app.spacy_ner_mod = spacy_ner
profile = state / "profile"
profile.mkdir(parents=True, exist_ok=True)
with contextlib.redirect_stdout(io.StringIO()):
    app.anonymizer, _, app.anon_map, app.morf_env = build_anonymizer(str(profile), str(profile / "hw.json"))

cases = [
    ("F1-retained", "ul. Polna 5 Radom", "ul. Polna 5 Radom"),
    ("F2-retained", "Pan Jan Kalisz, ul. Polna 5", "ul. Polna 5"),
    ("city-control", "Kalisz, ul. Polna 5", "Kalisz, ul. Polna 5"),
    ("F3-person-city", "Podpis: Jan Kalisz. Adres doręczenia: Kalisz, ul. Polna 5.", "Kalisz, ul. Polna 5"),
    ("F4-postal", "Adres: 26-600 Radom, ul. Polna 5", None),
]
token = re.compile(r"(?:OSOBA|ADRES|FIRMA|EMAIL|NUMER|KWOTA|INSTYTUCJA)_\d{3}(?!\d)")
rows = []
for name, text, address in cases:
    with contextlib.redirect_stdout(io.StringIO()):
        result = pseudonymize_document(text, app)
    rev = result.reverse_map
    restored = token.sub(lambda m: rev.get(m.group(), m.group()), result.text)
    good = not result.error and restored == text
    if address is not None:
        good = good and any(k.startswith("ADRES_") and v == address for k, v in rev.items())
    if name == "F2-retained":
        good = good and any(k.startswith("OSOBA_") and v == "Jan Kalisz" for k, v in rev.items())
    if name == "F4-postal":
        good = good and "26-600" not in result.text
    rows.append(dict(case=name, input=text, output=result.text, mapping=rev, warnings=result.guard_warnings,
                     error=result.error, restored_via_map=restored, ok=good))
print(json.dumps(rows, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(row["ok"] for row in rows) else 1)
