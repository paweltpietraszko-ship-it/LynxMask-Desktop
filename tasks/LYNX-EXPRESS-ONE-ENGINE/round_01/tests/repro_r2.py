"""Independent HTTP audit reproducer; synthetic inputs only.

Run against audited backend on 8767, using an isolated synthetic profile.
Read full token only from this checkout. Never print tokens or response bodies.
"""
from pathlib import Path
import re

import requests

ROOT = "http://127.0.0.1:8767"
HOST = {"Host": "127.0.0.1:8765"}
assert requests.get(ROOT + "/health", headers=HOST, timeout=5).status_code == 200
FULL = (Path(__file__).resolve().parents[4] / "backend/api_token.txt").read_text().strip()
EXPR = requests.get(ROOT + "/express/token", headers=HOST, timeout=5).json()["token"]


def post(path, token, text):
    return requests.post(ROOT + path, headers={**HOST, "X-Api-Token": token},
                         files={"file": ("audit.txt", text.encode(), "text/plain")}, timeout=30)


def signature(response):
    data = response.json()
    # Session header changes on every request; contract compares document content.
    return (response.status_code, data.get("anonymized_preview", "").split("]\n\n", 1)[-1],
            data.get("tokens"), data.get("blocked"), data.get("guard_reasons"), data.get("error"))


DOCS = [
    "Pozew złożył Jan Kowalski, PESEL 44051401359. Kontakt: sekretariat@example.test.",
    "Termin składania ofert upływa w poniedziałek po południu.",
    "Numer konta: PL61 1090 1014 0000 0712 l981 2874, PESEL: 4405140l359.",
    "Pozwany OSOBA_001 otrzymał pismo.",
]
for index, text in enumerate(DOCS):
    full, expr = post("/preview", FULL, text), post("/preview", EXPR, text)
    assert signature(full) == signature(expr), ("different modes", index)
    if index == 0:
        assert "Kowalski" not in signature(expr)[1] and "44051401359" not in signature(expr)[1]
        assert any(token["type"] == "OSOBA" for token in expr.json()["tokens"])
    if index == 3:
        assert expr.status_code == 422
assert post("/preview-express", FULL, DOCS[0]).status_code == 404
assert post("/preview-express", EXPR, DOCS[0]).status_code == 401
schema = requests.get(ROOT + "/openapi.json", headers={**HOST, "X-Api-Token": FULL}, timeout=10).json()
checked = 0
for path, methods in schema["paths"].items():
    if path in ("/health", "/express/token", "/preview"):
        continue
    for method in methods:
        if method not in ("get", "post", "delete", "put", "patch"):
            continue
        target = re.sub(r"\{[^}]+\}", "audit-placeholder", path)
        response = requests.request(method, ROOT + target, headers={**HOST, "X-Api-Token": EXPR}, timeout=10)
        assert response.status_code == 401, (method, path, response.status_code)
        checked += 1
print("INDEPENDENT_HTTP: 4/4 comparisons; NER+PESEL masked; injection rejected; old route 404/401; denied:", checked)
