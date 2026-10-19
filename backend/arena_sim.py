"""
arena_sim.py — LYNX-ARCH-ARENA v0.1: deterministyczny obrońca gry falsyfikującej architekturę kandydatów.

Eksperyment (gałąź experiment/lynx-architecture-arena), NIE ścieżka pseudonimizacji produktu:
pipeline/API go nie importują. Tylko stdlib, bez modeli i sieci.

Uruchomienie: cd backend && py -3 arena_sim.py   (STDIN: JSONL, STDOUT: JSONL, jedna linia na przypadek)
Wejście:  {"text": str, "base_candidates": [{"start","end","kind","source","evidence"}], "mode": "full"}
Wyjście:  {"status": "RENDERED"|"STOP", "masked", "tokens", "trace", "reason_code", "guard_flags"}

Fazy (brief r2): A BASE → B/C ANCHOR (@ i ul. na ORYGINALE) → D ARBITER → E ONE APPLY → F GUARD-DRON.
reason_code (stabilne): INVALID_INPUT, TOKEN_INJECTION, ANCHOR_UNCERTAIN, AMBIGUOUS, WORD_BOUNDARY, INTERNAL_ERROR.
WORD_BOUNDARY (v0.1.1, Codex r4 F1): przyjęty span zaczyna się lub kończy w środku wyrazu (N2) — odmowa zamiast sklejonego tokenu.
Trace: tylko metadane (faza, typ, indeksy, decyzja) — bez wartości; wyjątek nigdy nie ujawnia tekstu.

Decyzja CC (luka briefu, D.ii): kotwica, której wyprowadzony span leży W CAŁOŚCI wewnątrz kandydata BASE tego samego
typu, jest „zakryta” (B: „szuka niezakrytych kotwic”) i odpada z decyzją anchor_covered — BASE pozostaje.
Każde inne zawieranie się spanów tego samego typu, w którym większy nie pochodzi z kotwicy, to STOP/AMBIGUOUS.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata

KINDS = ("FIRMA", "OSOBA", "NUMER", "KWOTA", "ADRES", "INSTYTUCJA", "EMAIL")
TOKEN_RE = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")  # S2
_HSPACE = " \t"
_EMAIL_LEFT = "._%+-"
_EMAIL_RIGHT = ".,_-"
_UL_STOP = ",;:!?.\n\r"
_UL_RE = re.compile(r"(?i)(?<![^\W_])ul\.[ \t]+")
_GUARD_UL = re.compile(r"(?i)(?<![^\W_])ul\.(?=[ \t\r\n]|$)")
_GUARD_ID = re.compile(r"(?<!\w)(?i:PESEL|NIP)(?!\w)[ \t]*(?::[ \t]*)?[0-9OolIiSsBbZz](?:[ \t-]*[0-9OolIiSsBbZz]){2,}")


class Stop(Exception):
    """Uzasadniona odmowa z kodem powodu (bez treści wejścia)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ── A. BASE ─────────────────────────────────────────────────────────────────────
def _base(text: str, raw: object, trace: list) -> list[dict]:
    if not isinstance(raw, list):
        raise Stop("INVALID_INPUT")
    merged: dict[tuple, dict] = {}
    for c in raw:
        if not isinstance(c, dict):
            raise Stop("INVALID_INPUT")
        s, e, k = c.get("start"), c.get("end"), c.get("kind")
        if type(s) is not int or type(e) is not int or not (0 <= s < e <= len(text)) or k not in KINDS:
            raise Stop("INVALID_INPUT")
        ev = c.get("evidence") or []
        if not isinstance(ev, list):
            raise Stop("INVALID_INPUT")
        key = (s, e, k)
        cur = merged.setdefault(key, {"start": s, "end": e, "kind": k, "origin": "base", "evidence": set()})
        cur["evidence"].update(str(x) for x in ev)  # te same dowody z dwóch silników liczone raz
    for c in merged.values():
        trace.append({"phase": "base", "kind": c["kind"], "start": c["start"], "end": c["end"], "decision": "accepted"})
    return list(merged.values())


# ── B/C. ANCHOR ─────────────────────────────────────────────────────────────────
def _email_span(text: str, at: int) -> tuple[int, int]:
    s = at
    while s > 0 and (text[s - 1].isalnum() or text[s - 1] in _EMAIL_LEFT):
        s -= 1
    e = at + 1
    if e >= len(text) or not text[e].isalnum():
        raise Stop("ANCHOR_UNCERTAIN")
    while e < len(text) and (text[e].isalnum() or text[e] in _EMAIL_RIGHT):
        e += 1
    while e > at + 1 and text[e - 1] in ".,":  # terminalna interpunkcja nie jest wartością
        e -= 1
    return s, _email_tail(text, e)


def _email_tail(text: str, e: int) -> int:
    """Jeden opcjonalny ogon: poziome spacje + '.' + 2–4 litery, potem koniec/spacja/interpunkcja."""
    i = e
    while i < len(text) and text[i] in _HSPACE:
        i += 1
    if i == e or i >= len(text) or text[i] != ".":
        return e
    j = i + 1
    while j < len(text) and text[j].isalpha():
        j += 1
    n = j - i - 1
    nxt = text[j] if j < len(text) else None
    if 2 <= n <= 4 and (nxt is None or nxt.isspace() or not (nxt.isalnum() or nxt == "_")):
        return j
    return e


def _address_span(text: str, m: re.Match) -> tuple[int, int]:
    i, end, members = m.end(), None, 0
    while members < 3 and i < len(text) and text[i].isalnum():
        j = i
        while j < len(text) and (text[j].isalnum() or text[j] in "-/"):
            j += 1
        end, members = j, members + 1
        k = j
        while k < len(text) and text[k] in _HSPACE:
            k += 1
        if k == j or k >= len(text) or text[k] in _UL_STOP:
            break
        i = k
    if end is None:
        raise Stop("ANCHOR_UNCERTAIN")
    return m.start(), end


def _anchors(text: str, base: list[dict], trace: list) -> list[dict]:
    found = [("EMAIL", *_email_span(text, i)) for i, ch in enumerate(text) if ch == "@"]
    emails = sorted({(s, e) for _, s, e in found})
    for (s1, e1), (s2, e2) in zip(emails, emails[1:]):
        if s2 < e1:  # wyprowadzone spany dwóch kotwic @ nakładają się, a nie są identyczne
            raise Stop("AMBIGUOUS")
    found += [("ADRES", *_address_span(text, m)) for m in _UL_RE.finditer(text)]
    out = []
    for kind, s, e in sorted(set(found), key=lambda x: (x[1], x[2], x[0])):
        covered = any(b["kind"] == kind and b["start"] <= s and e <= b["end"] and (b["start"], b["end"]) != (s, e)
                      for b in base)
        trace.append({"phase": "anchor", "kind": kind, "start": s, "end": e,
                      "decision": "anchor_covered" if covered else "proposed"})
        if not covered:
            ev = "ANCHOR_AT" if kind == "EMAIL" else "ANCHOR_UL"
            out.append({"start": s, "end": e, "kind": kind, "origin": "anchor", "evidence": {ev}})
    return out


# ── D. ARBITER ──────────────────────────────────────────────────────────────────
def _arbiter(text: str, cands: list[dict], trace: list) -> list[dict]:
    merged: dict[tuple, dict] = {}
    for c in sorted(cands, key=lambda c: (c["start"], c["end"], c["kind"])):
        key = (c["start"], c["end"], c["kind"])
        if key in merged:  # dokładny duplikat (base + anchor): jeden kandydat, dowody scalone
            merged[key]["evidence"] |= c["evidence"]
            merged[key]["origin"] = "base+anchor"
        else:
            merged[key] = dict(c, evidence=set(c["evidence"]))
    items, dropped = list(merged.values()), set()
    for a_i, a in enumerate(items):
        for b in items[a_i + 1:]:
            if not (a["start"] < b["end"] and b["start"] < a["end"]):
                continue
            if a["kind"] != b["kind"]:
                raise Stop("AMBIGUOUS")
            dropped.add(_contained_loser(a, b))
    kept = [c for c in items if id(c) not in dropped]
    for c in kept:  # N2 (Codex r4 F1): granica w środku wyrazu → nie wydajemy sklejonego tokenu, nie poszerzamy spanu
        if _inside_word(text, c["start"]) or _inside_word(text, c["end"]):
            raise Stop("WORD_BOUNDARY")
    for c in items:
        trace.append({"phase": "arbiter", "kind": c["kind"], "start": c["start"], "end": c["end"],
                      "decision": "dropped_contained" if id(c) in dropped else "kept"})
    return kept


def _contained_loser(a: dict, b: dict) -> int:
    """D.ii: ten sam typ, jeden zawiera drugi — większy zostaje tylko gdy wynika z kotwicy C, a mniejszy pochodzi
    z BASE (także BASE identyczny z kotwicą). Dwie różne kotwice zawierające się → brak dowodu granic → STOP."""
    if a["start"] <= b["start"] and b["end"] <= a["end"]:
        big, small = a, b
    elif b["start"] <= a["start"] and a["end"] <= b["end"]:
        big, small = b, a
    else:
        raise Stop("AMBIGUOUS")  # D.iii: częściowe nakładanie
    if "anchor" not in big["origin"] or small["origin"] not in ("base", "base+anchor"):
        raise Stop("AMBIGUOUS")
    return id(small)


def _word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_" or unicodedata.category(ch).startswith("M")  # Codex r5: kategoria M (nie tylko combining>0)


def _inside_word(text: str, i: int) -> bool:
    return 0 < i < len(text) and _word_char(text[i - 1]) and _word_char(text[i])


# ── E. ONE APPLY ────────────────────────────────────────────────────────────────
def _apply(text: str, kept: list[dict]) -> tuple[str, list[dict]]:
    kept = sorted(kept, key=lambda c: c["start"])
    counters: dict[str, int] = {}
    by_value: dict[tuple, str] = {}
    tokens = []
    for c in kept:  # numeracja wg położenia; ta sama dosłowna wartość → ten sam token
        original = text[c["start"]:c["end"]]
        key = (c["kind"], original)
        if key not in by_value:
            counters[c["kind"]] = counters.get(c["kind"], 0) + 1
            by_value[key] = f"{c['kind']}_{counters[c['kind']]:03d}"
        tokens.append({"token": by_value[key], "kind": c["kind"], "start": c["start"], "end": c["end"],
                       "original": original})
    masked = text
    for t in reversed(tokens):  # jedna podmiana na oryginale, od prawej
        masked = masked[:t["start"]] + t["token"] + masked[t["end"]:]
    return masked, tokens


# ── F. GUARD-DRON (atrapa, NIE OutputGuard) ─────────────────────────────────────
def _guard(masked: str) -> list[dict]:
    flags = {("AT_REMAINS", i, i + 1) for i, ch in enumerate(masked) if ch == "@"}
    flags |= {("UL_REMAINS", m.start(), m.end()) for m in _GUARD_UL.finditer(masked)}
    flags |= {("ID_LABEL_REMAINS", m.start(), m.end()) for m in _GUARD_ID.finditer(masked)}
    return [{"kind": k, "start": s, "end": e} for k, s, e in sorted(flags, key=lambda f: (f[1], f[2], f[0]))]


# ── Przypadek i pętla JSONL ─────────────────────────────────────────────────────
def run_case(case: object) -> dict:
    trace: list = []
    try:
        if not isinstance(case, dict) or not isinstance(case.get("text"), str) or case.get("mode", "full") != "full":
            raise Stop("INVALID_INPUT")
        text = case["text"]
        if TOKEN_RE.search(text):
            raise Stop("TOKEN_INJECTION")
        base = _base(text, case.get("base_candidates", []), trace)
        kept = _arbiter(text, base + _anchors(text, base, trace), trace)
        masked, tokens = _apply(text, kept)
        return {"status": "RENDERED", "masked": masked, "tokens": tokens, "trace": trace,
                "reason_code": None, "guard_flags": _guard(masked)}
    except Stop as s:
        code = s.code
    except Exception:  # noqa: BLE001 — bez treści wyjątku (może zawierać tekst wejścia)
        code = "INTERNAL_ERROR"
    trace.append({"phase": "arbiter", "kind": None, "start": None, "end": None, "decision": f"stop:{code}"})
    return {"status": "STOP", "masked": None, "tokens": [], "trace": trace, "reason_code": code, "guard_flags": []}


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except ValueError:
            case = None
        sys.stdout.write(json.dumps(run_case(case), ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
