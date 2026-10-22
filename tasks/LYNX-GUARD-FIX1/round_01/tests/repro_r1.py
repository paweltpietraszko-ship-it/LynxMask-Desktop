"""FIX1 F1: uruchom na izolowanej kopii backendu exact SHA, bez uruchamiania API."""
import os
import sys
import tempfile
from pathlib import Path

backend = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix="lynx-fix1-repro-") as state:
    for key in ("ANONYMIZER_PROFILE_DIR", "PROFILE_DIR", "PSE_REGISTRY", "ARCHIVE_DIR", "HARDWARE_PROFILE"):
        os.environ[key] = str(Path(state) / key)
    sys.path.insert(0, str(backend))
    from guard_residue import collect_warnings
    failures = 0
    for surname in ("Kasprzak", "Kasprowicz", "Sądowski"):
        text = "Protokół podpisał " + surname + " w obecności świadka."
        ws = collect_warnings(text, allowlist=[])
        ok = any(w["fragment"] == surname and "R1" in w["rules"] for w in ws)
        assert all(text[w["start"]:w["end"]] == w["fragment"] for w in ws)
        print(surname, "PASS" if ok else "FAIL", [(w["fragment"], w["rules"]) for w in ws])
        failures += not ok
    control = collect_warnings("Protokół podpisał Pan Kasprzak w obecności świadka.", allowlist=[])
    assert any(w["fragment"] == "Kasprzak" and "R1" in w["rules"] for w in control)
    print("TITLE_CONTROL PASS")
    sys.exit(1 if failures else 0)
