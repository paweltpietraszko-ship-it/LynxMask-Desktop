"""
benchmark_ocr_diagnostics.py — LYNX-OCR-PARITY krok 1: „silnik czy OCR” dla benchmark.py.

Dodatkowy widok do dotychczasowych metryk benchmarku (ich nie zmienia). Zasada z Mobile
(BenchmarkInstrumentedTest.kt: classifyMiss, fuzzyMatch, classifyExtraToken):
  pominięta encja gold →
    BUG_SILNIKA        — wartość jest w tekście oddanym silnikowi (`original_text` z /preview) jako całość
                         (tolerancja spacji/łączników, nie fragment dłuższej wartości); KANDYDAT, nie dowód.
    OCR_ZNIEKSZTAŁCONY — brak dokładnej, jest bliski odpowiednik na granicach słów jednej linii
                         (Levenshtein: ≥9 znaków, odległość 1 / 2 od 15 / 3 od 24).
    BRAK_W_OCR         — brak dokładnego i bliskiego odpowiednika (nie dowód, że nic nie zostało na obrazie).
    NOT_MEASURED       — brak/pusty `original_text`; REVIEW — tylko wewnątrz dłuższej wartości albo <9 znaków.
  token spoza gold (legacy false_positives) → EXTRA_MASK_OK / EXTRA_MASK_POLICY / UX_FP / REVIEW.
Dokumenty odrzucone przez OCR i z błędem HTTP nie są klasyfikowane. Raport `ocr_diagnostics.json`
bez wartości, fragmentów OCR i tokenów API — tylko ID pliku, klucz gold, typ, etykieta, powód.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MISS_LABELS = ("BUG_SILNIKA", "OCR_ZNIEKSZTAŁCONY", "BRAK_W_OCR", "NOT_MEASURED", "REVIEW")
EXTRA_LABELS = ("EXTRA_MASK_OK", "EXTRA_MASK_POLICY", "UX_FP", "REVIEW")
POLICY_MASK_TYPES = frozenset({"KWOTA", "NUMER"})  # produkt zawsze maskuje, gold ich nie opisuje
UX_FP_DENYLIST = ("daneosobowe", "danychosobowych", "danekontaktowe")  # jak Mobile; tylko potwierdzone frazy
MIN_FUZZY_LEN = 9


def norm(v: str) -> str:
    """Identyczna z benchmark._norm (test pilnuje zgodności): nowa linia → spacja, bez spacji i łączników, małe litery."""
    v = v.replace("\n", " ").replace("\r", " ")
    while "  " in v:
        v = v.replace("  ", " ")
    return v.replace(" ", "").replace("-", "").lower()


def max_distance(length: int) -> int:
    return 3 if length >= 24 else 2 if length >= 15 else 1


def levenshtein(a: str, b: str, limit: int) -> int:
    """Odległość edycyjna; przerywa po przekroczeniu `limit` (zwraca limit + 1)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def fuzzy_equal(a: str, b: str) -> bool:
    """Bliski odpowiednik znormalizowanych wartości (próg skalowany długością, jak Mobile)."""
    if len(a) < MIN_FUZZY_LEN or len(b) < MIN_FUZZY_LEN:
        return False
    d = max_distance(max(len(a), len(b)))
    return abs(len(a) - len(b)) <= d and levenshtein(a, b, d) <= d


def _line_candidates(line: str, target_len: int, d: int):
    """Ciągi kolejnych słów jednej linii o długości po normalizacji w [target_len-d, target_len+d]."""
    words = line.split()
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            cand = norm(" ".join(words[i:j]))
            if len(cand) > target_len + d:
                break
            if len(cand) >= target_len - d:
                yield cand


def has_fuzzy_counterpart(value_n: str, text: str) -> bool:
    if len(value_n) < MIN_FUZZY_LEN:
        return False
    d = max_distance(len(value_n))
    # kandydat zawierający cały gold plus dopisane znaki to dłuższa obca wartość, nie zniekształcenie (Codex r2 F1)
    return any(fuzzy_equal(value_n, c) and value_n not in c
               for line in text.splitlines() for c in _line_candidates(line, len(value_n), d))


_LEFT_JOIN = "._%+@-"   # znak przed wartością, który czyni ją częścią dłuższej (skrzynka, nazwisko złożone)
_RIGHT_JOIN = "@_-"


def present_as_whole(value_n: str, text: str) -> bool:
    """Wartość w tekście jako całość: tolerancja spacji/łączników/wielkości liter, ale nie fragment dłuższej
    wartości (Codex r2 F1: „Nowak” w „Nowakowski”, skrzynka w dłuższej skrzynce, cyfry w dłuższym numerze)."""
    if not value_n:
        return False
    sep = r"[\s\-]*"
    pattern = sep.join(re.escape(ch) for ch in value_n)
    for m in re.finditer(pattern, text, re.IGNORECASE):
        before = text[m.start() - 1] if m.start() > 0 else " "
        after = text[m.end()] if m.end() < len(text) else " "
        if not (before.isalnum() or before in _LEFT_JOIN) and not (after.isalnum() or after in _RIGHT_JOIN):
            return True
    return False


def classify_miss(value: str, original_text: Any) -> tuple[str, str | None]:
    """Etykieta i powód dla encji gold pominiętej przez dotychczasowe `analyze`."""
    if not isinstance(original_text, str) or not original_text.strip():
        return "NOT_MEASURED", "no_original_text"
    value_n = norm(value)
    if present_as_whole(value_n, original_text):
        return "BUG_SILNIKA", None
    if has_fuzzy_counterpart(value_n, original_text):
        return "OCR_ZNIEKSZTAŁCONY", None
    if value_n and value_n in norm(original_text):
        return "REVIEW", "only_inside_longer_value"
    if len(value_n) < MIN_FUZZY_LEN:
        return "REVIEW", "short_value_no_fuzzy"
    return "BRAK_W_OCR", None


def classify_extra(token: dict, gold: list[tuple[str, str]]) -> str:
    """Token spoza dopasowania gold; `gold` = [(znormalizowana wartość, oczekiwany typ)]."""
    tok_n, tok_type = norm(str(token.get("original", ""))), token.get("type")
    if any(t == tok_type and fuzzy_equal(tok_n, g) for g, t in gold):
        return "EXTRA_MASK_OK"
    if tok_type in POLICY_MASK_TYPES:
        return "EXTRA_MASK_POLICY"
    if tok_type in ("OSOBA", "ORGANIZACJA") and any(p in tok_n for p in UX_FP_DENYLIST):
        return "UX_FP"
    return "REVIEW"


def doc_status(result: dict) -> str:
    """Te same warunki co build_report: rejected / error / accepted (+ guard_blocked osobno)."""
    if result.get("ocr_rejected"):
        return "rejected"
    if result.get("bench_error") or result.get("http_status") != 200:
        return "error"
    return "guard_blocked" if result.get("guard_blocked") else "accepted"


class Collector:
    """Zbiera diagnostykę w trakcie przebiegu; surowy `original_text` tylko w pamięci wywołania."""

    def __init__(self) -> None:
        self.items: list[dict] = []
        self.docs: Counter = Counter()
        self.legacy = Counter()

    def record(self, gt: dict, resp: dict, result: dict) -> None:
        status = doc_status(result)
        self.docs[status] += 1
        if status in ("rejected", "error"):
            return
        self.legacy["privacy_missed"] += result["summary"].get("privacy_missed", 0)
        self.legacy["false_positives"] += result["summary"].get("false_positives", 0)
        original = resp.get("original_text")
        for e in result["entities"]:
            if not e["privacy_found"]:
                label, reason = classify_miss(e["value"], original)
                self._add(result["file"], "miss", e["key"], e["expected_type"], label, reason, status)
        gold = [(norm(e["value"]), e["expected_type"]) for e in result["entities"]]
        for i, fp in enumerate(result.get("false_positives", [])):
            self._add(result["file"], "extra", f"token_{i}", fp.get("type"), classify_extra(fp, gold), None, status)

    def _add(self, file: str, kind: str, key: str, typ: Any, label: str, reason: str | None, status: str) -> None:
        self.items.append({"file": file, "kind": kind, "key": key, "type": typ, "label": label,
                           "reason": reason, "doc_status": status})

    def summary(self) -> dict:
        miss = Counter(i["label"] for i in self.items if i["kind"] == "miss")
        miss_guard = Counter(i["label"] for i in self.items if i["kind"] == "miss" and i["doc_status"] == "guard_blocked")
        extra = Counter(i["label"] for i in self.items if i["kind"] == "extra")
        by_type = Counter(f"{i['kind']}:{i['type']}:{i['label']}" for i in self.items)
        return {"docs": {k: self.docs.get(k, 0) for k in ("accepted", "guard_blocked", "rejected", "error")},
                "miss": {k: miss.get(k, 0) for k in MISS_LABELS},
                "miss_in_guard_blocked_docs": dict(miss_guard),
                "extra": {k: extra.get(k, 0) for k in EXTRA_LABELS},
                "by_type": dict(sorted(by_type.items())),
                "consistent_with_legacy": (sum(miss.values()) == self.legacy["privacy_missed"]
                                           and sum(extra.values()) == self.legacy["false_positives"])}

    def write(self, run_dir: Path) -> dict:
        s = self.summary()
        items = sorted(self.items, key=lambda i: (i["file"], i["kind"], i["key"]))
        with open(Path(run_dir) / "ocr_diagnostics.json", "w", encoding="utf-8") as f:
            json.dump({"summary": s, "items": items}, f, ensure_ascii=False, indent=2)
        print("[OCR-DIAG] pominięte " + " ".join(f"{k}={v}" for k, v in s["miss"].items())
              + " | spoza gold " + " ".join(f"{k}={v}" for k, v in s["extra"].items())
              + " | dok. " + " ".join(f"{k}={v}" for k, v in s["docs"].items())
              + f" | zgodność z legacy: {'OK' if s['consistent_with_legacy'] else 'ROZJAZD'}")
        return s


_DEFAULT = Collector()


def record(gt: dict, resp: dict, result: dict) -> None:
    _DEFAULT.record(gt, resp, result)


def write(run_dir: Path) -> dict:
    return _DEFAULT.write(run_dir)


def analyze_and_record(analyze_fn, gt: dict, resp: dict) -> dict:
    """Wywołanie z benchmark.run_benchmark (zamiast samego analyze — funkcja nie rośnie, ratchet gate)."""
    result = analyze_fn(gt, resp)
    record(gt, resp, result)
    return result


def build_report_and_write(build_fn, results: list, run_dir: Path) -> dict:
    """Wywołanie z benchmark.main: dotychczasowy raport bez zmian, potem ocr_diagnostics.json."""
    build_fn(results, run_dir)
    return write(run_dir)
