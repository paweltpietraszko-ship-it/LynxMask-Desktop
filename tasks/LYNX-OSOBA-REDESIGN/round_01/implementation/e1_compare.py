"""E1: ten sam kod, przełącznik LYNX_OSOBA_DECIDER off vs on, te same dokumenty. Słowa zakryte jako OSOBA (dodane/utracone) i pytania R1."""
import contextlib, io, json, os, re, sys, tempfile
from collections import Counter
src, cache, out = sys.argv[1:4]
prof = tempfile.mkdtemp(); os.environ["PROFILE_DIR"] = prof; os.environ["ANONYMIZER_PROFILE_DIR"] = prof + "/a"
os.chdir(src); sys.path.insert(0, "."); sys.stdout.reconfigure(encoding="utf-8")
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
W = re.compile(r"[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż-]{2,}")
def run(t, mode):
    os.environ["LYNX_OSOBA_DECIDER"] = mode
    st = AppState(); st.spacy_ner_mod = spacy_ner; d = tempfile.mkdtemp(dir=prof)
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(d, d + "/hw.json")
        r = pseudonymize_document(t, st)
    words = {w for k, v in r.reverse_map.items() if k.startswith("OSOBA") for w in W.findall(v)}
    r1 = [w["fragment"] for w in r.guard_warnings if "R1" in w["rules"]]
    return words, r1, len(r.guard_warnings)
res = {}; added = Counter(); lost = Counter(); r1o = r1n = go = gn = 0
for f in sorted(os.listdir(cache)):
    t = json.load(open(os.path.join(cache, f), encoding="utf-8")).get("text") or ""
    if not t.strip(): continue
    wo, ro, go1 = run(t, "off"); wn, rn, gn1 = run(t, "on")
    res[f] = {"added": sorted(wn - wo), "lost": sorted(wo - wn), "r1_off": len(ro), "r1_on": len(rn), "r1_on_frag": rn}
    added.update(wn - wo); lost.update(wo - wn); r1o += len(ro); r1n += len(rn); go += go1; gn += gn1
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("dok.", len(res), "| R1 off/on:", r1o, r1n, "| wszystkie ostrzeżenia off/on:", go, gn)
print("DODANE słowa OSOBA:", sum(added.values()), " | ".join(f"{w}:{n}" for w, n in added.most_common(80)))
print("UTRACONE słowa OSOBA:", sum(lost.values()), " | ".join(f"{w}:{n}" for w, n in lost.most_common(80)))
on_frag = Counter(x for v in res.values() for x in v["r1_on_frag"])
print("R1 (on) najczęstsze:", " | ".join(f"{w}:{n}" for w, n in on_frag.most_common(40)))
