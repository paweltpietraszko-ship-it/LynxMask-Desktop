"""
chain_compare.py — LYNX-OCR-GATE-COMPARE ETAP 1 (brief v3.3): zdjęcie → P1 → PP-OCRv6 → /preview → Guard-reszta. Produkt bez zmian.
REAL_MASKING_PIPELINE: tekst z PP (+P1) jako .txt do prawdziwego /preview w jednorazowej kopii `git archive <SHA> backend`
(podproces z cwd w kopii, TestClient z pełnym _lifespan, env C3, pusty profil, migawka przed/po). HYPOTHETICAL_GUARD
(`would_ask`) liczony osobno. HerBERT odłożony (limit 600 linii) → NOT_RUN(HerBERT). Reguły zamrożone commitem przed holdoutem.
Raport JSON tylko do --out poza repo: ID syntetyków, klucze/typy, statusy, liczby, czasy, SHA (--real: wyłącznie agregaty).
Kroki --steps: clean, known (wybór N), holdout (raz, przy N z known), p1, product (obraz → /preview, Tesseract), real.
  py -3 tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py --known <50> --holdout <100> --clean <dataset_clean>
      --real <dataset_real/images> --protect <backend OWNERA> --out <poza repo>/stage1_report.json --steps clean,known
Kod wyjścia: 0 wykonano, 2 NOT_RUN (ścieżki, modele, kolejność kroków).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True   # pomiar nie zapisuje __pycache__ w backend/ repo (migawka C3)
ROOT = Path(__file__).resolve().parents[3]
if "--worker" not in sys.argv:   # worker importuje backend wyłącznie z kopii (cwd)
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-PARITY-STEP2" / "measure"))

# ── reguły zamrożone przed holdoutem ─────────────────────────────────────────
N_GRID = (15, 20, 30, 40, None)        # None = ∞
FRAG_MIN = 4                           # fragment gold widoczny: >= 4 kolejne znaki alfanumeryczne
P1_ORDER, P1_MIN_WORDS, P1_TIE, P1_SIDE = (0, 90, 270, 180), 20, 0.02, 1000
P1_TARGET_SECS, P1_TARGET_ACC = 3.0, 0.98
READY_ASK_MEDIAN, READY_HOLE_PER_100, READY_L1_REJECT, READY_ACCEPTED = 8, 1.0, 0.05, 0.80
WORKER_TIMEOUT = 7200
TOK = re.compile(r"\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)")   # S2
TOK_ADJ = re.compile(TOK.pattern + r"[-./ ]?(\d+)|(\d+)[-./ ]?" + TOK.pattern)
SENT = "\u2063"
WORD = re.compile(r"[\w@.+/-]*\w")
SEQ = re.compile(r"[\w@.+/-]*\w|" + SENT)
LEX_WORD = re.compile(r"[^\W\d_]{3,}")
DATE = re.compile(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}")
SHORT_NUM = re.compile(r"\d{1,4}([.,]\d+)?")
SHORT_GROUP = re.compile(r"\d{1,4}")
UR_ANCHOR = re.compile(r"ur|urodz\w*", re.I)
DIGIT_LIKE = str.maketrans("OoIilSsBbZz", "00111558622")   # klasa cyfropodobnych jak AnchorEngine Mobile
PROPER = {"imię", "nazwisko", "nazwa_geograficzna", "nazwa_organizacji", "nazwa_rzeczy", "nazwa_własna"}
NAME = {"imię", "nazwisko"}
ABBR = set("ul al os pl nr tel zam sygn adw art ust pkt poz ur mec tys zł gr ok np tj tzw r godz str lit par dz itd itp "
           "ww jw wg dot ds".split())
HEADER_END = "]\n\n"
_MORF = None

# ── HYPOTHETICAL_GUARD: Guard-reszta ─────────────────────────────────────────
@functools.lru_cache(maxsize=None)
def _analyse(w: str) -> tuple:
    global _MORF
    if _MORF is None:
        import morfeusz2
        _MORF = morfeusz2.Morfeusz(generate=False)
    return tuple(_MORF.analyse(w))

@functools.lru_cache(maxsize=None)
def kind(w: str) -> str | None:
    """Powód pytania o słowo; None = bezsporne (zwykłe słowo Morfeusza bez imienia/nazwiska/nazwy, skrót, liczba <= 4
    cyfry, data bez kotwicy). Zawsze pytamy: wielka litera + imię/nazwisko, nieznane Morfeuszowi, cyfry/kody."""
    if len(w) < 2 or w.lower() in ABBR or SHORT_NUM.fullmatch(w) or DATE.fullmatch(w):
        return None
    if re.search(r"\d", w):
        return "digits"
    if w.isupper():
        w = w.capitalize()   # „KOWALSKI” w nagłówku = „Kowalski”
    an = [a for a in _analyse(w) if a[2][2] != "ign"] or [a for a in _analyse(w.lower()) if a[2][2] != "ign"]
    if not an:
        return "unknown"
    quals = [set(a[2][3]) for a in an]
    if w[0].isupper() and any(q & NAME for q in quals):
        return "name"
    return None if any(not (q & PROPER) for q in quals) else "proper"

def residue_seq(text: str) -> list[str | None]:
    """Słowa tekstu po /preview w kolejności; token = None (liczy się do odległości)."""
    return [None if w == SENT else w.strip("./-") for w in SEQ.findall(TOK.sub(f" {SENT} ", text))]

def would_ask(text: str) -> set[str]:
    """Różne słowa, o które Guard-reszta zapytałby (symulacja). Dodatki briefu: sąsiadujące krótkie grupy cyfr
    (>= 2 grupy w odległości <= 1 słowa) i data przy „ur.” zawsze do pytania."""
    seq, ask = residue_seq(text), set()
    for i, w in enumerate(seq):
        if w is None:
            continue
        prev, near = seq[max(0, i - 2):i], seq[max(0, i - 2):i] + seq[i + 1:i + 3]
        if (kind(w) or (DATE.fullmatch(w) and any(p and UR_ANCHOR.fullmatch(p) for p in prev))
                or (SHORT_GROUP.fullmatch(w) and any(p and SHORT_GROUP.fullmatch(p) for p in near))):
            ask.add(w)
    return ask

# ── statusy wartości gold (C2) ───────────────────────────────────────────────
def strip_header(out: str) -> str:
    return out.split(HEADER_END, 1)[1] if out.startswith("[") and HEADER_END in out else out

def doc_ctx(out: str) -> dict:
    """Tekst po /preview, ten sam z tokenami zastąpionymi spacjami (offsety zachowane) i jego słowa (słowo, start, koniec, linia)."""
    clean = TOK.sub(lambda m: " " * len(m.group()), out)
    words = [(m.group().strip("./-"), m.start(), m.end(), clean.count("\n", 0, m.start())) for m in WORD.finditer(clean)]
    return {"out": out, "clean": clean, "words": words}

def _windows(s: str, k: int = FRAG_MIN) -> set[str]:
    return {s[i:i + k] for i in range(len(s) - k + 1)}

def _fuzzy_hit(vn: str, words: list) -> list:
    from benchmark_ocr_diagnostics import MIN_FUZZY_LEN, fuzzy_equal, max_distance, norm
    if len(vn) < MIN_FUZZY_LEN:
        return []
    d = max_distance(len(vn))
    for i in range(len(words)):
        for j in range(i + 1, len(words) + 1):
            if words[j - 1][3] != words[i][3]:
                break
            cand = norm(" ".join(x[0] for x in words[i:j]))
            if len(cand) > len(vn) + d:
                break
            if len(cand) >= len(vn) - d and vn not in cand and fuzzy_equal(vn, cand):
                return words[i:j]
    return []

def _fragment_hit(value: str, words: list) -> list:
    """Fragment >= 4: cyfry wartości w jednym ciągu cyfr słowa albo rdzeń słowa wartości (wielka litera zachowana)."""
    dw = _windows(re.sub(r"\D", "", value))
    stems = [g[:max(FRAG_MIN, len(g) - 2)] for g in re.findall(r"[^\W\d_]{4,}", value)]
    return [x for x in words if any(_windows(r) & dw for r in re.findall(r"\d{4,}", x[0]))
            or any(x[0].lower().startswith(s.lower()) and (x[0][:1].isupper() or not s[:1].isupper()) for s in stems)]

def _chain_hit(words: list, dw: set) -> list:
    """Cyfry rozbite na >= 2 sąsiadujące grupy < 4 w jednej linii, razem z oknem 4 cyfr wartości."""
    hits, chain = [], []
    for x in words + [("", 0, 0, -1)]:
        if re.fullmatch(r"\d{1,3}", x[0]) and (not chain or chain[-1][3] == x[3]):
            chain.append(x)
            continue
        if len(chain) >= 2 and _windows("".join(c[0] for c in chain)) & dw:
            hits += chain
        chain = [x] if re.fullmatch(r"\d{1,3}", x[0]) else []
    return hits

def _weak_hit(value: str, ctx: dict) -> list:
    """Ślad nierozstrzygalny regułą fragmentu: cyfropodobne litery, grupy < 4, reszta cyfr przy tokenie, wnętrze dłuższej wartości."""
    from benchmark_ocr_diagnostics import classify_miss, norm
    digits, words = re.sub(r"\D", "", value), ctx["words"]
    dw = _windows(digits)
    hits = [x for x in words if any(_windows(r) & dw for r in re.findall(r"\d{4,}", x[0].translate(DIGIT_LIKE)))]
    hits += _chain_hit(words, dw)
    spans = [m.span(1) if m.group(1) else m.span(2) for m in TOK_ADJ.finditer(ctx["out"])
             if len(digits) >= FRAG_MIN and (m.group(1) or m.group(2)) in digits]
    hits += [x for x in words if any(x[1] < b and a < x[2] for a, b in spans)]
    if not hits and classify_miss(value, ctx["clean"]) == ("REVIEW", "only_inside_longer_value"):
        hits = [x for x in words if norm(value)[:FRAG_MIN] in norm(x[0])] or [("", 0, 0, -1)]
    return hits

def evidence(value: str, ctx: dict) -> tuple[str | None, list]:
    """('strong' | 'weak' | None, słowa wyjścia niosące wartość)."""
    from benchmark_ocr_diagnostics import norm, present_as_whole
    vn, words = norm(value), ctx["words"]
    if vn and present_as_whole(vn, ctx["clean"]):
        spans = [m.span() for m in re.finditer(r"[\s\-]*".join(map(re.escape, vn)), ctx["clean"], re.I)]
        return "strong", [x for x in words if any(x[1] < b and a < x[2] for a, b in spans)] or [("", 0, 0, -1)]
    for hit in (_fuzzy_hit(vn, words), _fragment_hit(value, words)):
        if hit:
            return "strong", hit
    weak = _weak_hit(value, ctx)
    return ("weak", weak) if weak else (None, [])

def _token_match(value: str, originals: list) -> bool:
    from benchmark_ocr_diagnostics import fuzzy_equal, norm
    vn = norm(value)
    return any(vn == (tn := norm(str(o))) or (len(vn) >= 6 and len(tn) >= FRAG_MIN and (vn in tn or tn in vn))
               or fuzzy_equal(vn, tn) for o in originals)

def _in_text(value: str, text: str) -> bool:
    from benchmark_ocr_diagnostics import has_fuzzy_counterpart, norm, present_as_whole
    vn = norm(value)
    return bool(vn) and (present_as_whole(vn, text) or has_fuzzy_counterpart(vn, text) or vn in norm(text))

def value_status(value: str, ocr_text: str, ctx: dict, originals: list, ask: set) -> tuple[str, list]:
    """Rozłączny status C2 wartości gold w dokumencie niezablokowanym."""
    level, ev = evidence(value, ctx)
    if level:
        if all(x[0] in ask for x in ev):
            return "ASKED", ev
        return ("HOLE" if level == "strong" else "UNKNOWN_REVIEW"), ev
    if _token_match(value, originals):
        return "MASKED", []
    return ("UNKNOWN_REVIEW" if _in_text(value, ocr_text) else "NOT_IN_OCR"), []

def category(resp: dict) -> str:
    """ok / blocked (Guard, odmowa) / ocr_rejected (bramka dzisiejszego OCR) / error."""
    if resp.get("code") == 200 and not resp.get("blocked") and not resp.get("error"):
        return "ok"
    if resp.get("ocr_rejected"):
        return "ocr_rejected"
    return "blocked" if resp.get("blocked") else "error"

def eval_doc(ocr_text: str, resp: dict, entities: dict) -> dict:
    """Wynik dokumentu: kategoria, liczba would_ask, statusy gold (bez wartości)."""
    import benchmark
    doc = {"category": category(resp), "ask": None, "gold": []}
    if doc["category"] != "ok":
        return doc
    ctx = doc_ctx(strip_header(resp.get("out") or ""))
    ask = would_ask(ctx["out"])
    doc["ask"] = len(ask)
    for key, val in entities.items():
        st = value_status(str(val), ocr_text, ctx, resp.get("originals", []), ask)[0]
        doc["gold"].append({"key": key, "type": benchmark._ENTITY_TYPE_MAP.get(key, "?"),
                            "critical": key in benchmark._CRITICAL_KEYS, "status": st})
    return doc

# ── C4: odmowa N, podsumowanie, wybór N, kryteria ────────────────────────────
def accepted(doc: dict, n: int | None) -> bool:
    return doc["category"] == "ok" and (n is None or doc["ask"] / doc.get("pages", 1) <= n)

def _bucket(doc: dict, n: int | None) -> str:
    return "accepted" if accepted(doc, n) else "rejected_n" if doc["category"] == "ok" else doc["category"]

def _med(xs: list) -> float | None:
    return statistics.median(xs) if xs else None

def _gold_counts(docs: list, n: int | None) -> dict:
    ok = [dict(g, level=d.get("level")) for d in docs if d["category"] == "ok" for g in d["gold"]]
    acc = [dict(g, level=d.get("level")) for d in docs if accepted(d, n) for g in d["gold"]]
    cnt = lambda rows, f: dict(sorted(Counter(f(g) for g in rows).items()))   # noqa: E731
    return {"gold_total": sum(d.get("n_gold", len(d["gold"])) for d in docs),
            "gold_evaluated": len(ok), "not_in_ocr": sum(g["status"] == "NOT_IN_OCR" for g in ok),
            "status_all_ok": cnt(ok, lambda g: g["status"]), "status_accepted": cnt(acc, lambda g: g["status"]),
            "status_accepted_critical": cnt([g for g in acc if g["critical"]], lambda g: g["status"]),
            "status_accepted_by_type": cnt(acc, lambda g: f"{g['type']}:{g['status']}"),
            "status_accepted_by_level": cnt(acc, lambda g: f"L{g['level']}:{g['status']}"),
            "hole_crit": sum(g["status"] == "HOLE" and g["critical"] for g in acc),
            "hole_noncrit": sum(g["status"] == "HOLE" and not g["critical"] for g in acc),
            "unknown": sum(g["status"] == "UNKNOWN_REVIEW" for g in acc),
            "unknown_crit": sum(g["status"] == "UNKNOWN_REVIEW" and g["critical"] for g in acc)}

def summarize(docs: list, n: int | None) -> dict:
    by = Counter(_bucket(d, n) for d in docs)
    lv = lambda lvl: [d for d in docs if d.get("level") == lvl]   # noqa: E731
    acc = [d for d in docs if accepted(d, n)]
    l1 = lv(1)
    s = {"n": n, "docs_total": len(docs), "docs": {k: by.get(k, 0) for k in ("accepted", "rejected_n", "blocked", "error", "ocr_rejected")},
         "by_level": {f"L{k}": dict(Counter(_bucket(d, n) for d in lv(k))) for k in sorted({d.get("level") for d in docs})
                      if k is not None},
         "rejected_l0": sum(_bucket(d, n) == "rejected_n" for d in lv(0)),
         "rejected_l1_share": round(sum(_bucket(d, n) == "rejected_n" for d in l1) / len(l1), 3) if l1 else 0.0,
         "ask_median_accepted": _med([d["ask"] for d in acc]), "ask_max_accepted": max((d["ask"] for d in acc), default=None),
         "ask_median_all_ok": _med([d["ask"] for d in docs if d["category"] == "ok"]),
         "ask_max_all_ok": max((d["ask"] for d in docs if d["category"] == "ok"), default=None)}
    s.update(_gold_counts(docs, n))
    return s

def choose_n(docs: list) -> tuple[int | None | str, list]:
    """C4: dopuszczalne N = 0 HOLE krytycznych w przyjętych i 0 odrzuconych L0; najwięcej przyjętych; remis → większe N."""
    table = []
    for n in N_GRID:
        s = summarize(docs, n)
        table.append({"n": n, "admissible": s["hole_crit"] == 0 and s["rejected_l0"] == 0,
                      "accepted": s["docs"]["accepted"], "hole_crit": s["hole_crit"], "rejected_l0": s["rejected_l0"]})
    ok = [t for t in table if t["admissible"]]
    if not ok:
        return "NO_RULE", table
    return max(ok, key=lambda t: (t["accepted"], float("inf") if t["n"] is None else t["n"]))["n"], table

def ready(s: dict, isolation_ok: bool, no_rule: bool = False) -> dict:
    """Kryteria READY_FOR_PRODUCT_BRIEF (holdout, wybrane N). UNKNOWN_REVIEW rozstrzyga CC w DELIVERY."""
    acc, total = s["docs"]["accepted"], s["docs_total"]
    c = {"1_hole_critical_0": s["hole_crit"] == 0,
         "2_hole_noncritical_per_100_accepted": acc > 0 and s["hole_noncrit"] * 100 / acc <= READY_HOLE_PER_100,
         "3_unknown_review_resolved": "PENDING_CC_REVIEW" if s["unknown"] else True,
         "4_rejections": s["rejected_l0"] == 0 and s["rejected_l1_share"] <= READY_L1_REJECT and acc >= READY_ACCEPTED * total,
         "5_ask_median_accepted": s["ask_median_accepted"] is not None and s["ask_median_accepted"] <= READY_ASK_MEDIAN,
         "6_isolation": isolation_ok}
    if no_rule or any(v is False for v in c.values()):
        verdict = "NOT_READY"
    else:
        verdict = "PENDING_CC_REVIEW" if c["3_unknown_review_resolved"] == "PENDING_CC_REVIEW" else "READY_FOR_PRODUCT_BRIEF"
    return {"criteria": c, "verdict": verdict, "no_rule": no_rule}

def cases(docs: list, set_name: str, n: int | None) -> list:
    """Wszystkie HOLE i UNKNOWN_REVIEW (dokumenty niezablokowane) — bez wartości; do przeglądu CC."""
    return [{"set": set_name, "doc": d["id"], "level": d.get("level"), "accepted": accepted(d, n),
             **{k: g[k] for k in ("key", "type", "critical", "status")}}
            for d in docs if d["category"] == "ok" for g in d["gold"] if g["status"] in ("HOLE", "UNKNOWN_REVIEW")]

# ── P1: prostowanie ──────────────────────────────────────────────────────────
def lex_score(text: str) -> tuple[float, int]:
    ws = LEX_WORD.findall(text)
    known = sum(1 for w in ws if any(a[2][2] != "ign" for a in _analyse(w)))
    return (known / len(ws) if ws else 0.0), len(ws)

def choose_rotation(scores: dict) -> int:
    """Obrót o najwyższym odsetku słów Morfeusza (min. P1_MIN_WORDS); remis (< P1_TIE) lub brak minimum → P1_ORDER."""
    ok = {d: s for d, s in scores.items() if s[1] >= P1_MIN_WORDS}
    if not ok:
        return P1_ORDER[0]
    best = max(r for r, _ in ok.values())
    return next(d for d in P1_ORDER if d in ok and best - ok[d][0] < P1_TIE)

def rotate(img, deg: int):
    import cv2
    codes = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return img if deg % 360 == 0 else cv2.rotate(img, codes[deg % 360])

def pp_read(eng, img) -> str:
    import cv2
    from ocr_rapid import build_text
    r = eng(cv2.imencode(".png", img)[1].tobytes())
    return build_text(r.boxes, r.txts) if r is not None and r.boxes is not None else ""

def decide_rotation(eng, img) -> tuple[int, float]:
    """Decyzja na pomniejszonej kopii (dłuższy bok P1_SIDE); zwraca obrót korygujący (w prawo) i czas decyzji."""
    import cv2
    t0 = time.perf_counter()
    f = min(1.0, P1_SIDE / max(img.shape[:2]))
    small = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else img
    deg = choose_rotation({d: lex_score(pp_read(eng, rotate(small, d))) for d in P1_ORDER})
    return deg, time.perf_counter() - t0

def ocr_image(eng, path: Path) -> dict:
    """P1 + jeden pełny odczyt PP na wybranym obrocie."""
    import cv2
    import numpy as np
    img = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"text": "", "rot": None, "secs_decide": 0.0, "secs_ocr": 0.0}
    deg, secs = decide_rotation(eng, img)
    t0 = time.perf_counter()
    return {"text": pp_read(eng, rotate(img, deg)), "rot": deg, "secs_decide": secs, "secs_ocr": time.perf_counter() - t0}

# ── C3: izolacja i worker ────────────────────────────────────────────────────
def snapshot(paths: list) -> dict:
    snap = {}
    for root in map(Path, paths):
        for p in (root.rglob("*") if root.exists() else []):
            try:
                if p.is_file():
                    st = p.stat()
                    snap[str(p)] = (st.st_size, st.st_mtime_ns)
            except OSError:
                snap[str(p)] = None
    return snap

def isolation(before: dict, after: dict) -> tuple[str, int]:
    changed = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k)]
    return ("OK" if not changed else "NOT_RUN(ISOLATION)"), len(changed)

def health_ok(h) -> bool:
    return isinstance(h, dict) and h.get("status") == "ok" and all(h.get(k) for k in ("anonymizer", "spacy_ner", "crypto_ok")) \
        and h.get("morfeusz") not in (None, "unavailable")

def _post(c, hdr: dict, job: dict) -> dict:
    f = ("doc.txt", job["text"].encode("utf-8"), "text/plain") if "text" in job else \
        ("scan.png", Path(job["image"]).read_bytes(), "image/png")
    t0 = time.perf_counter()
    try:
        r = c.post("/preview", files={"file": f}, headers=hdr)
        j = r.json()
    except Exception as e:  # noqa: BLE001
        return {"code": None, "error": type(e).__name__, "secs": time.perf_counter() - t0}
    return {"code": r.status_code, "blocked": bool(j.get("blocked")), "error": bool(j.get("error")),
            "ocr_rejected": bool(j.get("ocr_rejected")), "out": j.get("anonymized_preview") or "",
            "originals": [t.get("original", "") for t in j.get("tokens") or []], "guard_reasons": len(j.get("guard_reasons") or []),
            "ocr_text": j.get("original_text") if "image" in job else None,
            "ocr_quality": (j.get("ocr") or {}).get("quality"), "secs": time.perf_counter() - t0}

def worker(jobs_path: str, out_path: str) -> int:
    """W kopii backendu (cwd): pełny _lifespan przez TestClient, /health, potem /preview dla każdego zadania."""
    sys.path.insert(0, os.getcwd())
    res: dict = {"items": []}
    try:
        import pseudominizer_api as api
        from fastapi.testclient import TestClient
        if not Path(api.__file__).resolve().is_relative_to(Path.cwd().resolve()):
            raise RuntimeError("import_outside_copy")
        with TestClient(api.app, base_url="http://127.0.0.1:8765") as c:
            hdr = {"X-Api-Token": Path(api._API_TOKEN_PATH).read_text(encoding="utf-8").strip()}
            res["health"] = c.get("/health", headers=hdr).json()
            if health_ok(res["health"]):
                res["items"] = [_post(c, hdr, j) for j in json.loads(Path(jobs_path).read_text(encoding="utf-8"))]
    except Exception as e:  # noqa: BLE001 — bez treści wyjątku
        res["startup_error"] = type(e).__name__
    Path(out_path).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return 0

def _worker_env(tmp: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("LYNX_")}
    env.update(ANONYMIZER_PROFILE_DIR=str(tmp / "anon_profile"), PROFILE_DIR=str(tmp / "profile"),
               PSE_REGISTRY=str(tmp / "pse_registry.json"), ARCHIVE_DIR=str(tmp / "archive"),
               HARDWARE_PROFILE=str(tmp / "hardware_profile.json"), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return env

def run_variant(jobs: list, ctx: dict) -> tuple[list | None, dict]:
    """Jedna jednorazowa kopia `git archive <SHA> backend` na przebieg; odpowiedzi tylko gdy start i izolacja OK."""
    tmp, res = Path(tempfile.mkdtemp(prefix="lynx_chain_")), {}
    meta: dict = {"copy_sha": ctx["sha"]}
    t0 = time.perf_counter()
    try:
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", ctx["sha"], "backend"],
                             capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(tmp, filter="data")
        for d in ("anon_profile", "profile", "archive"):
            (tmp / d).mkdir()
        (tmp / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
        subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(tmp / "jobs.json"),
                        str(tmp / "res.json")], cwd=tmp / "backend", env=_worker_env(tmp), capture_output=True,
                       timeout=WORKER_TIMEOUT)
        meta["startup_error_file"] = (tmp / "backend" / "startup_error.json").is_file()
        res = json.loads((tmp / "res.json").read_text(encoding="utf-8")) if (tmp / "res.json").is_file() else \
            {"startup_error": "no_result"}
    except Exception as e:  # noqa: BLE001
        res = {"startup_error": type(e).__name__}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    meta.update(secs=round(time.perf_counter() - t0, 1), health=res.get("health"), startup_error=res.get("startup_error"),
                copy_removed=not tmp.exists())
    meta["startup"] = "OK" if health_ok(res.get("health")) and not res.get("startup_error") \
        and not meta.get("startup_error_file") else "NOT_RUN(STARTUP)"
    meta["isolation"], meta["changed_paths"] = isolation(ctx["snap"], snapshot(ctx["protect"]))
    ok = meta["startup"] == "OK" and meta["isolation"] == "OK" and len(res.get("items", [])) == len(jobs)
    return (res["items"] if ok else None), meta

# ── kroki ────────────────────────────────────────────────────────────────────
def _gt(ds: Path) -> list:
    return json.loads((ds / "ground_truth.json").read_text(encoding="utf-8"))

def _docs(gt: list, reads: list, resps: list, ctx: dict) -> list:
    docs = []
    for g, rd, r in zip(gt, reads, resps):
        ocr_text = r.get("ocr_text") if r.get("ocr_text") is not None else rd.get("text", "")
        d = eval_doc(ocr_text, r, g.get("entities", {}))
        d.update(id=Path(g["file"]).stem, level=g.get("degradation_level"), n_gold=len(g.get("entities", {})),
                 rot=rd.get("rot"), secs_decide=rd.get("secs_decide"), secs_ocr=rd.get("secs_ocr"), secs_preview=r.get("secs"),
                 ocr_quality=r.get("ocr_quality"), guard_reasons=r.get("guard_reasons"))
        docs.append(d)
    return docs

def _run_set(gt: list, reads: list, jobs: list, ctx: dict) -> tuple[list | None, dict]:
    resps, meta = run_variant(jobs or [{"text": r["text"]} for r in reads], ctx)
    return (None if resps is None else _docs(gt, reads, resps, ctx)), meta

def _pp_run(ds: Path, ctx: dict) -> tuple[list | None, dict]:
    gt = _gt(ds)
    return _run_set(gt, [ocr_image(ctx["eng"](), ds / g["file"]) for g in gt], [], ctx)

def step_clean(a, ctx, rep) -> dict:
    gt = _gt(a.clean)
    reads = [{"text": (a.clean / g["file"]).read_text(encoding="utf-8")} for g in gt]
    docs, meta = _run_set(gt, reads, [], ctx)
    if docs is None:
        return {"run": meta, "verdict": "NOT_RUN"}
    return {"run": meta, "summary": summarize(docs, None), "cases": cases(docs, "clean", None)}

def step_known(a, ctx, rep) -> dict:
    docs, meta = _pp_run(a.known, ctx)
    if docs is None:
        return {"run": meta, "chosen_n": "NOT_RUN"}
    chosen, table = choose_n(docs)
    n = None if chosen == "NO_RULE" else chosen
    return {"run": meta, "chosen_n": chosen, "table": table, "summary": summarize(docs, n), "cases": cases(docs, "known", n),
            "p1_rot_at_0": dict(Counter(str(d["rot"]) for d in docs)), "docs": docs}

def step_holdout(a, ctx, rep) -> dict:
    chosen = rep.get("known", {}).get("chosen_n", "NOT_RUN")
    if chosen == "NOT_RUN" or "summary" in rep.get("holdout", {}):
        return {"verdict": "NOT_RUN", "why": "brak N z known albo holdout już zmierzony (jeden raz)"}
    docs, meta = _pp_run(a.holdout, ctx)
    if docs is None:
        return {"run": meta, "verdict": "NOT_RUN"}
    n = None if chosen == "NO_RULE" else chosen
    s = summarize(docs, n)
    return {"run": meta, "n": chosen, "summary": s, "ready": ready(s, meta["isolation"] == "OK", chosen == "NO_RULE"),
            "cases": cases(docs, "holdout", n), "p1_rot_at_0": dict(Counter(str(d["rot"]) for d in docs)), "docs": docs}

def step_p1(a, ctx, rep) -> dict:
    import cv2
    import numpy as np
    rows = []
    for ds in (a.known, a.holdout):
        for g in _gt(ds):
            img = cv2.imdecode(np.fromfile(str(ds / g["file"]), np.uint8), cv2.IMREAD_COLOR)
            for sim in (0, 90, 180, 270):
                deg, secs = decide_rotation(ctx["eng"](), rotate(img, sim))
                rows.append({"sim": sim, "ok": (sim + deg) % 360 == 0, "secs": secs})
    share = lambda rs: round(sum(r["ok"] for r in rs) / max(1, len(rs)), 4)   # noqa: E731
    secs, acc = sorted(r["secs"] for r in rows), share([r for r in rows if r["sim"]])
    out = {"decisions": len(rows), "accuracy_rotated": acc, "secs_median": round(statistics.median(secs), 2),
           "accuracy_by_sim": {s: share([r for r in rows if r["sim"] == s]) for s in (0, 90, 180, 270)},
           "secs_p95": round(secs[int(0.95 * (len(secs) - 1))], 2), "secs_max": round(secs[-1], 2)}
    out["target_met"] = acc >= P1_TARGET_ACC and out["secs_median"] <= P1_TARGET_SECS
    out["P2_NEEDED"] = not out["target_met"]
    return out

def step_product(a, ctx, rep) -> dict:
    out = {}
    for name, ds in (("known", a.known), ("holdout", a.holdout)):
        gt = _gt(ds)
        docs, meta = _run_set(gt, [{} for _ in gt], [{"image": str((ds / g["file"]).resolve())} for g in gt], ctx)
        out[name] = {"run": meta} if docs is None else {"run": meta, "summary": summarize(docs, None),
                                                       "cases": cases(docs, f"product_{name}", None)}
    return out

def step_real(a, ctx, rep) -> dict:
    """Realne zdjęcia: wyłącznie agregaty (bez nazw plików, tekstu, ID)."""
    paths = sorted(p for p in a.real.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    reads = [ocr_image(ctx["eng"](), p) for p in paths]
    resps, meta = run_variant([{"text": r["text"]} for r in reads], ctx)
    if resps is None:
        return {"run": meta, "verdict": "NOT_RUN"}
    docs = [eval_doc(rd["text"], r, {}) for rd, r in zip(reads, resps)]
    asks = [d["ask"] for d in docs if d["category"] == "ok"]
    chosen = rep.get("known", {}).get("chosen_n")
    return {"run": meta, "images": len(paths), "categories": dict(Counter(d["category"] for d in docs)),
            "rotation": dict(Counter(str(r["rot"]) for r in reads)), "ask_median": _med(asks), "ask_max": max(asks, default=None),
            "rejected_at_n": {str(n): sum(x > n for x in asks) for n in N_GRID if n} | {"chosen_n": chosen},
            "secs_decide_median": _med([r["secs_decide"] for r in reads]), "secs_decide_max": max(r["secs_decide"] for r in reads),
            "secs_ocr_median": _med([r["secs_ocr"] for r in reads])}

STEPS = {s: globals()[f"step_{s}"] for s in ("clean", "known", "holdout", "p1", "product", "real")}

# ── wejście ──────────────────────────────────────────────────────────────────
def _repo_roots() -> set:
    common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True, text=True).stdout.strip()
    return {ROOT} | ({Path(common).resolve().parent} if common else set())

def check_paths(a) -> str | None:
    """Tryb gold tylko na syntetycznych paczkach z ground_truth.json; --out poza repo."""
    for ds in (a.known, a.holdout, a.clean):
        if ds is not None and ("dataset_real" in ds.resolve().as_posix() or not (ds / "ground_truth.json").is_file()):
            return f"{ds.name}: tylko syntetyczna paczka z ground_truth.json"
    if any(r == a.out.resolve() or r in a.out.resolve().parents for r in _repo_roots()):
        return "--out musi leżeć poza repo"
    return None

def setup(a) -> dict | str:
    import ocr_rapid
    from pp_quality import MODEL_SHA256, digest, preflight
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    pre = preflight(ocr_rapid.model_dir())
    needs_pp = bool({"known", "holdout", "p1", "real"} & set(a.steps.split(",")))
    if needs_pp and not (pre and pre["models_match_phase_a"]):
        return "modele PP-OCRv6 brak/inne niż faza A (SHA256)"
    me = Path(__file__).resolve()
    dirty = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", str(me)]).returncode != 0
    protect = [ROOT / "backend", Path.home() / ".pseudominizer", Path.home() / "lynx_models", *a.protect]
    meta = {"code_sha": sha, "script_sha256": hashlib.sha256(me.read_bytes()).hexdigest(), "script_dirty_vs_head": dirty, "pp": pre, "pp_expected": MODEL_SHA256,
            "herbert": "NOT_RUN(HerBERT): odłożony — skrypt > 600 linii (brief GATE)", "protected_roots": len(protect),
            "digests": {k: digest(p) for k, p in (("known", a.known), ("holdout", a.holdout), ("clean", a.clean)) if p},
            "rules": {k: v for k, v in globals().items() if k.startswith(("N_GRID", "FRAG_MIN", "P1_", "READY_"))}}
    return {"sha": sha, "protect": protect, "snap": snapshot(protect), "eng": ocr_rapid._get_engine, "meta": meta}

def _line(step: str, r: dict) -> str:
    s, run = r.get("summary") or {}, r.get("run") or {}
    return (f"[CHAIN] {step}: start={run.get('startup')} izolacja={run.get('isolation')} N={r.get('chosen_n', r.get('n'))} "
            f"docs={s.get('docs')} HOLE kryt/niekryt={s.get('hole_crit')}/{s.get('hole_noncrit')} UNKNOWN={s.get('unknown')} "
            f"ask_med={s.get('ask_median_accepted')} werdykt={(r.get('ready') or {}).get('verdict', r.get('verdict', '-'))}")

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    for name in ("--known", "--holdout", "--clean", "--real"):
        ap.add_argument(name, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--steps", default="clean,known")
    ap.add_argument("--protect", type=Path, action="append", default=[])
    a = ap.parse_args(argv)
    why = check_paths(a) or next((f"krok {s} wymaga brakującej ścieżki" for s in a.steps.split(",")
                                  if s not in STEPS or (s in ("known", "holdout", "p1", "product") and not (a.known and a.holdout))
                                  or (s == "clean" and not a.clean) or (s == "real" and not a.real)), None)
    ctx = setup(a) if not why else why
    if isinstance(ctx, str):
        print("NOT_RUN:", ctx)
        return 2
    report = json.loads(a.out.read_text(encoding="utf-8")) if a.out.is_file() else {}
    report.setdefault("meta", {}).update(ctx["meta"])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    for step in a.steps.split(","):
        report[step] = STEPS[step](a, ctx, report)
        a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(_line(step, report[step]), flush=True)
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        raise SystemExit(worker(sys.argv[2], sys.argv[3]))
    raise SystemExit(main())
