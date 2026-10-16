#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dict_auto_builder.py v1.0
===========================
Automatycznie buduje słowniki z wyników testów — bez ręcznego JSON.

Źródła (szuka sam, bierze najnowsze):
  - benchmark_results/**/missed_candidates.json
  - benchmark_results/**/bugs.txt  (FP → blocklist NER)
  - smoke_e2e_report.txt / benchmark_results/smoke/smoke_e2e_report.txt

Wyjście:
  dict_templates/generated/auto_kontrahenci.json   → import do profilu
  dict_templates/generated/auto_ner_boilerplate.json → dla Claude → ner_blocklist.py
  dict_templates/generated/auto_engine_fixes.txt   → NIP/email/telefon (regex, nie słownik)

Uruchomienie:
  python dict_auto_builder.py
  python dict_auto_builder.py --apply          # od razu wrzuca do profilu biura
  python dict_auto_builder.py --run-benchmark  # najpierw benchmark, potem build

Dla Pawła: odpal run_dict_auto.bat i daj Claude pliki z folderu generated/.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
BENCHMARK_ROOT = BACKEND_DIR / "benchmark_results"
OUT_DIR = BACKEND_DIR / "dict_templates" / "generated"
PROFILE_DIR = Path(
    __import__("os").getenv(
        "ANONYMIZER_PROFILE_DIR",
        str(BACKEND_DIR / "anon_profiles" / "pseudominizer"),
    )
)

# entity_key z benchmark → typ tokenu w profilu (pominięte = silnik regex)
_KEY_TO_TYPE: dict[str, str | None] = {
    "imie_nazwisko": "OSOBA",
    "imie_nazwisko_nabywcy": "OSOBA",
    "imie_nazwisko_zleceniodawca": "OSOBA",
    "imie_nazwisko_zleceniobiorca": "OSOBA",
    "autor": "OSOBA",
    "osoba": "OSOBA",
    "adres": "ADRES",
    "adres_nabywcy": "ADRES",
    "adres_zleceniobiorca": "ADRES",
    "adres_zleceniodawca": "ADRES",
    "email": "EMAIL",
    # structural — nie do trie
    "pesel": None,
    "nip": None,
    "nip_sprzedawcy": None,
    "nip_nabywcy": None,
    "iban": None,
    "telefon": None,
    "regon_sprzedawcy": None,
    "dowod_osobisty": None,
    "numer_paszportu": None,
    "numer_kw": None,
    "numer_faktury": None,
    "data_urodzenia": None,
}

# FP z bugs.txt — heurystyka: jedno słowo / etykieta dokumentu → blocklist
_BOILERPLATE_FP = re.compile(
    r"→\s*\[(?:OSOBA|FIRMA|ORGANIZACJA)\]\s*\"([^\"]+)\"",
    re.IGNORECASE,
)
_BLOCKLIST_HINTS = {
    "dluznik", "dluznika", "wierzyciel", "wierzyciela", "nabywca", "sprzedawca",
    "platnosc", "platnosci", "odebral", "odebrala", "doreczone", "doreczono",
    "wplata", "wplate", "poucze", "pouczenie", "orzekam", "oswiadczenia",
    "oswiadczenie", "podpisi", "podnisi", "podpis", "zalacznik", "wezwanie",
    "zleceniodawca", "zleceniobiorca", "zamawiajacy", "wykonawca", "faktura",
    "fakturavvat", "platnosc", "komornik", "dluznikowi",
}

_SMOKE_LINE = re.compile(r"^\s*\[(OSOBA|FIRMA|ADRES|EMAIL|INSTYTUCJA)\]\s*(.+)$")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.strip().lower())


def _latest_files(pattern: str) -> list[Path]:
    hits = sorted(BENCHMARK_ROOT.rglob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return hits


def _collect_missed() -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for path in _latest_files("missed_candidates.json")[:3]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            cand = str(row.get("candidate", "")).strip()
            if not cand or _norm(cand) in seen:
                continue
            seen.add(_norm(cand))
            out.append({**row, "_from": str(path.relative_to(BACKEND_DIR))})
    return out


def _collect_smoke_entries() -> list[dict]:
    paths = [
        BACKEND_DIR / "smoke_e2e_report.txt",
        BENCHMARK_ROOT / "smoke" / "smoke_e2e_report.txt",
    ]
    for extra in _latest_files("smoke_e2e_report.txt")[:2]:
        if extra not in paths:
            paths.append(extra)

    entries: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = _SMOKE_LINE.match(line)
            if not m:
                continue
            typ, val = m.group(1), m.group(2).strip()
            if typ == "INSTYTUCJA":
                typ = "FIRMA"
            if typ in ("KWOTA", "NUMER"):
                continue
            if len(val) < 4 or _norm(val) in seen:
                continue
            # fragmenty zbyt krótkie / ogólne
            if val.lower() in ("kancelarii", "kancelaria prawna", "wspólnicy sp. z o.o"):
                continue
            seen.add(_norm(val))
            entries.append({
                "value": val,
                "type": typ,
                "source": f"smoke:{path.name}",
            })
    return entries


def _collect_fp_blocklist() -> list[str]:
    words: set[str] = set()
    for path in _latest_files("bugs.txt")[:3]:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in _BOILERPLATE_FP.finditer(text):
            raw = m.group(1).strip()
            n = _norm(raw)
            if len(n) < 4:
                continue
            # prawdziwe imię+nazwisko (2 słowa, oba >2 znaki) — nie blocklist
            parts = n.split()
            if len(parts) >= 2 and all(len(p) > 2 for p in parts[:2]):
                if not any(h in n for h in _BLOCKLIST_HINTS):
                    continue
            if any(h in n for h in _BLOCKLIST_HINTS):
                words.add(n)
            elif len(parts) == 1 and n in _BLOCKLIST_HINTS:
                words.add(n)
            elif raw[0].isupper() and len(raw.split()) == 1 and len(raw) > 5:
                # pojedyncze dziwne słowo typu Ośwadczenia, Podpisi
                if raw.lower().endswith(("nosci", "enie", "al", "ek", "ka")):
                    words.add(n)
    return sorted(words)


def _missed_to_entries(missed: list[dict]) -> tuple[list[dict], list[str]]:
    dict_entries: list[dict] = []
    engine_fixes: list[str] = []

    for row in missed:
        cand = str(row.get("candidate", "")).strip()
        key = str(row.get("entity_key", "")).strip()
        tok_type = _KEY_TO_TYPE.get(key)
        if tok_type is None:
            if key:
                engine_fixes.append(f"{key}: {cand}  ({row.get('source_file', '?')})")
            continue
        dict_entries.append({
            "value": cand,
            "type": tok_type,
            "forms": [],
            "source": f"benchmark:{row.get('source_file', '?')} key={key}",
            "_auto": True,
        })
    return dict_entries, engine_fixes


def _merge_entries(*groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for e in group:
            val = str(e.get("value", "")).strip()
            if not val:
                continue
            k = f"{e.get('type', '?')}:{_norm(val)}"
            if k in seen:
                continue
            seen.add(k)
            merged.append(e)
    return merged


def _apply_to_profile(entries: list[dict]) -> dict[str, str]:
    from anonymizer import AnonymizerMap
    from morfeusz_env import MorfEnv

    morf = MorfEnv()
    morf.load()
    amap = AnonymizerMap(PROFILE_DIR, morf)
    batch = [(e["value"], e["type"]) for e in entries if e.get("type") in (
        "FIRMA", "OSOBA", "ADRES", "EMAIL", "NUMER", "KWOTA"
    )]
    if not batch:
        return {}
    return amap.add_entities_batch(batch)


def build(apply: bool = False) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    missed = _collect_missed()
    from_missed, engine_fixes = _missed_to_entries(missed)
    from_smoke = _collect_smoke_entries()
    blocklist = _collect_fp_blocklist()

    entries = _merge_entries(from_missed, from_smoke)

    kontrahenci = {
        "_schema": "lynxmask-dict-import v1",
        "_generated": ts,
        "_note": "Wygenerowano automatycznie — nie edytuj ręcznie, odpal dict_auto_builder.py",
        "entries": entries,
    }
    boilerplate = {
        "_schema": "lynxmask-ner-blocklist-import v1",
        "_generated": ts,
        "_note": "Claude: dopisz words do ner_blocklist.py _NER_BLOCKLIST",
        "words": blocklist,
    }

    (OUT_DIR / "auto_kontrahenci.json").write_text(
        json.dumps(kontrahenci, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "auto_ner_boilerplate.json").write_text(
        json.dumps(boilerplate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixes_text = "\n".join([
        f"AUTO ENGINE FIXES — {ts}",
        "Te encje NIE idą do słownika — poprawka regex/warstwy (Claude):",
        "",
        *engine_fixes,
    ]) + "\n"
    (OUT_DIR / "auto_engine_fixes.txt").write_text(fixes_text, encoding="utf-8")

    print(f"\n[dict_auto] Wygenerowano w: {OUT_DIR}")
    print(f"  Słownik (maskowanie):  {len(entries)} wpisów")
    print(f"  Blocklist NER:         {len(blocklist)} słów")
    print(f"  Do silnika (nie dict): {len(engine_fixes)} pozycji")

    if apply and entries:
        print("\n[dict_auto] Import do profilu biura...")
        try:
            result = _apply_to_profile(entries)
            print(f"  Zaimportowano / dopasowano: {len(result)} encji")
        except Exception as e:
            print(f"  BŁĄD importu: {e}")
            print("  Pliki JSON zapisane — Claude może importować ręcznie.")
            return 1

    print("\n[dict_auto] Dla Claude: przeczytaj generated/auto_*.json i auto_engine_fixes.txt")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-builder słowników LynxMask")
    ap.add_argument("--apply", action="store_true", help="Importuj od razu do profilu biura")
    ap.add_argument(
        "--run-benchmark",
        action="store_true",
        help="Uruchom benchmark.py --count 50 przed buildem",
    )
    args = ap.parse_args()

    if args.run_benchmark:
        import subprocess
        print("[dict_auto] Uruchamiam benchmark...")
        subprocess.run(
            [__import__("sys").executable, str(BACKEND_DIR / "benchmark.py"), "--count", "50"],
            cwd=str(BACKEND_DIR),
            check=False,
        )

    return build(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
