# LYNX-EMAIL-LOCALPART-OCR: przegląd wariantów e-maila, stary kod (BASE) vs bieżący, oba tryby, NER wyłączony. Dane syntetyczne.
# Uruchom z backend/. Wyciek = fragment lokalnej części (≥3 znaki) jawny w wyniku; „po” = tekst za adresem musi zostać bez zmian.
import contextlib, io, itertools, json, os, re, subprocess, sys, tempfile
from unittest.mock import patch
BASE = "5dd5c6ece1ebb511695c763524d5193f00a2b944"
sys.path[:0] = [".", "../audyt"]
LOCALS = ["anna. nowak", "anna.nowak", "a. nowak", "anna. nowak.k", "ANNA. NOWAK", "Anna. Nowak", "anna.  nowak", "anna.   nowak",
          "anna.\tnowak", "jan_k. nowak", "anna. nowak_2"]  # kontrakt: brief §OWNER_ACCEPTED (1–3 odstępy, dowolna wielkość liter)
BEFORE = ["Kontakt: ", "Kontakt. ", "Podpisano. ", "dane. ", ""]
ATS = ["@", " @", "@ "]
DOMS = ["example.pl", "wp. pl"]
AFTER = [". Termin płatności.", " dalej", "\nKolejna linia."]

def cases():
    return [f"{b}{l}{a}{d}{f}" for b, l, a, d, f in itertools.product(BEFORE, LOCALS, ATS, DOMS, AFTER)]

def run_all(cs):
    import layers.ner_adapter as na
    from pipeline_new import run_pipeline_new, run_pipeline_express
    out = {}
    for c in cs:
        for name, fn in (("full", run_pipeline_new), ("expr", run_pipeline_express)):
            with patch.object(na, "process_ner", return_value=({}, {})), contextlib.redirect_stdout(io.StringIO()):
                out[f"{c}|{name}"] = fn(c, anon_map={})[0]
    return out

def leak(case, out):
    local = next(l for l in LOCALS if l in case)
    return any(w in out for w in re.findall(r"[A-Za-z0-9_]{3,}", local))

def after_ok(case, out):
    return out.endswith(next(f for f in AFTER if case.endswith(f)))

if __name__ == "__main__":
    cs = cases()
    if sys.argv[1:] == ["--child"]:
        print(json.dumps(run_all(cs))); sys.exit()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "worktree", "add", "-q", "--detach", tmp, BASE], check=True)
        try:
            old = json.loads(subprocess.run([sys.executable, "-W", "ignore", os.path.abspath(__file__), "--child"], cwd=os.path.join(tmp, "backend"),
                                            capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout.splitlines()[-1])
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", tmp], check=True)
    new = run_all(cs)
    c = lambda k: k.rsplit("|", 1)[0]
    reg = [k for k in new if (not leak(c(k), old[k]) and leak(c(k), new[k])) or (after_ok(c(k), old[k]) and not after_ok(c(k), new[k]))]
    fixed = [k for k in new if leak(c(k), old[k]) and not leak(c(k), new[k])]
    still = [k for k in new if leak(c(k), new[k])]
    print(f"przypadków {len(new)}: regresje {len(reg)}, naprawione {len(fixed)}, nadal jawny fragment {len(still)}, "
          f"zmieniony tekst za adresem {sum(not after_ok(c(k), new[k]) for k in new)}")
    for k in (reg + still)[:15]:
        print("  ", "REG" if k in reg else "OLD", repr(k), "->", repr(new[k]))
