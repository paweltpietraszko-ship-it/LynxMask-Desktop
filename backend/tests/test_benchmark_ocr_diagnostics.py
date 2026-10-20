# LYNX-OCR-PARITY krok 1 — testy diagnostyki „silnik czy OCR” (dane wyłącznie syntetyczne).
# Uruchamiać jawnie: py -3 -m pytest tests/test_benchmark_ocr_diagnostics.py -q (plik spoza pytest.ini python_files).
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import benchmark  # noqa: E402
import benchmark_ocr_diagnostics as d  # noqa: E402


@pytest.mark.parametrize("v", ["Jan  Kowalski", "ul. Polna 1\n00-950 Warszawa", "+48 605-858-864", "A\r\nB", ""])
def test_norm_identical_to_benchmark(v):
    assert d.norm(v) == benchmark._norm(v)


@pytest.mark.parametrize("value,text,label", [
    ("44051401359", "PESEL: 44051401359\nkoniec", "BUG_SILNIKA"),                   # dokładnie w tekście silnika
    ("+48 605 858 864", "Tel.: +48 605 858 864", "BUG_SILNIKA"),                    # spacje bez znaczenia
    ("jan.kowalski83@poczta.pl", "E-mail: jan.kowalski83Qpoczta.pl", "OCR_ZNIEKSZTAŁCONY"),   # @ → Q
    ("+48 605 858 864", "Tel.: +48 605 B58 864", "OCR_ZNIEKSZTAŁCONY"),             # cyfra przekręcona, ze spacjami
    ("44051401359", "Dokument bez tej wartości 98765432109", "BRAK_W_OCR"),         # inny numer tej długości
    ("jan.kowalski@firma.pl", "jan.kowalski\nQfirma.pl", "BRAK_W_OCR"),             # bez sklejania linii
    ("44051401359", None, "NOT_MEASURED"),
    ("44051401359", "   ", "NOT_MEASURED"),
    ("Jan Nowak", "Jan Nowek", "REVIEW"),                                           # <9 znaków: bez fuzzy
    # Codex r2 F1: fragment dłuższej obcej wartości to nie BUG_SILNIKA ani zniekształcenie
    ("Jan Nowak", "Podpis: Jan Nowakowski", "REVIEW"),
    ("anna@example.org", "Kontakt: joanna@example.org", "REVIEW"),
    ("44051401359", "Numer: 1440514013599", "REVIEW"),
    ("Jan Nowak", "Podpis: Jan Nowak.", "BUG_SILNIKA"),                             # interpunkcja to granica
    ("anna@example.org", "Kontakt: anna@example.org.pl", "REVIEW"),                # Codex r3: dłuższa domena
    ("anna@example.org", "Pisz na anna@example.org. Dziękuję", "BUG_SILNIKA"),     # kropka kończąca zdanie
    ("44051401359", "PESEL:\n440514 01359", "BUG_SILNIKA"),                         # spacje i nowa linia w środku
])
def test_classify_miss(value, text, label):
    assert d.classify_miss(value, text)[0] == label


@pytest.mark.parametrize("length,d1_ok,d2_ok,d3_ok", [(9, True, False, False), (15, True, True, False),
                                                      (24, True, True, True)])
def test_distance_thresholds(length, d1_ok, d2_ok, d3_ok):
    base = "a" * length
    assert d.fuzzy_equal(base, "b" + base[1:]) is d1_ok
    assert d.fuzzy_equal(base, "bb" + base[2:]) is d2_ok
    assert d.fuzzy_equal(base, "bbb" + base[3:]) is d3_ok
    assert d.fuzzy_equal("a" * 8, "b" + "a" * 7) is False


def test_classify_extra_four_labels():
    gold = [(d.norm("jan.kowalski@poczta.pl"), "EMAIL")]
    assert d.classify_extra({"original": "jan.kowalskiQpoczta.pl", "type": "EMAIL"}, gold) == "EXTRA_MASK_OK"
    assert d.classify_extra({"original": "1 500,00 zł", "type": "KWOTA"}, gold) == "EXTRA_MASK_POLICY"
    assert d.classify_extra({"original": "Dane osobowe", "type": "OSOBA"}, gold) == "UX_FP"
    assert d.classify_extra({"original": "Kraków", "type": "ORGANIZACJA"}, gold) == "REVIEW"


def _gt(file, **ents):
    return {"file": file, "doc_type": "x", "quality_score": 90, "degradation_level": 0, "entities": ents}


def _resp(text, tokens, **kw):
    return dict({"bench_http_status": 200, "original_text": text, "tokens": tokens}, **kw)


def _run(collector, gt, resp):
    result = benchmark.analyze(gt, resp)
    collector.record(gt, resp, result)
    return result


def test_collector_counts_match_legacy_and_statuses(tmp_path):
    c = d.Collector()
    tok = [{"token": "NUMER_001", "original": "44051401359", "type": "NUMER"},
           {"token": "KWOTA_001", "original": "1 500,00 zł", "type": "KWOTA"},
           {"token": "OSOBA_001", "original": "Dane osobowe", "type": "OSOBA"}]
    r1 = _run(c, _gt("a.png", pesel="44051401359", email="jan.kowalski83@poczta.pl", telefon="+48 605 858 864"),
              _resp("PESEL 44051401359 e-mail jan.kowalski83Qpoczta.pl tel. +48 605 858 864", tok))
    _run(c, _gt("b.png", pesel="44051401359"), _resp("", [], ocr_rejected=True))           # bez klasyfikacji
    _run(c, _gt("c.png", pesel="44051401359"), {"bench_error": "Timeout", "bench_http_status": 0})
    _run(c, _gt("d.png", pesel="44051401359"), _resp("PESEL 44051401359", [], blocked=True))
    s = c.write(tmp_path)
    assert s["docs"] == {"accepted": 1, "guard_blocked": 1, "rejected": 1, "error": 1}
    assert s["miss"]["BUG_SILNIKA"] == 2 and s["miss"]["OCR_ZNIEKSZTAŁCONY"] == 1
    assert s["miss_in_guard_blocked_docs"] == {"BUG_SILNIKA": 1}
    assert s["extra"] == {"EXTRA_MASK_OK": 0, "EXTRA_MASK_POLICY": 1, "UX_FP": 1, "REVIEW": 0}
    assert r1["summary"]["false_positives"] == 2 and s["consistent_with_legacy"] is True


def test_report_has_no_values_and_is_deterministic(tmp_path):
    def run(out):
        c = d.Collector()
        _run(c, _gt("a.png", email="jan.kowalski83@poczta.pl", pesel="44051401359"),
             _resp("e-mail jan.kowalski83Qpoczta.pl, PESEL 44051401359", []))
        c.write(out)
        return (out / "ocr_diagnostics.json").read_text(encoding="utf-8")
    (tmp_path / "1").mkdir(), (tmp_path / "2").mkdir()
    a, b = run(tmp_path / "1"), run(tmp_path / "2")
    assert a == b
    for secret in ("44051401359", "kowalski", "poczta"):
        assert secret not in a
    items = json.loads(a)["items"]
    assert {i["label"] for i in items} == {"BUG_SILNIKA", "OCR_ZNIEKSZTAŁCONY"}
    assert set(items[0]) == {"file", "kind", "key", "type", "label", "reason", "doc_status"}


def test_benchmark_hooks_keep_legacy_result(tmp_path, monkeypatch):
    c = d.Collector()
    monkeypatch.setattr(d, "_DEFAULT", c)
    gt, resp = _gt("a.png", pesel="44051401359"), _resp("PESEL 44051401359", [])
    assert d.analyze_and_record(benchmark.analyze, gt, resp) == benchmark.analyze(gt, resp)
    calls = []
    s = d.build_report_and_write(lambda r, p: calls.append((r, p)), ["x"], tmp_path)
    assert calls == [(["x"], tmp_path)] and s["miss"]["BUG_SILNIKA"] == 1
