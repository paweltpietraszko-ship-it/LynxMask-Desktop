"""Analiza PRZED/PO z raw_przed.json / raw_po.json -> wynik.json, porownanie.html. Uzycie: python measure_cmp.py <katalog>"""
import json, re, sys, collections, difflib, html, statistics
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
D = Path(sys.argv[1])
RX = re.compile(r"((?:[A-ZŁŚŻŹĆŃÓ][\w\-&.]*\s+){1,5})(Sp\.\s?z\s?o\.\s?o\.?(?:\s?sp\.\s?k\.|\s?S\.K\.A\.?)?|S\.A\.|S\.C\.|Sp\.\s?k\.|Sp\.\s?j\.)", re.U)
LEGAL = {"sp", "z", "o", "spółka", "sa", "sc", "ska", "sk", "zoo", "oo", "skarbowy"}
FORM = re.compile(r"\s*(Sp\.\s?z\s?o\.\s?o\.?(?:\s?sp\.\s?k\.|\s?S\.K\.A\.?)?|S\.A\.|S\.C\.|Sp\.\s?k\.|Sp\.\s?j\.)\s*$")
OSK = {"imie_nazwisko", "imie_nazwisko_zleceniodawca", "imie_nazwisko_zleceniobiorca", "imie_nazwisko_nabywcy", "autor", "osoba", "skarzacy", "oskarzony"}
G = {}
for p, pre in ((r"C:\Projects\LynxMask\dataset_clean\ground_truth.json", "clean"), (r"C:\Users\p_pie\Desktop\LynxMask-Desktop\backend\dataset_20260627_095419\ground_truth.json", "img")):
    for d in json.load(open(p, encoding="utf-8")): G[(pre, d["file"].split("/")[-1])] = d
CITY_STEMS = ["krak", "warsz", "wrocła", "pozna", "gdańs", "gdyn", "zakopan", "toru", "łodz", "łódź", "katowic", "lublin", "szczeci", "bydgosz", "opol", "rzesz", "kielc", "olsztyn", "tarnow", "tarnów", "radom", "sopo", "białyst", "częstoch", "gliwic", "zabrz", "bielsk", "elbl", "płock", "kalisz", "legnic", "londyn"]
def norm(s): return re.sub(r"[^\w]+", " ", s.lower()).strip()
def words(s): return [w for w in re.split(r"[^\w]+", s) if w]
def stems(s): return [w.lower()[:max(3, len(w) - 2)] for w in words(s) if len(w) >= 3]
def pgold(j, it):
    txt = j["text"] or it.get("orig") or ""
    if j["set"] == "sweep": return {j["name"]}
    if j["set"] == "cel": return set()
    out = {m.group(0).strip() for m in RX.finditer(txt)}
    if j["set"] in ("clean", "img"):
        m = re.search(r"SPRZEDAWCA:\s*\n\s*([^\n]+)", txt)
        if m: out.add(m.group(1).strip())
    return out
def classify_fp(o):
    n = o.strip(); nl = n.lower()
    if re.fullmatch(r"(sp\.? ?)?z o\.?o\.?( s\.?k\.?a\.?)?", n, re.I): return "T"
    if re.match(r"(SR\b|Sąd|Urząd|Starostwo|Zakład Ubezpieczeń Społecznych|Zaklad Ubezpiecze|Miasto|Gmin|Rzecznik|Wydzia[łl]e Spraw|Kancelaria Komornicza|Urzędu)", n): return "instytucja"
    if any(c in nl for c in CITY_STEMS) and len(n.split()) <= 2: return "adres/miasto"
    if re.match(r"(ul\.|al\.|pl\.|os\.)", nl) or re.search(r"\d", n): return "adres/numer"
    if re.fullmatch(r"[A-ZŁŚŻŹĆŃÓ][\w\-]+ [A-ZŁŚŻŹĆŃÓ][\w\-]+", n): return "osoba-podobne"
    if len(n.split()) == 1 and n[:1].isupper() and len(n) < 14: return "słowo pospolite (1 wyraz)"
    return "inne"
def classify_os_fp(o):
    n = o.strip(); nl = n.lower()
    if any(c in nl for c in CITY_STEMS): return "miasto/odmiana"
    if re.match(r"(ul\.|al\.|pl\.)", nl) or re.search(r"\d", n): return "adres/numer"
    if re.match(r"(SR\b|Sąd|Urząd|Starostwo|Zakład|Miasto|Gmin)", n): return "instytucja"
    if len(n.split()) == 1: return "jeden wyraz (słowo pospolite/imię)"
    if re.fullmatch(r"[A-ZŁŚŻŹĆŃÓ][\w\-]+ [A-ZŁŚŻŹĆŃÓ][\w\-]+", n): return "dwa wyrazy (imię-nazwisko-podobne)"
    return "inne"
GEN = {"firma", "usługi", "kancelaria", "centrum", "hurtownia", "serwis", "zakład"}
def leak_firm(f, prev):
    head = FORM.sub("", f).strip(); form = FORM.search(f)
    hw = [w for w in words(head) if len(w) >= 3 or w.isupper()]
    pl = prev.lower()
    if re.sub(r"\s+", " ", head).lower() in re.sub(r"\s+", " ", pl): return "JAWNA", hw
    rem = [w for w in hw if re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", pl) and w.lower() not in GEN]
    if rem: return ("CZĘŚCIOWO", rem) if len(rem) < len(hw) else ("JAWNA", rem)
    if form and re.sub(r"\s+", " ", form.group(1).strip().rstrip(".")).lower() in re.sub(r"\s+", " ", pl): return "CZĘŚCIOWO", ["(tylko forma prawna)"]
    return "ZAKRYTA", []
def leak_os(name, prev):
    st = stems(name); pl = prev.lower()
    rem = [s for s in st if re.search(r"(?<!\w)" + re.escape(s), pl)]
    if st[:1] == ["jak"] and not re.search(r"(?<!\w)jakub", pl): rem = [s for s in rem if s != "jak"]
    return "ZAKRYTA" if not rem else ("JAWNA" if len(rem) == len(st) else "CZĘŚCIOWO")
def analyze(raw):
    out = {"sets": {}, "docs": {}}
    for s in ("clean", "img", "mobile", "sweep", "cel"):
        Dd = dict(docs=0, skipped=[], firma_gold=collections.Counter(), docs_leak=set(), tok_tp=0, tok_T=0, tok_fp=collections.Counter(), firma_tokens=0,
                  pattern_nazwa_sp=0, os_gold=collections.Counter(), os_tok_tp=0, os_tok_fp=collections.Counter(), guard_blocked=[], secs=[], restore_bad=[], collisions=[])
        for j, it in zip(raw["jobs"], raw["items"]):
            if j["set"] != s: continue
            doc = j["path"].split("\\")[-1]; key = f"{s}/{doc}"
            if it["code"] != 200 or it.get("blocked"):
                Dd["skipped"].append(doc)
                if it.get("blocked"): Dd["guard_blocked"].append([doc, it.get("scal"), it.get("guard")])
                out["docs"][key] = {"skipped": True, "code": it["code"], "blocked": bool(it.get("blocked"))}
                continue
            Dd["docs"] += 1; Dd["secs"].append(it["secs"]); prev = it["preview"]; orig = j["text"] if j["text"] is not None else (it.get("orig") or "")
            pg = pgold(j, it); pg = {f for f in pg if not any(f != g and f in g for g in pg)}
            toksF = [t for t in it["tokens"] if t[1] == "FIRMA"]
            fl = {}
            pw = set(w for g in pg for w in norm(g).split() if w not in LEGAL and len(w) > 2)
            for f in pg:
                st, rem = leak_firm(f, prev); fl[f] = st; Dd["firma_gold"][st] += 1
                if st != "ZAKRYTA": Dd["docs_leak"].add(doc)
            Dd["pattern_nazwa_sp"] += len(re.findall(r"(?:Sp\.\s?z\s?o\.\s?o\.?|S\.A\.|Sp\.\s?k\.|Sp\.\s?j\.|S\.C\.)\s*\[?FIRMA_\d+", prev))
            fpF = []
            for t in toksF:
                c = classify_fp(t[2]); Dd["firma_tokens"] += 1
                tw = set(w for w in norm(t[2]).split() if w not in LEGAL and len(w) > 2)
                if tw & pw: Dd["tok_tp"] += 1
                elif c == "T": Dd["tok_T"] += 1
                else: Dd["tok_fp"][c] += 1; fpF.append([c, t[2]])
            osl = {}; fpO = []
            if (s, doc) in G:
                gold = [v for k, v in G[(s, doc)]["entities"].items() if k in OSK]
                for v in gold:
                    st = leak_os(v, prev); osl[v] = st; Dd["os_gold"][st] += 1
                gs = [x for v in gold for x in stems(v)]
                for t in it["tokens"]:
                    if t[1] == "OSOBA":
                        ts = [w.lower() for w in words(t[2])]
                        if any(w.startswith(x) for w in ts for x in gs): Dd["os_tok_tp"] += 1
                        else:
                            c = classify_os_fp(t[2]); Dd["os_tok_fp"][c] += 1; fpO.append([c, t[2]])
            elif s in ("mobile", "cel"):
                for t in it["tokens"]:
                    if t[1] == "OSOBA": fpO.append([classify_os_fp(t[2]) + " (bez golda)", t[2]])
            rest = re.sub(r"^\[Dokument pseudonimizowany.*?\]\n\n", "", prev, count=1, flags=re.S); bymap = collections.defaultdict(set)
            for t in it["tokens"]: bymap[t[0]].add(t[2])
            for tk in sorted(bymap, key=len, reverse=True):
                if len(bymap[tk]) > 1: Dd["collisions"].append([doc, tk, sorted(bymap[tk])])
                rest = rest.replace(tk, sorted(bymap[tk])[0])
            if j["text"] is not None and rest != orig: Dd["restore_bad"].append(doc)
            out["docs"][key] = dict(firma_gold=fl, os_gold=osl, fpF=fpF, fpO=fpO, tokens=it["tokens"], prev=prev, orig=orig, restore_ok=(rest == orig) if j["text"] is not None else None, rest=rest)
        Dd["docs_leak"] = len(Dd["docs_leak"])
        for k in ("firma_gold", "tok_fp", "os_gold", "os_tok_fp"): Dd[k] = dict(Dd[k])
        sec = Dd.pop("secs"); Dd["median_preview_s"] = round(statistics.median(sec), 3) if sec else None
        out["sets"][s] = Dd
    out["import_secs"] = raw.get("import_secs"); out["startup_secs"] = raw.get("startup_secs"); out["wall"] = raw.get("wall"); out["sha"] = raw.get("sha")
    return out
raws = {k: json.load(open(D / f"raw_{k}.json", encoding="utf-8")) for k in ("przed", "po")}
A = {k: analyze(v) for k, v in raws.items()}
timing = {}
for k in ("przed2", "po2"):
    if (D / f"raw_{k}.json").is_file():
        r2 = json.load(open(D / f"raw_{k}.json", encoding="utf-8"))
        timing[k] = {"import_secs": r2.get("import_secs"), "startup_secs": r2.get("startup_secs"), "wall": r2.get("wall"),
                     "median_preview_s_clean": statistics.median([i["secs"] for j, i in zip(r2["jobs"], r2["items"]) if j["set"] == "clean" and i["code"] == 200])}
RK = {"ZAKRYTA": 0, "CZĘŚCIOWO": 1, "JAWNA": 2}
diffs = []
for key, a in A["przed"]["docs"].items():
    b = A["po"]["docs"].get(key)
    if a.get("skipped") or not b or b.get("skipped"):
        if a.get("skipped") != (b or {}).get("skipped"): diffs.append(dict(key=key, klasa="zmiana blokady Guard", wartosc="", typ=""))
        continue
    for f in set(a["firma_gold"]) | set(b["firma_gold"]):
        x, y = a["firma_gold"].get(f), b["firma_gold"].get(f)
        if x != y: diffs.append(dict(key=key, klasa=("nowy wyciek (firma)" if RK.get(y, 0) > RK.get(x, 0) else "naprawiony wyciek (firma)"), wartosc=f, typ=f"{x} -> {y}"))
    for v in set(a["os_gold"]) | set(b["os_gold"]):
        x, y = a["os_gold"].get(v), b["os_gold"].get(v)
        if x != y: diffs.append(dict(key=key, klasa=("nowy wyciek (OSOBA)" if RK.get(y, 0) > RK.get(x, 0) else "naprawiony wyciek (OSOBA)"), wartosc=v, typ=f"{x} -> {y}"))
    for nm, la, lb in (("FIRMA", a["fpF"], b["fpF"]), ("OSOBA", a["fpO"], b["fpO"])):
        ca, cb = collections.Counter(map(tuple, la)), collections.Counter(map(tuple, lb))
        for k2, n in (cb - ca).items(): diffs.append(dict(key=key, klasa=f"nowy FP {nm}", wartosc=k2[1], typ=k2[0]))
        for k2, n in (ca - cb).items(): diffs.append(dict(key=key, klasa=f"usunięty FP {nm}", wartosc=k2[1], typ=k2[0]))
    ta = collections.Counter((t[1], t[2]) for t in a["tokens"] if t[1] in ("FIRMA", "OSOBA")); tb = collections.Counter((t[1], t[2]) for t in b["tokens"] if t[1] in ("FIRMA", "OSOBA"))
    for k2 in set((ta - tb).keys()) | set((tb - ta).keys()):
        if not any(d["key"] == key and d["wartosc"] == k2[1] for d in diffs):
            diffs.append(dict(key=key, klasa="zmiana granic/tokenu", wartosc=k2[1], typ=f"{k2[0]} {'tylko PO' if k2 in (tb - ta) else 'tylko PRZED'}"))
    if a["prev"] != b["prev"] and not any(d["key"] == key for d in diffs):
        diffs.append(dict(key=key, klasa="zmiana granic/tokenu", wartosc="(inna numeracja/podmiana)", typ=""))
tokcmp = dict(docs=0, identical=0, differ=0, differ_examples=[])
for key, a in A["przed"]["docs"].items():
    b = A["po"]["docs"].get(key)
    if a.get("skipped") or not b or b.get("skipped"): continue
    tokcmp["docs"] += 1
    tokcmp["restored_equal_przed_po"] = tokcmp.get("restored_equal_przed_po", 0) + (a["rest"] == b["rest"])
    if a["rest"] != b["rest"]: tokcmp.setdefault("restored_differ_docs", []).append(key)
    if a["tokens"] == b["tokens"]: tokcmp["identical"] += 1
    else:
        tokcmp["differ"] += 1
        ma = {t[0]: t[2] for t in a["tokens"]}; mb = {t[0]: t[2] for t in b["tokens"]}
        ch = [[k2, ma.get(k2), mb.get(k2)] for k2 in sorted(set(ma) | set(mb)) if ma.get(k2) != mb.get(k2)]
        tokcmp["differ_examples"].append([key, ch[:6], len(ch)])
for nm in ("przed", "po"):
    tokcmp["restore_bad_" + nm] = sum(len(s["restore_bad"]) for s in A[nm]["sets"].values())
    tokcmp["coll_" + nm] = sum(len(s["collisions"]) for s in A[nm]["sets"].values())
    tokcmp["restore_bad_list_" + nm] = [x for s in A[nm]["sets"].values() for x in s["restore_bad"]][:20]
    tokcmp["coll_list_" + nm] = [x for s in A[nm]["sets"].values() for x in s["collisions"]][:20]
slim = {k: {kk: vv for kk, vv in v.items() if kk != "docs"} for k, v in A.items()}
cel = {k.split("/")[1]: {"przed": A["przed"]["docs"][k].get("prev"), "po": A["po"]["docs"][k].get("prev")} for k in A["po"]["docs"] if k.startswith("cel/")}
json.dump(dict(przed=slim["przed"], po=slim["po"], timing_repeat=timing, diffs=diffs, przywroc=tokcmp, cel=cel), open(D / "wynik.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
order = ["nowy wyciek (OSOBA)", "nowy wyciek (firma)", "zmiana blokady Guard", "nowy FP FIRMA", "nowy FP OSOBA", "zmiana granic/tokenu", "usunięty FP FIRMA", "usunięty FP OSOBA", "naprawiony wyciek (firma)", "naprawiony wyciek (OSOBA)"]
COL = {"nowy wyciek (OSOBA)": "#c00", "nowy wyciek (firma)": "#c00", "zmiana blokady Guard": "#c00", "nowy FP FIRMA": "#d60", "nowy FP OSOBA": "#d60", "zmiana granic/tokenu": "#888"}
def regions(pa, pb):
    la, lb = pa.split("\n"), pb.split("\n"); out = []
    sm = difflib.SequenceMatcher(None, la, lb, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal": continue
        x, y = "\n".join(la[i1:i2]), "\n".join(lb[j1:j2])
        n = 0
        while n < min(len(x), len(y)) and x[n] == y[n]: n += 1
        m = 0
        while m < min(len(x), len(y)) - n and x[-1 - m] == y[-1 - m]: m += 1
        def frag(t):
            s0 = max(0, n - 60); e0 = len(t) - m + 60
            return ("…" if s0 else "") + t[s0:e0] + ("…" if e0 < len(t) else "")
        out.append((frag(x), frag(y)))
    return out
byk = collections.defaultdict(list)
for d in diffs: byk[d["key"]].append(d)
def prio(key): return min(order.index(d["klasa"]) if d["klasa"] in order else 99 for d in byk[key])
cnt = collections.Counter(d["klasa"] for d in diffs)
h = ["<!doctype html><meta charset='utf-8'><title>PRZED/PO FIRMA-FILTER-FIX</title><style>body{font:14px Segoe UI,sans-serif;margin:16px;max-width:1300px}.d{border:1px solid #ccc;margin:10px 0;padding:8px;border-radius:6px}.b{display:inline-block;color:#fff;padding:1px 7px;border-radius:9px;margin-right:6px;font-size:12px}pre{white-space:pre-wrap;margin:2px 0;background:#f6f6f6;padding:4px}table{width:100%}td{vertical-align:top;width:50%}.p{background:#fee}.o{background:#efe}</style>"]
h.append(f"<h2>PRZED (main {A['przed']['sha'][:8]}) vs PO ({A['po']['sha'][:8]}) - dokumenty z różnicą: {len(byk)}</h2><p>Kolejność: nowe wycieki, nowe FP, zmiany granic, usunięte FP, naprawy. Fragmenty podglądu zanonimizowanego (±60 znaków).</p>")
h.append("<p>" + "; ".join(f"{k}: {v}" for k, v in sorted(cnt.items())) + "</p>")
for key in sorted(byk, key=lambda k: (prio(k), k)):
    a, b = A["przed"]["docs"].get(key, {}), A["po"]["docs"].get(key, {})
    h.append(f"<div class='d'><b>{html.escape(key)}</b><br>")
    for d in byk[key]: h.append(f"<span class='b' style='background:{COL.get(d['klasa'], '#27a')}'>{html.escape(d['klasa'])}</span>{html.escape(str(d['wartosc']))} <i>{html.escape(str(d['typ']))}</i><br>")
    if a.get("prev") is not None and b.get("prev") is not None:
        for fx, fy in regions(a["prev"], b["prev"])[:6]:
            h.append(f"<table><tr><td><small>PRZED</small><pre class='p'>{html.escape(fx)}</pre></td><td><small>PO</small><pre class='o'>{html.escape(fy)}</pre></td></tr></table>")
    h.append("</div>")
(D / "porownanie.html").write_text("".join(h), encoding="utf-8")
for nm in ("przed", "po"):
    print("=====", nm, A[nm]["sha"][:8], "import", A[nm]["import_secs"], "startup", A[nm]["startup_secs"], "wall", round(A[nm]["wall"]))
    for s, v in A[nm]["sets"].items():
        print(s, {k: v[k] for k in ("docs", "firma_gold", "docs_leak", "tok_tp", "tok_T", "tok_fp", "pattern_nazwa_sp", "os_gold", "os_tok_tp", "os_tok_fp", "median_preview_s")}, "blocked", len(v["guard_blocked"]), "skipped", len(v["skipped"]))
print("timing_repeat", timing)
print("przywroc", {k: v for k, v in tokcmp.items() if k != "differ_examples"})
print("diff classes", dict(cnt))
