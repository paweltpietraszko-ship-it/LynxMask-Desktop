"""LYNX-NER-MULTILINE — przegląd rodziny: położenie końca wiersza w spanie NER × etykieta × treść, baza vs bieżące drzewo.

Kontrolowany NERResult (jak reproduktor Codexa r2) → prawdziwy pipeline.pseudonymize_document z Guardem.
Regresja = bieżące drzewo gorsze od bazy: jawne słowo identyfikujące, nowa blokada/błąd albo zepsute Przywróć.
Dane syntetyczne. Uruchom z katalogu repo: py -3 tasks/LYNX-NER-MULTILINE/round_01/implementation/edge_sweep.py [BASE_SHA]
"""
import contextlib
import io
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
BASE = sys.argv[1] if len(sys.argv) > 1 else "c62f819"
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]
TOKEN = re.compile(r"(?:FIRMA|OSOBA|ADRES|INSTYTUCJA|NUMER|EMAIL|KWOTA)_\d{3}")

CONTENT = {  # etykieta → (treść z miejscem {nl} na wewnętrzny koniec wiersza, słowa identyfikujące)
    "OSOBA": [("Bartosz{nl}Kowalczyk", ["Bartosz", "Kowalczyk"]), ("Kowalczyk", ["Kowalczyk"]),
              ("Beata Zielonka{nl}Dariusz Wrona", ["Zielonka", "Wrona"])],
    "FIRMA": [("Testopolia{nl}Systemy", ["Testopolia"]), ("Testopolia", ["Testopolia"]),
              ("Testopolia Systemy{nl}Sp. z o.o.", ["Testopolia"]), ("Testopolia Systemy{nl}Spółka Akcyjna", ["Testopolia"])],
}
PLACES = {  # nazwa → (wnętrze, przód, tył)
    "brak": (" ", "", ""), "przód-LF": (" ", "\n", ""), "tył-LF": (" ", "", "\n"), "tył-CRLF": (" ", "", "\r\n"),
    "oba-brzegi": (" ", "\n", "\n"), "wnętrze-LF": ("\n", "", ""), "wnętrze-CRLF": ("\r\n", "", ""),
    "wnętrze-spacje": (" \n ", "", ""), "wnętrze+tył": ("\n", "", "\n"),
}


def main():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import engine_quality
        import ner_layer
        import pipeline
        import spacy_ner
    base = types.ModuleType("ner_layer_base")
    base.__file__ = str(ROOT / "backend/ner_layer.py")
    src = subprocess.check_output(["git", "show", f"{BASE}:backend/ner_layer.py"], cwd=ROOT).decode("utf-8")
    exec(compile(src, base.__file__, "exec"), base.__dict__)
    regressions, rows = [], 0
    with tempfile.TemporaryDirectory(prefix="lynx_edge_") as folder:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            state = engine_quality.build_state(folder)
        for label, items in CONTENT.items():
            for tmpl, words in items:
                for place, (inner, lead, trail) in PLACES.items():
                    if "{nl}" not in tmpl and inner != " ":
                        continue
                    span = lead + tmpl.format(nl=inner) + trail
                    text = "Wykonawca: " + span + "; koniec umowy."
                    ent = spacy_ner.NERResult(text=span, label=label, confidence=.9,
                                              start=text.index(span), end=text.index(span) + len(span))
                    res = {}
                    for name, owner in (("base", base._process_ner), ("head", ner_layer._process_ner)):
                        with patch.object(spacy_ner, "detect_entities", return_value=[ent]), \
                                patch.object(ner_layer, "_process_ner", owner), \
                                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            r = pipeline.pseudonymize_document(text, state)
                        back = TOKEN.sub(lambda m, rm=r.reverse_map: rm.get(m.group(0), m.group(0)), r.text)
                        res[name] = (sum(w in r.text for w in words), r.guard_blocked or bool(r.error), back == text)
                    rows += 1
                    (b_vis, b_blk, b_rst), (h_vis, h_blk, h_rst) = res["base"], res["head"]
                    if h_vis > b_vis or (h_blk and not b_blk) or (b_rst and not h_rst):
                        regressions.append((label, tmpl, place, res))
                    flag = "REGRESJA" if regressions and regressions[-1][:3] == (label, tmpl, place) else \
                        ("lepiej" if h_vis < b_vis else "")
                    print(f"{label:5} {tmpl.replace('{nl}', '/'):34} {place:15} jawne {b_vis}->{h_vis} "
                          f"blok {b_blk}->{h_blk} Przywróć {b_rst}->{h_rst} {flag}")
    print(f"\nprzypadków {rows}, regresji {len(regressions)}")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
