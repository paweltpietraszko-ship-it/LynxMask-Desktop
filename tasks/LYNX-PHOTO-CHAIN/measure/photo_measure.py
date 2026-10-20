"""
photo_measure.py — LYNX-PHOTO-CHAIN §3: pomiar odbioru łańcucha zdjęć (poza produktem; CC 20.10).

Kroki (--steps):
  thresholds  w procesie (bez API): pewność orientacji i udział słownikowy odczytu PP na zbiorze ZNANYM (obroty 0/90/180/270)
              i — tylko agregaty — na realnych zdjęciach (--real). Tabela kandydatów progów: odmowy wg poziomu L0–L3.
  e2e         obraz → prawdziwy /preview w jednorazowej kopii `git archive <SHA> backend` (TestClient, pełny _lifespan, pusty
              profil, katalog OWNERA chroniony migawką) — wariant main (Tesseract) albo gałąź z LYNX_OCR_ENGINE=rapid.
              Ocena wartości gold i would_ask: funkcje z tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py (bez zmian).
Raport JSON tylko poza repo; syntetyki: ID/klucze/statusy, realne zdjęcia: wyłącznie agregaty.
  py -3 tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py --steps thresholds --known <50> --real <dataset_real/images> --out <json>
  py -3 tasks/LYNX-PHOTO-CHAIN/measure/photo_measure.py --steps e2e --sha <SHA> [--rapid --models <dir>] --set <dataset>
      --name <etykieta> [--rotations 0,90,180,270] [--env K=V] --protect <backend OWNERA> --out <json>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
ROT_CODES = {90: 0, 180: 1, 270: 2}   # cv2.ROTATE_90_CLOCKWISE / 180 / 90_COUNTERCLOCKWISE = obrót zgodnie z ruchem wskazówek


def _cc():
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-PARITY-STEP2" / "measure"))
    sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-GATE-COMPARE" / "measure"))
    import chain_compare
    return chain_compare


def _imread(path: Path):
    import cv2
    import numpy as np
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)


def _rot(img, deg: int):
    import cv2
    return img if deg == 0 else cv2.rotate(img, ROT_CODES[deg])


def _med(xs):
    return round(statistics.median(xs), 3) if xs else None


# ── thresholds ───────────────────────────────────────────────────────────────
def step_thresholds(a) -> dict:
    import photo_chain
    import ocr_rapid
    gt = json.loads((a.known / "ground_truth.json").read_text(encoding="utf-8"))
    rows = []
    for g in gt:
        img = _imread(a.known / g["file"])
        for deg in (0, 90, 180, 270):
            r = _rot(img, deg)
            angle, conf = photo_chain.classify(r)
            text = ocr_rapid.recognize(photo_chain.upright(r, angle), 600) if deg == 0 or angle != deg else None
            known, total = photo_chain.dictionary_share(text) if text is not None else (None, None)
            rows.append({"id": Path(g["file"]).stem, "level": g.get("degradation_level"), "rot": deg, "pred": angle,
                         "ori": round(conf, 3), "known": known, "total": total})
    base = [r for r in rows if r["rot"] == 0]
    out = {"known_docs": len(gt), "orientation_correct": sum(r["pred"] == r["rot"] for r in rows), "orientation_total": len(rows),
           "ori_min": min(r["ori"] for r in rows), "ori_p1": sorted(r["ori"] for r in rows)[len(rows) // 100],
           "share_by_level": {f"L{lv}": sorted(round(r["known"] / r["total"], 3) if r["total"] else 0.0
                                               for r in base if r["level"] == lv) for lv in (0, 1, 2, 3)},
           "words_min": min(r["total"] for r in base), "rows": rows}
    table = []
    for dmin in (0.0, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8):
        rej = Counter(f"L{r['level']}" for r in base
                      if not r["total"] or r["total"] < photo_chain.MIN_WORDS or r["known"] / r["total"] < dmin)
        table.append({"dict_min": dmin, "rejected": sum(rej.values()), "by_level": dict(sorted(rej.items()))})
    out["dict_table_known_upright"] = table
    if a.real:
        real = []
        for p in sorted(q for q in a.real.iterdir() if q.suffix.lower() in (".jpg", ".jpeg", ".png")):
            img = _imread(p)
            angle, conf = photo_chain.classify(img)
            t0 = time.perf_counter()
            text = ocr_rapid.recognize(photo_chain.upright(img, angle), 600)
            known, total = photo_chain.dictionary_share(text)
            real.append({"ori": round(conf, 2), "share": round(known / total, 2) if total else 0.0, "words": total,
                         "secs_ocr": round(time.perf_counter() - t0, 2), "megapixels": round(img.shape[0] * img.shape[1] / 1e6, 1)})
        out["real_aggregates_sorted_by_ori"] = sorted(real, key=lambda r: r["ori"])   # bez nazw plików i tekstu
    return out


# ── e2e ──────────────────────────────────────────────────────────────────────
def _post(c, hdr: dict, image: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = c.post("/preview", files={"file": ("scan.png", Path(image).read_bytes(), "image/png")}, headers=hdr)
        j = r.json()
    except Exception as e:  # noqa: BLE001
        return {"code": None, "error": type(e).__name__, "secs": time.perf_counter() - t0}
    ocr = j.get("ocr") or {}
    return {"code": r.status_code, "blocked": bool(j.get("blocked")), "error": bool(j.get("error")),
            "ocr_rejected": bool(j.get("ocr_rejected")) or ocr.get("quality") == "reject",
            "out": j.get("anonymized_preview") or "", "originals": [t.get("original", "") for t in j.get("tokens") or []],
            "guard_reasons": len(j.get("guard_reasons") or []), "ocr_text": j.get("original_text"),
            "ocr_quality": ocr.get("quality"), "ocr_engine": ocr.get("engine"), "ocr_reason": ocr.get("reason"),
            "error_has_alternative": "wklei" in (j.get("error") or "").lower(), "secs": time.perf_counter() - t0}


def worker(jobs_path: str, out_path: str) -> int:
    sys.path.insert(0, os.getcwd())
    res: dict = {"items": []}
    try:
        import psutil
        import pseudominizer_api as api
        from fastapi.testclient import TestClient
        if not Path(api.__file__).resolve().is_relative_to(Path.cwd().resolve()):
            raise RuntimeError("import_outside_copy")
        with TestClient(api.app, base_url="http://127.0.0.1:8765") as c:
            hdr = {"X-Api-Token": Path(api._API_TOKEN_PATH).read_text(encoding="utf-8").strip()}
            res["health"] = c.get("/health", headers=hdr).json()
            proc = psutil.Process()
            for job in json.loads(Path(jobs_path).read_text(encoding="utf-8")):
                item = _post(c, hdr, job)
                item["rss_mb"] = round(proc.memory_info().rss / 2**20)
                res["items"].append(item)
    except Exception as e:  # noqa: BLE001
        res["startup_error"] = type(e).__name__
    Path(out_path).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return 0


def run_variant(a, cc, jobs: list) -> tuple[list | None, dict]:
    tmp = Path(tempfile.mkdtemp(prefix="lynx_photo_"))
    protect = [ROOT / "backend", Path.home() / ".pseudominizer", *a.protect]
    snap = cc.snapshot(protect)
    meta: dict = {"copy_sha": a.sha, "rapid": a.rapid, "env": a.env}
    res: dict = {}
    t0 = time.perf_counter()
    try:
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", a.sha, "backend"],
                             capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(tmp, filter="data")
        for d in ("anon_profile", "profile", "archive"):
            (tmp / d).mkdir()
        (tmp / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        env = cc._worker_env(tmp)
        if a.rapid:
            env.update(LYNX_OCR_ENGINE="rapid", LYNX_OCR_MODEL_DIR=str(a.models))
        env.update(dict(kv.split("=", 1) for kv in a.env))
        subprocess.run([sys.executable, "-B", str(HERE), "--worker", str(tmp / "jobs.json"), str(tmp / "res.json")],
                       cwd=tmp / "backend", env=env, capture_output=True, timeout=7200)
        res = json.loads((tmp / "res.json").read_text(encoding="utf-8")) if (tmp / "res.json").is_file() else \
            {"startup_error": "no_result"}
    except Exception as e:  # noqa: BLE001
        res = {"startup_error": type(e).__name__}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    meta.update(secs=round(time.perf_counter() - t0, 1), startup_error=res.get("startup_error"),
                startup="OK" if cc.health_ok(res.get("health")) and not res.get("startup_error") else "NOT_RUN(STARTUP)")
    meta["isolation"], meta["changed_paths"] = cc.isolation(snap, cc.snapshot(protect))
    ok = meta["startup"] == "OK" and meta["isolation"] == "OK" and len(res.get("items", [])) == len(jobs)
    return (res["items"] if ok else None), meta


def step_e2e(a) -> dict:
    import cv2
    cc = _cc()
    gt = json.loads((a.set / "ground_truth.json").read_text(encoding="utf-8"))
    rots = [int(x) for x in a.rotations.split(",")]
    work = Path(tempfile.mkdtemp(prefix="lynx_photo_rot_"))   # obrócone kopie syntetyków, usuwane po pomiarze
    jobs, meta_rows = [], []
    try:
        for g in gt:
            img = _imread(a.set / g["file"])
            for deg in rots:
                p = a.set / g["file"] if deg == 0 else work / f"{Path(g['file']).stem}_{deg}.png"
                if deg:
                    cv2.imwrite(str(p), _rot(img, deg))
                jobs.append(str(p.resolve()))
                meta_rows.append((g, deg))
        items, meta = run_variant(a, cc, jobs)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if items is None:
        return {"run": meta, "verdict": "NOT_RUN"}
    out = {"run": meta}
    for deg in rots:
        docs = []
        for (g, d), r in zip(meta_rows, items):
            if d != deg:
                continue
            doc = cc.eval_doc(r.get("ocr_text") or "", r, g.get("entities", {}))
            if r.get("ocr_rejected"):
                doc["category"] = "ocr_rejected"
            doc.update(id=Path(g["file"]).stem, level=g.get("degradation_level"), n_gold=len(g.get("entities", {})),
                       engine=r.get("ocr_engine"), reason=r.get("ocr_reason"), secs=r.get("secs"), rss=r.get("rss_mb"),
                       alt=r.get("error_has_alternative"), guard_reasons=r.get("guard_reasons"))
            docs.append(doc)
        s = cc.summarize(docs, None)
        secs = sorted(x["secs"] for x in docs if x["secs"] is not None)
        s.update(engines=dict(Counter(str(x["engine"]) for x in docs)), reasons=dict(Counter(str(x["reason"]) for x in docs)),
                 refusals_without_alternative=sum(x["category"] == "ocr_rejected" and not x["alt"] for x in docs),
                 guard_blocked=sum(x["category"] == "blocked" for x in docs),
                 secs_median=_med(secs), secs_p95=round(secs[int(0.95 * (len(secs) - 1))], 2) if secs else None,
                 secs_first=round(docs[0]["secs"], 2) if docs else None, rss_max_mb=max((x["rss"] or 0) for x in docs))
        out[f"rot{deg}"] = {"summary": s, "cases": cc.cases(docs, f"{a.name}_rot{deg}", None),
                            "docs": [{k: x.get(k) for k in ("id", "level", "category", "engine", "reason", "ask")} for x in docs]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", required=True)
    ap.add_argument("--known", type=Path)
    ap.add_argument("--real", type=Path)
    ap.add_argument("--set", type=Path)
    ap.add_argument("--name", default="set")
    ap.add_argument("--sha")
    ap.add_argument("--rapid", action="store_true")
    ap.add_argument("--models", type=Path)
    ap.add_argument("--rotations", default="0")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--protect", type=Path, action="append", default=[])
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    if ROOT in a.out.resolve().parents:
        print("NOT_RUN: --out musi leżeć poza repo")
        return 2
    report = json.loads(a.out.read_text(encoding="utf-8")) if a.out.is_file() else {}
    for step in a.steps.split(","):
        if step == "thresholds":
            _cc()
            report["thresholds"] = step_thresholds(a)
        else:
            report[f"e2e_{a.name}"] = step_e2e(a)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[PHOTO] {step} zapisany", flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        raise SystemExit(worker(sys.argv[2], sys.argv[3]))
    raise SystemExit(main())
