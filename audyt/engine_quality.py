"""LYNX-DICT-LEAKTEST etap 1 — pomiar jakości silnika M1–M3 bez zmian silnika. Dane syntetyczne.

M1: wycieki na czystym tekście (+ holdout rozłącznych nazwisk), M2: fałszywe trafienia na tekście bez encji,
M3: wierność symulowanego Przywróć (audyt/unmask_sim.py; osobno kolejność wstawiania jak Object.keys w UI).
Produkcyjny pipeline.pseudonymize_document + AppState z prawdziwym NER, profil wyłącznie w TemporaryDirectory.
Raport bez tekstów i wartości encji — tylko ID przypadków, statusy i liczby. Raportu nie wolno zapisać w repo.
Użycie (z korzenia repo): py -3 audyt/engine_quality.py --seed 2026 --out <poza-repo>/quality.json
    [--holdout <ścieżka do JSON {nazwisko: [formy]}, np. Mobile app/src/main/assets/surnames_extended.json>]
Kod wyjścia: 0 OK, 2 NOT_RUN (brak spaCy/Morfeusza — bez atrapy NER).
"""
import argparse
import datetime
import difflib
import gc
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path[:0] = [BACKEND, os.path.join(ROOT, "audyt")]

# bez \b na początku: token bywa sklejony z cyframi („PL6110NUMER_001” — IBAN-RECEPTA)
TOKEN_RE = re.compile(r"(?<![A-Za-z_])(?:OSOBA|FIRMA|INSTYTUCJA|NUMER|EMAIL|KWOTA|ADRES)_\d{3,}(?!\d)")

M1_TEMPLATES = {  # typ pisma → szablon ze slotem {E}
    "urzedowe": "Organ prowadzący postępowanie wskazuje stronę: {E}. Sprawę prowadzi referat B.",
    "umowa": "§ 1. Wykonawca: {E}. Umowa obowiązuje od dnia podpisania.",
    "faktura": "Faktura VAT nr 12/2026. Nabywca: {E}. Termin płatności 14 dni.",
    "korespondencja": "Dzień dobry, w sprawie zgłoszenia podaję dane: {E}. Pozdrawiam serdecznie.",
}
M1_ENTITIES = [  # (kategoria oczekiwana, wariant, wstawiany tekst, oczekiwany span)
    ("OSOBA", "pelne", "Jan Kowalski", "Jan Kowalski"),
    ("OSOBA", "odmiana", "pismo Anny Wiśniewskiej", "Anny Wiśniewskiej"),
    ("OSOBA", "tytul", "dr Piotr Nowak", "Piotr Nowak"),
    ("OSOBA", "caps", "JAN KOWALSKI", "JAN KOWALSKI"),
    ("OSOBA", "inicjal", "J. Kowalski", "J. Kowalski"),
    ("FIRMA", "spzoo", "Budex Sp. z o.o.", "Budex Sp. z o.o"),
    ("ADRES", "pelny", "ul. Długa 5, 00-950 Warszawa", "ul. Długa 5, 00-950 Warszawa"),
    ("NUMER", "nip", "NIP 526-000-12-46", "526-000-12-46"),
    ("NUMER", "pesel", "PESEL 44051401359", "44051401359"),
    ("NUMER", "iban", "konto PL61 1090 1014 0000 0712 1981 2874", "PL61 1090 1014 0000 0712 1981 2874"),
    ("NUMER", "telefon", "tel. +48 512 987 654", "+48 512 987 654"),
    ("EMAIL", "email", "jan.kowalski@example.pl", "jan.kowalski@example.pl"),
]
M2_CASES = [  # (wariant, tekst bez encji OSOBA/FIRMA, {kategoria: wartości maskowane zgodnie z kontraktem})
    ("piatek", "Spotkanie odbędzie się w piątek o godzinie dziesiątej.", {}),
    ("zaplata", "Zapłata nastąpi przelewem w terminie czternastu dni.", {}),
    ("miasto", "Pracownik od lat pracuje w Radomiu i dojeżdża autobusem.", {}),
    ("instytucje", "Kontrolę przeprowadził ZUS, a dane zebrał GUS.", {"INSTYTUCJA": ["ZUS", "GUS"]}),
    ("naglowek_caps", "ZAKRES OBOWIĄZKÓW\nOpis stanowiska znajduje się poniżej.", {}),
    ("akronimy", "System ERP i CRM wdrożono w dziale IT w zeszłym roku.", {}),
    ("ulica_patronimiczna", "Biuro mieści się przy ul. Kowalskiego 7 w centrum.", {"ADRES": ["ul. Kowalskiego 7"]}),
    ("kwota", "Do zapłaty pozostaje 1 250,00 zł brutto.", {"KWOTA": ["1 250,00 zł"]}),
]
HOLDOUT_N = 40
HOLDOUT_TEMPLATE = "Wniosek złożył Pan {E} w dniu wczorajszym."


def build_cases():
    """Deterministyczna lista M1/M2: (id, sekcja, kategoria, tekst, span|None, dozwolone kategorie)."""
    cases = [(f"M1-{doc}-{cat}-{var}", "M1", cat, tpl.format(E=ins), span, {})
             for doc, tpl in M1_TEMPLATES.items() for cat, var, ins, span in M1_ENTITIES]
    cases += [(f"M2-{var}", "M2", None, text, None, allowed) for var, text, allowed in M2_CASES]
    return cases


def load_holdout(path, seed):
    """Nazwiska rozłączne ze słownikami silnika i szablonami M1. None = brak danych (NOT_MEASURED)."""
    if not path or not os.path.exists(path):
        return None, {"status": "NOT_MEASURED", "reason": "brak pliku holdout"}
    from ner_blocklist import _PERSON_FORMS
    used = {w.lower() for _, _, ins, _ in M1_ENTITIES for w in ins.split()}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    pool = sorted(base for base, forms in data.items()
                  if {base.lower(), *map(str.lower, forms)}.isdisjoint(_PERSON_FORMS | used) and base.isalpha())
    sample = random.Random(seed).sample(pool, min(HOLDOUT_N, len(pool)))
    overlap = [s for s in sample if s.lower() in _PERSON_FORMS]
    info = {"status": "OK" if not overlap else "SEPARATION_FAILED", "pool": len(pool), "sample": len(sample),
            "rejected_overlap": len(data) - len(pool), "overlap_in_sample": len(overlap)}
    cases = [(f"H-{i:03d}", "HOLDOUT", "OSOBA", HOLDOUT_TEMPLATE.format(E=f"Jan {s.capitalize()}"),
              f"Jan {s.capitalize()}", {}) for i, s in enumerate(sample)]
    return (cases if not overlap else None), info


def _norm(s):
    return re.sub(r"\W", "", s).lower()


def _output_tokens(result):
    """Tokeny faktycznie obecne w wyniku i mające wpis w mapie — sam wpis w mapie nie dowodzi zamaskowania."""
    return {t: result.reverse_map[t] for t in TOKEN_RE.findall(result.text) if t in result.reverse_map}


def _overlaps(val, ref):
    nv, nr = _norm(val), _norm(ref)
    return bool(nv) and (nv in nr or nr in nv)


def _covering_tokens(span, rev):
    """Tokeny, których wartość (bez spacji/interpunkcji) leży w spanie lub go zawiera; drugi wynik: pełne pokrycie."""
    ns = _norm(span)
    toks = [tok for tok, val in rev.items() if _overlaps(val, span)]
    covered = sum(len(_norm(rev[t])) for t in toks if _norm(rev[t]) in ns)
    return toks, any(ns in _norm(rev[t]) for t in toks) or covered >= len(ns)


def classify_m1(text, span, cat, result):
    """Status M1: error / blocked / leak / leak_partial / partial_mask / masked / wrong_category / no_mapping / assumption."""
    if span not in text:
        return "assumption"
    if result.error:
        return "error"
    if result.guard_blocked:
        return "blocked"  # zablokowany wynik nigdy nie liczy się jako zamaskowany
    if span in result.text:
        return "leak"
    words = [w for w in re.findall(r"\w{3,}", span) if not w.isdigit() or len(w) >= 4]
    if any(re.search(rf"\b{re.escape(w)}\b", result.text) for w in words):
        return "leak_partial"
    toks, full = _covering_tokens(span, _output_tokens(result))
    if not toks:
        return "no_mapping"
    if any(t.split("_")[0] != cat for t in toks):
        return "wrong_category"  # każdy token pokrywający span musi mieć oczekiwaną kategorię
    return "masked" if full else "partial_mask"  # partial: część wartości jawna w wyniku (np. początek IBAN)


def classify_m2(allowed, result):
    """Status M2: error / blocked / fp / contract / clean. Kontrakt = token dozwolonej kategorii, którego wartość to CAŁA
    oczekiwana wartość (bez spacji/interpunkcji) i ta wartość zniknęła z wyniku (allowed: {kategoria: [wartości]}).
    Ta sama kategoria na innym słowie — także na fragmencie oczekiwanej wartości („kowal” w adresie) — to FP."""
    if result.error:
        return "error"
    if result.guard_blocked:
        return "blocked"
    toks = _output_tokens(result)
    if any(not any(_norm(v) == _norm(ref) and ref not in result.text for ref in allowed.get(t.split("_")[0], ()))
           for t, v in toks.items()):
        return "fp"
    return "contract" if toks else "clean"


def _insertion_unmask(text, rev):
    for tok, orig in rev.items():  # Depseudonimizuj.tsx: Object.keys(map) w kolejności wstawiania
        text = text.replace(tok, orig)
    return text


def roundtrip(original, result, spans=()):
    """M3: status i diff poza spanami encji. blocked/error nie przechodzą round-tripu."""
    from unmask_sim import unmask
    if result.error or result.guard_blocked:
        return {"status": "blocked_or_error"}
    missing = sorted(set(TOKEN_RE.findall(result.text)) - set(result.reverse_map))
    restored = unmask(result.text, result.reverse_map)
    out = {"status": "identical" if restored == original and not missing else "diff",
           "missing_map": len(missing), "order_divergence": restored != _insertion_unmask(result.text, result.reverse_map)}
    if missing:
        out["status"] = "missing_map"
    if restored != original:
        ranges = [(o.find(s), o.find(s) + len(s)) for o in [original] for s in spans if s and s in o]
        ops = [op for op in difflib.SequenceMatcher(None, original, restored, autojunk=False).get_opcodes() if op[0] != "equal"]
        out["diff_ops"] = len(ops)
        out["diff_outside_spans"] = sum(1 for op in ops if not any(a <= op[1] and op[2] <= b for a, b in ranges))
    return out


def _engine_available():
    try:
        import spacy
        spacy.load("pl_core_news_lg")
        import morfeusz2
        morfeusz2.Morfeusz()
        return True, ""
    except Exception as exc:
        return False, type(exc).__name__


def build_state(tmp):
    """AppState jak w API, profil wyłącznie w katalogu tymczasowym (bez seeda — stan produkcyjny, BUG-SEED-DEAD)."""
    from pipeline import AppState
    from anonymizer import build_anonymizer
    import spacy_ner
    st = AppState()
    st.spacy_ner_mod = spacy_ner
    st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(tmp, os.path.join(tmp, "hw.json"))
    return st


def summarize(rows, key):
    out = {}
    for r in rows:
        out.setdefault(r.get("category") or "ALL", {}).setdefault(r[key], 0)
        out[r.get("category") or "ALL"][r[key]] += 1
    return out


def measure(cases, run):
    """run(text) -> PipelineResult. Zwraca wiersze z ID i statusami (bez tekstów i wartości)."""
    rows = []
    for cid, sec, cat, text, span, allowed in cases:
        try:
            res = run(text)
        except Exception as exc:  # błąd poza pipeline — jawny status, nigdy sukces
            rows.append({"id": cid, "section": sec, "category": cat, "status": "error", "m3": {"status": "blocked_or_error"},
                         "exc": type(exc).__name__})
            continue
        status = classify_m2(allowed, res) if sec == "M2" else classify_m1(text, span, cat, res)
        rows.append({"id": cid, "section": sec, "category": cat, "status": status, "m3": roundtrip(text, res, [span] if span else [])})
    return rows


def report(rows, meta, holdout_info):
    def sec(name):
        return [r for r in rows if r["section"] == name]
    m3 = [dict(r["m3"], id=r["id"]) for r in rows if r["m3"]["status"] != "blocked_or_error"]
    return dict(meta, holdout_info=holdout_info, assumption_failures=sum(r["status"] == "assumption" for r in rows),
                M1=summarize(sec("M1"), "status"), HOLDOUT=summarize(sec("HOLDOUT"), "status") if sec("HOLDOUT") else "NOT_MEASURED",
                M2=summarize(sec("M2"), "status"),
                M3={"checked": len(m3), "identical": sum(r["status"] == "identical" for r in m3),
                    "diff_outside_spans": sum(1 for r in m3 if r.get("diff_outside_spans")),
                    "missing_map": sum(1 for r in m3 if r["missing_map"]), "order_divergence": sum(r["order_divergence"] for r in m3),
                    "not_identical_ids": [r["id"] for r in m3 if r["status"] != "identical"]},
                cases=[{k: r[k] for k in ("id", "status")} for r in rows])


def _out_path(path):
    full = os.path.abspath(path)
    canon = [os.path.normcase(os.path.realpath(x)) for x in (full, ROOT)]  # Windows: wielkość liter / skróty ścieżek
    if os.path.commonpath(canon) == canon[1]:
        raise SystemExit("--out wskazuje do repo — raporty zapisuj poza repozytorium")
    return full


def _layout_doc(did, entry, directory, run):
    """[LYNX-PUBLIC-DATA-TESTS] Jeden plik z lokalnego manifestu: produkcyjny _extract_text, potem pipeline. Wiersze bez wartości."""
    from document_processor import _extract_text
    fpath = os.path.join(directory, entry["file"])
    base = {"doc": did, "type": entry["type"]}
    rows = [dict(base, category=f["category"], in_table=bool(f.get("in_table"))) for f in entry["fields"]]
    if not os.path.exists(fpath):
        return {"id": did, "type": entry["type"], "status": "NOT_RUN", "reason": "brak pliku"}, [dict(r, status="NOT_RUN") for r in rows]
    content = open(fpath, "rb").read()
    info = {"id": did, "type": entry["type"], "sha256": hashlib.sha256(content).hexdigest()[:16], "n_fields": len(rows)}
    text, err, _ = _extract_text(content, os.path.basename(fpath))
    if err or not text.strip():
        return dict(info, status="NOT_RUN", reason="ekstrakcja: błąd lub pusty tekst"), [dict(r, status="NOT_RUN") for r in rows]
    res = run(text)
    for row, f in zip(rows, entry["fields"]):
        v = f["value"]
        expected = sum(g["value"] == v for g in entry["fields"])  # ta sama wartość w kilku polach (np. akapit + komórka)
        if text.count(v) >= expected:
            row["status"] = classify_m1(text, v, f["category"], res)
        elif v in text:  # mniej wystąpień niż pól — nie wiadomo, które pole dotarło; nie sukces (Codex r2 F1)
            row["status"] = "EXTRACTION_UNVERIFIED"
        else:  # pole nie dotarło do tekstu — błąd EKSTRAKCJI, nigdy „masked”
            row["status"] = "EXTRACTION_CHANGED" if _norm(v) and _norm(v) in _norm(text) else "EXTRACTION_MISSING"
    present = [f["value"] for f in entry["fields"] if f["value"] in text]
    return dict(info, status="MEASURED", m3=roundtrip(text, res, present)["status"]), rows


def measure_layout(directory, run):
    """Tryb layout: prawdziwe puste wzory DOCX/PDF wypełnione syntetyką; klucz = lokalny manifest.json. Raport tylko liczbowy."""
    path = os.path.join(directory, "manifest.json")
    if not os.path.exists(path):
        return {"status": "NOT_RUN", "reason": "brak manifest.json"}
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    docs, rows = [], []
    for i, entry in enumerate(entries, 1):
        info, doc_rows = _layout_doc(f"L-{i:03d}", entry, directory, run)
        docs.append(info)
        rows += doc_rows
    measured = [r for r in rows if r["status"] != "NOT_RUN"]
    by = {}
    for r in rows:
        key = f"{r['type']}/{'tabela' if r['in_table'] else 'tekst'}"
        by.setdefault(key, {}).setdefault(r["status"], 0)
        by[key][r["status"]] += 1
    return {"status": "OK" if measured else "NO_FIELDS_MEASURED", "docs": docs, "fields_measured": len(measured),
            "fields_not_run": len(rows) - len(measured), "by_type_location": by}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "lynx_engine_quality.json"))
    ap.add_argument("--holdout")
    ap.add_argument("--layout", help="lokalny katalog z manifest.json i wypełnionymi wzorami DOCX/PDF (poza repo lub ignorowany)")
    args = ap.parse_args(argv)
    out = _out_path(args.out)
    logging.disable(logging.CRITICAL)
    os.chdir(BACKEND)
    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    meta = {"git_sha": sha, "date": datetime.datetime.now().isoformat(timespec="seconds"), "seed": args.seed}
    ok, why = _engine_available()
    if not ok:
        rep = dict(meta, status="NOT_RUN", reason=f"NER/Morfeusz niedostępny: {why}")
        return _write(out, rep, 2)
    holdout, hinfo = load_holdout(args.holdout, args.seed)
    cases = build_cases() + (holdout or [])
    meta["input_digest"] = hashlib.sha256(json.dumps([c[:5] for c in cases], ensure_ascii=False).encode()).hexdigest()[:16]
    import pipeline
    meta.update(status="OK", pipeline="pipeline_new" if getattr(pipeline, "USE_NEW_PIPELINE", False) else "legacy", n_cases=len(cases))
    tmp = tempfile.TemporaryDirectory(prefix="lynx_quality_")
    try:
        st = build_state(tmp.name)
        rows = measure(cases, lambda t: pipeline.pseudonymize_document(t, st))
        layout = measure_layout(os.path.abspath(os.path.join(ROOT, args.layout)), lambda t: pipeline.pseudonymize_document(t, st)) if args.layout else None
    finally:
        st = None
        gc.collect()
        tmp.cleanup()
    rep = report(rows, meta, hinfo)
    if layout is not None:
        rep["LAYOUT"] = layout
    return _write(out, rep, 0)


def _write(out, rep, code):
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1, default=sorted)
    m3 = rep.get("M3", {})
    print(f"[{rep['status']}] sha={rep['git_sha'][:8]} seed={rep['seed']} M1={rep.get('M1')} HOLDOUT={rep.get('HOLDOUT')} "
          f"M2={rep.get('M2')} M3 identical={m3.get('identical')}/{m3.get('checked')} -> {out}")
    if "LAYOUT" in rep:
        lay = rep["LAYOUT"]
        print(f"LAYOUT [{lay['status']}] pola zmierzone={lay.get('fields_measured')} not_run={lay.get('fields_not_run')} {lay.get('by_type_location')}")
    return code


if __name__ == "__main__":
    sys.exit(main())
