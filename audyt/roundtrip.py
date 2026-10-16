"""Wierność Przywracania: unmask(anonymized_preview, mapa) vs tekst wejściowy.
Logika unmask = frontend Depseudonimizuj.tsx (audyt/unmask_sim.py).
Wejście: katalog z *.json zapisanymi przez run_docs.py. Wypisuje tylko statystyki i
zamaskowane fragmenty różnic."""
import sys
import os
import json
import difflib
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unmask_sim import unmask

def m(s):
    return re.sub(r"([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9]{2})[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż0-9]+", lambda x: x.group(1) + "*" * (len(x.group(0)) - 2), s)

d = sys.argv[1]
for f in sorted(os.listdir(d)):
    if not f.endswith(".json") or f.startswith("_"):
        continue
    j = json.load(open(os.path.join(d, f), encoding="utf-8"))
    src = j["original_text"]
    out = j["anonymized_preview"].split("]\n\n", 1)[1]
    rev = {t["token"]: t["original"] for t in j["tokens"]}
    back = unmask(out, rev)
    sm = difflib.SequenceMatcher(None, src, back, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
    ident = src == back
    ws_only = re.sub(r"\s+", "", src) == re.sub(r"\s+", "", back)
    print(f"{f[:-5]:42} identyczny={ident!s:5} tylko_białe_znaki={ws_only!s:5} różnic={len(ops)} ratio={sm.ratio():.4f}")
    shown = 0
    for tag, i1, i2, j1, j2 in ops:
        a, b = src[i1:i2], back[j1:j2]
        if re.sub(r"\s", "", a) == re.sub(r"\s", "", b):
            continue
        if shown < 6:
            print(f"     {tag}: {m(a)!r} -> {m(b)!r}")
        shown += 1
    if shown > 6:
        print(f"     ... +{shown-6} innych nie-białych różnic")
