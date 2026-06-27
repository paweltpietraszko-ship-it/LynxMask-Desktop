# tests/test_smoke_e2e.py v1.2
"""
Smoke E2E — pełny HTTP backend, bez ground truth.

Ścieżki:
  1. Tekst syntetyczny → /preview → sprawdzenie braku wycieku (sanity check)
  2. Pliki testowe (Pliki testowe/*.txt) → /preview → raport wykrytych encji

Raport zapisywany do: benchmark_results/smoke/smoke_e2e_report.txt
Po uruchomieniu przejrzyj raport i powiedz co nie działa.

Uruchomienie:
  python -m pytest tests/test_smoke_e2e.py -v -s
  (backend musi działać na 127.0.0.1:8765)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BACKEND_URL = "http://127.0.0.1:8765"
PREVIEW_URL = f"{BACKEND_URL}/preview"
TIMEOUT_S   = 60

BACKEND_DIR   = Path(__file__).resolve().parent.parent
TEST_DOCS_DIR = BACKEND_DIR.parent / "Pliki testowe"
TOKEN_PATH    = BACKEND_DIR / "api_token.txt"
_SMOKE_DIR    = BACKEND_DIR / "benchmark_results" / "smoke"
REPORT_PATH   = _SMOKE_DIR / "smoke_e2e_report.txt"

TOKEN_RE = re.compile(r"\b(NUMER|EMAIL|ADRES|OSOBA|FIRMA|KWOTA|INSTYTUCJA)_\d{3}\b")

# Encje krytyczne — ich obecność w wyjściu = wyciek PII
_CRITICAL_PATTERNS = [
    re.compile(r"\b\d{11}\b"),
    re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b"),
    re.compile(r"\bPL\s*\d{2}[\s\d]{26,}\b"),
    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}"),
    re.compile(r"(?<![A-Za-z])[A-Z]{3}\s?\d{6}\b"),
    re.compile(r"\b[A-Z]{2}\s?\d{7}\b"),
]


def _auth_headers() -> dict[str, str]:
    try:
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
        return {"X-Api-Token": token} if token else {}
    except FileNotFoundError:
        return {}


def _preview_text(text: str, filename: str) -> tuple[dict[str, Any], int]:
    r = requests.post(
        PREVIEW_URL,
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
        headers=_auth_headers(),
        timeout=TIMEOUT_S,
    )
    try:
        body = r.json()
    except Exception:
        body = {"error": f"Nie-JSON (HTTP {r.status_code})"}
    return body, r.status_code


def _preview_file(path: Path) -> tuple[dict[str, Any], int]:
    import mimetypes
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    r = requests.post(
        PREVIEW_URL,
        files={"file": (path.name, path.read_bytes(), mime)},
        headers=_auth_headers(),
        timeout=TIMEOUT_S,
    )
    try:
        body = r.json()
    except Exception:
        body = {"error": f"Nie-JSON (HTTP {r.status_code})"}
    return body, r.status_code


def _check_critical_leaks(text: str) -> list[str]:
    return [m.group(0) for pat in _CRITICAL_PATTERNS for m in pat.finditer(text)]


def _token_summary(tokens: list[dict]) -> dict[str, list[str]]:
    by_type: dict[str, list[str]] = {}
    for t in tokens:
        tid   = t.get("token", "")
        orig  = t.get("original", tid)
        ttype = tid.split("_")[0] if "_" in tid else "?"
        by_type.setdefault(ttype, []).append(orig[:60])
    return by_type


@pytest.fixture(scope="module")
def require_backend() -> None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", headers=_auth_headers(), timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"Backend niedostępny: {exc}")
    if not r.ok:
        pytest.skip(f"Backend health HTTP {r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — syntetyczny tekst, sanity check
# ─────────────────────────────────────────────────────────────────────────────

class TestSmokeTextPath:
    """Tekst → /preview → sprawdzenie braku wycieku."""

    def test_e2e_text_basic(self, require_backend: None) -> None:
        original = (
            "Jan Kowalski, PESEL 92081512345, NIP 526-285-30-52, "
            "ul. Zielona 1, 65-001 Zielona Góra, jan@test.pl, "
            "IBAN: PL61 1090 1014 0000 0712 1981 2874"
        )
        body, status = _preview_text(original, "smoke_syntetyczny.txt")

        assert status == 200, f"HTTP {status}: {body}"
        assert not body.get("error"), f"error={body.get('error')!r}"

        anon   = body.get("anonymized_preview", "")
        tokens = body.get("tokens", [])

        assert tokens, "Silnik nie wykrył żadnych encji"
        leaks = _check_critical_leaks(anon)
        assert not leaks, f"Wyciek PII w wyjściu: {leaks}"

        print(f"\n[SYNTETYCZNY] {len(tokens)} tokenów: "
              f"{[t.get('token') for t in tokens]}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — pliki testowe lvl0-lvl3, raport
# ─────────────────────────────────────────────────────────────────────────────

_EXTENSIONS = ("*.txt", "*.jpg", "*.jpeg", "*.png", "*.pdf")
TEST_FILES = (
    sorted(f for ext in _EXTENSIONS for f in TEST_DOCS_DIR.glob(ext))
    if TEST_DOCS_DIR.exists() else []
)


@pytest.mark.skipif(not TEST_FILES, reason="Brak plików w 'Pliki testowe/'")
class TestSmokeTestFiles:
    """Pliki testowe lvl0-lvl3 → /preview → raport encji."""

    @pytest.mark.parametrize("doc_path", TEST_FILES, ids=[p.name for p in TEST_FILES])
    def test_plik_testowy(self, require_backend: None, doc_path: Path) -> None:
        if doc_path.suffix == ".txt":
            body, status = _preview_text(doc_path.read_text(encoding="utf-8"), doc_path.name)
        else:
            body, status = _preview_file(doc_path)

        assert status in (200, 422), f"{doc_path.name}: HTTP {status}"

        if status == 422 and body.get("ocr_rejected"):
            pytest.skip(f"{doc_path.name}: OCR odrzucił zdjęcie (za niska jakość)")

        assert status == 200, f"{doc_path.name}: HTTP {status} — {body.get('error')}"
        assert not body.get("error"), f"{doc_path.name}: error={body.get('error')!r}"

        anon    = body.get("anonymized_preview", "")
        tokens  = body.get("tokens", [])
        leaks   = _check_critical_leaks(anon)
        summary = _token_summary(tokens)

        ocr_conf = body.get("ocr", {}).get("confidence", "—")
        print(f"\n── {doc_path.name} (OCR conf: {ocr_conf}) ──")
        print(f"   Tokenów: {len(tokens)}")
        for ttype, vals in sorted(summary.items()):
            print(f"   {ttype:12s} ({len(vals)}): {', '.join(vals[:6])}")
        if leaks:
            print(f"   ⚠ WYCIEKI: {leaks[:5]}")

        assert not leaks, f"{doc_path.name}: wyciek PII: {leaks[:3]}"

    def test_generuj_raport(self, require_backend: None) -> None:
        """Zapisuje smoke_e2e_report.txt — przejrzyj i powiedz co nie działa."""
        lines = ["SMOKE E2E — RAPORT WYKRYTYCH ENCJI", "=" * 60, ""]

        for doc_path in TEST_FILES:
            if doc_path.suffix == ".txt":
                body, status = _preview_text(doc_path.read_text(encoding="utf-8"), doc_path.name)
            else:
                body, status = _preview_file(doc_path)

            lines.append(f"── {doc_path.name} ──")

            if status != 200 or body.get("error"):
                lines.append(f"   BŁĄD: HTTP {status} / {body.get('error')}")
                lines.append("")
                continue

            anon    = body.get("anonymized_preview", "")
            tokens  = body.get("tokens", [])
            leaks   = _check_critical_leaks(anon)
            summary = _token_summary(tokens)

            lines.append(f"   Tokenów łącznie: {len(tokens)}")
            for ttype, vals in sorted(summary.items()):
                for v in vals:
                    lines.append(f"   [{ttype}] {v}")

            if leaks:
                lines.append(f"   ⚠ WYCIEKI PII: {leaks}")
            else:
                lines.append("   ✓ Brak wycieków krytycznych")

            lines.append("")
            lines.append("   Tekst po maskowaniu (pierwsze 500 znaków):")
            lines.append("   " + anon[:500].replace("\n", " "))
            lines.append("")

        _SMOKE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nRaport zapisany: {REPORT_PATH}")
        assert REPORT_PATH.exists()
