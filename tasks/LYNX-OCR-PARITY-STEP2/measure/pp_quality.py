"""
pp_quality.py — LYNX-OCR-PARITY krok 2, faza B1: pomiar, czy pewności per linia PP-OCRv6 odróżniają dobry odczyt od złego.

Narzędzie offline (syntetyki), produkt bez zmian. Używa `ocr_rapid._get_engine()` i `build_text` z backendu
oraz `benchmark_ocr_diagnostics.classify_miss` do porównania gold z odczytem.
Silnik wywoływany raz na dokument z `text_score=0.0` (widać też linie, które produkcyjny filtr 0.5 odrzuca);
tekst „produkcyjny” = tylko linie ze score ≥ PROD_TEXT_SCORE, jak w `ocr_rapid` dziś.
Siatka reguł GRID ustalona z góry; wybór na zbiorze znanym (--known), jednorazowa falsyfikacja na --holdout.
Raport JSON do --out (poza repo): tylko ID plików, klucze/typy gold, etykiety, liczby — bez wartości i tekstu OCR.
Użycie (z katalogu repo):
  py -3 tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py --known backend/dataset_20260627_095419 \
      --holdout backend/dataset_20261016_fresh --out <poza repo>/pp_quality.json
Kod wyjścia: 0 pomiar wykonany, 2 NOT_RUN (brak/inne modele lub pakiet).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

PROD_TEXT_SCORE = 0.5   # rapidocr 3.10 Global.text_score (domyślnie używany przez ocr_rapid)
MODEL_SHA256 = {        # z DELIVERY fazy A (b721394)
    "PP-OCRv6_det_small.onnx": "090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f",
    "PP-OCRv6_rec_small.onnx": "6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx": "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c",
}
AGGS = ("min", "q10")
GRID = [(agg, ok_t, warn_t) for agg in AGGS
        for ok_t, warn_t in ((0.95, 0.85), (0.9, 0.8), (0.9, 0.7), (0.85, 0.7), (0.8, 0.6))]
LABEL = {"BUG_SILNIKA": "INTACT", "OCR_ZNIEKSZTAŁCONY": "DISTORTED", "BRAK_W_OCR": "MISSING",
         "REVIEW": "REVIEW", "NOT_MEASURED": "MISSING"}
ALERT_TYPES = {"EMAIL", "TELEFON"}


def validate(res) -> tuple[list, list, list] | None:
    """Powiązane boxes/txts/scores albo None (brak, rozbieżne długości, NaN/inf, poza [0,1])."""
    boxes, txts, scores = getattr(res, "boxes", None), getattr(res, "txts", None), getattr(res, "scores", None)
    if boxes is None and txts is None and scores is None:
        return [], [], []
    if boxes is None or txts is None or scores is None or not (len(boxes) == len(txts) == len(scores)):
        return None
    out = []
    for s in scores:
        if not isinstance(s, (int, float)) or not math.isfinite(s) or not 0.0 <= s <= 1.0:
            return None
        out.append(float(s))
    return list(boxes), list(txts), out


def quantile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def features(scores: list[float], txts: list[str]) -> dict:
    """Cechy dokumentu z pewności rozpoznania linii; to NIE jest pokrycie obrazu tekstem."""
    kept = [s for s, t in zip(scores, txts) if s >= PROD_TEXT_SCORE and t.strip()]
    f = {"n_boxes": len(scores), "n_lines_kept": len(kept), "n_dropped_by_filter": sum(s < PROD_TEXT_SCORE for s in scores),
         "text_len": sum(len(t) for s, t in zip(scores, txts) if s >= PROD_TEXT_SCORE)}
    if kept:
        f.update(min=min(kept), q10=quantile(kept, 0.10), mean=sum(kept) / len(kept),
                 **{f"share_below_{t}": sum(s < t for s in kept) / len(kept) for t in (0.7, 0.8, 0.9)})
    return f


def gold_labels(entities: dict, text: str) -> list[dict]:
    """Etykieta każdej wartości gold względem odczytu (bez wartości w wyniku)."""
    import benchmark
    from benchmark_ocr_diagnostics import classify_miss
    out = []
    for key, val in entities.items():
        label = "MISSING" if not text.strip() else LABEL[classify_miss(str(val), text)[0]]
        out.append({"key": key, "type": benchmark._ENTITY_TYPE_MAP.get(key, "?"),
                    "critical": key in benchmark._CRITICAL_KEYS, "label": label})
    return out


def measure_doc(engine, image_bytes: bytes, entities: dict) -> dict:
    from ocr_rapid import build_text
    t0 = time.perf_counter()
    v = validate(engine(image_bytes, text_score=0.0))
    secs = time.perf_counter() - t0
    if v is None:
        return {"valid": False, "features": {}, "gold": gold_labels(entities, ""), "secs": secs}
    boxes, txts, scores = v
    keep = [i for i, s in enumerate(scores) if s >= PROD_TEXT_SCORE]
    text = build_text([boxes[i] for i in keep], [txts[i] for i in keep]) if keep else ""
    return {"valid": True, "features": features(scores, txts), "gold": gold_labels(entities, text), "secs": secs}


def status(doc: dict, rule: tuple) -> str:
    """ok/warn/reject; nieważne scores albo pusty odczyt → reject (brak podstaw do oceny)."""
    agg, ok_t, warn_t = rule
    value = doc["features"].get(agg) if doc["valid"] else None
    if value is None:
        return "reject"
    return "ok" if value >= ok_t else "warn" if value >= warn_t else "reject"


def evaluate(docs: list[dict], rule: tuple) -> dict:
    """Ile dokumentów ok/warn/reject i ile strat gold w dokumentach dopuszczonych (ok + warn)."""
    st = Counter(status(d, rule) for d in docs)
    acc = [d for d in docs if status(d, rule) != "reject"]
    lab = Counter(g["label"] for d in acc for g in d["gold"])
    return {"rule": {"agg": rule[0], "ok": rule[1], "warn": rule[2]}, "docs": dict(st),
            "accepted_gold": dict(lab),
            "accepted_critical_not_intact": sum(g["critical"] and g["label"] != "INTACT" for d in acc for g in d["gold"]),
            "accepted_alert_not_intact": sum(g["type"] in ALERT_TYPES and g["label"] != "INTACT" for d in acc for g in d["gold"]),
            "rejected_gold_intact": sum(g["label"] == "INTACT" for d in docs if status(d, rule) == "reject" for g in d["gold"])}


def select(known_tables: list[dict]) -> dict | None:
    """Wybór WYŁĄCZNIE na zbiorze znanym: zero nienaruszonych-krytycznych strat w dopuszczonych, potem najwięcej dopuszczonych."""
    safe = [t for t in known_tables if t["accepted_critical_not_intact"] == 0]
    if not safe:
        return None
    return max(safe, key=lambda t: (t["docs"].get("ok", 0) + t["docs"].get("warn", 0), -t["accepted_alert_not_intact"]))


def summary(docs: list[dict]) -> dict:
    lab = Counter(g["label"] for d in docs for g in d["gold"])
    per_type = Counter(f"{g['type']}:{g['label']}" for d in docs for g in d["gold"])
    mins = [d["features"]["min"] for d in docs if d["valid"] and "min" in d["features"]]
    hist = Counter(min(9, int(m * 10)) / 10 for m in mins)
    confident_errors = [{"file": d["file"], "key": g["key"], "type": g["type"], "label": g["label"],
                         "doc_min": round(d["features"]["min"], 3)}
                        for d in docs if d["valid"] and d["features"].get("min", 0) >= 0.9
                        for g in d["gold"] if g["label"] in ("DISTORTED", "MISSING")]
    return {"docs": len(docs), "invalid": sum(not d["valid"] for d in docs), "gold": dict(lab),
            "gold_per_type": dict(sorted(per_type.items())), "doc_min_hist": dict(sorted(hist.items())),
            "dropped_by_filter_lines": sum(d["features"].get("n_dropped_by_filter", 0) for d in docs),
            "high_score_errors": confident_errors, "secs_per_page": round(sum(d["secs"] for d in docs) / max(1, len(docs)), 2)}


def run_dataset(engine, ds: Path) -> list[dict]:
    gt = json.loads((ds / "ground_truth.json").read_text(encoding="utf-8"))
    docs = []
    for d in gt:
        m = measure_doc(engine, (ds / d["file"]).read_bytes(), d.get("entities", {}))
        docs.append(dict(m, file=Path(d["file"]).name, level=d.get("degradation_level")))
    return docs


def preflight(model_dir: Path) -> dict | None:
    """Wersje i SHA256 modeli; None = NOT_RUN (nic nie jest pobierane)."""
    try:
        import onnxruntime
        import rapidocr  # noqa: F401
        from importlib.metadata import version
    except ImportError:
        return None
    sha = {}
    for name, expected in MODEL_SHA256.items():
        p = model_dir / name
        if not p.is_file():
            return None
        sha[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"rapidocr": version("rapidocr"), "onnxruntime": onnxruntime.__version__, "model_sha256": sha,
            "models_match_phase_a": sha == MODEL_SHA256}


def digest(ds: Path) -> str:
    return hashlib.sha256((ds / "ground_truth.json").read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--known", required=True, type=Path)
    ap.add_argument("--holdout", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    import ocr_rapid
    pre = preflight(ocr_rapid.model_dir())
    if pre is None or not pre["models_match_phase_a"]:   # Codex B1 r2 F1: inne modele = brak porównywalności
        why = "modele PP-OCRv6 inne niż w fazie A (SHA256)" if pre else "brak pakietu rapidocr/onnxruntime albo modeli PP-OCRv6"
        print("NOT_RUN:", why, "w", ocr_rapid.model_dir())
        return 2
    engine = ocr_rapid._get_engine()
    known, holdout = run_dataset(engine, a.known), run_dataset(engine, a.holdout)
    kt = [evaluate(known, r) for r in GRID]
    chosen = select(kt)
    ht = [evaluate(holdout, r) for r in GRID]
    chosen_holdout = next((t for t in ht if t["rule"] == chosen["rule"]), None) if chosen else None
    verdict = "NO_SAFE_GATE" if chosen is None or chosen_holdout["accepted_critical_not_intact"] > 0 else "CANDIDATE"
    code_sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    try:
        import psutil
        rss_mb = round(psutil.Process().memory_info().rss / 2**20)
    except ImportError:
        rss_mb = None
    report = {"meta": dict(pre, code_sha=code_sha, prod_text_score=PROD_TEXT_SCORE, grid=[list(r) for r in GRID], rss_mb=rss_mb,
                           known=str(a.known.name), known_digest=digest(a.known),
                           holdout=str(a.holdout.name), holdout_digest=digest(a.holdout)),
              "known": {"summary": summary(known), "rules": kt}, "holdout": {"summary": summary(holdout), "rules": ht},
              "chosen_on_known": chosen, "chosen_on_holdout": chosen_holdout, "verdict": verdict,
              "docs": {"known": known, "holdout": holdout}}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[PP-QUALITY] {verdict}; reguła (zbiór znany): {chosen['rule'] if chosen else '—'}; "
          f"znany: {chosen['docs'] if chosen else '—'}; holdout: {chosen_holdout['docs'] if chosen_holdout else '—'}; "
          f"krytyczne nie-nienaruszone dopuszczone (holdout): {chosen_holdout['accepted_critical_not_intact'] if chosen_holdout else '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
