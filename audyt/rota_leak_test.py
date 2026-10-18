"""Pomiar szczelności LynxMask dla krótkich pytań koordynatora grafiku (Elnath Rota).
Imiona: backend/names_inflected.json, nazwiska: backend/surnames_top1000.json,
formy przypadków generowane Morfeuszem2. Dane syntetyczne (losowe pary, ziarno stałe).

Tryby:
  prod       — stan jak w API dziś: spaCy + anonymizer, profil bez seeda (seed pada, BUG-ONBOARD-BATCH)
  seed       — hipotetycznie naprawiony seed (12 288 form imion/nazwisk w trie)
  known      — symulacja mask(text, known_people): do pustego profilu dodane tylko osoby z pytania

Użycie: python audyt/rota_leak_test.py [--modes prod,seed,known] [--out plik.json]"""
import sys
import os
import re
import json
import time
import random
import logging
import tempfile
import argparse
import resource
logging.disable(logging.CRITICAL)
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, B); os.chdir(B)
import morfeusz2

CASES = ["nom", "gen", "dat", "acc", "inst", "loc"]
TPL = {
    "nom":  "{X} ma L4 do piątku, bo złamał nogę, przestaw grafik.",
    "gen":  "Czemu nie ma {X} na sobotniej zmianie?",
    "dat":  "Czemu {X} nie dało soboty, skoro ma L4 bo złamał nogę?",
    "acc":  "Wpisz {X} na niedzielę rano zamiast nocki.",
    "inst": "Zamień się z {X} na czwartek, bo ma wizytę u lekarza.",
    "loc":  "Pomyśl o {X} przy układaniu grafiku na grudzień.",
}
morf = morfeusz2.Morfeusz()

def form(lemma, case, gender):
    for f, _, tag, *_ in morf.generate(lemma):
        p = tag.split(":")
        if len(p) >= 4 and p[1] == "sg" and case in p[2].split(".") and gender in p[3].split("."):
            return f
    return None

def gender_of(name):
    for _, _, (f, lem, tag, *_ ) in morf.analyse(name):
        if tag.startswith("subst:sg:nom"):
            return "f" if ":f" in tag else "m1"
    return "m1"

def fem_surname(s):
    for a, b in (("ski", "ska"), ("cki", "cka"), ("dzki", "dzka")):
        if s.endswith(a):
            return s[: -len(a)] + b
    return s

def build_sentences(seed=2026):
    rnd = random.Random(seed)
    names = [n.capitalize() for n in json.load(open("names_inflected.json", encoding="utf-8"))]
    surn = [s.capitalize() for s in json.load(open("surnames_top1000.json", encoding="utf-8"))]
    males = [n for n in names if gender_of(n) == "m1"]
    fems = [n for n in names if gender_of(n) == "f"]
    out = []
    for case in CASES:
        for kind in ("m", "m", "f", "f", "s", "s"):
            for _ in range(50):
                sur = rnd.choice(surn)
                if kind == "f":
                    n = rnd.choice(fems); g = "f"; sl = fem_surname(sur)
                else:
                    n = rnd.choice(males); g = "m1"; sl = sur
                nf = form(n, case, g)
                sf = form(sl, case, g) or (sl if g == "f" else None)
                if nf and sf:
                    break
            parts = [sf] if kind == "s" else [nf, sf]
            out.append({"case": case, "kind": kind, "forms": parts, "lemmas": ([sl] if kind == "s" else [n, sl]),
                        "text": TPL[case].format(X=" ".join(parts))})
    return out

def make_state(mode):
    from pipeline import AppState
    import spacy_ner
    import anonymizer as A
    from anonymizer import build_anonymizer
    st = AppState(); st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="lynx_rota_")
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    if mode == "seed":
        A.MAX_ONBOARD_BATCH = 10 ** 6  # obejście BUG-ONBOARD-BATCH tylko w tym procesie
        from seed_profile import seed_if_needed
        seed_if_needed(st.anon_map)
    return st

def leaked(masked, forms):
    return [f for f in forms if re.search(r"(?<![\wąćęłńóśźż])" + re.escape(f) + r"(?![\wąćęłńóśźż])", masked)]

def run_mode(mode, sents):
    from pipeline import pseudonymize_document
    t0 = time.perf_counter(); st = make_state(mode); t_init = time.perf_counter() - t0
    rows, times = [], []
    for s in sents:
        if mode == "known":
            # mask(text, known_people): osoba z obsady dodana jako wymuszony słownik
            # (add_entity generuje odmiany Morfeuszem). Każde pytanie = świeży stan.
            st = make_state("prod")
            for lem in s["lemmas"]:
                st.anon_map.add_entity(lem, "OSOBA")
            if len(s["lemmas"]) == 2:
                st.anon_map.add_entity(" ".join(s["lemmas"]), "OSOBA")
        t1 = time.perf_counter()
        # tryb „express” (run_pipeline_express bez NER) usunięty w LYNX-EXPRESS-ONE-ENGINE — Express = ten sam silnik
        r = pseudonymize_document(s["text"], st); txt, rev, blocked = r.text, r.reverse_map, r.guard_blocked
        times.append(time.perf_counter() - t1)
        rows.append({**s, "masked": txt, "map": rev, "blocked": blocked, "leaked": leaked(txt, s["forms"])})
    return rows, t_init, times

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--modes", default="prod,seed,known"); ap.add_argument("--out")
    a = ap.parse_args()
    t0 = time.perf_counter()
    import pipeline  # noqa: F401  (pomiar zimnego startu: import całego pipeline)
    import spacy_ner
    spacy_ner._get_nlp()
    cold = time.perf_counter() - t0
    sents = build_sentences()
    print(f"zdania: {len(sents)}, form: {sum(len(s['forms']) for s in sents)}; zimny start (import+spaCy): {cold:.1f}s; "
          f"RSS max: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MB")
    result = {}
    for mode in a.modes.split(","):
        rows, t_init, times = run_mode(mode, sents)
        nf = sum(len(r["forms"]) for r in rows); nl = sum(len(r["leaked"]) for r in rows)
        sl = sum(1 for r in rows if r["leaked"])
        by = {}
        for r in rows:
            k = r["case"]; by.setdefault(k, [0, 0]); by[k][0] += len(r["forms"]); by[k][1] += len(r["leaked"])
        times.sort()
        print(f"\n[{mode}] init {t_init:.2f}s | formy jawnie: {nl}/{nf} ({100*nl/nf:.0f}%) | zdania z wyciekiem: {sl}/{len(rows)} "
              f"| czas/zdanie mediana {1000*times[len(times)//2]:.0f} ms, max {1000*times[-1]:.0f} ms")
        print("   per przypadek (jawne/razem):", {k: f"{v[1]}/{v[0]}" for k, v in by.items()})
        result[mode] = rows
    print(f"\nRSS max po wszystkim: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MB")
    if a.out:
        json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
