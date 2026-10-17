# LYNX-IBAN-FOREIGN-ALNUM: przegląd IBAN (obce z literami/cyfrowe + PL), baza vs bieżący, oba tryby, NER wyłączony. Dane syntetyczne.
# Uruchom z backend/. Wyciek = człon ≥4 znaków IBAN jawny w wyniku; „po” = tekst za numerem bez zmian.
import contextlib, io, itertools, json, os, re, subprocess, sys, tempfile
from unittest.mock import patch
BASE = "0dd4bdc1e63cd72f36e6cc47525f54f67e53ada4"
sys.path[:0] = [".", "../audyt"]
IBANS = ["GB82 WEST 1234 5698 7654 32", "NL91 ABNA 0417 1643 00", "IT60 X054 2811 1010 0000 0123 456", "FR14 2004 1010 0505 0001 3M02 606",
         "DE89 3704 0044 0532 0130 00", "CH93 0076 2011 6238 5295 7", "PL61 1090 1014 0000 0712 1981 2874"]
LABELS = ["", "Konto: ", "IBAN: ", "Nr konta: ", "Przelew na "]
AFTER = [". Dalej.", " dziś", "\nKolejna linia."]

def cases():
    out = []
    for iban, compact, lab, aft in itertools.product(IBANS, [False, True], LABELS, AFTER):
        out.append(f"{lab}{iban.replace(' ', '') if compact else iban}{aft}")
    return out

def run_all(cs):
    import layers.ner_adapter as na
    from pipeline_new import run_pipeline_new, run_pipeline_express
    res = {}
    for c in cs:
        for name, fn in (("full", run_pipeline_new), ("expr", run_pipeline_express)):
            with patch.object(na, "process_ner", return_value=({}, {})), contextlib.redirect_stdout(io.StringIO()):
                res[f"{c}|{name}"] = fn(c, anon_map={})[0]
    return res

def leak(case, out):
    iban = next(i for i in IBANS if i in case or i.replace(" ", "") in case)
    flat = iban.replace(" ", "")
    return any(flat[k:k + 4] in out.replace(" ", "") for k in range(len(flat) - 3))

def after_ok(case, out):
    return out.endswith(next(a for a in AFTER if case.endswith(a)))

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
    print(f"przypadków {len(new)}: regresje {len(reg)}, naprawione {len(fixed)}, nadal wyciek {len(still)}, "
          f"zmieniony tekst po numerze {sum(not after_ok(c(k), new[k]) for k in new)}")
    for k in (reg + still)[:12]:
        print("  ", "REG" if k in reg else "OLD", repr(k), "->", repr(new[k]))
