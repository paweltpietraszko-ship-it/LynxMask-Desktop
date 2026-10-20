"""
paired_ocr.py — LYNX-OCR-CASCADE C1: czy odczyty PP-OCRv6 i Tesseracta da się skojarzyć po geometrii obrazu.

Narzędzie offline na syntetykach, produkt bez zmian. PP: `ocr_rapid._get_engine()` (jedno wywołanie na obraz,
produkcyjny filtr pewności), Tesseract: `image_to_data` z tym samym `lang`/`--psm 3` co `ocr_engine`.
Region = ramka PP; słowa Tesseracta przypisywane tylko z jednej linii TSV (block/par/line), której pion pokrywa ramkę,
i tylko te, których środek leży w poziomym zakresie ramki — bez sklejania kolumn, pól i linii.
Statusy rozłączne (STATUSES); zgoda dwóch OCR nie jest dowodem poprawności. Sumy kontrolne: python-stdnum.
Reguły (stałe niżej) zamrożone przed holdoutem. Raport JSON do --out poza repo: ID plików, klucze/typy gold,
statusy, liczby — bez wartości, tekstu OCR i współrzędnych.
Użycie (z katalogu repo):
  py -3 tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py --known backend/dataset_20260627_095419 \
      --holdout backend/dataset_20261016_fresh --out <poza repo>/paired_ocr.json
Kod wyjścia: 0 pomiar wykonany, 2 NOT_RUN (brak/inne modele, brak Tesseracta, zła ścieżka).
"""
from __future__ import annotations

import argparse
import io
import math
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-PARITY-STEP2" / "measure"))

STATUSES = ("BOTH_AGREE", "PP_DISTORTED_TESS_VALID", "PP_MISSING_TESS_PRESENT", "CONFLICT_REVIEW",
            "PP_ONLY", "TESS_ONLY_UNCERTAIN", "UNMEASURABLE")
ALARM = {"PP_DISTORTED_TESS_VALID", "PP_MISSING_TESS_PRESENT", "CONFLICT_REVIEW"}
# alarm konkretny: spór o identyfikator, brak pokrycia albo niejednoznaczna geometria (nie zwykła różnica tekstu)
SPECIFIC = {"tess_checksum", "valid_id", "text", "two_valid_ids", "tess_valid_pp_no_id", "pp_invalid_id",
            "no_valid_checksum", "ambiguous_lines"}
MIN_V_OVERLAP = 0.5      # nakładanie pionowe względem niższej ramki: ta sama linia
MAX_SKEW_DEG = 10.0      # ramka PP bardziej obrócona → brak wspólnej geometrii z linią TSV
DUP_IOU = 0.5            # dwie ramki PP na tym samym miejscu → niejednoznaczne
TESS_LOW_CONF = 30       # jak `ocr_engine`: słowo conf < 30 to znak złej jakości
TIMEOUT_S = 60
CHECKSUM_PREFIXES = ("pesel", "nip", "regon", "iban")
_ID_RUN = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]{2}[ \-]?)?\d[\d \-]{7,40}\d(?![0-9])")
_MEANINGFUL = re.compile(r"[^\W\d_]{3,}|\d{4,}")


# ── sumy kontrolne ───────────────────────────────────────────────────────────

def _valid(compact: str) -> bool:
    from stdnum import iban
    from stdnum.pl import nip, pesel, regon
    if compact[:2].isalpha():
        return iban.is_valid(compact)
    checks = {26: lambda v: iban.is_valid("PL" + v), 11: pesel.is_valid, 10: nip.is_valid,
              9: regon.is_valid, 14: regon.is_valid}
    fn = checks.get(len(compact)) if compact.isdigit() else None
    return bool(fn and fn(compact))


def ids(text: str) -> list[tuple[str, bool]]:
    """Ciągi przypominające identyfikator (≥9 znaków bez separatorów) i czy mają poprawną sumę; też ich części."""
    out = {}
    for m in _ID_RUN.finditer(text):
        whole = re.sub(r"[ \-]", "", m.group()).upper()
        for c in [whole] + [re.sub(r"-", "", p).upper() for p in m.group().split()]:
            if len(c) >= 9 and c not in out:
                out[c] = _valid(c)
    if any(out.values()):   # część poprawnej wartości nie jest osobnym uszkodzonym identyfikatorem
        good = [c for c, ok in out.items() if ok]
        out = {c: ok for c, ok in out.items() if ok or not any(c in g or g in c for g in good)}
    return sorted(out.items())


# ── geometria ────────────────────────────────────────────────────────────────

def pp_regions(boxes, txts) -> list[dict]:
    """Ramki PP jako prostokąty; zła lub obrócona ramka → `bad` (UNMEASURABLE)."""
    out = []
    for box, txt in zip(boxes if boxes is not None else [], txts if txts is not None else []):
        r = {"text": str(txt), "bad": None}
        try:
            pts = [(float(p[0]), float(p[1])) for p in box]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            if len(pts) != 4 or not all(map(math.isfinite, xs + ys)) or min(xs + ys) < 0:
                raise ValueError
            r["rect"] = (min(xs), min(ys), max(xs), max(ys))
            if r["rect"][2] <= r["rect"][0] or r["rect"][3] <= r["rect"][1]:
                raise ValueError
            if abs(math.degrees(math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0]))) > MAX_SKEW_DEG:
                r["bad"] = "rotated"
        except (TypeError, ValueError, IndexError):
            r.update(rect=None, bad="bad_box")
        out.append(r)
    return out


def tess_lines(d: dict) -> tuple[list[dict], int]:
    """Linie TSV (słowa z jednej block/par/line, z położeniem i conf); liczba słów z błędną ramką."""
    groups, bad = defaultdict(list), 0
    for i, t in enumerate(d.get("text", [])):
        if not str(t).strip() or float(d["conf"][i]) < 0:
            continue
        x, y, w, h = (int(d[k][i]) for k in ("left", "top", "width", "height"))
        if w <= 0 or h <= 0 or x < 0 or y < 0:
            bad += 1
            continue
        key = (d["page_num"][i], d["block_num"][i], d["par_num"][i], d["line_num"][i])
        groups[key].append({"rect": (x, y, x + w, y + h), "text": str(t).strip(), "conf": float(d["conf"][i])})
    lines = []
    for key in sorted(groups):
        ws = sorted(groups[key], key=lambda w: w["rect"][0])
        lines.append({"words": ws, "rect": (min(w["rect"][0] for w in ws), min(w["rect"][1] for w in ws),
                                            max(w["rect"][2] for w in ws), max(w["rect"][3] for w in ws))})
    return lines, bad


def _v_overlap(a, b) -> float:
    return max(0.0, min(a[3], b[3]) - max(a[1], b[1])) / max(1e-9, min(a[3] - a[1], b[3] - b[1]))


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix
    return ix / union if union > 0 else 0.0


def _words_in(rect, line) -> list[dict]:
    return [w for w in line["words"] if rect[0] <= (w["rect"][0] + w["rect"][2]) / 2 <= rect[2]]


# ── statusy ──────────────────────────────────────────────────────────────────

def judge_pair(pp_text: str, tess_text: str) -> tuple[str, str]:
    """Status sparowanego regionu. Poprawna suma po jednej stronie nie rozstrzyga sporu dwóch poprawnych wartości."""
    from benchmark_ocr_diagnostics import fuzzy_equal, norm
    ip, it = ids(pp_text), ids(tess_text)
    vp, vt = {c for c, ok in ip if ok}, {c for c, ok in it if ok}
    bad_pp = any(not ok for _, ok in ip)
    if ip or it:
        if vt - vp and vp - vt:
            return "CONFLICT_REVIEW", "two_valid_ids"
        if vt - vp:
            return ("PP_DISTORTED_TESS_VALID", "tess_checksum") if bad_pp else ("CONFLICT_REVIEW", "tess_valid_pp_no_id")
        if bad_pp:
            return "CONFLICT_REVIEW", "pp_invalid_id"
        if vp and vp == vt:
            return "BOTH_AGREE", "text_equal" if norm(pp_text) == norm(tess_text) else "ids_equal"
        return "CONFLICT_REVIEW", "checksum_favors_pp" if vp else "no_valid_checksum"
    a, b = norm(pp_text), norm(tess_text)
    if a == b:
        return "BOTH_AGREE", "text_equal"
    return "CONFLICT_REVIEW", "text_close" if fuzzy_equal(a, b) else "text_differs"


def _tess_only(words: list[dict]) -> dict:
    text = " ".join(w["text"] for w in words)
    valid = any(ok for _, ok in ids(text))
    low = sorted(w["conf"] for w in words)[len(words) // 2] < TESS_LOW_CONF
    if valid:
        st = ("PP_MISSING_TESS_PRESENT", "valid_id")
    elif not _MEANINGFUL.search(text):
        st = ("TESS_ONLY_UNCERTAIN", "noise")
    else:
        st = ("TESS_ONLY_UNCERTAIN", "low_conf") if low else ("PP_MISSING_TESS_PRESENT", "text")
    return {"status": st[0], "reason": st[1], "pp_text": "", "tess_text": text}


def _pp_region_status(i: int, r: dict, regs: list[dict], lines: list[dict], used: set) -> dict:
    rec = {"pp_text": r["text"], "tess_text": ""}
    if r["bad"]:
        return dict(rec, status="UNMEASURABLE", reason=r["bad"])
    cands = [(k, _words_in(r["rect"], ln)) for k, ln in enumerate(lines) if _v_overlap(r["rect"], ln["rect"]) > MIN_V_OVERLAP]
    cands = [(k, ws) for k, ws in cands if ws]
    for k, ws in cands:
        used.update((k, id(w)) for w in ws)
    if any(j != i and o["rect"] and _iou(r["rect"], o["rect"]) > DUP_IOU for j, o in enumerate(regs)):
        return dict(rec, status="UNMEASURABLE", reason="duplicate_box")
    if not cands:
        return dict(rec, status="PP_ONLY", reason="no_tess_words")
    if len(cands) > 1:
        return dict(rec, status="CONFLICT_REVIEW", reason="ambiguous_lines")
    rec["tess_text"] = " ".join(w["text"] for w in cands[0][1])
    st, why = judge_pair(r["text"], rec["tess_text"])
    return dict(rec, status=st, reason=why)


def classify_doc(regs: list[dict], lines: list[dict]) -> list[dict]:
    """Każdy region PP i każdy ciąg niewykorzystanych słów jednej linii TSV dostaje dokładnie jeden status."""
    used: set = set()
    out = [dict(_pp_region_status(i, r, regs, lines, used), src="pp") for i, r in enumerate(regs)]
    for k, ln in enumerate(lines):
        rest = [w for w in ln["words"] if (k, id(w)) not in used]
        if rest:
            out.append(dict(_tess_only(rest), src="tess"))
    return out


# ── pomiar dokumentu ─────────────────────────────────────────────────────────

def run_pp(image_bytes: bytes):
    import ocr_rapid
    return ocr_rapid._pool.submit(ocr_rapid._get_engine(), image_bytes).result(timeout=TIMEOUT_S)


def run_tess(img) -> dict:
    import ocr_engine
    import pytesseract
    lang = "pol" if ocr_engine._check_polish_lang() else "eng"
    return pytesseract.image_to_data(img, lang=lang, config="--psm 3", output_type=pytesseract.Output.DICT,
                                     timeout=TIMEOUT_S)


def measure_doc(image_bytes: bytes, pp_fn=run_pp, tess_fn=run_tess) -> dict:
    """Regiony ze statusami albo `unmeasurable` z powodem (awaria, czas, inna ramka obrazu)."""
    from PIL import Image
    doc = {"regions": [], "unmeasurable": None, "pp_text": "", "secs_pp": 0.0, "secs_tess": 0.0, "tess_bad_words": 0}
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        return dict(doc, unmeasurable=f"image_{type(e).__name__}")
    for name, fn, arg in (("pp", pp_fn, image_bytes), ("tess", tess_fn, img)):
        t0 = time.perf_counter()
        try:
            doc[name] = fn(arg)
        except Exception as e:  # noqa: BLE001 — bez treści wyjątku
            doc["unmeasurable"] = f"{name}_{'timeout' if 'imeout' in type(e).__name__ + str(e)[:40] else type(e).__name__}"
        doc[f"secs_{name}"] = time.perf_counter() - t0
        if doc["unmeasurable"]:
            return {k: v for k, v in doc.items() if k not in ("pp", "tess")}
    return _finish(doc, img.size)


def _finish(doc: dict, size) -> dict:
    from ocr_rapid import build_text
    pp, tsv = doc.pop("pp"), doc.pop("tess")
    pages = [(tsv["width"][i], tsv["height"][i]) for i, lv in enumerate(tsv.get("level", [])) if lv == 1]
    if pages != [tuple(size)]:
        return dict(doc, unmeasurable="frame_mismatch")
    boxes, txts = (getattr(pp, "boxes", None), getattr(pp, "txts", None)) if pp is not None else (None, None)
    if (boxes is None) != (txts is None) or (boxes is not None and len(boxes) != len(txts)):
        return dict(doc, unmeasurable="pp_inconsistent")
    lines, doc["tess_bad_words"] = tess_lines(tsv)
    regs = pp_regions(boxes, txts)
    doc["pp_text"] = build_text(boxes, txts) if boxes is not None and len(boxes) else ""
    doc["regions"] = classify_doc(regs, lines)
    return doc


# ── porównanie z gold (niezależne od statusów) ───────────────────────────────

def _label(value: str, text: str) -> str:
    from benchmark_ocr_diagnostics import classify_miss
    return {"BUG_SILNIKA": "INTACT", "OCR_ZNIEKSZTAŁCONY": "DISTORTED", "BRAK_W_OCR": "MISSING",
            "REVIEW": "REVIEW", "NOT_MEASURED": "MISSING"}[classify_miss(value, text)[0]]


def gold_cases(doc: dict, entities: dict) -> list[dict]:
    """Dla każdej wartości gold: etykieta odczytu PP, region, w którym ją widać, i co pokazał tam Tesseract."""
    import benchmark
    from benchmark_ocr_diagnostics import norm
    gold_n = {norm(str(v)).upper() for v in entities.values()}
    for r in doc["regions"]:
        valid_t = {c for c, ok in ids(r["tess_text"]) if ok}
        r["gold_hit"] = bool(valid_t & gold_n) if r["status"] == "PP_DISTORTED_TESS_VALID" else (
            any(_label(str(v), r["tess_text"]) != "MISSING" for v in entities.values())
            if r["status"] == "PP_MISSING_TESS_PRESENT" else None)
    out = []
    for key, val in entities.items():
        c = {"key": key, "type": benchmark._ENTITY_TYPE_MAP.get(key, "?"), "critical": key in benchmark._CRITICAL_KEYS,
             "checksum": key.startswith(CHECKSUM_PREFIXES), "pp": _label(str(val), doc["pp_text"]) if not doc["unmeasurable"]
             else "UNMEASURED", "region": "NOT_LOCATED", "reason": None, "tess_in_region": None}
        for r in doc["regions"]:
            lp, lt = _label(str(val), r["pp_text"]), _label(str(val), r["tess_text"])
            if {lp, lt} & {"INTACT", "DISTORTED"}:
                c.update(region=r["status"], reason=r["reason"], tess_in_region=lt)
                break
        c["rescue_candidate"] = c["pp"] != "INTACT" and c["region"] in ("PP_DISTORTED_TESS_VALID", "PP_MISSING_TESS_PRESENT") \
            and c["tess_in_region"] == "INTACT"
        c["alarmed"] = c["pp"] != "INTACT" and c["region"] in ALARM
        c["alarmed_specific"] = c["alarmed"] and c["reason"] in SPECIFIC
        out.append(c)
    return out


# ── zbiór, podsumowanie, werdykt ─────────────────────────────────────────────

def run_dataset(ds: Path, pp_fn=run_pp, tess_fn=run_tess) -> list[dict]:
    import json
    docs = []
    for g in json.loads((ds / "ground_truth.json").read_text(encoding="utf-8")):
        d = measure_doc((ds / g["file"]).read_bytes(), pp_fn, tess_fn)
        d["gold"] = gold_cases(d, g.get("entities", {}))
        d.update(file=Path(g["file"]).name, level=g.get("degradation_level"))
        docs.append(d)
    return docs


def summary(docs: list[dict]) -> dict:
    regs = [r for d in docs for r in d["regions"]]
    gold = [dict(c, level=d["level"]) for d in docs for c in d["gold"]]
    lost = [c for c in gold if c["pp"] not in ("INTACT", "UNMEASURED")]
    lost_crit = [c for c in lost if c["critical"]]
    clean_docs = [d for d in docs if not d["unmeasurable"] and all(c["pp"] == "INTACT" or not c["critical"] for c in d["gold"])]
    s = {"docs": len(docs), "unmeasurable": dict(Counter(d["unmeasurable"] for d in docs if d["unmeasurable"])),
         "regions": dict(Counter(r["status"] for r in regs)),
         "reasons": dict(sorted(Counter(f"{r['status']}:{r['reason']}" for r in regs).items())),
         "gold": len(gold), "pp_labels": dict(Counter(c["pp"] for c in gold)),
         "pp_lost_by_region": dict(Counter(c["region"] for c in lost)),
         "pp_lost_per_type_level": dict(sorted(Counter(f"{c['type']}:L{c['level']}:{c['region']}" for c in lost).items())),
         "critical_lost": len(lost_crit), "critical_alarmed": sum(c["alarmed"] for c in lost_crit),
         "critical_alarmed_specific": sum(c["alarmed_specific"] for c in lost_crit),
         "critical_rescue_candidates": sum(c["rescue_candidate"] for c in lost_crit),
         "rescue_candidates_all": sum(c["rescue_candidate"] for c in lost),
         "tess_valid_regions": Counter(r["gold_hit"] for r in regs if r["status"] == "PP_DISTORTED_TESS_VALID"),
         "tess_present_regions": Counter(r["gold_hit"] for r in regs if r["status"] == "PP_MISSING_TESS_PRESENT"),
         "alarms_per_doc_without_critical_loss": round(sum(r["status"] in ALARM for d in clean_docs for r in d["regions"])
                                                       / max(1, len(clean_docs)), 2),
         "specific_alarms_per_doc_without_critical_loss": round(sum(r["status"] in ALARM and r["reason"] in SPECIFIC
                                                                for d in clean_docs for r in d["regions"])
                                                                / max(1, len(clean_docs)), 2),
         "secs_pp": round(sum(d["secs_pp"] for d in docs) / max(1, len(docs)), 2),
         "secs_tess": round(sum(d["secs_tess"] for d in docs) / max(1, len(docs)), 2),
         "tess_bad_words": sum(d["tess_bad_words"] for d in docs)}
    s["tess_valid_regions"] = {str(k): v for k, v in s["tess_valid_regions"].items()}
    s["tess_present_regions"] = {str(k): v for k, v in s["tess_present_regions"].items()}
    return s


def verdict(s: dict) -> dict:
    """Reguła zamrożona przed holdoutem: naprawa sumą tylko gdy ratuje krytyczne i nie podsuwa obcych wartości;
    alarm pokrycia oceniany osobno (ile krytycznych strat PP wskazuje)."""
    false_valid = s["tess_valid_regions"].get("False", 0)
    rescue = "CANDIDATE" if s["critical_rescue_candidates"] > false_valid and s["critical_rescue_candidates"] > 0 \
        else "NOT_FEASIBLE"
    n, a = s["critical_lost"], s["critical_alarmed_specific"]
    alarm = "NO_LOSSES" if n == 0 else "CANDIDATE" if a == n else "PARTIAL" if a else "NOT_FEASIBLE"
    return {"rescue_by_checksum": rescue, "coverage_alarm": alarm}


def _cases(docs: list[dict]) -> list[dict]:
    return [{"file": d["file"], "level": d["level"], **{k: c[k] for k in ("key", "type", "critical", "pp", "region",
             "reason", "tess_in_region", "rescue_candidate", "alarmed", "alarmed_specific")}} for d in docs for c in d["gold"]
            if c["pp"] != "INTACT" or c["region"] in ("PP_DISTORTED_TESS_VALID", "PP_MISSING_TESS_PRESENT")]


def _check_paths(a) -> str | None:
    for ds in (a.known, a.holdout):
        if "dataset_real" in ds.resolve().as_posix() or not (ds / "ground_truth.json").is_file():
            return f"{ds.name}: tylko syntetyczna paczka z ground_truth.json"
    if ROOT in a.out.resolve().parents:
        return "--out musi leżeć poza repo"
    return None


def main(argv=None) -> int:
    import json

    import ocr_engine
    import ocr_rapid
    from pp_quality import digest, preflight
    ap = argparse.ArgumentParser()
    for name in ("--known", "--holdout", "--out"):
        ap.add_argument(name, required=True, type=Path)
    a = ap.parse_args(argv)
    pre = preflight(ocr_rapid.model_dir())
    why = _check_paths(a) or (None if pre and pre["models_match_phase_a"] else "modele PP-OCRv6 brak/inne niż faza A") \
        or (None if ocr_engine._tesseract_available() else "brak Tesseracta")
    if why:
        print("NOT_RUN:", why)
        return 2
    known, holdout = run_dataset(a.known), run_dataset(a.holdout)
    sk, sh = summary(known), summary(holdout)
    import psutil
    code_sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    report = {"meta": dict(pre, code_sha=code_sha, rss_mb=round(psutil.Process().memory_info().rss / 2**20),
                           rules={"MIN_V_OVERLAP": MIN_V_OVERLAP, "MAX_SKEW_DEG": MAX_SKEW_DEG, "DUP_IOU": DUP_IOU,
                                  "TESS_LOW_CONF": TESS_LOW_CONF, "TIMEOUT_S": TIMEOUT_S},
                           known=a.known.name, known_digest=digest(a.known), holdout=a.holdout.name,
                           holdout_digest=digest(a.holdout)),
              "known": {"summary": sk, "verdict": verdict(sk), "cases": _cases(known)},
              "holdout": {"summary": sh, "verdict": verdict(sh), "cases": _cases(holdout)}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, s in (("znany", sk), ("holdout", sh)):
        print(f"[PAIRED-OCR] {name}: {verdict(s)}; krytyczne stracone przez PP {s['critical_lost']}, "
              f"wskazane alarmem {s['critical_alarmed']} (konkretnym {s['critical_alarmed_specific']}), kandydaci naprawy {s['critical_rescue_candidates']}; "
              f"niemierzalne {sum(s['unmeasurable'].values())}/{s['docs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
