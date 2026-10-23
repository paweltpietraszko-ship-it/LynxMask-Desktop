"""Ocena 3 filtrów Guard R1 na wszystkich 902 ostrzeżeniach (lokalnie). Wynik: agregaty; przykłady tylko z dokumentów nieprywatnych."""
import json, re, sys
from collections import Counter
src, data = sys.argv[1:3]
sys.path.insert(0, src); sys.stdout.reconfigure(encoding="utf-8")
import person_decision as pd
from osoba_not_person import first_names, _TITLE_RE, _ROLE_RE
FUNC = re.compile(r"(?i)^(?:wojewod|starost|komornik|prezes|sędzi|marszał|burmistrz|wójt|prokurator|notariusz|dyrektor|kierownik"
                  r"|minister|posł|poseł|senator|rzecznik|inspektor|kanclerz|premier|prezydent|protokolant|przewodnicząc)")
ADJ = re.compile(r"(?:ski|cki|dzki|ska|cka|dzka|skie|ckie|skiego|ckiego|dzkiego|skiej|ckiej|dzkiej|skim|ckim|dzkim|ską|cką|skich|ckich|skiemu)$")
CAPW = re.compile(r"[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+")
names = first_names()
def neighbors(ctx, i, j):
    before, after = ctx[:i], ctx[j:]
    b = re.search(r"(?:^|[\s(„\"])([A-ZĄĆĘŁŃÓŚŹŻ][\w-]*|OSOBA_\d{3})[ \t]+$", before)
    a = re.match(r"[ \t]+([A-ZĄĆĘŁŃÓŚŹŻ][\w-]*|OSOBA_\d{3})", after)
    return [x.group(1) for x in (b, a) if x], before
def anchored(ctx, i, j):
    nb, before = neighbors(ctx, i, j)
    line = before[before.rfind("  ") + 1:] if "  " in before else before
    if _TITLE_RE.search(before[-14:]) or _ROLE_RE.search(before[-40:]):
        return True
    return any(n.startswith("OSOBA_") or n.lower() in names or re.fullmatch(r"[A-ZĄĆĘŁŃÓŚŹŻ]\.", n) for n in nb)
rows = json.load(open(data, encoding="utf-8"))["wszystkie"]
res = Counter(); tp_hit = Counter(); ex = {}
for r in rows:
    ctx, fr = r["ctx"], r["frag"]
    i = ctx.find(fr, max(0, 60 - 5)) if ctx.find(fr, max(0, 60 - 5)) >= 0 else ctx.find(fr)
    j = i + len(fr)
    f = pd._features(fr)
    anc = anchored(ctx, i, j)
    nb, _ = neighbors(ctx, i, j)
    cls = "zostaje"
    if not anc:
        if f["white"]:
            cls = "F1_biala_lista"
        elif FUNC.match(fr):
            cls = "F2_funkcja"
        elif ADJ.search(fr.lower()) and any(not n.startswith("OSOBA_") and n.lower() not in names
                                             and pd._features(n)["count"] < 100 and not pd._features(n)["morf_person"] for n in nb):
            cls = "F3_przymiotnik_w_nazwie"
    res[cls] += 1
    if r["tp"]:
        tp_hit[cls] += 1
    if not r["private"]:
        ex.setdefault(cls, Counter())[fr] += 1
print("razem:", len(rows), "| prywatne:", sum(x["private"] for x in rows))
for k, v in res.most_common():
    print(f"  {k}: {v}  (w tym dopasowanie do osoby z gold: {tp_hit[k]})", "| np.:", ", ".join(f"{w}:{n}" for w, n in ex.get(k, Counter()).most_common(15)))
