"""Zbiór testowy Pawła: przepuszcza corpus/ przez silnik (w procesie, pusty profil) i porównuje z gold_clean/gold_stress.

Użycie (z katalogu repo, środowisko .venv):
    .venv\\Scripts\\python.exe testset_owner\\run_testset.py [katalog_backendu] [plik_wyniku.json]
Domyślnie katalog_backendu = backend/ tego repo. Wynik: tabela na ekranie + JSON z listą wycieków i pytań Guarda.

Wyciek = wartość z klucza nadal widoczna w wyniku:
  osoba   — każde słowo imienia/nazwiska (≥3 litery) osobno, całe słowo;
  adres   — ulica z numerem (część przed przecinkiem); samo miasto jest jawne z założenia;
  numery  — PESEL, NIP, IBAN, dowód, telefon, sygnatury… po usunięciu spacji, kresek i ukośników;
  e-mail  — dosłownie;
  daty    — osobna kolumna (data urodzenia / data pisma), bo polityka dat jest inna niż PII.
Klucz mówi tylko, co musi zniknąć — nadmaskowania ten skrypt nie mierzy.
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PERSON = ("imie_nazwisko", "skarzacy", "oskarzony", "autor", "osoba")
DATES = ("data", "data_urodzenia")


def _kind(field):
    if field.startswith(PERSON):
        return "osoba"
    if field.startswith("adres"):
        return "adres"
    if field == "email":
        return "email"
    if field in DATES:
        return "data"
    return "numer"


def _flat(s):
    return re.sub(r"[\s\-/.]", "", s).lower()


def leaks(out, entities):
    """Lista (pole, rodzaj, fragment) wartości z klucza widocznych w tekście wyniku."""
    found, flat = [], _flat(out)
    for field, val in entities.items():
        if not isinstance(val, str) or not val.strip():
            continue
        kind = _kind(field)
        if kind == "osoba":
            for w in re.findall(r"[^\W\d_]{3,}", val):
                if re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", out):
                    found.append((field, kind, w))
        elif kind == "adres":
            street = val.split(",")[0].strip()
            if street and _flat(street) in flat:
                found.append((field, kind, street))
        elif kind == "email":
            if val.lower() in out.lower():
                found.append((field, kind, val))
        elif _flat(val) and _flat(val) in flat:
            found.append((field, kind, val))
    return found


def main():
    backend = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "backend"))
    out_json = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tempfile.gettempdir(), "testset_owner_wynik.json")
    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    gold = {}
    for s in ("clean", "stress"):
        for d in json.load(open(os.path.join(HERE, f"gold_{s}.json"), encoding="utf-8")):
            gold[d["id"]] = d["entities"]
    texts = {r["id"]: open(os.path.join(HERE, "corpus", r["id"]), encoding="utf-8", errors="replace").read() for r in manifest}

    prof = tempfile.mkdtemp()
    os.environ["PROFILE_DIR"] = prof
    os.environ["ANONYMIZER_PROFILE_DIR"] = prof + "/a"
    os.chdir(backend)
    sys.path.insert(0, backend)
    sys.stdout.reconfigure(encoding="utf-8")
    import spacy_ner
    from anonymizer import build_anonymizer
    from pipeline import AppState, pseudonymize_document

    per_set = defaultdict(Counter)
    detail = {"backend": backend, "docs": {}}
    leak_frag = defaultdict(Counter)
    for r in manifest:
        t = texts[r["id"]]
        if not t.strip():
            continue
        st = AppState()
        st.spacy_ner_mod = spacy_ner
        d = tempfile.mkdtemp(dir=prof)
        with contextlib.redirect_stdout(io.StringIO()):
            st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, d + "/hw.json")
            res = pseudonymize_document(t, st)
        warns = [w["fragment"] for w in res.guard_warnings]
        c = per_set[r["set"]]
        c["dok"] += 1
        c["pytania"] += len(warns)
        rec = {"set": r["set"], "pytania": warns}
        if r["id"] in gold:
            lk = leaks(res.text, gold[r["id"]])
            rec["wycieki"] = lk
            for field, kind, frag in lk:
                guarded = any(frag in w or w in frag for w in warns)
                c[f"{kind}:{'z_pytaniem' if guarded else 'cichy'}"] += 1
                if not guarded:
                    leak_frag[kind][frag] += 1
            for field, val in gold[r["id"]].items():
                c[f"{_kind(field)}:razem"] += 1
        detail["docs"][r["id"]] = rec

    print(f"backend: {backend}")
    print(f"{'zbiór':8} {'dok':>4} {'pytań/dok':>9}  ciche wycieki (z pytaniem) / wartości w kluczu")
    for s in ("clean", "stress", "testy", "pliki", "ocr"):
        c = per_set[s]
        if not c["dok"]:
            continue
        line = f"{s:8} {c['dok']:>4} {c['pytania'] / c['dok']:>9.2f}  "
        if s in ("clean", "stress"):
            line += "  ".join(f"{k} {c[k + ':cichy']}({c[k + ':z_pytaniem']})/{c[k + ':razem']}"
                              for k in ("osoba", "adres", "numer", "email", "data"))
        print(line)
    for k, cnt in leak_frag.items():
        print(f"ciche {k}: " + ", ".join(f"{f}:{n}" for f, n in cnt.most_common(15)))
    json.dump(detail, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"szczegóły: {out_json}")


if __name__ == "__main__":
    main()
