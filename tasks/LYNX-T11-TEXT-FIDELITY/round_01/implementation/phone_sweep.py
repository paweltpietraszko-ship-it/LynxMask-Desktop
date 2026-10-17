# LYNX-T11 runda 4: przegląd rodziny telefonów vs normalizator sprzed T11 (576d133). Dane syntetyczne. Uruchom z backend/.
# Regresja = stary normalizator zamienił cały numer na cyfry, nowy nie; albo zmienione słowo po numerze.
import itertools, subprocess, sys, types
sys.path.insert(0, ".")
src = subprocess.check_output(["git", "show", "576d133:backend/layers/ocr_normalizer.py"], text=True, encoding="utf-8")
old = types.ModuleType("o"); old.__file__ = "layers/ocr_normalizer.py"; exec(compile(src, old.__file__, "exec"), old.__dict__)
from layers.ocr_normalizer import normalize_ocr as new
num = lambda s: s.replace(" ", "").lstrip("+").isdigit()
reg = n = 0
for p, g, t in itertools.product(["+48 ", "+48", "0048 ", "48 ", ""], ["606 219 ", "6O6 2l9 "], map("".join, itertools.product("TIlOSBGZzo", repeat=3))):
    for after in ["", ". Termin płatności", " zglosil sie"]:
        text, k = f"Tel: {p}{g}{t}{after}", len(p) + len(g) + 3
        o, nn = old.normalize_ocr(text)[5:5 + k], new(text)
        n += 1
        reg += (num(o) and not num(nn[5:5 + k])) or (bool(after) and not nn.endswith(after))
words = [(p, w) for p in ["+48 ", "+48", "0048 ", "48 ", ""] for w in ["To jest", "Termin", "zglosil", "Ola", "IT", "OSiR", "BIZ", "Zoo", "SOS"]
         if not new(f"tel. {p}512 987 654 {w}").endswith(w)]
print(f"przypadków {n}, regresji/zmian słów {reg}; słowa po pełnym numerze zmienione: {len(words)}")
