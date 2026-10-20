"""LYNX-OCR-CASCADE C1: kontrpróby parowania PP/Tesseract na sztucznych ramkach (bez modeli, bez obrazów z danymi)."""
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-CASCADE" / "measure"))
pytest.importorskip("stdnum")
import paired_ocr as po  # noqa: E402

NIP_OK, NIP_BAD = "7423337590", "742337590"       # poprawna suma / brak cyfry
NIP_OK2 = "5260250274"
PESEL_OK = "50022458822"
IBAN_OK = "PL33240101356059863195777884"


def box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def tsv(words, size=(1000, 1000)):
    """words: (line_key, x0, y0, x1, y1, text, conf); pierwszy wiersz = strona (level 1)."""
    d = {k: [] for k in ("level", "page_num", "block_num", "par_num", "line_num", "left", "top", "width", "height",
                         "conf", "text")}
    rows = [(1, (0, 0, 0), 0, 0, size[0], size[1], -1, "")] + [(5, *w[:5], w[6], w[5]) for w in words]
    for lv, key, x0, y0, x1, y1, conf, text in rows:
        for k, v in zip(d, (lv, 1, *key, x0, y0, x1 - x0, y1 - y0, conf, text)):
            d[k].append(v)
    return d


def classify(pp, words):
    lines, _ = po.tess_lines(tsv(words))
    return po.classify_doc(po.pp_regions([b for b, _ in pp], [t for _, t in pp]), lines)


def test_ids_checksums():
    assert dict(po.ids(f"NIP: {NIP_OK[:3]}-{NIP_OK[3:6]}-{NIP_OK[6:8]}-{NIP_OK[8:]}")) == {NIP_OK: True}
    assert dict(po.ids(f"IBAN: {IBAN_OK}"))[IBAN_OK] is True
    assert dict(po.ids("NIP 742-33-75-90")) == {NIP_BAD: False}
    assert po.ids("65-001 Gdańsk, tel. 12") == []


def test_two_columns_similar_values_not_joined():
    pp = [(box(100, 100, 300, 130), f"NIP {NIP_OK}"), (box(600, 100, 800, 130), f"NIP {NIP_OK2}"),
          (box(100, 140, 300, 170), f"NIP {NIP_OK2}")]
    words = [((1, 1, 1), 100, 100, 140, 130, "NIP", 90), ((1, 1, 1), 150, 100, 300, 130, NIP_OK, 90),
             ((1, 1, 1), 600, 100, 640, 130, "NIP", 90), ((1, 1, 1), 650, 100, 800, 130, NIP_OK2, 90),
             ((1, 1, 2), 100, 140, 140, 170, "NIP", 90), ((1, 1, 2), 150, 140, 300, 170, NIP_OK2, 90)]
    out = classify(pp, words)
    assert [(r["status"], r["tess_text"]) for r in out] == [
        ("BOTH_AGREE", f"NIP {NIP_OK}"), ("BOTH_AGREE", f"NIP {NIP_OK2}"), ("BOTH_AGREE", f"NIP {NIP_OK2}")]


def test_distorted_pp_valid_tess_same_field_only():
    pp = [(box(100, 100, 300, 130), f"NIP {NIP_BAD}")]
    same = [((1, 1, 1), 100, 100, 140, 130, "NIP", 90), ((1, 1, 1), 150, 100, 300, 130, NIP_OK, 90)]
    assert classify(pp, same)[0]["status"] == "PP_DISTORTED_TESS_VALID"
    far = [((1, 1, 1), 100, 100, 140, 130, "NIP", 90), ((1, 1, 1), 150, 100, 300, 130, "123", 90),
           ((2, 1, 1), 100, 700, 300, 730, NIP_OK, 90)]
    out = classify(pp, far)
    assert out[0]["status"] == "CONFLICT_REVIEW" and out[0]["reason"] == "pp_invalid_id"
    assert out[1]["src"] == "tess" and out[1]["status"] == "PP_MISSING_TESS_PRESENT"   # tylko jako osobny brak


def test_missing_line_iban_is_candidate_without_insert():
    pp = [(box(100, 100, 300, 130), "Wezwanie do zapłaty")]
    words = [((1, 1, 1), 100, 100, 300, 130, "Wezwanie do zapłaty", 90),
             ((1, 1, 2), 100, 300, 160, 330, "IBAN:", 90), ((1, 1, 2), 170, 300, 600, 330, IBAN_OK, 85)]
    out = classify(pp, words)
    assert out[0]["status"] == "BOTH_AGREE"
    assert (out[1]["status"], out[1]["reason"], out[1]["pp_text"]) == ("PP_MISSING_TESS_PRESENT", "valid_id", "")


@pytest.mark.parametrize("pp_t,tess_t,reason", [(NIP_OK, NIP_OK2, "two_valid_ids"), (NIP_BAD, "742337591", "pp_invalid_id"),
                                                (PESEL_OK, "5002245882", "checksum_favors_pp")])
def test_conflicts_not_resolved_by_validator(pp_t, tess_t, reason):
    assert po.judge_pair(f"nr {pp_t}", f"nr {tess_t}") == ("CONFLICT_REVIEW", reason)


def test_uncertain_inputs_never_default_agree():
    assert po.judge_pair("Łódź, ul. Żółta", "Lodz, ul. Zolta")[0] == "CONFLICT_REVIEW"
    bad = po.pp_regions([box(10, 10, 10, 30), [[0, 0], [1, 1]], [[0, 0], [100, 80], [90, 120], [-10, 40]],
                         [[0, 0], [100, 40], [100, 60], [0, 20]], None], ["a", "b", "c", "d", "e"])
    assert [r["bad"] for r in bad] == ["bad_box", "bad_box", "bad_box", "rotated", "bad_box"]
    assert po.pp_regions([box(10, 10, 5, 5)], ["odwrócona"])[0]["bad"] == "rotated"
    dup = classify([(box(100, 100, 300, 130), "Jan"), (box(102, 100, 300, 131), "Jan")],
                   [((1, 1, 1), 100, 100, 300, 130, "Jan", 90)])
    assert [r["reason"] for r in dup] == ["duplicate_box", "duplicate_box"]
    lines, bad_words = po.tess_lines(tsv([((1, 1, 1), 10, 10, 5, 30, "x", 90), ((1, 1, 1), 10, 10, 50, 30, "Ala", 90)]))
    assert bad_words == 1 and len(lines) == 1
    two = classify([(box(100, 100, 300, 160), "Ala ma")], [((1, 1, 1), 100, 100, 300, 128, "Ala", 90),
                                                          ((1, 1, 2), 100, 132, 300, 160, "ma", 90)])
    assert two[0]["reason"] == "ambiguous_lines"


class _Res:
    def __init__(self, boxes, txts):
        self.boxes, self.txts = boxes, txts


def _png(size=(400, 200)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _boom(_):
    raise RuntimeError("Tesseract process timeout")


def _no_model(_):
    raise FileNotFoundError("brak modeli PP-OCR: det")


@pytest.mark.parametrize("pp_fn,tess_fn,why", [
    (_no_model, lambda img: tsv([]), "pp_FileNotFoundError"),
    (lambda b: _Res([], []), _boom, "tess_timeout"),
    (lambda b: _Res([], []), lambda img: tsv([], size=(800, 200)), "frame_mismatch"),
    (lambda b: _Res([box(1, 1, 9, 9)], []), lambda img: tsv([], size=(400, 200)), "pp_inconsistent")])
def test_failures_are_unmeasurable(pp_fn, tess_fn, why, capsys):
    doc = po.measure_doc(_png(), pp_fn, tess_fn)
    assert doc["unmeasurable"] == why and doc["regions"] == []
    gold = po.gold_cases(doc, {"pesel": PESEL_OK})
    assert gold[0]["pp"] == "UNMEASURED" and not gold[0]["alarmed"]
    assert PESEL_OK not in capsys.readouterr().out


def test_deterministic_and_value_free_summary():
    words = [((1, 1, 1), 100, 100, 140, 130, "NIP", 90), ((1, 1, 1), 150, 100, 300, 130, NIP_OK, 90)]
    pp_fn = lambda b: _Res([box(100, 100, 300, 130)], [f"NIP {NIP_BAD}"])  # noqa: E731
    runs = []
    for _ in range(2):
        doc = po.measure_doc(_png(), pp_fn, lambda img: tsv(words, size=(400, 200)))
        doc.update(gold=po.gold_cases(doc, {"nip": NIP_OK}), file="doc_x.png", level=1)
        runs.append((po.summary([doc]), po._cases([doc])))
    for r in runs:
        r[0].pop("secs_pp"), r[0].pop("secs_tess")
    assert runs[0] == runs[1]
    s, cases = runs[0]
    assert s["regions"] == {"PP_DISTORTED_TESS_VALID": 1} and s["tess_valid_regions"] == {"True": 1}
    assert cases[0]["rescue_candidate"] and NIP_OK not in repr(runs[0])


def test_paths_outside_repo_and_synthetic_only(tmp_path):
    ds = tmp_path / "dataset_x"
    ds.mkdir()
    (ds / "ground_truth.json").write_text("[]", encoding="utf-8")
    args = type("A", (), {"known": ds, "holdout": ds, "out": ROOT / "out.json"})
    assert "poza repo" in po._check_paths(args)
    args.out = tmp_path / "out.json"
    assert po._check_paths(args) is None
    args.known = tmp_path / "dataset_real"
    assert po._check_paths(args) is not None


@pytest.mark.parametrize("gap,parts", [(0, 1), (650, 2)])
def test_tess_rest_split_by_column_gap(gap, parts):
    """Codex r2 F1: dwa odległe pola jednej linii TSV nie tworzą razem poprawnego NIP."""
    words = [((1, 1, 1), 10, 20, 100, 40, NIP_OK[:5], 90), ((1, 1, 1), 110 + gap, 20, 200 + gap, 40, NIP_OK[5:], 90)]
    out = classify([], words)
    assert len(out) == parts
    assert [r["reason"] for r in out] == (["valid_id"] if parts == 1 else ["text", "text"])


def test_bad_box_in_full_doc_is_status_not_crash():
    """Codex r2 F2: ramka None przechodzi przez measure_doc jako UNMEASURABLE, bez wyjątku."""
    doc = po.measure_doc(_png(), lambda b: _Res([None, box(10, 10, 200, 40)], ["x", "Ala"]),
                         lambda img: tsv([((1, 1, 1), 10, 10, 200, 40, "Ala", 90)], size=(400, 200)))
    assert doc["unmeasurable"] is None and doc["pp_text"] == "Ala"
    assert [(r["status"], r["reason"]) for r in doc["regions"]] == [("UNMEASURABLE", "bad_box"), ("BOTH_AGREE", "text_equal")]
