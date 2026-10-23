"""Diagnoza szumu R1: dla każdego ostrzeżenia R1 — która gałąź reguły zadziałała, cechy kontekstu, czy fragment jest osobą z gold.
Użycie: python r1_diag.py <src_backend> <jobs.json>[,<jobs2.json>] <out_dir>
Fragmenty zapisywane tylko dla dokumentów nieprywatnych (private=False); dla prywatnych wyłącznie liczby."""
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

src, jobs_arg, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACT = r"C:\Users\p_pie\AppData\Local\Temp\lynx_cc_review\status_2210\extract_one.py"
PY = sys.executable
prof = tempfile.mkdtemp(prefix="r1_profile_")
os.environ["PROFILE_DIR"] = prof
os.environ["ANONYMIZER_PROFILE_DIR"] = os.path.join(prof, "anon")
os.chdir(src)
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
import guard_residue as gr  # noqa: E402
import spacy_ner  # noqa: E402
from anonymizer import build_anonymizer  # noqa: E402
from osoba_not_person import _common_or_person  # noqa: E402
from pipeline import AppState, pseudonymize_document  # noqa: E402

CACHE = os.path.join(HERE, "text_cache")
os.makedirs(CACHE, exist_ok=True)


def text_of(path):
    key = re.sub(r"[^\w.]", "_", path)[-150:] + ".json"
    c = os.path.join(CACHE, key)
    if not os.path.exists(c):
        if path.lower().endswith((".txt", ".md")):
            json.dump({"text": open(path, encoding="utf-8", errors="replace").read(), "err": None}, open(c, "w", encoding="utf-8"))
        else:
            subprocess.run([PY, EXTRACT, src, path, c], capture_output=True, timeout=300)
    try:
        d = json.load(open(c, encoding="utf-8"))
        return d.get("text") or ""
    except Exception:
        return ""


def branch(text, s, e):
    """Gałąź _person_word, która dała True."""
    m = re.match(r".+", text[s:e])
    word, low = m.group(0), m.group(0).lower()
    if gr._TITLE_BEFORE_RE.search(text[max(0, s - 8):s]):
        return "tytul"
    parts = [gr._morf_interps(w) for w in word.split("-")]
    if any(p is None for p in parts):
        return "morf_blad"
    quals = [{q.split("_(")[0] for i in p for q in i[2][3]} for p in parts]
    if quals[0] & {"imię", "nazwisko"}:
        common, _person, _geo = _common_or_person(word.split("-")[0])
        sub = "imie" if "imię" in quals[0] else "nazwisko"
        return f"{sub}+pospolite" if common else f"{sub}_tylko"
    if all(i[2][2] == "ign" for i in parts[0]):
        return "nieznane_koncowka"
    return "inne"


def ctx(text, s, e):
    line_s = text.rfind("\n", 0, s) + 1
    line_e = text.find("\n", e)
    line = text[line_s:line_e if line_e >= 0 else len(text)]
    letters = [c for c in line if c.isalpha()]
    caps_line = bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.6
    prev_cap = re.search(r"(?:^|[\s(„\"])([A-ZĄĆĘŁŃÓŚŹŻ][\w\-]+)[ \t]+$", text[max(0, s - 40):s]) is not None
    next_cap = re.match(r"[ \t]+[A-ZĄĆĘŁŃÓŚŹŻ][\w\-]+", text[e:e + 40]) is not None
    tok_near = re.search(r"OSOBA_\d{3}", text[max(0, s - 60):e + 60]) is not None
    return {"caps_line": caps_line, "prev_cap": prev_cap, "next_cap": next_cap, "osoba_obok": tok_near}


def gold_person_stems(fields):
    st = set()
    for typ, val in fields:
        if typ == "OSOBA":
            for w in re.findall(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]{3,}", val):
                st.add(w.lower()[:4])
    return st


jobs = []
for f in jobs_arg.split(","):
    jobs += json.load(open(f, encoding="utf-8"))

cnt = defaultdict(Counter)       # set -> kategoria
tp = defaultdict(Counter)        # set -> kategoria (fragment osobą z gold)
feat = defaultdict(Counter)      # kategoria -> cechy
frag = defaultdict(Counter)      # kategoria -> fragment (tylko publiczne)
docs = Counter()
for i, j in enumerate(jobs):
    text = text_of(j["path"])
    if not text.strip():
        continue
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    d = tempfile.mkdtemp(prefix="r1_", dir=prof)
    import contextlib, io  # noqa: E401
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, os.path.join(d, "hw.json"))
        try:
            r = pseudonymize_document(text, st)
        except Exception as ex:
            print("ERR", j["set"], type(ex).__name__, flush=True)
            continue
    docs[j["set"]] += 1
    stems = gold_person_stems(j.get("fields") or [])
    out_text = r.text
    for w in r.guard_warnings or []:
        if "R1" not in w["rules"]:
            continue
        s, e = w["start"], w["end"]
        released = any("nie miał dowodu" in x for x in w["reasons"])
        cat = "released" if released else branch(out_text, s, e)
        cnt[j["set"]][cat] += 1
        is_tp = w["fragment"].lower()[:4] in stems
        if is_tp:
            tp[j["set"]][cat] += 1
        for k, v in ctx(out_text, s, e).items():
            if v:
                feat[cat][k] += 1
        feat[cat]["_n"] += 1
        if not j.get("private"):
            frag[cat][w["fragment"]] += 1
    print(i, j["set"], sum(cnt[j["set"]].values()), flush=True)

res = {"docs": docs, "r1_wg_zbioru": cnt, "tp_wg_zbioru": tp, "cechy": feat,
       "top_fragmenty": {k: v.most_common(60) for k, v in frag.items()}}
json.dump(res, open(os.path.join(out, "r1_diag.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for s_, c in cnt.items():
    print(s_, docs[s_], "dok.", dict(c), "TP:", dict(tp[s_]))
