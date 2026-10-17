# LYNX-T07: przegląd rodziny numerów, stary kod (BASE) vs bieżący, oba tryby, NER wyłączony. Dane syntetyczne.
# Uruchom z backend/: py -3 ../tasks/LYNX-T07-IBAN-RECEPTA/round_01/implementation/number_sweep.py
# Wyciek = grupa ≥4 cyfr z wartości jawna w wyniku. Regresja = przed: bez wycieku, po: wyciek.
import contextlib, io, itertools, os, subprocess, sys, tempfile
from unittest.mock import patch
BASE = "7c6475e579ea9306eab2968520a19abf534b3d1f"
sys.path[:0] = [".", "../audyt"]

def run_all(cases):
    import layers.ner_adapter as na
    from pipeline_new import run_pipeline_new, run_pipeline_express
    res = {}
    for c in cases:
        for name, fn in (("full", run_pipeline_new), ("expr", run_pipeline_express)):
            with patch.object(na, "process_ner", return_value=({}, {})), contextlib.redirect_stdout(io.StringIO()):
                res[(c, name)] = fn(c, anon_map={})[0]
    return res

def cases():
    digits = "611090101400000712198128743456"
    out = []
    for n, sep, label, cc in itertools.product([8, 11, 15, 22, 26, 30], ["", " ", "-", "  ", "	", " 	"], ["", "Konto ", "Nr ", "tel. ", "numer recepty: "], ["", "PL"]):
        d = digits[:n]
        val = sep.join(d[i:i + 4] for i in range(0, n, 4)) if sep else d
        out.append(f"Dane: {label}{cc}{val}. Dalej tekst.")
    out += [f"Dane: {d}, ref 12345678. Dalej tekst." for d in ("123456789012345", "123 456 789 012 345")]  # r3 F1: krótki po długim
    return out

def leaks(text, out):
    val = text.split("Dane: ")[1].split(". Dalej")[0]
    return any(g in out for g in [val[i:i + 4] for i in range(len(val) - 3) if val[i:i + 4].isdigit()])

if __name__ == "__main__":
    cs = cases()
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        import json; print(json.dumps({f"{k[0]}|{k[1]}": v for k, v in run_all(cs).items()})); sys.exit()
    import json
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "worktree", "add", "-q", "--detach", tmp, BASE], check=True)
        try:
            old = json.loads(subprocess.run([sys.executable, "-W", "ignore", os.path.abspath(__file__), "--child"], cwd=os.path.join(tmp, "backend"),
                                            capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout.splitlines()[-1])
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", tmp], check=True)
    new = {f"{k[0]}|{k[1]}": v for k, v in run_all(cs).items()}
    reg = [k for k in new if not leaks(k.split("|")[0], old[k]) and leaks(k.split("|")[0], new[k])]
    fixed = [k for k in new if leaks(k.split("|")[0], old[k]) and not leaks(k.split("|")[0], new[k])]
    still = [k for k in new if leaks(k.split("|")[0], new[k])]
    tail = [k for k in new if not new[k].endswith(". Dalej tekst.")]
    print(f"przypadków {len(new)}: regresje {len(reg)}, naprawione {len(fixed)}, nadal wyciek {len(still)}, zmieniony tekst po numerze {len(tail)}")
    for k in (reg + still)[:12]:
        print("  ", "REG" if k in reg else "OLD", repr(k), "->", repr(new[k]))
