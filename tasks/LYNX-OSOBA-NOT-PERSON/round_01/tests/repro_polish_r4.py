"""Read-only Polish controls for R1. Usage: python repro_polish_r4.py <exact backend path>"""
import json
import sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
import ner_layer
try:
    import osoba_not_person as onp
except ModuleNotFoundError:
    onp = None
rows = {}
for name in ("Czerwiec", "Styczeń"):
    word = name.lower()
    rows[name] = {
        "kept": [e.text for e in ner_layer._filter_institutions([SimpleNamespace(text=name, label="OSOBA")])],
        "person_forms": word in ner_layer._PERSON_FORMS,
        "white": word in onp.WHITE_LISTS if onp else None,
        "deny": word in onp.OSOBA_DENYLIST if onp else None,
    }
print(json.dumps(rows, ensure_ascii=True, indent=2))
