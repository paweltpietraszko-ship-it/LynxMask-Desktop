# LYNX-ARENA-SIGNALS-PILOT — rzeczywiste detektory → te same kandydatury do R1/R2. Dane wyłącznie syntetyczne.
# Gold ustalany przy SKŁADANIU tekstu z bloków (nie .find na dokumencie). Gold jest tylko tutaj (sędzia).
# Uruchamiać jawnie: py -3 -m pytest tests/test_arena_signal_probe.py -q -s (plik spoza pytest.ini python_files).
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import arena_signal_probe as probe  # noqa: E402
import arena_v02  # noqa: E402


def compose(sid, *blocks):
    """Blok: str (bez PII) | (wartość, kind) | (wartość, kind, [(start_w_bloku, end_w_bloku, kind), ...])."""
    text, gold = "", []
    for block in blocks:
        if isinstance(block, str):
            text += block
            continue
        value, kind, *nested = block
        parent = len(gold)
        gold.append({"start": len(text), "end": len(text) + len(value), "kind": kind})
        for s, e, k in (nested[0] if nested else []):
            gold.append({"start": len(text) + s, "end": len(text) + e, "kind": k, "parent": parent})
        text += value
    return {"id": sid, "text": text, "gold": gold}


NFD = lambda s: unicodedata.normalize("NFD", s)  # noqa: E731

SAMPLES = [
    compose("S01", "PESEL: ", ("44051401359", "NUMER"), ", e-mail: ", ("jan.nowak@example.pl", "EMAIL"), "."),
    compose("S02", "Odpowiedź proszę kierować na ", ("a.nowak@hurtownia-stal", "EMAIL"), " do piątku."),
    compose("S03", "Umowę zawarto z ", ("Kowalski i Wspólnicy Sp. z o.o.", "FIRMA", [(0, 8, "OSOBA")]),
            " z siedzibą w Poznaniu."),
    compose("S04", "Siedziba: ", ("ul. Jana Kochanowskiego 12, 60-101 Poznań", "ADRES", [(4, 23, "OSOBA")]), "."),
    compose("S05", "Obecni: ", ("Anna Wiśniewska", "OSOBA"), ", ", ("Piotr Zieliński", "OSOBA"), ", ",
            ("Marek Lewandowski", "OSOBA"), "."),
    compose("S06", "Pan ", ("Tomasz Dąbrowski", "OSOBA"), " podpisał umowę, tel. ", ("601 234 567", "NUMER"),
            ". Dnia 5 maja ", ("Tomasz Dąbrowski", "OSOBA"), " potwierdził, tel. ", ("601 234 567", "NUMER"), "."),
    compose("S07", "Kontakt: ", (NFD("żaneta.wójcik@firma.pl"), "EMAIL"), ", opiekun ", (NFD("Józef Wójcik"), "OSOBA"), "."),
    compose("S08", "Rozmawiał z nami ", ("Jan Nowak", "OSOBA"), ", który polecił współpracę z ",
            ("Wielkopolskie Usługi Budowlane Sp. z o.o.", "FIRMA"), "."),
    compose("S09", "Spotkanie zaplanowano na poniedziałek o godzinie 10:00 w sali konferencyjnej."),
    compose("S10", "Biuro: ", ("ul. Polna 12/4, 00-950 Warszawa", "ADRES"), ", tel. ", ("+48 22 123 45 67", "NUMER"), "."),
    compose("S11", "Odbiorca:\n", ("Katarzyna Mazur", "OSOBA"), "\n", ("ul. Długa 5, 80-001 Gdańsk", "ADRES")),
    compose("S12", "Prezes ", ("Adam Kowalczyk", "OSOBA"), " reprezentuje ",
            ("Mazowiecka Hurtownia Stali S.A.", "FIRMA"), " w Warszawie."),
]
BY_ID = {s["id"]: s for s in SAMPLES}


def cand(start, end, kind, source="test"):
    return {"start": start, "end": end, "kind": kind, "source": source, "evidence": ["OBSERVED_DETECTOR"]}


def spacy_ok(text):  # stub SpaCy do testów niezależnych od modelu
    return probe._source("OK", [])


# ── Sędzia: gold ────────────────────────────────────────────────────────────────
def test_gold_built_from_blocks_is_valid():
    assert 10 <= len(SAMPLES) <= 12
    for s in SAMPLES:
        probe.validate_sample(s)
    s04 = BY_ID["S04"]
    assert s04["text"][s04["gold"][1]["start"]:s04["gold"][1]["end"]] == "Jana Kochanowskiego"
    assert BY_ID["S09"]["gold"] == []


def test_classify_gold_statuses():
    gold = [{"start": 0, "end": 10, "kind": "FIRMA"}, {"start": 0, "end": 4, "kind": "OSOBA", "parent": 0},
            {"start": 12, "end": 15, "kind": "NUMER"}, {"start": 20, "end": 25, "kind": "EMAIL"},
            {"start": 30, "end": 35, "kind": "OSOBA"}]
    cands = [cand(0, 10, "FIRMA"), cand(12, 15, "OSOBA"), cand(20, 24, "EMAIL")]
    assert probe.classify_gold(gold, cands, {}) == [
        "EXACT_CANDIDATE", "COVERED_BY_PARENT", "WRONG_KIND", "BAD_SPAN", "NO_CANDIDATE"]
    assert probe.classify_gold(gold, cands, {"OSOBA": "MODEL_UNAVAILABLE"})[4] == "SOURCE_MODEL_UNAVAILABLE"


# ── Rzeczywiste detektory: offsety 1:1 ──────────────────────────────────────────
def test_minimal_reproducer_identity_contact_real_offsets():
    s = BY_ID["S01"]
    got = probe.collect(s["text"], spacy_fn=spacy_ok)
    assert {n: x["status"] for n, x in got["sources"].items()} == {
        "identity": "OK", "contact": "OK", "address": "OK", "SPACY_DIRECT": "OK"}
    spans = {(c["start"], c["end"], c["kind"], c["source"]) for c in got["candidates"]}
    pesel, email = s["gold"]
    assert (pesel["start"], pesel["end"], "NUMER", "identity") in spans
    assert (email["start"], email["end"], "EMAIL", "contact") in spans
    assert all(c["evidence"] == ["OBSERVED_DETECTOR"] for c in got["candidates"])


def test_every_real_layer_candidate_replays_exactly():
    for s in SAMPLES:
        for name, fn in probe._layers().items():
            src = probe.layer_source(name, fn, s["text"])
            assert src["status"] == "OK", (s["id"], name)
            for c in src["candidates"]:
                assert 0 <= c["start"] < c["end"] <= len(s["text"]) and c["kind"] in probe.KINDS


def test_spacy_real_model_or_explicit_error():
    s = BY_ID["S12"]
    src = probe.spacy_source(s["text"])
    assert src["status"] in ("OK", "MODEL_UNAVAILABLE", "MAPPING_ERROR", "ADAPTER_UNSUPPORTED")
    if src["status"] == "MODEL_UNAVAILABLE":
        pytest.skip("pl_core_news_lg niedostępny — jawny MODEL_UNAVAILABLE")
    assert src["status"] == "OK" and src["candidates"]
    assert {c["kind"] for c in src["candidates"]} <= {"OSOBA", "FIRMA"}


# ── Nieprawidłowy adapter ≠ spadek recall ───────────────────────────────────────
def _layer_outside_change(state):
    state.allocator.allocate("NUMER", "44051401359", 7, 18)
    state.text = state.text[:7] + "NUMER_001" + state.text[18:] + " "


def _layer_shifted(state):
    state.allocator.allocate("NUMER", "44051401359", 8, 19)
    state.text = state.text[:7] + "NUMER_001" + state.text[18:]


def _layer_raises(state):
    raise RuntimeError(state.text)


@pytest.mark.parametrize("fn,code", [(_layer_outside_change, "MAPPING_ERROR"), (_layer_shifted, "MAPPING_ERROR"),
                                     (_layer_raises, "DETECTOR_ERROR")])
def test_broken_layer_is_explicit_not_no_candidate(fn, code):
    s = BY_ID["S01"]
    r = probe.probe(s, layers=probe._layers() | {"identity": fn}, spacy_fn=spacy_ok)
    assert r["sources"]["identity"]["status"] == code
    assert r["gold"] == ["SOURCE_" + code, "EXACT_CANDIDATE"]  # NUMER zablokowany, EMAIL z contact
    assert all(v["status"] == "NOT_RUN" for v in r["variants"].values())


class _Ent:
    def __init__(self, text, label, start, end):
        self.text, self.label, self.start, self.end = text, label, start, end


def test_spacy_truncated_multiline_person_is_mapping_error(monkeypatch):
    import spacy_ner
    s = BY_ID["S11"]
    start = s["gold"][0]["start"]
    monkeypatch.setattr(spacy_ner, "detect_entities",  # skrócony text przy pozostawionym end (wrapper FIX-NER-ML-2)
                        lambda t: [_Ent("Katarzyna Mazur", "OSOBA", start, start + len("Katarzyna Mazur\nul."))])
    monkeypatch.setattr(spacy_ner, "_get_nlp", lambda: None)
    r = probe.probe(s, spacy_fn=None)
    assert r["sources"]["SPACY_DIRECT"]["status"] == "MAPPING_ERROR"
    assert r["gold"][0] == "SOURCE_MAPPING_ERROR"


def test_spacy_dedup_and_model_unavailable(monkeypatch):
    import spacy_ner
    s = BY_ID["S06"]
    g = s["gold"][0]
    monkeypatch.setattr(spacy_ner, "_get_nlp", lambda: None)
    monkeypatch.setattr(spacy_ner, "detect_entities", lambda t: [_Ent(t[g["start"]:g["end"]], "OSOBA", g["start"], g["end"])])
    assert probe.spacy_source(s["text"])["status"] == "ADAPTER_UNSUPPORTED"

    def broken():
        raise RuntimeError("brak modelu")
    monkeypatch.setattr(spacy_ner, "_get_nlp", broken)
    r = probe.probe(BY_ID["S12"])
    assert r["sources"]["SPACY_DIRECT"]["status"] == "MODEL_UNAVAILABLE"
    assert r["gold"] == ["SOURCE_MODEL_UNAVAILABLE", "SOURCE_MODEL_UNAVAILABLE"]


# ── Areny: identyczne wejście, STOP jako STOP, H1 ───────────────────────────────
def test_same_candidate_set_for_strict_and_structured(monkeypatch):
    seen = []
    real = arena_v02.run_case
    monkeypatch.setattr(arena_v02, "run_case", lambda case: seen.append(json.dumps(case["base_candidates"])) or real(case))
    s = BY_ID["S03"]
    g = s["gold"]
    cands = [cand(g[0]["start"], g[0]["end"], "FIRMA"), cand(g[1]["start"], g[1]["end"], "OSOBA")]
    results, _, unchanged = probe.run_variants(s["text"], cands)
    assert len(seen) == 2 and seen[0] == seen[1] and unchanged
    statuses = probe.classify_gold(g, cands, {})
    strict = probe.judge_variant(s["text"], g, statuses, results["strict"])
    assert strict["status"] == "STOP" and strict["arbiter_stop"] == 2  # OSOBA⊂FIRMA: R1 STOP, nie sukces


def test_h1_false_wide_firm_stays_falsification_of_r2():
    s = BY_ID["S08"]
    person, firm = s["gold"]
    wide = cand(person["start"], firm["end"], "FIRMA")  # osoba + proza + prawdziwa firma z „Sp. z o.o.”
    cands = [wide, cand(person["start"], person["end"], "OSOBA")]
    results, _, _ = probe.run_variants(s["text"], cands)
    statuses = probe.classify_gold(s["gold"], cands, {})
    structured = probe.judge_variant(s["text"], s["gold"], statuses, results["structured"])
    assert structured["status"] == "RENDERED" and structured["overmask"] == 1 and structured["arbiter_discarded"] == 1
    assert probe.judge_variant(s["text"], s["gold"], statuses, results["strict"])["status"] == "STOP"


def test_rendered_counts_and_invariants():
    text = "Kontakt: ala@firma.pl, dzwoń"
    gold = [{"start": 9, "end": 21, "kind": "EMAIL"}]
    results, _, _ = probe.run_variants(text, [cand(9, 21, "EMAIL"), cand(23, 28, "OSOBA")])
    r = probe.judge_variant(text, gold, ["EXACT_CANDIDATE"], results["strict"])
    assert r["status"] == "RENDERED" and (r["fn"], r["fp"], r["overmask"]) == (0, 1, 0) and r["invariants"] == []
    bad = [{"token": "EMAIL_001", "kind": "EMAIL", "start": 9, "end": 20, "original": "ala@firma.pX"}]
    assert probe.invariant_failures(text, bad, "x") == ["N1", "N2", "N3", "N4"]
    g = [{"start": 0, "end": 9, "kind": "FIRMA"}, {"start": 10, "end": 13, "kind": "OSOBA"},
         {"start": 14, "end": 17, "kind": "OSOBA"}]
    toks = [{"start": 0, "end": 4}, {"start": 5, "end": 9}, {"start": 14, "end": 16}]
    assert probe._render_counts("Abcd Efgh Ijk Lmn", g, toks) == {
        "fn": 1, "fn_partial": 1, "split": 1, "fp": 0, "overmask": 0}


# ── Pełny pilot: agregaty bez tekstu ───────────────────────────────────────────
def test_pilot_report_aggregates_only():
    out = probe.run_samples(SAMPLES)
    dumped = json.dumps(out, ensure_ascii=False)
    for s in SAMPLES:
        for g in s["gold"]:
            assert s["text"][g["start"]:g["end"]] not in dumped
    assert out["samples"] == len(SAMPLES) and sum(out["gold"].values()) == sum(len(s["gold"]) for s in SAMPLES)
    for v in probe.VARIANTS:
        statuses = {k: n for k, n in out["variants"][v].items() if k.startswith("status:")}
        assert sum(statuses.values()) == len(SAMPLES)
        assert out["variants"][v].get("invariant_failures", 0) == 0
    print("\nPILOT_REPORT " + json.dumps(out, ensure_ascii=False, indent=1))


def test_cli_rejects_bad_input_without_echo():
    secret = "Tajne Nazwisko 99999999999"
    r = subprocess.run([sys.executable, str(BACKEND / "arena_signal_probe.py")], input=json.dumps({"text": secret}) + "\n",
                       capture_output=True, text=True, encoding="utf-8", cwd=BACKEND)
    assert r.returncode == 2 and "INVALID_INPUT" in r.stdout and secret not in r.stdout + r.stderr


def test_frozen_arenas_unchanged():
    r = subprocess.run(["git", "diff", "--quiet", "4c75236", "--", "arena_sim.py", "arena_v02.py",
                        "tests/test_arena_sim.py", "tests/test_arena_v02.py"], cwd=BACKEND)
    assert r.returncode == 0
