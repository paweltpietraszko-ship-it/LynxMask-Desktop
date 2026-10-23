"""C1: nazwiska z listy (Mobile 39k, oczyszczona) klasyfikowane przez Morfeusza jako tylko-pospolite (common=True, person=False);
ich liczba w PESEL 2026-01-20; obecność w person_forms (silnik). Plus: czy najczęstsze słowa z released() są na liście nazwisk."""
import csv, json, os, sys
src, pdir, surn = sys.argv[1:4]
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
from osoba_not_person import _common_or_person
from ner_layer import _PERSON_FORMS
cnt = {}
for f in ("m_2026.csv", "f_2026.csv"):
    for row in csv.DictReader(open(os.path.join(pdir, f), encoding="utf-8")):
        k = row["Nazwisko aktualne"].strip().lower(); cnt[k] = cnt.get(k, 0) + int(row["Liczba"])
d = json.load(open(surn, encoding="utf-8"))
forms = set(d) | {f for v in d.values() for f in v}
only = []
for base in d:
    if " " in base: continue
    c, p, g = _common_or_person(base)
    if c is True and p is False:
        only.append((cnt.get(base, 0), base, base in _PERSON_FORMS))
only.sort(reverse=True)
print("hasła listy:", len(d), "| tylko-pospolite wg Morfeusza:", len(only), "| z nich w person_forms:", sum(x[2] for x in only))
print("osób w PESEL z takimi nazwiskami:", sum(x[0] for x in only))
print("największe:", ", ".join(f"{b} {c}{' [pf]' if pf else ''}" for c, b, pf in only[:40]))
rel = ["Odwołującego", "Odwołujący", "Odwołującemu", "Przystępującego", "Protokolant", "Powódka", "Powodowi", "Pozwanemu", "Protestującego",
       "Skarżącego", "Zaskarżonemu", "Gwaranta", "Poręczyciela", "Mebla", "Ergo", "Loco", "Komornika", "Sam", "Mają", "Rady", "Marszałek", "Konieczne", "Pola"]
print("released (main) na liście nazwisk:", [w for w in rel if w.lower() in forms])
print("released (main) NIE na liście:", [w for w in rel if w.lower() not in forms])
