#!/usr/bin/env python3
"""
LYNX-T01 — pomiar na nazwiskach SPOZA słownika Desktop (doprecyzowanie D2 z cc_review_r1.md).

Nazwiska: LynxMask Mobile `app/src/main/assets/surnames_extended.json` (repo paweltpietraszko-ship-it/LynxMask),
minus wszystko z `backend/surnames_top1000.json`. Odmiany generuje Morfeusz. Imiona: `backend/names_inflected.json`.
Porównanie: ner_layer/ner_blocklist z wersji przed zmianą (katalog --old) vs obecne w backend/.
Wyciek = forma nazwiska widoczna w wyniku pipeline_new.run_pipeline_new (świeży profil, bez seeda).

Użycie (z korzenia repo):
  py -3 tasks/LYNX-T01-NER-PREFIX/round_01/implementation/holdout_measure.py \
      --mobile-surnames <ścieżka>/surnames_extended.json [--old <katalog ze starymi ner_*.py>] [--n 120]
"""
import argparse
import importlib.util
import json
import os
import random
import sys
import warnings

warnings.filterwarnings("ignore")
CASES = {  # przypadek -> (tag Morfeusza, szablon zdania)
    "nom": ("sg:nom", "Pan {s} ma L4 do piątku."),
    "gen": ("sg:gen", "Proszę o zmianę grafiku dla {s} od poniedziałku."),
    "dat": ("sg:dat", "Czemu {s} nie dano wolnej soboty?"),
    "inst": ("sg:inst", "Rozmawiałem z {s} o urlopie."),
}
FULL = "Wnioskodawca {f} {s} złożył pismo w sprawie zaległego wynagrodzenia."


def load_old(old_dir, backend):
    for name in ("ner_blocklist", "ner_layer"):
        spec = importlib.util.spec_from_file_location(name, os.path.join(old_dir, name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)


def masc_forms(morf, base):
    """{przypadek: forma} dla męskiej formy nazwiska, jeśli Morfeusz zna je jako nazwisko."""
    out = {}
    for form, _lemma, tag, quals, _labels in morf.generate(base):
        if not any(q.startswith("nazwisko") for q in quals) or ":m1" not in tag:
            continue
        for case, (needle, _t) in CASES.items():
            if needle in tag and case not in out:
                out[case] = form
    return out if len(out) == len(CASES) else None


def build(args, morf):
    known = {k.lower() for k in json.load(open(os.path.join(args.backend, "surnames_top1000.json"), encoding="utf-8"))}
    names = [n.capitalize() for n in json.load(open(os.path.join(args.backend, "names_inflected.json"), encoding="utf-8"))]
    pool = sorted(s for s in json.load(open(args.mobile_surnames, encoding="utf-8"))
                  if s.isalpha() and s.lower() not in known)
    rnd = random.Random(2026)
    rnd.shuffle(pool)
    items = []
    for s in pool:
        forms = masc_forms(morf, s.capitalize())
        if forms:
            items.append((rnd.choice(names), forms))
        if len(items) >= args.n:
            break
    return items


def run(items):
    from pipeline_new import run_pipeline_new
    leaks, total = {c: 0 for c in list(CASES) + ["full"]}, 0
    for first, forms in items:
        total += 1
        for case, (_n, tmpl) in CASES.items():
            out, _r, _b = run_pipeline_new(tmpl.format(s=forms[case]), anon_map={})
            leaks[case] += forms[case] in out
        out, _r, _b = run_pipeline_new(FULL.format(f=first, s=forms["nom"]), anon_map={})
        leaks["full"] += forms["nom"] in out
    return leaks, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mobile-surnames", required=True)
    ap.add_argument("--backend", default="backend")
    ap.add_argument("--old")
    ap.add_argument("--n", type=int, default=120)
    args = ap.parse_args()
    args.backend = os.path.abspath(args.backend)
    sys.path.insert(0, args.backend)
    os.chdir(args.backend)
    if args.old:
        load_old(os.path.abspath(args.old), args.backend)
    import morfeusz2
    items = build(args, morfeusz2.Morfeusz())
    leaks, total = run(items)
    label = "PRZED (stary filtr)" if args.old else "PO (LYNX-T01)"
    print(f"{label}: {total} nazwisk spoza surnames_top1000, wycieki (forma jawna w wyniku):")
    for case, n in leaks.items():
        print(f"  {case:5s} {n:4d}/{total}  ({100 * n / total:.1f}%)")
    print(f"  RAZEM {sum(leaks.values())}/{total * len(leaks)}")


if __name__ == "__main__":
    main()
