# LYNX-NEWLINE-CROSSING r2: JEDNA wartość przełamana nową linią (OCR) w każdym możliwym miejscu odstępu/separatora — baza vs bieżący,
# oba tryby, NER wyłączony, dane syntetyczne. Uruchom z backend/. Wyciek = grupa ≥3 cyfr / fragment lokalnej części jawny w wyniku.
import contextlib, io, json, os, re, subprocess, sys, tempfile
from unittest.mock import patch
BASE = "cbfa3c17a95486194bd38bceab1a88bffc44f023"
sys.path[:0] = [".", "../audyt"]
VALUES = ["512 987 654", "Tel. 512 987 654", "+48 512 987 654", "526-000-12-46", "NIP 526-000-12-46", "44051401359",
          "PESEL 44051401359", "PL61 1090 1014 0000 0712 1981 2874", "jan.kowalski@example.pl"]

def cases():
    out = []
    for v in VALUES:
        for i, ch in enumerate(v):
            if ch in " -@" and 0 < i < len(v) - 1:
                out.append(f"Dane: {v[:i]}\n{v[i + 1:] if ch == ' ' else v[i:] if ch == '@' else v[i + 1:]} koniec." if ch != "-" else f"Dane: {v[:i + 1]}\n{v[i + 1:]} koniec.")
        out.append(f"Dane: {v} koniec.")
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
    body = case.split("Dane: ")[1].rsplit(" koniec.", 1)[0]
    frags = [f for f in re.findall(r"[0-9]{3,}|[a-z]{4,}", body) if f not in ("example", "koniec")]
    return any(f in out for f in frags)

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
    reg = [k for k in new if not leak(c(k), old[k]) and leak(c(k), new[k])]
    fixed = [k for k in new if leak(c(k), old[k]) and not leak(c(k), new[k])]
    still = [k for k in new if leak(c(k), new[k])]
    print(f"przypadków {len(new)}: regresje {len(reg)}, naprawione {len(fixed)}, nadal wyciek {len(still)}")
    for k in (reg + still)[:12]:
        print("  ", "REG" if k in reg else "OLD", repr(k), "->", repr(new[k]))
