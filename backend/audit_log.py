"""
audit_log.py  v1.1
[FIX-AUDIT-MODE] AUDIT_MODE = False przed dystrybucją.
[FIX-AUDIT-PII]  Usunięto input_fragment i output_fragment z rekordu —
                 zawierały do 500 znaków oryginalnego tekstu (PII).

Moduł audytu pseudonimizacji — zapisuje wyniki /preview do pliku JSONL.

Włączanie/wyłączanie:
  AUDIT_MODE = True   — aktywny (tryb deweloperski / testowy)
  AUDIT_MODE = False  — wyłączony (produkcja — zero overhead, zero zapisu)

Format pliku: pseudominizer_audit.jsonl
  Jeden rekord JSON per linia. Łatwy import do Excela, pandas, grep.

Wywołanie z pseudominizer_api.py:
  from audit_log import record_preview
  record_preview(pse_code, original_text, anon_text, result)
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pseudominizer.audit")

# ── Konfiguracja ──────────────────────────────────────────────────────────────

# PRODUKCJA: False — zero zapisu, zero I/O
AUDIT_MODE = True  # logi aktywne — kasowane ręcznie przez właściciela

AUDIT_FILE = Path("pseudominizer_audit.jsonl")


# ── API publiczne ─────────────────────────────────────────────────────────────

def record_preview(
    pse_code:      str,
    original_text: str,
    anon_text:     str,
    tokens:        list,
    guard_blocked: bool,
    guard_reasons: list,
    error:         str | None = None,
) -> None:
    """
    Zapisuje jeden rekord audytu do AUDIT_FILE.
    Gdy AUDIT_MODE = False — natychmiastowy return, brak I/O.

    Parametry:
      pse_code       — kod PSE sesji (PSE-RRRR-NNNN)
      original_text  — tekst wejściowy (przed pseudonimizacją)
      anon_text      — tekst wyjściowy (po pseudonimizacji)
      tokens         — lista tokenów z /preview (token, original, type, label)
      guard_blocked  — czy output_guard zablokował eksport
      guard_reasons  — lista powodów blokady/ostrzeżeń guarda
      error          — błąd pipeline'u jeśli wystąpił
    """
    if not AUDIT_MODE:
        return

    try:
        _write_record(pse_code, original_text, anon_text, tokens, guard_blocked, guard_reasons, error)
    except Exception as e:
        # Audit nie może crashować głównego pipeline'u
        logger.warning("[AUDIT] Błąd zapisu rekordu %s: %s", pse_code, e)


# ── Implementacja ─────────────────────────────────────────────────────────────

def _build_token_summary(tokens: list) -> dict:
    """
    Buduje podsumowanie tokenów pogrupowane po typie.
    Zwraca: {typ: [{token, original}, ...]}
    """
    summary: dict = {}
    for t in tokens:
        ttype = t.get("type", "INNE")
        if ttype not in summary:
            summary[ttype] = []
        summary[ttype].append({
            "token":    t.get("token", ""),
            "original": t.get("original", ""),
        })
    return summary


def _coverage_stats(original: str, anon: str, tokens: list) -> dict:
    """
    Podstawowe statystyki pokrycia:
      - ile tokenów każdego typu
      - czy jakiś token nie zastąpił oryginału (original widoczny w wyjściu)
    """
    type_counts: dict = {}
    leaks: list = []

    for t in tokens:
        ttype = t.get("type", "INNE")
        type_counts[ttype] = type_counts.get(ttype, 0) + 1

        original_val = t.get("original", "")
        if original_val and len(original_val) >= 4:
            if original_val.lower() in anon.lower():
                leaks.append({
                    "token":    t.get("token", ""),
                    "original": original_val,
                })

    return {
        "type_counts": type_counts,
        "total":       len(tokens),
        "leaks":       leaks,
        "leak_count":  len(leaks),
    }


def _write_record(
    pse_code:      str,
    original_text: str,
    anon_text:     str,
    tokens:        list,
    guard_blocked: bool,
    guard_reasons: list,
    error:         str | None,
) -> None:
    stats   = _coverage_stats(original_text, anon_text, tokens)
    summary = _build_token_summary(tokens)

    record = {
        "timestamp":     datetime.now().isoformat(timespec="seconds"),
        "pse":           pse_code,
        "error":         error,
        "guard_blocked": guard_blocked,
        "guard_reasons": guard_reasons,
        "stats":         stats,
        "tokens":        summary,
        "input_length":  len(original_text),
        "output_length": len(anon_text),
        # input_fragment i output_fragment usunięte — zawierały PII
    }

    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Skrócone info w głównym logu — bez PII
    leak_info  = f" ⚠ LEAKS: {stats['leak_count']}" if stats["leak_count"] else ""
    guard_info = " GUARD_BLOCKED" if guard_blocked else ""
    logger.info(
        "[AUDIT] %s — %d tokenów %s%s%s",
        pse_code,
        stats["total"],
        str(stats["type_counts"]),
        leak_info,
        guard_info,
    )
