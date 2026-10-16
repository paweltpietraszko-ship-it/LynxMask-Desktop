#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preview_real_docs.py v1.0
=========================
Przetwarza zdjęcia/PDF z dataset_real/images/ przez /preview
i zapisuje czytelny raport — BEZ ground_truth.json.

Dla właściciela: otwórz raport, zobacz co zostało odkryte, wklej fragment do Claude.

Uruchomienie:
  python preview_real_docs.py
  (backend musi działać: python pseudominizer_api.py)

Wejście:  dataset_real/images/*  (jpg, png, pdf, …)
Wyjście: preview_real_results/run_YYYYMMDD_HHMMSS/raport.txt
"""

from __future__ import annotations

import mimetypes
import sys
from datetime import datetime
from pathlib import Path

import requests

BACKEND_URL = "http://127.0.0.1:8765"
TIMEOUT_S = 120

BACKEND_DIR = Path(__file__).parent
IMAGES_DIR = BACKEND_DIR / "dataset_real" / "images"
TOKEN_PATH = BACKEND_DIR / "api_token.txt"


def _headers() -> dict[str, str]:
    try:
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {}
    return {"X-Api-Token": token} if token else {}


def _preview(path: Path) -> tuple[dict, int]:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as f:
        r = requests.post(
            f"{BACKEND_URL}/preview",
            files={"file": (path.name, f, mime)},
            headers=_headers(),
            timeout=TIMEOUT_S,
        )
    try:
        body = r.json()
    except Exception:
        body = {"error": f"Odpowiedź nie-JSON (HTTP {r.status_code})"}
    return body, r.status_code


def main() -> int:
    if not IMAGES_DIR.is_dir():
        print(f"[BŁĄD] Brak folderu: {IMAGES_DIR}")
        print("       Utwórz i wrzuć tam zdjęcia/PDF.")
        return 1

    files = sorted(
        p for p in IMAGES_DIR.iterdir()
        if p.is_file() and p.name.lower() not in (".gitkeep", ".ds_store")
    )
    if not files:
        print(f"[INFO] Folder pusty: {IMAGES_DIR}")
        print("       Wrzuć zdjęcia i uruchom ponownie.")
        return 0

    try:
        h = requests.get(f"{BACKEND_URL}/health", headers=_headers(), timeout=5)
        if not h.ok:
            print("[BŁĄD] Backend nie odpowiada. Uruchom: python pseudominizer_api.py")
            return 1
    except requests.RequestException:
        print("[BŁĄD] Backend niedostępny na 127.0.0.1:8765")
        return 1

    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_dir = BACKEND_DIR / "preview_real_results" / f"run_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "raport.txt"

    lines: list[str] = [
        "LYNXMASK — RAPORT MASKOWANIA (realne dokumenty)",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Dokumentów: {len(files)}",
        "",
        "Jak czytać:",
        "  - WYNIK MASKOWANIA = tekst po pseudonimizacji (to wklejasz Claude)",
        "  - CO ZAMASKOWANO = lista tokenów (oryginał → TOKEN)",
        "  - Jeśli widzisz prawdziwe dane w WYNIKU — napisz Claude: „wyciek: ...”",
        "",
        "=" * 72,
    ]

    for i, path in enumerate(files, 1):
        body, status = _preview(path)
        lines.append("")
        lines.append(f"### [{i}/{len(files)}] {path.name}")
        lines.append("-" * 72)

        if status != 200:
            lines.append(f"STATUS: HTTP {status}")
            lines.append(f"BŁĄD: {body.get('error', body)}")
            if body.get("ocr_rejected"):
                lines.append("→ OCR odrzucił dokument (zbyt słabe zdjęcie) — to OK, nie bug silnika.")
            continue

        if body.get("blocked"):
            lines.append("STATUS: GUARD ZABLOKOWAŁ (wyciek w wyniku)")
            for reason in body.get("guard_reasons") or []:
                lines.append(f"  - {reason}")
            continue

        ocr = body.get("ocr") or {}
        conf = ocr.get("confidence")
        if conf is not None:
            lines.append(f"OCR confidence: {conf:.0f}%")

        lines.append("")
        lines.append("WYNIK MASKOWANIA:")
        lines.append(body.get("anonymized_preview", "(pusty)"))

        tokens = body.get("tokens") or []
        lines.append("")
        lines.append(f"CO ZAMASKOWANO ({len(tokens)} tokenów):")
        if not tokens:
            lines.append("  (nic — silnik nic nie wykrył)")
        else:
            for t in tokens:
                lines.append(f"  {t.get('type', '?'):12}  {t.get('original', '?')!r}  →  {t.get('token', '?')}")

        lines.append("")
        lines.append("─" * 40)
        lines.append("Twoja ocena (opcjonalnie, dla Claude):")
        lines.append("  Wyciek: …")
        lines.append("  Fałszywy alarm: …")
        lines.append("  OK: tak/nie")

    text = "\n".join(lines) + "\n"
    report_path.write_text(text, encoding="utf-8")

    print(f"\n[OK] Raport: {report_path}")
    print(f"     Otwórz plik — sekcja WYNIK MASKOWANIA + ewentualne wycieki → wklej do Claude.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
