"""Przepuszcza dokumenty przez działający backend (/preview, ścieżka produkcyjna) i
wykrywa automatycznie kandydatów na wycieki w wyniku. Pełne wyniki zapisuje do
katalogu podanego w --out (NIE do repo — zawierają syntetyczne PII).
Użycie: python audyt/run_docs.py --out DIR plik1 plik2 ..."""
import os
import re
import json
import argparse
import requests
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
API = "http://127.0.0.1:8765"
TOK = open(os.path.join(B, "api_token.txt")).read().strip()
TOKEN = re.compile(r"(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3,}(?!\d)")
names = json.load(open(os.path.join(B, "names_inflected.json"), encoding="utf-8"))
surn = json.load(open(os.path.join(B, "surnames_top1000.json"), encoding="utf-8"))
NAMEFORMS = {f for v in list(names.values()) + list(surn.values()) for f in v} | set(names) | set(surn)
COMMON = {"piątek", "piątku", "maj", "maja", "róża", "mróz", "lis", "baran", "kania", "sikora", "wróbel", "zając"}

def mask(s):
    s = s.strip()
    return s if len(s) <= 3 else s[:3] + "*" * (len(s) - 3)

def leaks(out):
    t = TOKEN.sub(" ", out)
    res = []
    for m in re.finditer(r"\d(?:[ \-./]?\d){5,}", t):
        res.append(("CYFRY>=6", m.group(0)))
    for m in re.finditer(r"[\w.\-+]+\s?@\s?[\w\-]+(?:\.[\w\-]+)+", t):
        res.append(("EMAIL", m.group(0)))
    for m in re.finditer(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", t):
        w = m.group(0).lower()
        if w in NAMEFORMS and w not in COMMON:
            res.append(("IMIĘ/NAZWISKO(słownik)", m.group(0)))
    return res

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    summary = []
    for f in a.files:
        with open(f, "rb") as fh:
            r = requests.post(f"{API}/preview", files={"file": (os.path.basename(f), fh, "text/plain")},
                              headers={"X-Api-Token": TOK}, timeout=120)
        d = r.json()
        out = d.get("anonymized_preview", "") or ""
        base = os.path.basename(f)
        open(os.path.join(a.out, base + ".out.txt"), "w", encoding="utf-8").write(out)
        json.dump(d, open(os.path.join(a.out, base + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        L = leaks(out)
        cats = {}
        for t in d.get("tokens", []):
            cats[t["type"]] = cats.get(t["type"], 0) + 1
        print(f"\n=== {base}: HTTP {r.status_code} blocked={d.get('blocked')} tokens={cats}")
        for g in d.get("guard_reasons", [])[:6]:
            print("   guard:", re.sub(r"«[^»]*»", "«…»", re.sub(r"'[^']*'", "'…'", g))[:120])
        for k, v in L:
            print(f"   KANDYDAT {k}: {mask(v)}")
        summary.append({"file": base, "blocked": d.get("blocked"), "tokens": cats, "kandydaci": [(k, mask(v)) for k, v in L]})
    json.dump(summary, open(os.path.join(a.out, "_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
