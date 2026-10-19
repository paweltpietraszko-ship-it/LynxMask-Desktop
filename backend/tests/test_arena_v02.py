"""Niezalezne proby mechaniki R1/R2 na tym samym wejsciu. Bez gold w runtime."""
import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
V02 = BACKEND / "arena_v02.py"
V01 = BACKEND / "arena_sim.py"


def span(text, value, kind, source="test"):
    start = text.index(value)
    return {"start": start, "end": start + len(value),
            "kind": kind, "source": source, "evidence": ["ASSERTED"]}


def cli(script, cases):
    input_data = "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases)
    out = subprocess.run([sys.executable, str(script)], input=input_data,
                         text=True, capture_output=True, encoding="utf-8", timeout=30, cwd=BACKEND)
    assert out.returncode == 0 and not out.stderr
    rows = [json.loads(line) for line in out.stdout.splitlines()]
    assert len(rows) == len(cases)
    return rows


def check_exact(text, r, expected_kind):
    assert r["status"] == "RENDERED"
    assert len(r["tokens"]) == 1
    t = r["tokens"][0]
    assert t["kind"] == expected_kind
    assert t["original"] == text[t["start"]:t["end"]]
    assert r["masked"].replace(t["token"], t["original"]) == text


def test_structured_recovers_three_cross_type_containments():
    cases = []
    t = "Mieszka przy ul. Jana Kowalskiego 5."
    cases.append({"text": t, "base_candidates": [span(t, "Jana Kowalskiego", "OSOBA")]})
    t = "Pełnomocnik: Kowalski i Wspólnicy Sp. z o.o."
    cases.append({"text": t, "base_candidates": [span(t, "Kowalski", "OSOBA"),
                  span(t, "Kowalski i Wspólnicy Sp. z o.o.", "FIRMA")]})
    t = "Kontakt: jan.kowalski@firma.pl"
    cases.append({"text": t, "base_candidates": [span(t, "jan.kowalski", "OSOBA")]})
    results = cli(V02, cases)
    for case, result, kind in zip(cases, results, ("ADRES", "FIRMA", "EMAIL")):
        assert result["strict"]["status"] == "STOP"
        assert result["strict"]["reason_code"] == "AMBIGUOUS"
        check_exact(case["text"], result["structured"], kind)
        assert result["changed"]


def test_spoofed_evidence_cannot_override_missing_structure():
    cases = []
    t = "Kowalski Projekt XYZ"
    cases.append({"text": t, "base_candidates": [span(t, "Kowalski", "OSOBA"),
                  span(t, t, "FIRMA", "LegalForm")]})
    t = "ul. Jana Kowalskiego"
    cases.append({"text": t, "base_candidates": [span(t, "Jana Kowalskiego", "OSOBA")]})
    out = cli(V02, cases)
    assert all(r["structured"]["status"] == "STOP" and
               r["structured"]["reason_code"] == "AMBIGUOUS" for r in out)


def test_partial_overlap_and_cut_word_remain_safe_stop():
    t1 = "Jan Kowalski"
    t2 = "Ala Nowakowska"
    cases = [
        {"text": t1, "base_candidates": [{"start": 0, "end": 2, "kind": "OSOBA",
                                          "source": "NER", "evidence": ["FORMAT"]}]},
        {"text": t2, "base_candidates": [{"start": 0, "end": 7, "kind": "OSOBA",
                                          "source": "NER", "evidence": []},
                                         {"start": 4, "end": 13, "kind": "OSOBA",
                                          "source": "NER2", "evidence": []}]},
    ]
    out = cli(V02, cases)
    assert [r["structured"]["reason_code"] for r in out] == ["WORD_BOUNDARY", "AMBIGUOUS"]
    assert all(r["structured"]["masked"] is None and not r["structured"]["tokens"] for r in out)


def test_strict_is_byte_equivalent_to_original():
    t = "Adres: ul. Polna l2/8"
    cases = [{"text": t, "base_candidates": []},
             {"text": "Jan Kowalski", "base_candidates": [span("Jan Kowalski", "Jan", "OSOBA")]}]
    original = cli(V01, cases)
    new = cli(V02, [dict(c, policy="strict") for c in cases])
    assert original == new


def test_permutation_and_invalid_policy():
    t = "Pełnomocnik: Kowalski i Wspólnicy Sp. z o.o."
    a, b = span(t, "Kowalski", "OSOBA"), span(t, "Kowalski i Wspólnicy Sp. z o.o.", "FIRMA")
    first, reversed_order = cli(V02, [
        {"text": t, "base_candidates": [a, b], "policy": "structured"},
        {"text": t, "base_candidates": [b, a], "policy": "structured"}])
    assert first == reversed_order
    invalid = cli(V02, [{"text": "SEKRET", "base_candidates": [], "policy": "unknown"}])[0]
    assert invalid["status"] == "STOP" and invalid["masked"] is None
    assert "SEKRET" not in json.dumps(invalid, ensure_ascii=False)
