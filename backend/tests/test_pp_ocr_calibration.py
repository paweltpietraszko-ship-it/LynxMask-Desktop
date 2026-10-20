# LYNX-OCR-PARITY krok 2 faza B1 — testy narzędzia kalibracji PP-OCRv6 (stuby interfejsu RapidOCR, dane syntetyczne).
# Uruchamiać jawnie: py -3 -m pytest tests/test_pp_ocr_calibration.py -q (plik spoza pytest.ini python_files).
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_spec = importlib.util.spec_from_file_location("pp_quality", ROOT / "tasks/LYNX-OCR-PARITY-STEP2/measure/pp_quality.py")
pq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pq)


def box(y):
    return [[10, y], [300, y], [300, y + 20], [10, y + 20]]


class Engine:
    """Stub: zwraca ustalone linie; zapisuje użyty text_score."""

    def __init__(self, lines):
        self.lines, self.calls = lines, []

    def __call__(self, image, text_score=None):
        self.calls.append(text_score)
        if self.lines is None:
            return SimpleNamespace(boxes=None, txts=None, scores=None)
        return SimpleNamespace(boxes=[box(30 * i) for i in range(len(self.lines))],
                               txts=[t for t, _ in self.lines], scores=[s for _, s in self.lines])


@pytest.mark.parametrize("res", [
    SimpleNamespace(boxes=[box(0)], txts=["a", "b"], scores=[0.9, 0.9]),        # rozbieżne długości
    SimpleNamespace(boxes=[box(0)], txts=["a"], scores=[float("nan")]),
    SimpleNamespace(boxes=[box(0)], txts=["a"], scores=[float("inf")]),
    SimpleNamespace(boxes=[box(0)], txts=["a"], scores=[1.5]),
    SimpleNamespace(boxes=[box(0)], txts=["a"], scores=None),
])
def test_invalid_scores_mean_no_basis_and_reject(res):
    assert pq.validate(res) is None
    doc = {"valid": False, "features": {}, "gold": []}
    assert all(pq.status(doc, r) == "reject" for r in pq.GRID)


def test_measure_doc_uses_all_lines_but_production_text_filter():
    eng = Engine([("PESEL 44051401359", 0.98), ("szum", 0.3), ("jan@poczta.pl", 0.91)])
    d = pq.measure_doc(eng, b"img", {"pesel": "44051401359", "email": "jan@poczta.pl", "telefon": "+48 605 858 864"})
    assert eng.calls == [0.0]                                    # silnik pyta o wszystkie linie
    f = d["features"]
    assert (f["n_boxes"], f["n_lines_kept"], f["n_dropped_by_filter"]) == (3, 2, 1)
    assert f["min"] == 0.91 and f["share_below_0.9"] == 0.0
    assert [(g["key"], g["label"], g["critical"]) for g in d["gold"]] == [
        ("pesel", "INTACT", True), ("email", "INTACT", False), ("telefon", "MISSING", False)]


def test_empty_or_missing_result_is_reject_with_all_gold_missing():
    for lines in (None, []):
        d = pq.measure_doc(Engine(lines), b"img", {"pesel": "44051401359"})
        assert d["gold"][0]["label"] == "MISSING"
        assert all(pq.status(d, r) == "reject" for r in pq.GRID)


def _doc(min_score, labels, critical=True, typ="NUMER"):
    return {"valid": True, "file": "x.png", "features": {"min": min_score, "q10": min_score},
            "gold": [{"key": f"k{i}", "type": typ, "critical": critical, "label": lab} for i, lab in enumerate(labels)]}


def test_evaluate_counts_ok_warn_reject_and_accepted_losses():
    docs = [_doc(0.97, ["INTACT"]), _doc(0.86, ["DISTORTED"]), _doc(0.5, ["INTACT", "MISSING"])]
    t = pq.evaluate(docs, ("min", 0.95, 0.85))
    assert t["docs"] == {"ok": 1, "warn": 1, "reject": 1}
    assert t["accepted_gold"] == {"INTACT": 1, "DISTORTED": 1}
    assert t["accepted_critical_not_intact"] == 1 and t["rejected_gold_intact"] == 1


def test_select_uses_only_known_tables_and_can_report_no_safe_gate():
    known = [pq.evaluate([_doc(0.97, ["INTACT"]), _doc(0.55, ["DISTORTED"])], r) for r in pq.GRID]  # 0.55 < każdy próg warn
    chosen = pq.select(known)
    assert chosen["accepted_critical_not_intact"] == 0
    assert pq.select([pq.evaluate([_doc(0.99, ["MISSING"])], r) for r in pq.GRID]) is None


def test_summary_lists_high_score_errors_without_values():
    docs = [dict(_doc(0.95, ["MISSING", "INTACT"]), secs=1.0)]
    s = pq.summary(docs)
    assert s["high_score_errors"] == [{"file": "x.png", "key": "k0", "type": "NUMER", "label": "MISSING", "doc_min": 0.95}]


def test_report_end_to_end_has_no_values_and_is_deterministic(tmp_path, monkeypatch):
    for name in ("known", "holdout"):
        ds = tmp_path / name
        (ds / "images").mkdir(parents=True)
        (ds / "images" / "a.png").write_bytes(b"img")
        (ds / "ground_truth.json").write_text(json.dumps([{"file": "images/a.png", "degradation_level": 0,
                                                           "entities": {"pesel": "44051401359"}}]), encoding="utf-8")
    import ocr_rapid
    monkeypatch.setattr(pq, "preflight", lambda d: {"rapidocr": "stub", "onnxruntime": "stub", "model_sha256": {},
                                                     "models_match_phase_a": True})
    monkeypatch.setattr(ocr_rapid, "_get_engine", lambda: Engine([("PESEL 44051401359", 0.97)]))
    outs = []
    for i in (1, 2):
        out = tmp_path / f"r{i}.json"
        assert pq.main(["--known", str(tmp_path / "known"), "--holdout", str(tmp_path / "holdout"), "--out", str(out)]) == 0
        rep = json.loads(out.read_text(encoding="utf-8"))
        for side in ("known", "holdout"):
            for d in rep["docs"][side]:
                d.pop("secs")
            rep[side]["summary"].pop("secs_per_page")
        rep["meta"].pop("rss_mb")
        outs.append(json.dumps(rep, sort_keys=True))
    assert outs[0] == outs[1] and "44051401359" not in outs[0]
    assert json.loads(outs[0])["verdict"] == "CANDIDATE"


def test_not_run_without_models(tmp_path, monkeypatch, capsys):
    import ocr_rapid
    monkeypatch.setattr(ocr_rapid, "model_dir", lambda: tmp_path)
    assert pq.main(["--known", str(tmp_path), "--holdout", str(tmp_path), "--out", str(tmp_path / "o.json")]) == 2
    assert "NOT_RUN" in capsys.readouterr().out and not (tmp_path / "o.json").exists()


def test_not_run_when_model_hashes_differ_from_phase_a(tmp_path, monkeypatch, capsys):
    import ocr_rapid
    for name in pq.MODEL_SHA256:
        (tmp_path / name).write_bytes(b"inny model")
    monkeypatch.setattr(ocr_rapid, "model_dir", lambda: tmp_path)
    monkeypatch.setattr(ocr_rapid, "_get_engine", lambda: pytest.fail("pomiar nie może ruszyć przy innych modelach"))
    assert pq.main(["--known", str(tmp_path), "--holdout", str(tmp_path), "--out", str(tmp_path / "o.json")]) == 2
    assert "SHA256" in capsys.readouterr().out and not (tmp_path / "o.json").exists()
