#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_real.py  v1.0
=======================
Benchmark na realnych dokumentach (zdjęcia telefonem, skany, pliki tekstowe).
Nie wymaga ground_truth — ocenia tylko co system wykrył i czy nie ma wycieków PII.

Folder z dokumentami rośnie wraz z projektem — dodawaj kolejne pliki kiedy
wpadną w ręce, benchmark automatycznie je podejmie.

Struktura folderu (domyślnie: ../Pliki testowe/):
  - dowolna mieszanka: *.jpg, *.jpeg, *.png, *.pdf, *.txt
  - opcjonalnie podkatalogi (np. faktury/, umowy/) — skanowane rekurencyjnie
  - brak ground_truth.json — to nie jest potrzebne

Uruchomienie:
  python benchmark_real.py
  python benchmark_real.py --folder "../Pliki testowe"
  python benchmark_real.py --folder "C:/Moje dokumenty/testy"
  python benchmark_real.py --folder "../Pliki testowe" --show-text

Raporty w: benchmark_results_real/run_YYYYMMDD_HHMMSS/
  summary.txt    — czytelne podsumowanie dla człowieka
  leaks.txt      — wycieki PII (jeśli jakieś wystąpią)
  report.json    — pełne dane per dokument (do analizy)

Wymagania:
  - backend LynxMask uruchomiony (python pseudominizer_api.py)
  - pip install requests
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Konfiguracja
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_URL = "http://127.0.0.1:8765"
TIMEOUT_S   = 90
BATCH_PAUSE = 2.0

_HERE       = Path(__file__).parent
TOKEN_PATH  = _HERE / "api_token.txt"
DEFAULT_FOLDER = _HERE.parent / "Pliki testowe"

_EXTENSIONS = (".jpg", ".jpeg", ".png", ".pdf", ".txt")

# Wzorce krytyczne — obecność w wyjściu = wyciek PII
_CRITICAL_PATTERNS = [
    ("PESEL (11 cyfr)",    re.compile(r"\b\d{11}\b")),
    ("NIP (xxx-xxx-xx-xx)",re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b")),
    ("IBAN PL",            re.compile(r"\bPL\s*\d{2}[\s\d]{20,40}(?=\D|$)", re.IGNORECASE)),
    ("Email",              re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}")),
    ("Dowód osobisty",     re.compile(r"(?<![A-Za-z])[A-Z]{3}\s?\d{6}\b")),
    ("Paszport",           re.compile(r"\b[A-Z]{2}\s?\d{7}\b")),
]


# ─────────────────────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────────────────────

def _load_token() -> str:
    for attempt in range(10):
        try:
            t = TOKEN_PATH.read_text(encoding="utf-8").strip()
            if t:
                return t
        except Exception:
            pass
        time.sleep(0.5)
    return ""


def _headers() -> dict[str, str]:
    t = _load_token()
    return {"X-Api-Token": t} if t else {}


def check_backend() -> bool:
    try:
        r = requests.get(f"{BACKEND_URL}/health", headers=_headers(), timeout=5)
        return r.ok
    except Exception:
        return False


def post_preview(path: Path) -> dict[str, Any]:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    try:
        if path.suffix.lower() == ".txt":
            data = path.read_text(encoding="utf-8", errors="replace")
            r = requests.post(
                f"{BACKEND_URL}/preview",
                files={"file": (path.name, data.encode("utf-8"), "text/plain")},
                headers=_headers(),
                timeout=TIMEOUT_S,
            )
        else:
            r = requests.post(
                f"{BACKEND_URL}/preview",
                files={"file": (path.name, path.read_bytes(), mime)},
                headers=_headers(),
                timeout=TIMEOUT_S,
            )
        try:
            body = r.json()
        except Exception:
            body = {"_error": f"Nie-JSON (HTTP {r.status_code})"}
        body["_http_status"] = r.status_code
        return body
    except requests.exceptions.Timeout:
        return {"_error": f"Timeout ({TIMEOUT_S}s)", "_http_status": 0}
    except requests.exceptions.ConnectionError:
        return {"_error": "Connection refused", "_http_status": 0}
    except Exception as e:
        return {"_error": str(e), "_http_status": 0}


# ─────────────────────────────────────────────────────────────────────────────
# Analiza
# ─────────────────────────────────────────────────────────────────────────────

def check_leaks(anon_text: str) -> list[tuple[str, str]]:
    """Zwraca listę (nazwa_wzorca, znaleziony_fragment) dla każdego wycieku."""
    found = []
    for name, pat in _CRITICAL_PATTERNS:
        for m in pat.finditer(anon_text):
            found.append((name, m.group(0)))
    return found


def token_summary(tokens: list[dict]) -> dict[str, list[str]]:
    by_type: dict[str, list[str]] = {}
    for t in tokens:
        tid   = t.get("token", "")
        orig  = t.get("original", tid)
        ttype = tid.split("_")[0] if "_" in tid else t.get("type", "?")
        by_type.setdefault(ttype, []).append(str(orig)[:60])
    return by_type


def analyze_response(path: Path, resp: dict[str, Any]) -> dict[str, Any]:
    http_status = resp.get("_http_status", 0)
    error       = resp.get("_error") or resp.get("error")
    rejected    = resp.get("ocr_rejected", False)

    result: dict[str, Any] = {
        "file":        path.name,
        "path":        str(path),
        "http_status": http_status,
        "error":       error,
        "rejected":    rejected,
        "ocr_conf":    None,
        "ocr_quality": None,
        "tokens":      [],
        "token_summary": {},
        "leaks":       [],
        "anon_preview": "",
    }

    if error or http_status not in (200, 422):
        return result

    if rejected:
        return result

    ocr = resp.get("ocr", {})
    result["ocr_conf"]    = ocr.get("confidence")
    result["ocr_quality"] = ocr.get("quality")

    tokens = resp.get("tokens", [])
    result["tokens"]        = tokens
    result["token_summary"] = token_summary(tokens)

    anon = resp.get("anonymized_preview", "")
    result["anon_preview"] = anon
    result["leaks"]        = check_leaks(anon)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Główna pętla
# ─────────────────────────────────────────────────────────────────────────────

def collect_files(folder: Path) -> list[Path]:
    files = []
    for ext in _EXTENSIONS:
        files.extend(folder.rglob(f"*{ext}"))
        files.extend(folder.rglob(f"*{ext.upper()}"))
    # deduplikacja + sortowanie po nazwie
    seen: set[Path] = set()
    result = []
    for f in sorted(files, key=lambda p: p.name.lower()):
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def run(folder: Path, show_text: bool) -> list[dict[str, Any]]:
    files = collect_files(folder)
    if not files:
        print(f"[BŁĄD] Brak obsługiwanych plików w: {folder}")
        sys.exit(1)

    print(f"\n[REAL BENCH] Folder: {folder}")
    print(f"[REAL BENCH] Plików: {len(files)}  |  Backend: {BACKEND_URL}\n")
    print("─" * 72)

    results = []
    for i, path in enumerate(files, 1):
        time.sleep(0.1)
        resp   = post_preview(path)
        result = analyze_response(path, resp)
        results.append(result)

        # Linia statusu
        status = ""
        if result["error"]:
            status = f"  BŁĄD: {result['error']}"
        elif result["rejected"]:
            status = "  [OCR REJECT]"
        else:
            conf_str = (f"  conf={result['ocr_conf']:.0f}%"
                        if result["ocr_conf"] is not None else "")
            n_tok    = len(result["tokens"])
            n_leak   = len(result["leaks"])
            leak_str = f"  ⚠ WYCIEK×{n_leak}" if n_leak else "  ✓ brak wycieków"
            status   = f"{conf_str}  tokenów={n_tok}{leak_str}"

        rel = path.relative_to(folder) if path.is_relative_to(folder) else path.name
        print(f"  [{i:3d}] {str(rel):<40}{status}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Raportowanie
# ─────────────────────────────────────────────────────────────────────────────

def build_report(results: list[dict], run_dir: Path, show_text: bool) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    accepted  = [r for r in results if not r["error"] and not r["rejected"] and r["http_status"] == 200]
    rejected  = [r for r in results if r["rejected"]]
    errors    = [r for r in results if r["error"]]
    with_leaks = [r for r in accepted if r["leaks"]]

    total_tokens = sum(len(r["tokens"]) for r in accepted)
    all_leaks    = [(r["file"], lk) for r in with_leaks for lk in r["leaks"]]

    # ── summary.txt ──────────────────────────────────────────────────────────
    L = [
        "BENCHMARK REAL — RAPORT",
        f"Data: {ts}",
        f"Run:  {run_dir}",
        "═" * 72, "",
        "WYNIK OGÓLNY",
        f"  Dokumentów łącznie:     {len(results)}",
        f"  Przetworzone:           {len(accepted)}",
        f"  Odrzucone (OCR reject): {len(rejected)}",
        f"  Błędy:                  {len(errors)}",
        f"  Tokenów wykrytych:      {total_tokens}",
        f"  Dokumenty z wyciekiem:  {len(with_leaks)}",
        "",
        ("⚠  UWAGA: WYCIEKI PII WYKRYTE — patrz leaks.txt"
         if with_leaks else "✓  Brak wycieków PII we wszystkich przetworzonych dokumentach"),
        "",
        "═" * 72,
        "SZCZEGÓŁY PER DOKUMENT",
        "",
    ]

    for r in results:
        L.append(f"── {r['file']} ──")

        if r["error"]:
            L.append(f"   BŁĄD: {r['error']}")
            L.append("")
            continue

        if r["rejected"]:
            L.append("   OCR REJECT (za niska jakość zdjęcia)")
            L.append("")
            continue

        conf_str = (f"{r['ocr_conf']:.0f}%"
                    if r["ocr_conf"] is not None else "—")
        L.append(f"   OCR confidence: {conf_str}  |  Tokenów: {len(r['tokens'])}")

        summary = r["token_summary"]
        if summary:
            for ttype, vals in sorted(summary.items()):
                L.append(f"   [{ttype}] ({len(vals)}): {', '.join(vals[:6])}"
                         + (" ..." if len(vals) > 6 else ""))
        else:
            L.append("   (brak wykrytych encji)")

        if r["leaks"]:
            L.append(f"   ⚠ WYCIEKI PII ({len(r['leaks'])}):")
            for name, val in r["leaks"]:
                L.append(f"      {name}: {val}")
        else:
            L.append("   ✓ Brak wycieków")

        if show_text and r["anon_preview"]:
            L.append("   Tekst po maskowaniu (pierwsze 400 znaków):")
            L.append("   " + r["anon_preview"][:400].replace("\n", " "))

        L.append("")

    # Per typ — podsumowanie zbiorcze
    all_types: dict[str, int] = {}
    for r in accepted:
        for ttype, vals in r["token_summary"].items():
            all_types[ttype] = all_types.get(ttype, 0) + len(vals)

    if all_types:
        L += ["═" * 72, "ENCJE ŁĄCZNIE (wszystkie przetworzone dokumenty)", ""]
        for ttype, count in sorted(all_types.items(), key=lambda x: -x[1]):
            L.append(f"  {ttype:<14} {count:4d}")
        L.append("")

    with open(run_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ── leaks.txt ─────────────────────────────────────────────────────────────
    if with_leaks:
        B = [
            "WYCIEKI PII — DO NAPRAWY",
            f"Data: {ts}",
            "═" * 72, "",
            f"Łącznie wycieków: {len(all_leaks)}  w  {len(with_leaks)} dokumentach",
            "",
        ]
        for r in with_leaks:
            B.append(f"  {r['file']}")
            for name, val in r["leaks"]:
                B.append(f"    [{name}] {val}")
            B.append("")
        with open(run_dir / "leaks.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(B) + "\n")
    else:
        (run_dir / "leaks.txt").write_text("Brak wycieków PII.\n", encoding="utf-8")

    # ── report.json ───────────────────────────────────────────────────────────
    export = []
    for r in results:
        export.append({
            "file":        r["file"],
            "http_status": r["http_status"],
            "error":       r["error"],
            "rejected":    r["rejected"],
            "ocr_conf":    r["ocr_conf"],
            "ocr_quality": r["ocr_quality"],
            "token_count": len(r["tokens"]),
            "token_summary": r["token_summary"],
            "leaks":       r["leaks"],
        })
    with open(run_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    # ── Finał na konsolę ─────────────────────────────────────────────────────
    print(f"\n{'═'*72}")
    print(f"BENCHMARK REAL ZAKOŃCZONY — {ts}")
    print(f"  Dokumentów:     {len(results)}")
    print(f"  Przetworzone:   {len(accepted)}")
    print(f"  Tokenów:        {total_tokens}")
    if with_leaks:
        print(f"  ⚠ WYCIEKI PII:  {len(with_leaks)} dokumenty — patrz leaks.txt")
    else:
        print(f"  ✓ Brak wycieków PII")
    print(f"  Raporty: {run_dir}")
    print(f"    summary.txt  leaks.txt  report.json")
    print("═" * 72)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    global BACKEND_URL

    parser = argparse.ArgumentParser(
        prog="benchmark_real.py",
        description="Benchmark LynxMask na realnych dokumentach — bez ground truth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python benchmark_real.py
  python benchmark_real.py --folder "../Pliki testowe"
  python benchmark_real.py --folder "C:/Dokumenty/testy" --show-text
  python benchmark_real.py --backend http://127.0.0.1:8765

Dodawanie nowych plików:
  Wrzuć JPG/PNG/PDF/TXT do folderu (lub podkatalogu) i uruchom ponownie.
  Benchmark automatycznie podejmie wszystkie pliki.
        """,
    )
    parser.add_argument("--folder", "-f", type=str, default=str(DEFAULT_FOLDER),
                        help=f"Folder z dokumentami (domyślnie: {DEFAULT_FOLDER})")
    parser.add_argument("--backend", type=str, default=BACKEND_URL,
                        help="URL backendu (domyślnie: http://127.0.0.1:8765)")
    parser.add_argument("--show-text", action="store_true",
                        help="Drukuj w raporcie pierwsze 400 znaków tekstu po maskowaniu")
    args = parser.parse_args()

    BACKEND_URL = args.backend
    folder      = Path(args.folder)

    if not folder.exists():
        print(f"[BŁĄD] Folder nie istnieje: {folder}")
        sys.exit(1)

    print(f"\n[CHECK] {BACKEND_URL} ...")
    if not check_backend():
        print("[BŁĄD] Backend nie odpowiada. Uruchom: python pseudominizer_api.py")
        sys.exit(1)
    print("[CHECK] Backend OK")

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("benchmark_results_real") / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results = run(folder, args.show_text)
    build_report(results, run_dir, args.show_text)


if __name__ == "__main__":
    main()
