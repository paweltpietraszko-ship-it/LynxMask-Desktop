# tests/test_smoke_e2e.py v1.0
"""
Smoke E2E — łączy warstwy, które reszta testów sprawdza osobno.

Ścieżki:
  1. Tekst → POST /preview → POST /archive → depseudo (bez OCR, pełny backend HTTP)
  2. dataset_real → ekstrakcja/OCR → /preview → brak wycieku encji krytycznych (GT)
  3. dataset_real (pierwszy plik) → /preview → /archive → depseudo

Dataset realny (opcjonalny — testy 2–3 skip gdy pusty):
  backend/dataset_real/ground_truth.json
  backend/dataset_real/images/*.jpg|png|pdf

Format ground_truth.json — jak w benchmark.py (tablica obiektów z polem entities).

Uruchomienie:
  python -m pytest tests/test_smoke_e2e.py -v
  (backend musi działać na 127.0.0.1:8765 — run_tests.bat sprawdza health)
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmark import analyze  # noqa: E402 — ta sama logika co benchmark

BACKEND_URL = "http://127.0.0.1:8765"
PREVIEW_URL = f"{BACKEND_URL}/preview"
TIMEOUT_S = 120

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BACKEND_DIR / "dataset_real"
GT_PATH = DATASET_DIR / "ground_truth.json"
TOKEN_PATH = BACKEND_DIR / "api_token.txt"

TOKEN_RE = re.compile(r"\b[A-Z][A-Z_]+_\d{3}\b")


def _auth_headers() -> dict[str, str]:
    try:
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {}
    return {"X-Api-Token": token} if token else {}


def _load_real_docs() -> list[tuple[dict[str, Any], Path]]:
    if not GT_PATH.exists():
        return []
    try:
        entries: list[dict[str, Any]] = json.loads(GT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(entries, list):
        return []

    docs: list[tuple[dict[str, Any], Path]] = []
    for entry in entries:
        if not isinstance(entry, dict) or "file" not in entry:
            continue
        rel = Path(entry["file"])
        candidates = [
            DATASET_DIR / rel,
            DATASET_DIR / "images" / rel.name,
            BACKEND_DIR / rel,
        ]
        img_path = next((p for p in candidates if p.is_file()), None)
        if img_path is not None:
            docs.append((entry, img_path))
    return docs


REAL_DOCS = _load_real_docs()


def _post_preview_bytes(data: bytes, filename: str, mime: str) -> tuple[dict[str, Any], int]:
    r = requests.post(
        PREVIEW_URL,
        files={"file": (filename, data, mime)},
        headers=_auth_headers(),
        timeout=TIMEOUT_S,
    )
    try:
        body = r.json()
    except Exception:
        body = {"error": f"Nie-JSON (HTTP {r.status_code})"}
    return body, r.status_code


def post_preview_text(text: str, filename: str = "smoke_e2e.txt") -> tuple[dict[str, Any], int]:
    return _post_preview_bytes(text.encode("utf-8"), filename, "text/plain")


def post_preview_file(path: Path) -> tuple[dict[str, Any], int]:
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        mime = "application/octet-stream"
    return _post_preview_bytes(path.read_bytes(), path.name, mime)


def depseudo_local(text: str, tokens: list[dict[str, Any]]) -> str:
    token_map = {t["token"]: t["original"] for t in tokens if t.get("token")}
    return TOKEN_RE.sub(lambda m: token_map.get(m.group(0), m.group(0)), text)


def save_archive(pse: str, tokens: list[dict], anon_text: str, guard_blocked: bool = False) -> bool:
    blob = json.dumps({"tokens": tokens, "anonymized_preview": anon_text}, ensure_ascii=False)
    enc_blob = base64.b64encode(blob.encode("utf-8")).decode("ascii")
    desc = base64.b64encode(b"smoke_e2e").decode("ascii")
    r = requests.post(
        f"{BACKEND_URL}/archive",
        headers=_auth_headers(),
        json={
            "pse": pse,
            "token_count": len(tokens),
            "enc_blob": enc_blob,
            "description": desc,
            "guard_blocked": guard_blocked,
        },
        timeout=30,
    )
    if not r.ok:
        return False
    return bool(r.json().get("ok"))


def delete_archive(pse: str) -> None:
    try:
        requests.delete(
            f"{BACKEND_URL}/archive/{pse}",
            headers=_auth_headers(),
            timeout=10,
        )
    except Exception:
        pass


def _assert_preview_ok(body: dict[str, Any], http_status: int, label: str) -> None:
    assert http_status == 200, f"{label}: HTTP {http_status}, body={body!r}"
    assert not body.get("error"), f"{label}: error={body.get('error')!r}"
    assert body.get("ocr_rejected") is not True, (
        f"{label}: OCR odrzucony (conf={body.get('ocr', {}).get('confidence')}) — "
        "dodaj lepsze zdjęcie albo oznacz w GT jako oczekiwany reject"
    )
    assert body.get("blocked") is not True, (
        f"{label}: Guard zablokował — {body.get('guard_reasons')}"
    )


def _assert_no_critical_leaks(gt_entry: dict[str, Any], body: dict[str, Any], label: str) -> None:
    report = analyze(gt_entry, body)
    missed = report["summary"].get("critical_missed", 0)
    if missed:
        leaks = [
            e["value"]
            for e in report["entities"]
            if e.get("critical") and not e.get("privacy_found")
        ]
        pytest.fail(f"{label}: wyciek encji krytycznych ({missed}): {leaks[:5]}")


@pytest.fixture(scope="module")
def require_backend() -> None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", headers=_auth_headers(), timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"Backend niedostępny: {exc}")
    if not r.ok:
        pytest.skip(f"Backend health HTTP {r.status_code}")


class TestSmokeTextPath:
    """Tekst → preview → archiwum → depseudo (bez OCR, pełny HTTP backend)."""

    def test_e2e_text_preview_archive_depseudo(self, require_backend: None) -> None:
        original = (
            "Jan Kowalski, PESEL 92081512345, NIP 526-285-30-52, "
            "ul. Zielona 1, 65-001 Zielona Góra, jan@test.pl"
        )
        body, status = post_preview_text(original)
        _assert_preview_ok(body, status, "tekst/preview")

        anon = body.get("anonymized_preview", "")
        tokens = body.get("tokens", [])
        pse = body.get("pse_code", "")
        assert pse, "Brak pse_code w odpowiedzi /preview"
        assert tokens, "Brak tokenów — silnik nic nie wykrył"

        for fragment in ("92081512345", "5262853052", "Jan Kowalski", "jan@test.pl"):
            assert fragment.lower() not in anon.lower(), f"Wyciek w preview: {fragment!r}"

        assert save_archive(pse, tokens, anon), f"Zapis /archive nieudany dla {pse}"
        try:
            restored = depseudo_local(anon, tokens)
            for token in tokens:
                orig = token.get("original", "")
                if len(orig) < 4:
                    continue
                assert orig.lower() in restored.lower(), f"Depseudo: brak {orig[:40]!r}"
            leftover = TOKEN_RE.findall(restored)
            assert not leftover, f"Nieodtworzone tokeny: {leftover}"
        finally:
            delete_archive(pse)


@pytest.mark.skipif(
    not REAL_DOCS,
    reason="dataset_real pusty — dodaj ground_truth.json + pliki w dataset_real/images/",
)
class TestSmokeRealDataset:
    """Realne zdjęcia/PDF — OCR/ekstrakcja → preview → GT (regresja produktowa)."""

    @pytest.mark.parametrize(
        "gt_entry,img_path",
        REAL_DOCS,
        ids=[p.name for _, p in REAL_DOCS],
    )
    def test_e2e_real_file_no_critical_leak(
        self,
        require_backend: None,
        gt_entry: dict[str, Any],
        img_path: Path,
    ) -> None:
        body, status = post_preview_file(img_path)
        label = img_path.name

        if status == 422 and body.get("ocr_rejected"):
            pytest.skip(f"{label}: OCR reject — oczekiwane dla słabego zdjęcia")

        _assert_preview_ok(body, status, label)
        entities = gt_entry.get("entities") or {}
        if not entities:
            pytest.skip(f"{label}: brak entities w GT — uzupełnij ground_truth.json")

        _assert_no_critical_leaks(gt_entry, body, label)

    def test_e2e_real_file_archive_roundtrip(self, require_backend: None) -> None:
        gt_entry, img_path = REAL_DOCS[0]
        body, status = post_preview_file(img_path)
        label = img_path.name

        if status == 422 and body.get("ocr_rejected"):
            pytest.skip(f"{label}: OCR reject — pomijam roundtrip archiwum")

        _assert_preview_ok(body, status, label)

        tokens = body.get("tokens", [])
        pse = body.get("pse_code", "")
        anon = body.get("anonymized_preview", "")
        assert pse and tokens, f"{label}: brak pse/tokens po preview"

        assert save_archive(pse, tokens, anon), f"Zapis archiwum nieudany: {pse}"
        try:
            restored = depseudo_local(anon, tokens)
            for token in tokens[:5]:
                orig = token.get("original", "")
                if len(orig) >= 4:
                    assert orig.lower() in restored.lower(), f"Depseudo: brak {orig[:40]!r}"
        finally:
            delete_archive(pse)

        if gt_entry.get("entities"):
            _assert_no_critical_leaks(gt_entry, body, label)
