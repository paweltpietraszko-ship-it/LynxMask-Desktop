"""Widok człowieka na zbiorze LYNX-GOLD-SET: silnik + Guard z podanej wersji kodu → porównanie z ground truth.

Użycie: python human_view.py <katalog_backend_kodu> <dataset_dir> <split: dev|test|all> <out_dir>
Wynik: <out_dir>/summary.json (agregaty), <out_dir>/views/<split>_<doc>.txt (to, co widzi człowiek: tekst + ostrzeżenia),
       <out_dir>/items_dev.jsonl (pozycje tylko z części dev — część test wyłącznie w agregatach).
Status pozycji pii: zakryte | wyciek_z_ostrzezeniem | cichy_wyciek (jawny ciąg ≥3 znaków liter/cyfr bez ostrzeżenia Guarda).
not_pii: zbedne_zakrycie, gdy jego litery/cyfry trafiły pod token.
"""
import difflib
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict

src, data, split, out = sys.argv[1:5]
os.makedirs(os.path.join(out, "views"), exist_ok=True)
prof = tempfile.mkdtemp(prefix="hv_profile_")
os.environ["PROFILE_DIR"] = prof
os.chdir(src)
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
import spacy_ner  # noqa: E402
from anonymizer import build_anonymizer  # noqa: E402
from pipeline import AppState, pseudonymize_document  # noqa: E402

TOKEN = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")
ALNUM = re.compile(r"[^\W_]{3,}")


def state():
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="hv_", dir=prof)
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
    return st


def char_map(orig: str, outt: str):
    """Dla każdego znaku oryginału: ('plain', pozycja_w_wyniku) albo ('masked', None). Tokeny są niepodzielne:
    jawne odcinki wyniku szukamy kolejno w oryginale; tekst oryginału między nimi, gdy w wyniku stał tam token, jest zakryty.
    Odcinek niedopasowany dokładnie (normalizacja OCR/cudzysłowów) dopasowujemy lokalnie znak po znaku (difflib bez tokenów)."""
    res = [("plain", 0)] * len(orig)
    cur, pending = 0, False
    pos = 0
    for m in list(TOKEN.finditer(outt)) + [None]:
        seg_end = m.start() if m else len(outt)
        seg = outt[pos:seg_end]
        if seg:
            idx = orig.find(seg, cur)
            if idx < 0 and len(seg) > 12:
                head = orig.find(seg[:12], cur)
                idx = head
            if idx < 0:  # odcinek zmieniony normalizacją: dopasuj lokalnie do najbliższego okna
                win = orig[cur:cur + len(seg) + 40]
                sm = difflib.SequenceMatcher(None, win, seg, autojunk=False)
                blocks = [b for b in sm.get_matching_blocks() if b.size]
                idx = cur + (blocks[0].a - blocks[0].b if blocks else 0)
                idx = max(cur, idx)
            gap_state = "masked" if pending else "plain"
            for k in range(cur, idx):
                res[k] = (gap_state, None if pending else pos)
            for k in range(len(seg)):
                if idx + k < len(orig):
                    res[idx + k] = ("plain", pos + k)
            cur = min(len(orig), idx + len(seg))
            pending = False
        if m:
            pending = True
            pos = m.end()
    if pending:
        for k in range(cur, len(orig)):
            res[k] = ("masked", None)
    return res


def evaluate(orig, gold, outt, warns):
    cm = char_map(orig, outt)
    wspans = [(w["start"], w["end"]) for w in warns]
    items = []
    for it in gold["pii"]:
        s, e = it["start"], it["end"]
        plain_runs = []
        for m in ALNUM.finditer(orig, s, e):
            pos = [cm[k] for k in range(m.start(), m.end())]
            if all(p[0] == "plain" for p in pos):
                plain_runs.append((pos[0][1], pos[-1][1] + 1, m.group(0)))
        if not plain_runs and it["type"] == "NUMER":  # krótkie numery: każda jawna cyfra ≥2 z rzędu
            for m in re.finditer(r"\d{2,}", orig[s:e]):
                pos = [cm[k] for k in range(s + m.start(), s + m.end())]
                if all(p[0] == "plain" for p in pos):
                    plain_runs.append((pos[0][1], pos[-1][1] + 1, m.group(0)))
        if not plain_runs:
            st = "zakryte"
        elif all(any(ws < re_ and rs < we for ws, we in wspans) for rs, re_, _ in plain_runs):
            st = "wyciek_z_ostrzezeniem"
        else:
            st = "cichy_wyciek"
        items.append({"kind": "pii", "type": it["type"], "rodo": it.get("rodo", True), "text": it["text"], "status": st,
                      "plain": [r[2] for r in plain_runs]})
    for it in gold.get("not_pii", []):
        s, e = it["start"], it["end"]
        masked = any(cm[k][0] == "masked" for m in ALNUM.finditer(orig, s, e) for k in range(m.start(), m.end()))
        items.append({"kind": "not_pii", "why": it.get("why"), "text": it["text"], "status": "zbedne_zakrycie" if masked else "ok"})
    return items


splits = ["dev", "test"] if split == "all" else [split]
summary = {}
for sp in splits:
    agg = Counter()
    by_type = defaultdict(Counter)
    warn_counts = []
    dev_items = []
    for fn in sorted(f for f in os.listdir(os.path.join(data, sp)) if f.endswith(".txt")):
        doc = fn[:-4]
        orig = open(os.path.join(data, sp, fn), encoding="utf-8").read()
        gold = json.load(open(os.path.join(data, sp, doc + ".json"), encoding="utf-8"))
        r = pseudonymize_document(orig, state())
        if r.error:
            agg["blad_silnika"] += 1
            continue
        warns = r.guard_warnings
        warn_counts.append(len(warns))
        items = evaluate(orig, gold, r.text, warns)
        for it in items:
            agg[it["kind"] + ":" + it["status"]] += 1
            if it["kind"] == "pii":
                by_type[it["type"] + (":rodo" if it["rodo"] else ":nierodo")][it["status"]] += 1
        view = r.text + "\n\n=== OSTRZEŻENIA GUARDA ===\n" + "\n".join(
            f"{w['level']} {'+'.join(w['rules'])}: {w['fragment']}" for w in warns)
        open(os.path.join(out, "views", f"{sp}_{doc}.txt"), "w", encoding="utf-8").write(view)
        if sp == "dev":
            dev_items += [{"doc": doc, **it} for it in items if it["status"] != "zakryte" and it["status"] != "ok"]
    n = len(warn_counts)
    warn_counts.sort()
    summary[sp] = {"docs": n, "pozycje": dict(agg), "wg_typu": {k: dict(v) for k, v in sorted(by_type.items())},
                   "ostrzezenia_na_dok": {"sr": round(sum(warn_counts) / max(n, 1), 2),
                                          "mediana": warn_counts[n // 2] if n else 0, "max": warn_counts[-1] if n else 0}}
    if sp == "dev":
        with open(os.path.join(out, "items_dev.jsonl"), "w", encoding="utf-8") as f:
            for it in dev_items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
json.dump(summary, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for sp, s in summary.items():
    p = s["pozycje"]
    tot = sum(v for k, v in p.items() if k.startswith("pii:"))
    print(f"[{sp}] dok={s['docs']} pii={tot} zakryte={p.get('pii:zakryte', 0)} z_ostrz={p.get('pii:wyciek_z_ostrzezeniem', 0)} "
          f"CICHE={p.get('pii:cichy_wyciek', 0)} | not_pii zbędne={p.get('not_pii:zbedne_zakrycie', 0)}/"
          f"{p.get('not_pii:zbedne_zakrycie', 0) + p.get('not_pii:ok', 0)} | ostrz/dok {s['ostrzezenia_na_dok']}")
    for t, c in s["wg_typu"].items():
        print(f"    {t}: {dict(c)}")
