#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark.py  v1.3
==================
Automatyczny tester pipeline OCR + maskowania LynxMask Desktop.

Symuluje zachowanie użytkownika który wgrywa dokumenty przez /preview:
  1. Generuje paczkę obrazów przez generator.py
  2. Odpytuje backend POST /preview dla każdego obrazu
  3. Porównuje wykryte tokeny z ground_truth
  4. Zapisuje raport JSON + czytelne podsumowanie + lista bugów

Uruchomienie:
  python benchmark.py --count 50
  python benchmark.py --count 150 --batch-size 50
  python benchmark.py --dataset dataset --no-generate
  python benchmark.py --count 50 --max-level 3    (domyślne — bez lvl 4-5)
  python benchmark.py --count 50 --max-level 5    (pełna skala degradacji)

Wymagania:
  - backend LynxMask uruchomiony (python pseudominizer_api.py)
  - generator.py w tym samym katalogu
  - pip install requests

Raporty w: benchmark_results/run_YYYYMMDD_HHMMSS/
  report.json              — pełne dane per dokument (source of truth, nie modyfikować)
  summary.txt              — podsumowanie dla człowieka
  bugs.txt                 — anomalie do przekazania instancji naprawczej
  missed_candidates.json   — kandydaci do słownika biurowego (workflow SPEC v1.0)

Changelog:
  v1.3 (14.06.2026)
    - [L75] _load_token_from_file(): retry loop 10×0.5s zamiast jednej próby.
      Rozwiązuje race condition gdy backend restartuje podczas startu benchmarku.
    - [L167] _headers(): odczytuje token z pliku przy każdym wywołaniu zamiast
      z globalnego API_TOKEN. Benchmark zawsze używa aktualnego tokenu z dysku.
  v1.2 (13.06.2026)
    - [L186] _norm(): dodano normalizację \\n → spacja. Naprawia systemowo fałszywe
      missy adresów gdzie OCR zwraca "ul. X N\\nKK-KKK Miasto" zamiast przecinka.
      [Potok Krytyczne, nota benchmarkowa; decyzja orchestratora 13.06.2026]
    - [L397] generate_dataset(): benchmark przekazuje --max-level do generatora,
      domyślnie 3. Nowy parametr CLI --max-level N. [decyzja orchestratora 13.06.2026]
    - [L760] Nowy parametr CLI --max-level (default: 3).
    - [L515] build_report(): tabelka per encja drukowana do stdout po każdym runie.
      Format: ZAKRYTE / POMINIĘTE (critical) / FAŁSZYWE per dokument + podsumowanie
      zbiorcze. Dokumenty z błędem HTTP lub ocr_rejected=true pokazane jako [POMINIĘTY].
    - [L709] missed_candidates.json: uzupełniono o pola run_id i ocr_conf_real
      zgodnie ze SPEC_SLOWNIK_WORKFLOW_v1.0. Pole context=null (benchmark nie ma
      dostępu do surowego tekstu OCR w tym miejscu — odnotowane w raporcie).
  v1.1
    - Wersja z poprawkami pipeline (historia w repozytorium)
  v1.0
    - Wersja bazowa
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
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
API_TOKEN   = ""
TIMEOUT_S   = 60
BATCH_PAUSE = 3.0


def _load_token_from_file() -> str:
    token_path = Path(__file__).parent / "api_token.txt"
    for attempt in range(10):
        try:
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Nie można odczytać api_token.txt po 10 próbach")

# ─────────────────────────────────────────────────────────────────────────────
# Ontologia tokenów — 10 typów MVP
# Cel: maskowanie danych, nie perfekcyjna klasyfikacja.
# PESEL/NIP/IBAN/REGON/DOWOD → wszystko to NUMER — sukces bezpieczeństwa.
# FIRMA/INSTYTUCJA → ORGANIZACJA — AI rozumie dokument bez precyzyjnej etykiety.
# ─────────────────────────────────────────────────────────────────────────────

_ENTITY_TYPE_MAP = {
    # OSOBA
    "imie_nazwisko":                "OSOBA",
    "imie_nazwisko_zleceniodawca":  "OSOBA",
    "imie_nazwisko_zleceniobiorca": "OSOBA",
    "imie_nazwisko_nabywcy":        "OSOBA",
    "autor":                        "OSOBA",
    "osoba":                        "OSOBA",
    # NUMER — wszystkie identyfikatory, bez rozróżniania typu
    "pesel":                        "NUMER",
    "pesel_zleceniodawca":          "NUMER",
    "nip":                          "NUMER",
    "nip_sprzedawcy":               "NUMER",
    "nip_nabywcy":                  "NUMER",
    "nip_zleceniodawca":            "NUMER",
    "nip_zleceniobiorca":           "NUMER",
    "regon_sprzedawcy":             "NUMER",
    "iban":                         "NUMER",
    "dowod_osobisty":               "NUMER",
    "numer_paszportu":              "NUMER",
    "numer_kw":                     "NUMER",
    "numer_dzialki":                "NUMER",
    "numer_klienta":                "NUMER",
    "numer_umowy":                  "NUMER",
    "numer_faktury":                "NUMER",
    "data_urodzenia":               "NUMER",
    # TELEFON
    "telefon":                      "TELEFON",
    # EMAIL
    "email":                        "EMAIL",
    # ADRES
    "adres":                        "ADRES",
    "adres_zleceniodawca":          "ADRES",
    "adres_zleceniobiorca":         "ADRES",
    "adres_nabywcy":                "ADRES",
    # SYGNATURA
    "sygnatura_akt":                "SYGNATURA",
    "sygnatura_komornicza":         "SYGNATURA",
    "sygnatura_administracyjna":    "SYGNATURA",
    "sygnatura":                    "SYGNATURA",
    "numer_sprawy":                 "SYGNATURA",
}

# Typy pipeline → ontologia benchmark
# Pipeline używa starych nazw wewnętrznie — mapujemy na 10 typów MVP
_PIPELINE_TYPE_MAP = {
    "OSOBA":      "OSOBA",
    "NUMER":      "NUMER",
    "ADRES":      "ADRES",
    "EMAIL":      "EMAIL",
    "KWOTA":      "KWOTA",
    "FIRMA":      "ORGANIZACJA",      # stara nazwa → nowa ontologia
    "INSTYTUCJA": "ORGANIZACJA",
    "TELEFON":    "TELEFON",
    "SYGNATURA":  "SYGNATURA",
    "DOKUMENT":   "DOKUMENT",
    "DATA":       "DATA",
}

# Encje krytyczne — wyciek tych jest niedopuszczalny niezależnie od typu tokenu
_CRITICAL_KEYS = {
    "pesel", "pesel_zleceniodawca",
    "nip", "nip_sprzedawcy", "nip_nabywcy",
    "nip_zleceniodawca", "nip_zleceniobiorca",
    "iban", "dowod_osobisty", "numer_paszportu",
}


# ─────────────────────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {"X-Api-Token": _load_token_from_file()}


def check_backend() -> dict[str, Any] | None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5, headers=_headers())
        return r.json() if r.ok else None
    except Exception:
        return None


def post_preview(image_path: Path) -> dict[str, Any]:
    """POST /preview — symuluje wgranie obrazu przez użytkownika."""
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"{BACKEND_URL}/preview",
                files={"file": (image_path.name, f, "image/png")},
                headers=_headers(),
                timeout=TIMEOUT_S,
            )
        try:
            data = r.json()
        except Exception:
            data = {"bench_error": f"JSON parse failed (HTTP {r.status_code})"}
        data["bench_http_status"] = r.status_code
        return data
    except requests.exceptions.Timeout:
        return {"bench_error": f"Timeout ({TIMEOUT_S}s)", "bench_http_status": 0}
    except requests.exceptions.ConnectionError:
        return {"bench_error": "Connection refused", "bench_http_status": 0}
    except Exception as e:
        return {"bench_error": str(e), "bench_http_status": 0}


# ─────────────────────────────────────────────────────────────────────────────
# Analiza
# ─────────────────────────────────────────────────────────────────────────────

def _norm(v: str) -> str:
    # [v1.2] \n → spacja przed usunięciem spacji — naprawia adresy gdzie OCR
    # zwraca "ul. X N\nKK-KKK Miasto" zamiast "ul. X N, KK-KKK Miasto"
    v = v.replace("\n", " ").replace("\r", " ")
    while "  " in v:
        v = v.replace("  ", " ")
    return v.replace(" ", "").replace("-", "").lower()


def _fuzzy_match_numeric(gt_norm: str, orig_norm: str) -> bool:
    """
    Tolerancja na jedną zagubioną/zmienioną cyfrę przez OCR.
    Stosowana tylko dla ciągów >= 9 cyfr (PESEL, NIP, IBAN).
    Przypadki:
      - OCR zgubił 1 cyfrę: '91012224742' vs '9101224742' (10 vs 11 cyfr)
      - OCR zmienił 1 cyfrę: '91012224742' vs '91012224743'
    Nie stosujemy dla krótszych wartości — zbyt dużo false positives.
    """
    if len(gt_norm) < 9 or len(orig_norm) < 9:
        return False
    # Różnica długości max 1
    if abs(len(gt_norm) - len(orig_norm)) > 1:
        return False
    # Sprawdź czy dłuższy zawiera krótszy jako subsequence z jedną luką
    longer  = gt_norm if len(gt_norm) >= len(orig_norm) else orig_norm
    shorter = gt_norm if len(gt_norm) < len(orig_norm) else orig_norm
    if len(longer) == len(shorter):
        # Ta sama długość — policz różniące się pozycje (max 1)
        diffs = sum(a != b for a, b in zip(longer, shorter))
        return diffs <= 1
    # Dłuższy o 1 — sprawdź czy skrócony pasuje po usunięciu jednej cyfry
    for skip in range(len(longer)):
        candidate = longer[:skip] + longer[skip+1:]
        if candidate == shorter:
            return True
    return False


def _map_pipeline_type(raw_type: str) -> str:
    """Mapuje typ z pipeline (FIRMA, INSTYTUCJA...) na ontologię MVP."""
    return _PIPELINE_TYPE_MAP.get(raw_type, raw_type)


def analyze(
    gt: dict[str, Any],
    resp: dict[str, Any],
) -> dict[str, Any]:
    """
    Dwie metryki zgodnie z filozofią produktu:

    PRIVACY SUCCESS — czy dane zostały ukryte (cokolwiek)?
      PESEL zamaskowany jako NUMER = sukces. Jedyne co liczy się dla RODO.

    SEMANTIC SUCCESS — czy zamaskowano pod właściwym typem ontologii?
      Metryka pomocnicza — AI może nadal rozumieć dokument.

    Dokumenty ocr_rejected są wyłączone z metryk — poprawne zachowanie systemu.
    """
    result: dict[str, Any] = {
        "file":             gt["file"],
        "doc_type":         gt.get("doc_type", "?"),
        "quality_score":    gt.get("quality_score", -1),
        "ocr_conf_real":    gt.get("ocr_conf_real"),
        "deg_level":        gt.get("degradation_level", -1),
        "http_status":      resp.get("bench_http_status", 0),
        "bench_error":      resp.get("bench_error"),
        "ocr_rejected":     resp.get("ocr_rejected", False),
        "guard_blocked":    resp.get("blocked", False),
        "guard_reasons":    resp.get("guard_reasons", []),
        "ocr_quality":      None,
        "ocr_conf_backend": None,
        "tokens_found":     [],
        "false_positives":  [],
        "entities":         [],
        "summary":          {},
        "dict_candidates":  [],
    }

    ocr_meta = resp.get("ocr")
    if ocr_meta:
        result["ocr_quality"]      = ocr_meta.get("quality")
        result["ocr_conf_backend"] = ocr_meta.get("confidence")

    backend_tokens = resp.get("tokens", [])
    result["tokens_found"] = [
        {
            "token":    t.get("token"),
            "original": t.get("original"),
            "type":     _map_pipeline_type(t.get("type", "")),
            "type_raw": t.get("type"),
        }
        for t in backend_tokens
    ]

    gt_entities: dict[str, Any] = gt.get("entities", {})
    gt_norms    = [_norm(str(v)) for v in gt_entities.values()]
    error_or_reject = bool(resp.get("bench_error") or resp.get("ocr_rejected"))

    total_p = detected_p = critical_missed = 0
    total_s = detected_s = 0

    for key, val in gt_entities.items():
        val_n        = _norm(str(val))
        is_crit      = key in _CRITICAL_KEYS
        expected_ont = _ENTITY_TYPE_MAP.get(key, "?")
        privacy_found  = False
        semantic_found = False

        if not error_or_reject:
            for tok in backend_tokens:
                tok_orig = _norm(str(tok.get("original", "")))
                tok_type = _map_pipeline_type(tok.get("type", ""))
                value_match = (
                    val_n == tok_orig
                    or (len(val_n) >= 6 and (val_n in tok_orig or tok_orig in val_n))
                    or _fuzzy_match_numeric(val_n, tok_orig)
                )
                if value_match:
                    privacy_found = True
                    if tok_type == expected_ont:
                        semantic_found = True
                    break

        total_p += 1
        if privacy_found:
            detected_p += 1
        else:
            if is_crit:
                critical_missed += 1
            if (not error_or_reject
                    and result["deg_level"] <= 1
                    and result["quality_score"] >= 85):
                result["dict_candidates"].append({
                    "candidate":     str(val),
                    "entity_key":    key,
                    "expected_type": expected_ont,
                    "doc_type":      gt.get("doc_type", "?"),
                    "deg_level":     result["deg_level"],
                    "quality_score": result["quality_score"],
                    "source_file":   gt["file"],
                })

        if privacy_found:
            total_s += 1
            if semantic_found:
                detected_s += 1

        result["entities"].append({
            "key":            key,
            "value":          str(val),
            "expected_type":  expected_ont,
            "privacy_found":  privacy_found,
            "semantic_found": semantic_found,
            "critical":       is_crit,
        })

    false_positives: list[dict] = []
    for tok in backend_tokens:
        orig   = str(tok.get("original", ""))
        orig_n = _norm(orig)
        if not orig_n or len(orig_n) < 2:
            continue
        matched = any(
            orig_n == gn or (len(orig_n) >= 6 and (orig_n in gn or gn in orig_n))
            for gn in gt_norms
        )
        if not matched:
            false_positives.append({
                "token":    tok.get("token"),
                "original": orig,
                "type":     _map_pipeline_type(tok.get("type", "")),
            })
    result["false_positives"] = false_positives

    missed_p = total_p - detected_p
    fp       = len(false_positives)
    tp       = detected_p
    privacy_recall    = round(tp / total_p, 3) if total_p > 0 else None
    precision         = round(tp / (tp + fp), 3) if (tp + fp) > 0 else None
    semantic_accuracy = round(detected_s / total_s, 3) if total_s > 0 else None
    f1 = (round(2 * precision * privacy_recall / (precision + privacy_recall), 3)
          if precision and privacy_recall and (precision + privacy_recall) > 0 else None)

    result["summary"] = {
        "total_entities":    total_p,
        "privacy_detected":  detected_p,
        "privacy_missed":    missed_p,
        "critical_missed":   critical_missed,
        "privacy_recall":    privacy_recall,
        "semantic_total":    total_s,
        "semantic_correct":  detected_s,
        "semantic_accuracy": semantic_accuracy,
        "false_positives":   fp,
        "precision":         precision,
        "f1":                f1,
        "recall":            privacy_recall,
        "detected":          detected_p,
        "missed":            missed_p,
    }
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Generowanie datasetu
# ─────────────────────────────────────────────────────────────────────────────

def generate_dataset(
    count: int,
    out_dir: str,
    seed: int | None,
    measure_conf: bool,
    max_level: int = 3,         # [v1.2] domyślnie 3, przekazywane z CLI
) -> Path:
    gen = Path(__file__).parent / "generator.py"
    if not gen.exists():
        print(f"[BŁĄD] Nie znaleziono generator.py w {gen.parent}")
        sys.exit(1)

    cmd = [sys.executable, str(gen), "--count", str(count), "--output", out_dir,
           "--max-level", str(max_level)]  # [v1.2] zawsze przekazuj max-level
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if measure_conf:
        cmd += ["--measure-conf"]

    print(f"\n[GEN] Generuję {count} dokumentów → {out_dir}")
    r = subprocess.run(cmd, check=False)
    if r.returncode != 0:
        print(f"[BŁĄD] generator.py zakończył się błędem (kod {r.returncode})")
        sys.exit(1)
    return Path(out_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Główna pętla
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark(
    dataset_dir: Path,
    run_dir: Path,
    batch_size: int,
) -> list[dict[str, Any]]:

    gt_path = dataset_dir / "ground_truth.json"
    if not gt_path.exists():
        print(f"[BŁĄD] Brak {gt_path}")
        sys.exit(1)

    with open(gt_path, encoding="utf-8") as f:
        ground_truth: list[dict] = json.load(f)

    images_dir = dataset_dir / "images"
    all_results: list[dict[str, Any]] = []
    total   = len(ground_truth)
    batches = (total + batch_size - 1) // batch_size

    print(f"\n[BENCH] Dokumentów: {total}  |  Paczki: {batches} × {batch_size}")
    print(f"[BENCH] Backend: {BACKEND_URL}\n")

    for batch_no in range(batches):
        b_start = batch_no * batch_size
        b_end   = min(b_start + batch_size, total)
        batch   = ground_truth[b_start:b_end]

        print(f"[PACZKA {batch_no+1}/{batches}]  dok. {b_start+1}–{b_end}")
        print("─" * 72)

        batch_results: list[dict] = []

        for i, gt_entry in enumerate(batch, 1):
            img_path = images_dir / Path(gt_entry["file"]).name
            if not img_path.exists():
                print(f"  [{i:3d}] BRAK: {img_path.name}")
                continue

            # Małe opóźnienie — chroni backend przed zalewem
            time.sleep(0.1)

            resp   = post_preview(img_path)
            result = analyze(gt_entry, resp)
            batch_results.append(result)

            # Linia statusu
            s       = result["summary"]
            rec     = f"{s.get('privacy_recall',0)*100:.0f}%" if s.get("privacy_recall") is not None else " N/A"
            prec    = f"{s.get('precision',0)*100:.0f}%" if s.get("precision") is not None else " N/A"
            fp_str  = f" FP:{s.get('false_positives',0)}" if s.get("false_positives", 0) > 0 else ""
            crit    = f" ⚠CRIT:{s['critical_missed']}" if s.get("critical_missed") else ""
            rej     = " [REJ]"   if result["ocr_rejected"] else ""
            grd     = " [GUARD]" if result["guard_blocked"] else ""
            err     = f" ERR:{result['bench_error']}" if result["bench_error"] else ""
            conf_b  = (f"conf={result['ocr_conf_backend']:.0f}%"
                       if result["ocr_conf_backend"] is not None
                       else f"qs={result['quality_score']}")
            conf_r  = (f" real={result['ocr_conf_real']:.0f}%"
                       if result["ocr_conf_real"] is not None else "")

            print(f"  [{i:3d}] {img_path.name:<20} {result['doc_type']:<22} "
                  f"lvl={result['deg_level']} {conf_b:<12}{conf_r:<10} "
                  f"R={rec} P={prec}{fp_str}{crit}{rej}{grd}{err}")

        all_results.extend(batch_results)
        _save_partial(all_results, run_dir, batch_no + 1)
        _print_batch_summary(batch_results, batch_no + 1)

        if batch_no < batches - 1:
            print(f"\n[PAUZA] {BATCH_PAUSE:.0f}s...\n")
            time.sleep(BATCH_PAUSE)

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Raportowanie
# ─────────────────────────────────────────────────────────────────────────────

def _print_batch_summary(results: list[dict], batch_no: int) -> None:
    if not results:
        return
    accepted   = [r for r in results if not r["ocr_rejected"] and not r["bench_error"] and r.get("http_status") == 200]
    rejected   = sum(1 for r in results if r["ocr_rejected"])
    errors     = sum(1 for r in results if r["bench_error"])
    guard_blk  = sum(1 for r in results if r["guard_blocked"])
    total_ent  = sum(r["summary"].get("total_entities", 0) for r in accepted)
    total_det  = sum(r["summary"].get("privacy_detected", 0) for r in accepted)
    total_fp   = sum(r["summary"].get("false_positives", 0) for r in accepted)
    total_crit = sum(r["summary"].get("critical_missed", 0) for r in accepted)
    recall     = total_det / total_ent if total_ent > 0 else 0
    tp_fp      = total_det + total_fp
    precision  = total_det / tp_fp if tp_fp > 0 else 0

    print(f"\n  ── Paczka {batch_no} ──  "
          f"recall={recall*100:.1f}%  precision={precision*100:.1f}%  "
          f"FP={total_fp}  crit_miss={total_crit}  "
          f"rej={rejected}  guard={guard_blk}  err={errors}\n")


def _print_entity_table(results: list[dict]) -> None:
    """
    [v1.2] Drukuje do stdout tabelkę per dokument: ZAKRYTE / POMINIĘTE / FAŁSZYWE.
    Tylko dokumenty zaakceptowane (http_status=200, ocr_rejected=False, brak bench_error).
    Dokumenty pominięte pokazane jako [POMINIĘTY: ...] — jedna linia, bez tabelki.
    Nie modyfikuje struktury JSON.
    """
    print(f"\n{'═' * 72}")
    print("TABELKA ENCJI PER DOKUMENT")
    print('═' * 72)

    total_docs      = len(results)
    processed_docs  = 0
    skipped_docs    = 0

    total_zakryte   = 0
    total_pominiete = 0
    total_crit_miss = 0
    total_falszywe  = 0
    total_tokeny    = 0

    for r in results:
        fname    = r.get("file", "?")
        doc_type = r.get("doc_type", "?")
        lvl      = r.get("deg_level", "?")
        qs       = r.get("quality_score", "?")
        rejected = r.get("ocr_rejected", False)
        err      = r.get("bench_error")
        http_st  = r.get("http_status", 0)

        # Nagłówek dokumentu
        print(f"\n{fname}  ({doc_type}, lvl{lvl}, quality {qs})")

        # Dokumenty pominięte — jedna linia
        if rejected:
            print(f"  [POMINIĘTY: OCR reject]")
            skipped_docs += 1
            continue
        if err or http_st != 200:
            reason = err if err else f"błąd HTTP {http_st}"
            print(f"  [POMINIĘTY: {reason}]")
            skipped_docs += 1
            continue

        processed_docs += 1
        entities      = r.get("entities", [])
        tokens_found  = r.get("tokens_found", [])
        false_pos     = r.get("false_positives", [])

        zakryte   = [e for e in entities if e.get("privacy_found")]
        pominiete = [e for e in entities if not e.get("privacy_found")]

        # Zbierz wartości ground truth dla wykrywania fałszywych
        gt_values = {e.get("value", "") for e in entities}

        # ZAKRYTE
        if zakryte:
            print(f"  ZAKRYTE:")
            for e in zakryte:
                tok_label = ""
                # Znajdź token który pasuje do tej encji
                val_n = _norm(str(e.get("value", "")))
                for t in tokens_found:
                    tok_orig_n = _norm(str(t.get("original", "")))
                    if (val_n == tok_orig_n
                            or (len(val_n) >= 6 and (val_n in tok_orig_n or tok_orig_n in val_n))
                            or _fuzzy_match_numeric(val_n, tok_orig_n)):
                        tok_label = f" → {t.get('token', '?')}"
                        break
                print(f"    {e.get('expected_type','?')} {e.get('value','?')}{tok_label}")
                total_zakryte += 1

        # POMINIĘTE
        if pominiete:
            print(f"  POMINIĘTE:")
            for e in pominiete:
                crit_mark = "  ⚠ critical" if e.get("critical") else ""
                print(f"    {e.get('expected_type','?')} {e.get('value','?')}{crit_mark}")
                total_pominiete += 1
                if e.get("critical"):
                    total_crit_miss += 1

        # FAŁSZYWE (false positives)
        if false_pos:
            print(f"  FAŁSZYWE:")
            for fp in false_pos:
                print(f"    {fp.get('token','?')} [{fp.get('type','?')}]"
                      f" → \"{fp.get('original','?')[:50]}\"")
                total_falszywe += 1

        total_tokeny += len(tokens_found)

        if not zakryte and not pominiete and not false_pos:
            print(f"  (brak encji w ground truth)")

    # Podsumowanie zbiorcze
    print(f"\n{'═' * 72}")
    print("=== PODSUMOWANIE ===")
    recall_pct = (total_zakryte / (total_zakryte + total_pominiete) * 100
                  if (total_zakryte + total_pominiete) > 0 else 0.0)
    crit_total = total_crit_miss + sum(
        1 for r in results
        if not r.get("ocr_rejected") and not r.get("bench_error") and r.get("http_status", 0) == 200
        for e in r.get("entities", [])
        if e.get("critical") and e.get("privacy_found")
    )
    crit_leakage = (total_crit_miss / crit_total * 100 if crit_total > 0 else 0.0)
    fpr = (total_falszywe / total_tokeny * 100 if total_tokeny > 0 else 0.0)

    print(f"Dokumentów: {total_docs} "
          f"(przetworzone: {processed_docs}, pominięte: {skipped_docs})")
    print(f"Privacy Recall:      {recall_pct:5.1f}%  (zakryte/wszystkie)")
    print(f"Critical Leakage:    {crit_leakage:5.1f}%  (pominięte critical/wszystkie critical)")
    print(f"False Positive Rate: {fpr:5.1f}%  (fałszywe/wszystkie tokeny)")
    print('═' * 72)


def build_report(results: list[dict[str, Any]], run_dir: Path) -> None:
    # [v1.2] Tabelka per encja — drukuj do stdout przed zapisem plików
    _print_entity_table(results)

    # report.json — source of truth, struktura bez zmian
    with open(run_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Rozdziel dokumenty: zaakceptowane vs odrzucone przez OCR ─────────────
    accepted  = [r for r in results if not r["ocr_rejected"] and not r["bench_error"] and r.get("http_status") == 200]
    rejected  = [r for r in results if r["ocr_rejected"]]
    errors    = [r for r in results if r["bench_error"]]
    guard_blk = [r for r in results if r["guard_blocked"]]

    # ── Metryki TYLKO dla zaakceptowanych ────────────────────────────────────
    def _sum(rs, key):
        return sum(r["summary"].get(key, 0) for r in rs)

    total_ent  = _sum(accepted, "total_entities")
    total_det  = _sum(accepted, "privacy_detected")
    total_miss = _sum(accepted, "privacy_missed")
    total_crit = _sum(accepted, "critical_missed")
    total_fp   = _sum(accepted, "false_positives")
    total_sem  = _sum(accepted, "semantic_total")
    total_sem_ok = _sum(accepted, "semantic_correct")

    tp_fp       = total_det + total_fp
    privacy_recall = total_det / total_ent if total_ent > 0 else 0
    precision      = total_det / tp_fp if tp_fp > 0 else 0
    semantic_acc   = total_sem_ok / total_sem if total_sem > 0 else 0
    f1_all = (2 * precision * privacy_recall / (precision + privacy_recall)
              if (precision + privacy_recall) > 0 else 0)

    # Krytyczny wskaźnik bezpieczeństwa
    total_crit_possible = sum(
        1 for r in accepted for e in r["entities"] if e["critical"]
    )
    critical_leakage_rate = (total_crit / total_crit_possible
                             if total_crit_possible > 0 else 0)

    # Acceptance rate
    total_docs   = len(results)
    accepted_cnt = len(accepted)
    accept_rate  = accepted_cnt / total_docs if total_docs > 0 else 0

    # ── Per typ (tylko zaakceptowane) ────────────────────────────────────────
    per_type: dict[str, dict[str, int]] = {}
    for r in accepted:
        for e in r["entities"]:
            et = e["expected_type"]
            per_type.setdefault(et, {"detected": 0, "total": 0, "fp": 0})
            per_type[et]["total"] += 1
            if e["privacy_found"]:
                per_type[et]["detected"] += 1
        for fp in r["false_positives"]:
            et = fp.get("type", "?")
            per_type.setdefault(et, {"detected": 0, "total": 0, "fp": 0})
            per_type[et]["fp"] += 1

    # ── Per poziom degradacji (tylko zaakceptowane) ───────────────────────────
    per_level: dict[int, dict[str, int]] = {}
    for r in accepted:
        lv = r["deg_level"]
        per_level.setdefault(lv, {"detected": 0, "total": 0, "docs": 0})
        per_level[lv]["docs"]     += 1
        per_level[lv]["total"]    += r["summary"]["total_entities"]
        per_level[lv]["detected"] += r["summary"]["privacy_detected"]

    # ── summary.txt ──────────────────────────────────────────────────────────
    L = [
        "BENCHMARK LYNXMASK — RAPORT",
        f"Data: {ts}",
        f"Run:  {run_dir}",
        "═" * 60, "",
        "═" * 60,
        "  GŁÓWNY KPI — CRITICAL LEAKAGE RATE",
        f"  {critical_leakage_rate*100:.1f}%  ({total_crit} wycieków / {total_crit_possible} krytycznych encji)",
        "  Cel: 0.0%  |  Encje: PESEL, NIP, IBAN, dowód, paszport",
        "═" * 60, "",
        "PRZEPUSTOWOŚĆ",
        f"  Dokumentów łącznie:        {total_docs}",
        f"  Zaakceptowanych przez OCR: {accepted_cnt}  ({accept_rate*100:.0f}%)",
        f"  Odrzuconych (conf<70%):    {len(rejected)}  — poprawne zachowanie systemu",
        f"  Błędy HTTP/timeout:        {len(errors)}",
        f"  Guard zablokował:          {len(guard_blk)}",
        "",
        "METRYKI (tylko zaakceptowane dokumenty)",
        "",
        "  A. PRIVACY — czy dane zostały ukryte?",
        f"     Recall:     {privacy_recall*100:.1f}%  ({total_det}/{total_ent} encji zamaskowanych)",
        f"     Precision:  {precision*100:.1f}%  (overmasking: {total_fp} FP)",
        f"     F1:         {f1_all*100:.1f}%",
        "",
        "  B. SEMANTIC — czy zamaskowano pod właściwym typem?",
        f"     Accuracy:   {semantic_acc*100:.1f}%  ({total_sem_ok}/{total_sem} poprawny typ)",
        f"     (metryka pomocnicza — PESEL jako NUMER = sukces privacy)",
        "",
        "  INTERPRETACJA:",
        "  Privacy Recall < 95%   → pipeline gubi encje — ryzyko wycieku",
        "  Precision < 85%        → pipeline maskuje za dużo — dokument traci użyteczność",
        "  Semantic Accuracy < 80% → typy tokenu wymagają korekty (nie wpływa na RODO)",
        "", "PRIVACY RECALL PER TYP ENCJI (zaakceptowane)",
    ]
    for et, c in sorted(per_type.items()):
        rc   = c["detected"] / c["total"] if c["total"] > 0 else 0
        fp_t = c.get("fp", 0)
        pr   = c["detected"] / (c["detected"] + fp_t) if (c["detected"] + fp_t) > 0 else 1.0
        bar  = "█" * int(rc * 16) + "░" * (16 - int(rc * 16))
        L.append(f"  {et:<12} R={rc*100:5.1f}% P={pr*100:5.1f}%  [{bar}]  "
                 f"({c['detected']}/{c['total']}  FP={fp_t})")

    L += ["", "PRIVACY RECALL PER POZIOM DEGRADACJI (zaakceptowane)"]
    lvl_labels = {0: "perfect scan  ", 1: "light noise   ", 2: "noise+blur    ",
                  3: "phone (good)  ", 4: "phone (casual)", 5: "poor quality  "}
    for lv in sorted(per_level):
        c  = per_level[lv]
        rc = c["detected"] / c["total"] if c["total"] > 0 else 0
        bar = "█" * int(rc * 20) + "░" * (20 - int(rc * 20))
        L.append(f"  Lvl {lv} {lvl_labels.get(lv,'')} [{bar}] {rc*100:5.1f}%  "
                 f"docs={c['docs']} ent={c['total']}")

    if rejected:
        L += ["", f"ODRZUCONE PRZEZ OCR ({len(rejected)} dok.) — poza metrykami"]
        for r in rejected[:10]:
            L.append(f"  {r['file']}  lvl={r['deg_level']}  qs={r['quality_score']}")
        if len(rejected) > 10:
            L.append(f"  ... i {len(rejected)-10} więcej")

    with open(run_dir / "summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ── bugs.txt ─────────────────────────────────────────────────────────────
    B = [f"BUGS / ANOMALIE — {ts}", "Do przekazania instancji naprawczej.",
         "═" * 60, ""]

    # Krytyczne wycieki (tylko zaakceptowane)
    crit_cases = [
        (r, e) for r in accepted for e in r["entities"]
        if not e["privacy_found"] and e["critical"]
    ]
    if crit_cases:
        B += [f"[KRYTYCZNE] Pominięte encje wysokiego ryzyka: {len(crit_cases)}", ""]
        for r, e in crit_cases[:40]:
            cr_str = (f"conf_real={r['ocr_conf_real']:.0f}%"
                      if r["ocr_conf_real"] is not None else f"qs={r['quality_score']}")
            B.append(f"  {r['file']}  lvl={r['deg_level']}  {cr_str}"
                     f"  {e['key']}={e['value'][:35]}")
        if len(crit_cases) > 40:
            B.append(f"  ... i {len(crit_cases)-40} więcej — patrz report.json")
        B.append("")

    if guard_blk:
        B += [f"[GUARD] Zablokowane: {len(guard_blk)}", ""]
        for r in guard_blk[:20]:
            B.append(f"  {r['file']}  lvl={r['deg_level']}")
            for reason in r["guard_reasons"][:3]:
                B.append(f"    → {reason}")
        B.append("")

    if total_fp > 0:
        B += [f"[FALSE POSITIVES] Overmasking: {total_fp} tokenów spoza ground truth", ""]
        worst = sorted(accepted, key=lambda r: r["summary"]["false_positives"], reverse=True)[:10]
        for r in worst:
            fp_count = r["summary"]["false_positives"]
            if fp_count == 0:
                break
            B.append(f"  {r['file']}  lvl={r['deg_level']}  FP={fp_count}")
            for fp in r["false_positives"][:4]:
                B.append(f"    → [{fp['type']}] \"{fp['original'][:40]}\"")
        B.append("")

    if errors:
        B += [f"[HTTP-ERRORS] Błędy: {len(errors)}", ""]
        for r in errors[:10]:
            B.append(f"  {r['file']} → {r['bench_error']}")
        B.append("")

    low_recall = [
        (et, c) for et, c in per_type.items()
        if c["total"] >= 5 and c["detected"] / c["total"] < 0.80
    ]
    if low_recall:
        B += ["[RECALL<80%] Typy z niskim privacy recall (min. 5 próbek):", ""]
        for et, c in sorted(low_recall, key=lambda x: x[1]["detected"] / x[1]["total"]):
            rc = c["detected"] / c["total"]
            B.append(f"  {et:<12} {rc*100:.1f}%  ({c['detected']}/{c['total']})")
        B.append("")

    if not (crit_cases or guard_blk or errors or low_recall):
        B.append("Brak krytycznych anomalii. Recall ogólny OK.")

    with open(run_dir / "bugs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(B) + "\n")

    # ── missed_candidates.json — do workflow słownika ────────────────────────
    # [v1.2] Format zgodny ze SPEC_SLOWNIK_WORKFLOW_v1.0 sekcja PLIK 1.
    # Pole context=null — benchmark nie ma dostępu do surowego tekstu OCR
    # w tym miejscu kodu, tylko do JSON wynikowego. Odnotowane w raporcie.
    run_id = f"run_{ts.replace('-','').replace(' ','_').replace(':','')}"
    raw_candidates = [c for r in accepted for c in r.get("dict_candidates", [])]

    # Wzbogać o pola wymagane przez SPEC (których nie ma w analyze())
    all_candidates = []
    for r in accepted:
        for c in r.get("dict_candidates", []):
            all_candidates.append({
                "candidate":      c["candidate"],
                "context":        None,           # brak dostępu do tekstu OCR tutaj
                "document_type":  c["doc_type"],
                "entity_key":     c["entity_key"],
                "deg_level":      c["deg_level"],
                "quality_score":  c["quality_score"],
                "ocr_conf_real":  r.get("ocr_conf_real"),   # z wyniku dokumentu
                "source_file":    c["source_file"],
                "run_id":         run_id,
            })

    # Zawsze zapisuj plik — pusty [] gdy brak kandydatów (SPEC wymaga pliku)
    with open(run_dir / "missed_candidates.json", "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    # ── Finał na konsolę ─────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"BENCHMARK ZAKOŃCZONY — {ts}")
    print(f"  Critical Leakage Rate: {critical_leakage_rate*100:.1f}%  ← GŁÓWNY KPI")
    print(f"  Privacy Recall:        {privacy_recall*100:.1f}%  (zaakceptowane)")
    print(f"  Precision:             {precision*100:.1f}%")
    print(f"  Semantic Accuracy:     {semantic_acc*100:.1f}%  (pomocnicza)")
    print(f"  Acceptance Rate:       {accept_rate*100:.0f}%  ({accepted_cnt}/{total_docs})")
    print(f"  Kandydaci do słownika: {len(all_candidates)}")
    print(f"  Raporty: {run_dir}")
    print(f"    report.json  summary.txt  bugs.txt  missed_candidates.json")
    print("═" * 60)


def _save_partial(results: list[dict], run_dir: Path, batch_no: int) -> None:
    with open(run_dir / f"partial_batch_{batch_no:02d}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    global BACKEND_URL, API_TOKEN

    parser = argparse.ArgumentParser(
        prog="benchmark.py",
        description="Automatyczny tester pipeline OCR+maskowania LynxMask Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python benchmark.py --count 50
  python benchmark.py --count 150 --batch-size 50
  python benchmark.py --dataset dataset --no-generate
  python benchmark.py --count 50 --seed 42
  python benchmark.py --count 50 --max-level 3    (domyślne — bez lvl 4-5)
  python benchmark.py --count 50 --max-level 5    (pełna skala degradacji)
        """,
    )
    parser.add_argument("--count",    "-n", type=int, default=50)
    parser.add_argument("--batch-size", "-b", type=int, default=50)
    parser.add_argument("--dataset",  "-d", type=str, default=None)
    parser.add_argument("--no-generate", action="store_true")
    parser.add_argument("--seed",     "-s", type=int, default=None)
    parser.add_argument("--measure-conf", action="store_true",
                        help="Mierz rzeczywisty conf Tesseract podczas generacji (wolniej)")
    parser.add_argument("--max-level", type=int, default=3, choices=range(6),
                        metavar="L",
                        help="Maks. poziom degradacji generatora 0–5 (default: 3). "
                             "Użyj --max-level 5 dla pełnej skali.")  # [v1.2]
    parser.add_argument("--backend",  type=str, default="http://127.0.0.1:8765")
    parser.add_argument("--token",    type=str, default="")
    args = parser.parse_args()

    BACKEND_URL = args.backend
    API_TOKEN   = args.token if args.token else _load_token_from_file()

    # Sprawdź backend
    print(f"\n[CHECK] {BACKEND_URL} ...")
    if API_TOKEN:
        print(f"[CHECK] Token: {'*' * 8}{API_TOKEN[-4:] if len(API_TOKEN) > 4 else '****'}")
    else:
        print(f"[CHECK] Brak tokenu — jeśli backend wymaga X-Api-Token, dodaj --token lub api_token.txt")
    health = check_backend()
    if health is None:
        print("[BŁĄD] Backend nie odpowiada. Uruchom: python pseudominizer_api.py")
        sys.exit(1)
    print(f"[CHECK] OK — anonymizer={health.get('anonymizer')}  "
          f"spacy={health.get('spacy_ner')}  crypto={health.get('crypto_ok')}")

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("benchmark_results") / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"[RUN]   → {run_dir}")

    if args.no_generate and args.dataset:
        dataset_dir = Path(args.dataset)
        if not dataset_dir.exists():
            print(f"[BŁĄD] Dataset nie istnieje: {dataset_dir}")
            sys.exit(1)
    else:
        dataset_dir = generate_dataset(
            count=args.count,
            out_dir=f"dataset_{ts}",
            seed=args.seed,
            measure_conf=args.measure_conf,
            max_level=args.max_level,       # [v1.2]
        )

    results = run_benchmark(
        dataset_dir=dataset_dir,
        run_dir=run_dir,
        batch_size=args.batch_size,
    )
    build_report(results, run_dir)


if __name__ == "__main__":
    main()
