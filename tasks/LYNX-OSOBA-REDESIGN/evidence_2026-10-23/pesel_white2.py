"""Biała lista przez PESEL: słowo małą literą w pismach → lematy Morfeusza → nazwisko z PESEL (100 ≤ osób < 1000), ≥2 dok.; bez miesięcy."""
import csv, glob, json, os, re, sys
from collections import defaultdict
import morfeusz2
sys.stdout.reconfigure(encoding="utf-8")
pdir, old_csv, out, *corpora = sys.argv[1:]
cnt = {}
for f in ("m_2026.csv", "f_2026.csv"):
    for r in csv.DictReader(open(os.path.join(pdir, f), encoding="utf-8")):
        k = r["Nazwisko aktualne"].strip().lower(); cnt[k] = cnt.get(k, 0) + int(r["Liczba"])
MONTHS = {"styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"}
m = morfeusz2.Morfeusz()
WORD = re.compile(r"(?<![\w-])[a-ząćęłńóśźż]{3,}(?![\w-])")
cache, docs, forms = {}, defaultdict(set), defaultdict(set)
for spec in corpora:
    _, pattern = spec.split("=", 1)
    for path in glob.glob(pattern):
        raw = open(path, encoding="utf-8", errors="replace").read()
        text = json.loads(raw).get("text", "") if path.endswith(".json") else raw
        text = re.sub(r"\S*[@/]\S*|\S+\.(?:pl|com|eu|gov|org|net)\S*", " ", text or "")
        for w in set(WORD.findall(text)):
            if w not in cache:
                cache[w] = {i[2][1].split(":")[0].lower() for i in m.analyse(w)} | {w}
            for l in cache[w]:
                if 100 <= cnt.get(l, 0) < 1000 and l not in MONTHS:
                    docs[l].add(path); forms[l].add(w)
new = {l for l in docs if len(docs[l]) >= 2}
old = {r["slowo"] for r in csv.DictReader(open(old_csv, encoding="utf-8-sig"), delimiter=";")}
print("PESEL-owa biała lista:", len(new), "| obecna (Mobile):", len(old), "| wspólne:", len(new & old))
print("tylko w nowej:", len(new - old), ", ".join(sorted(new - old, key=lambda x: -len(docs[x]))[:60]))
print("tylko w obecnej:", len(old - new), ", ".join(sorted(old - new)[:60]))
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["slowo", "osob_w_PESEL", "dokumentow_z_mala_litera", "jak_wystepuje_w_pismach", "uwaga (wpisz NAZWISKO jesli ma zostac)"])
    for l in sorted(new, key=lambda x: -len(docs[x])):
        w.writerow([l, cnt[l], len(docs[l]), ", ".join(sorted(forms[l])[:5]), ""])
