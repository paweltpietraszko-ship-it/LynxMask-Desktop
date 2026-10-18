# Blokada plików-olbrzymów (Paweł 2026-10-18): plik kodu ponad LIMIT linii nie może urosnąć.
# Nowa logika → nowy mały moduł, w dużym pliku tylko import. Zmniejszanie i zamiana 1:1 zawsze dozwolone.
# Dwa tryby, ta sama reguła:
#   --staged  git pre-commit (.githooks/pre-commit) — twarda blokada dla każdego narzędzia i każdego agenta;
#   --claude  hook PreToolUse Claude Code (.claude/settings.json) — zatrzymuje Edit/Write zanim kod powstanie.
# Bez wyjątków i bez przełącznika: zgoda na wzrost dużego pliku nie istnieje w tym mechanizmie.
import json
import subprocess
import sys
from pathlib import Path

LIMIT = 600
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs"}
MSG = ("BLOKADA ROZMIARU: {path} miałby {new} linii (limit {limit}, teraz {old}). "
       "Nie dopisuj do dużego pliku — nową logikę umieść w NOWYM małym module, tutaj tylko import/wywołanie.")


def _lines(text):
    return len(text.splitlines())


def _violation(path, old, new):
    if Path(path).suffix.lower() in CODE_EXT and new > LIMIT and new > old:
        return MSG.format(path=path, new=new, old=old, limit=LIMIT)
    return None


def _git_text(spec):
    r = subprocess.run(["git", "show", spec], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def check_staged():
    names = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
                           capture_output=True, text=True, check=True).stdout.split()
    errors = [e for p in names if (e := _violation(p, _lines(_git_text(f"HEAD:{p}")), _lines(_git_text(f":{p}"))))]
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


def _after_edit(current, inp):
    edits = inp.get("edits") or [inp]
    text = current
    for e in edits:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def check_claude():
    data = json.load(sys.stdin)
    inp = data.get("tool_input") or {}
    path = inp.get("file_path", "")
    if not path:
        return 0
    p = Path(path)
    current = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    after = inp["content"] if data.get("tool_name") == "Write" else _after_edit(current, inp)
    err = _violation(path, _lines(current), _lines(after))
    if err:
        print(err, file=sys.stderr)
        return 2  # Claude Code: exit 2 = narzędzie zablokowane, stderr wraca do modelu
    return 0


if __name__ == "__main__":
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(check_staged() if "--staged" in sys.argv else check_claude())
