"""LYNX-OCR-GATE-COMPARE ETAP 1: reguły pomiaru łańcucha (bez modeli i silnika; atrapy odpowiedzi /preview tylko tutaj)."""
import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tasks" / "LYNX-OCR-GATE-COMPARE" / "measure"))
import chain_compare as cc  # noqa: E402

NIP = "742-337-55-90"
IBAN = "PL61 1090 1014 0000 0712 1981 2874"
PHONE = "+48 663 794 026"


def status(value, out, ask=(), originals=(), ocr=None):
    return cc.value_status(value, out if ocr is None else ocr, cc.doc_ctx(out), list(originals), set(ask))[0]


def resp(out, code=200, blocked=False, originals=()):
    return {"code": code, "blocked": blocked, "error": False, "out": "[Dokument pseudonimizowany. Kod sesji: X.]\n\n" + out,
            "originals": list(originals)}


def doc(level, ask, gold=(), category="ok"):
    return {"id": f"d{level}{ask}", "level": level, "category": category, "ask": ask, "n_gold": len(gold),
            "gold": [{"key": k, "type": "NUMER", "critical": c, "status": s} for k, c, s in gold]}


# ── Guard-reszta (Morfeusz to biblioteka, nie model) ─────────────────────────

def test_guard_asks_capitalized_surname_that_is_common_word():
    pytest.importorskip("morfeusz2")
    assert cc.kind("Kowal") == "name" and "Kowal" in cc.would_ask("Pozwany Kowal wniósł apelację.")


def test_guard_asks_split_phone_and_birth_date():
    pytest.importorskip("morfeusz2")
    ask = cc.would_ask("tel. 663 794 026, ur. 12.03.1985, w dniu 12.03.1985")
    assert {"663", "794", "026", "12.03.1985"} <= ask


def test_guard_does_not_ask_ordinary_words():
    pytest.importorskip("morfeusz2")
    assert cc.would_ask("umowa została zawarta dnia 12.03.2024 w sprawie 5 ust") == set()
    assert cc.kind("kowal") is None and cc.kind("UMOWA") is None


def test_guard_token_counts_as_word_but_is_never_asked():
    assert cc.residue_seq("NIP NUMER_006-90 x") == ["NIP", None, "90", "x"]


# ── statusy C2 ───────────────────────────────────────────────────────────────

def test_damaged_nip_visible_is_hole_unless_asked():
    out = "NIP: 742-337-55-9O"
    assert status(NIP, out) == "HOLE"
    assert status(NIP, out, ask={"742-337-55-9O"}) == "ASKED"


def test_nip_tail_next_to_token_is_unknown_review():
    out = "NIP: NUMER_006-90"
    assert status(NIP, out, originals=["742-337-55"]) == "UNKNOWN_REVIEW"
    assert status(NIP, out, ask={"90"}, originals=["742-337-55"]) == "ASKED"


def test_iban_fragment_of_four_digits_is_hole():
    out = "konto NUMER_002 1981 2874"
    assert status(IBAN, out, originals=["PL61 1090 1014 0000 0712"]) == "HOLE"
    assert status(IBAN, out, ask={"1981", "2874"}) == "ASKED"


def test_iban_fully_masked():
    assert status(IBAN, "konto NUMER_002", originals=[IBAN], ocr="konto " + IBAN) == "MASKED"


def test_phone_split_into_short_groups_is_unknown_review():
    out = "tel. 663 794 NUMER_003"
    assert status(PHONE, out, originals=["026"]) == "UNKNOWN_REVIEW"
    assert status(PHONE, out, ask={"663", "794"}) == "ASKED"


def test_not_in_ocr_vs_lost_without_token():
    assert status(NIP, "NIP: brak", ocr="NIP: brak") == "NOT_IN_OCR"
    assert status(NIP, "NIP: brak", ocr="NIP: " + NIP) == "UNKNOWN_REVIEW"


def test_surname_fragment_inflected_is_hole():
    assert status("Jan Kowalski", "doręczono Kowalskiemu pismo") == "HOLE"
    assert status("Jan Kowalski", "doręczono OSOBA_001 pismo", originals=["Jan Kowalski"], ocr="doręczono Jan Kowalski pismo")         == "MASKED"


# ── kategorie i C4 ───────────────────────────────────────────────────────────

def test_blocked_document_is_not_accepted():
    d = dict(cc.eval_doc("NIP " + NIP, resp("NIP " + NIP, blocked=True), {"nip": NIP}), level=0, id="x", n_gold=1)
    s = cc.summarize([d], None)
    assert d["category"] == "blocked" and s["docs"]["accepted"] == 0 and s["docs"]["blocked"] == 1
    assert s["gold_evaluated"] == 0 and s["gold_total"] == 1


def test_ocr_rejected_and_error_categories():
    assert cc.category({"code": 422, "blocked": False, "ocr_rejected": True}) == "ocr_rejected"
    assert cc.category({"code": 400, "blocked": False, "error": True}) == "error"
    assert cc.category({"code": None, "error": "ConnectError"}) == "error"


def test_choose_n_picks_most_accepted_and_larger_on_tie():
    docs = [doc(0, 10), doc(1, 25, [("pesel", True, "HOLE")]), doc(2, 35)]
    chosen, table = cc.choose_n(docs)
    assert chosen == 20
    assert [t["admissible"] for t in table] == [True, True, False, False, False]


def test_choose_n_no_rule():
    chosen, _ = cc.choose_n([doc(0, 50, [("nip", True, "HOLE")])])
    assert chosen == "NO_RULE"
    assert cc.ready(cc.summarize([doc(0, 50)], None), True, no_rule=True)["verdict"] == "NOT_READY"


def test_ready_criteria():
    docs = [doc(0, 3, [("nip", True, "MASKED")]) for _ in range(9)] + [doc(1, 5, [("telefon", False, "UNKNOWN_REVIEW")])]
    r = cc.ready(cc.summarize(docs, 20), True)
    assert r["verdict"] == "PENDING_CC_REVIEW" and r["criteria"]["4_rejections"] is True
    assert cc.ready(cc.summarize(docs, 20), False)["verdict"] == "NOT_READY"


# ── P1 ───────────────────────────────────────────────────────────────────────

def test_p1_highest_share_wins():
    assert cc.choose_rotation({0: (0.30, 40), 90: (0.92, 40), 270: (0.50, 40), 180: (0.10, 40)}) == 90


def test_p1_tie_break_order():
    assert cc.choose_rotation({0: (0.80, 30), 90: (0.81, 30), 270: (0.2, 30), 180: (0.79, 30)}) == 0
    assert cc.choose_rotation({0: (0.3, 30), 90: (0.4, 30), 270: (0.90, 30), 180: (0.91, 30)}) == 270


def test_p1_minimum_words():
    assert cc.choose_rotation({0: (0.5, 5), 90: (0.99, 19), 270: (0.2, 3), 180: (0.1, 2)}) == 0
    assert cc.choose_rotation({0: (0.5, 5), 90: (0.6, 25), 270: (0.2, 3), 180: (0.1, 2)}) == 90


# ── C3: izolacja i ścieżki ───────────────────────────────────────────────────

def test_write_outside_temp_copy_is_not_run_isolation(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    before = cc.snapshot([tmp_path])
    assert cc.isolation(before, cc.snapshot([tmp_path])) == ("OK", 0)
    (tmp_path / "pse_registry.json").write_text("{}")
    assert cc.isolation(before, cc.snapshot([tmp_path])) == ("NOT_RUN(ISOLATION)", 1)


def test_run_variant_reports_isolation_and_startup_failure(tmp_path):
    ctx = {"sha": "0" * 40, "protect": [tmp_path], "snap": {}}
    (tmp_path / "changed.txt").write_text("x")
    items, meta = cc.run_variant([{"text": "x"}], ctx)
    assert items is None and meta["isolation"] == "NOT_RUN(ISOLATION)" and meta["startup"] == "NOT_RUN(STARTUP)"
    assert meta["copy_removed"] is True


def test_health_must_be_complete():
    good = {"status": "ok", "anonymizer": True, "spacy_ner": True, "morfeusz": "native", "crypto_ok": True}
    assert cc.health_ok(good) and not cc.health_ok(dict(good, anonymizer=False))
    assert not cc.health_ok(dict(good, morfeusz="unavailable")) and not cc.health_ok(None)


def _gold_dir(path):
    path.mkdir(parents=True)
    (path / "ground_truth.json").write_text("[]")
    return path


def test_refuses_real_photos_and_out_in_repo(tmp_path):
    ok = _gold_dir(tmp_path / "syn")
    real = _gold_dir(tmp_path / "dataset_real")
    ns = lambda **kw: argparse.Namespace(**{"known": ok, "holdout": ok, "clean": None, "out": tmp_path / "r.json", **kw})  # noqa: E731
    assert "syntetyczna" in cc.check_paths(ns(known=real))
    assert "poza repo" in cc.check_paths(ns(out=ROOT / "tasks" / "r.json"))
    assert cc.check_paths(ns()) is None


def test_herbert_arm_marked_not_run(tmp_path):
    a = argparse.Namespace(steps="clean", protect=[], known=None, holdout=None, clean=None)
    ctx = cc.setup(a)
    assert ctx["meta"]["herbert"].startswith("NOT_RUN(HerBERT)")


def test_two_runs_identical():
    pytest.importorskip("morfeusz2")
    out = "Pan OSOBA_001, NIP: NUMER_006-90, konto NUMER_002 1981 2874, tel. 663 794 NUMER_003"
    ents = {"nip": NIP, "iban": IBAN, "telefon": PHONE, "imie_nazwisko": "Jan Kowalski"}
    runs = [json.dumps(cc.summarize([dict(cc.eval_doc(out, resp(out, originals=["Jan Kowalski"]), ents), level=1, id="d",
                                          n_gold=4)], 20), sort_keys=True) for _ in range(2)]
    assert runs[0] == runs[1]


# ── ETAP 2: kotwica + wartość uszkodzona przez OCR (reproduktory, pełny silnik w katalogu tymczasowym) ──────────
@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "audyt")]
    import engine_quality as eq
    ok, why = eq._engine_available()
    if not ok:
        pytest.skip(f"NER/Morfeusz niedostępny: {why}")
    import pipeline
    st = eq.build_state(str(tmp_path_factory.mktemp("lynx_stage2")))
    return lambda t: pipeline.pseudonymize_document(t, st).text


@pytest.mark.parametrize("text,leak", [
    ("zamieszkały/a: ul. Chopina 74, 10-100 Bielsko-Biala\nNIP: 7423337590", "Bielsko-Biala"),   # ł→l (OCR)
    ("Adres: ul. Piotrkowska 5, 90-001 Lodz\nTel.: 601 234 567", "Lodz"),
    ("Adres e-mail:\nslawomirdabrowski@poczta.pì\nDANE PODATKOWE", "slawomirdabrowski"),        # l→ì w TLD
    ("Nr działki ewidencyjnej:\n373251.0081.9795\nObręb 0012", "9795"),                         # ogon numeru
    ("NIP: 742-33-75-90 | PESEL: 50022458822", "-90"),                                          # 9-cyfrowy NIP z OCR
    ("Jan Nowak, ur. 12.O3.1985 w Gdańsku", "12.O3.1985"),                                      # O zamiast 0
    ("Jan Nowak, ur 12.03.1985", "12.03.1985"),                                                 # „ur” bez kropki
])
def test_stage2_ocr_damaged_value_after_anchor_masked(engine, text, leak):
    assert leak not in engine(text)


@pytest.mark.parametrize("text,kept", [
    ("ur. 12.03.1985", None), ("tel. 322 19 27", None), ("Spotkanie w sobotę, kurs ur. bez daty", "kurs ur. bez daty"),
    ("Kielce, dnia 12 maja", "Kielce, dnia"),
])
def test_stage2_no_regression(engine, text, kept):
    out = engine(text)
    assert (kept in out) if kept else (text.split()[-1] not in out)


def test_ascii_fold_keeps_l_stroke():
    from layers.address import _ascii_fold
    assert (_ascii_fold("Bielsko-Biała"), _ascii_fold("Łódź")) == ("Bielsko-Biala", "Lodz")
