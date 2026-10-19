# LYNX-ARCH-ARENA v0.1 — testy obrońcy przez CLI (osobny proces), 16 przypadków Architekta, niezmienniki N1–N4,
# metamorfizmy, odporność wejścia. Gold jest TYLKO tutaj (sędzia), nigdy w danych dla arena_sim.py.
# Uruchamiać jawnie: py -3 -m pytest tests/test_arena_sim.py -q (plik spoza pytest.ini python_files).
import json
import os
import random
import subprocess
import sys

import pytest

SIM = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arena_sim.py"))

# (id, text, base_candidates, gold[(start, end, kind)]) — przepisane 1:1 z CASES_V01.md (zamrożone)
CASES = [
    ('A01', 'Kontakt: ala@firma.pl', [{'start': 9, 'end': 21, 'kind': 'EMAIL', 'source': 'EmailEngine', 'evidence': ['FORMAT']}], [(9, 21, 'EMAIL')]),
    ('A02', 'Kontakt: ala@firma,pl', [], [(9, 21, 'EMAIL')]),
    ('A03', 'Kontakt: ala@firma .pl', [{'start': 9, 'end': 18, 'kind': 'EMAIL', 'source': 'EmailEngine', 'evidence': ['FORMAT']}], [(9, 22, 'EMAIL')]),
    ('A04', 'Adres: ul. Polna l2/8', [], [(7, 21, 'ADRES')]),
    ('A05', 'Źródło: Dz. U. Nr 223', [], []),
    ('A06', 'Profil: @administrator', [], []),
    ('A07', 'Adres: ul. Polna 12, 65-001 Poznań', [{'start': 7, 'end': 19, 'kind': 'ADRES', 'source': 'AddressEngine', 'evidence': ['FORMAT']}], [(7, 34, 'ADRES')]),
    ('A08', 'Kontakt: ala@firma.pl; jutro spotkanie', [], [(9, 21, 'EMAIL')]),
    ('A09', 'Kontakt: ala@firma.pl\nAdres: ul. Polna l2', [], [(9, 21, 'EMAIL'), (29, 41, 'ADRES')]),
    ('A10', 'Kontakt: ala@firma.pl', [{'start': 9, 'end': 12, 'kind': 'OSOBA', 'source': 'NER', 'evidence': ['NER_SPACY']}], [(9, 21, 'EMAIL')]),
    ('A11', 'PESEL: 9O05141234O', [], [(7, 18, 'NUMER')]),
    ('A12', 'Oznaczenie: OSOBA_001', [], []),
    ('A13', '😀 Kontakt: żaneta@firma.pl', [], [(11, 26, 'EMAIL')]),
    ('A14', 'Maile: ala@firma.pl; ala@firma.pl', [], [(7, 19, 'EMAIL'), (21, 33, 'EMAIL')]),
    ('A15', 'Skrót ul. w instrukcji nie oznacza tu adresu.', [], []),
    ('A16', 'Adres: ul. Polna l2/8; PESEL 9O05141234O', [], [(7, 21, 'ADRES'), (29, 40, 'NUMER')]),
]

# Prognoza mechaniki Architekta (tabela r2): oczekiwane tokeny (start, end, kind) albo kod STOP
MECH = {
    "A01": [(9, 21, "EMAIL")], "A02": [(9, 21, "EMAIL")], "A03": [(9, 22, "EMAIL")], "A04": [(7, 21, "ADRES")],
    "A05": [], "A06": [(8, 22, "EMAIL")], "A07": [(7, 19, "ADRES")], "A08": [(9, 21, "EMAIL")],
    "A09": [(9, 21, "EMAIL"), (29, 41, "ADRES")], "A10": "AMBIGUOUS", "A11": [], "A12": "TOKEN_INJECTION",
    "A13": [(11, 26, "EMAIL")], "A14": [(7, 19, "EMAIL"), (21, 33, "EMAIL")], "A15": [(6, 26, "ADRES")],
    "A16": [(7, 21, "ADRES")],
}
# Klasyfikacja ochrony z tabeli r2 — test liczy ją z gold (sędzia), a nie z prognozy
PROTECTION = {"A01": "PASS", "A02": "PASS", "A03": "PASS", "A04": "PASS", "A05": "PASS", "A06": "FAIL",
              "A07": "FAIL", "A08": "PASS", "A09": "PASS", "A10": "SAFE_REFUSAL", "A11": "FAIL",
              "A12": "SAFE_REFUSAL", "A13": "PASS", "A14": "PASS", "A15": "FAIL", "A16": "FAIL"}
EXPECTED_SAFE_STOP = {"A10", "A12"}


def run(cases: list) -> list[dict]:
    """Jedno uruchomienie procesu dla wielu dokumentów (metamorfizm: kolejne dokumenty w tym samym procesie)."""
    inp = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases)
    p = subprocess.run([sys.executable, SIM], input=inp.encode("utf-8"), capture_output=True, timeout=60,
                       cwd=os.path.dirname(SIM))
    assert p.returncode == 0 and not p.stderr, p.stderr.decode("utf-8", "replace")[:300]
    lines = p.stdout.decode("utf-8").splitlines()
    assert len(lines) == len(cases)
    return [json.loads(x) for x in lines]


def _inp(text, base):
    return {"text": text, "base_candidates": base, "mode": "full"}


@pytest.fixture(scope="module")
def results():
    return dict(zip([c[0] for c in CASES], run([_inp(t, b) for _, t, b, _ in CASES])))


def invariants_ok(text, r):
    toks = sorted(r["tokens"], key=lambda t: t["start"])
    pos, rebuilt, restored = 0, "", ""
    for t in toks:
        assert t["original"] == text[t["start"]:t["end"]]                                     # N4
        for i in (t["start"], t["end"]):                                                       # N2: nie w środku wyrazu
            assert not (0 < i < len(text) and text[i - 1].isalnum() and text[i].isalnum()), (t, text)
        rebuilt += text[pos:t["start"]] + t["token"]
        restored += text[pos:t["start"]] + t["original"]
        pos = t["end"]
    assert rebuilt + text[pos:] == r["masked"]                                                 # N1: poza spanami 1:1
    assert restored + text[pos:] == text                                                       # N3: roundtrip mapą
    return True


def judge(cid, gold, r):
    """Sędzia ochrony (brief r2/C2): tylko gold i tekst; wynik obrońcy nie wylicza expected."""
    if r["status"] == "STOP":
        return "SAFE_REFUSAL" if cid in EXPECTED_SAFE_STOP else "UNEXPECTED_STOP"
    got = {(t["start"], t["end"], t["kind"]) for t in r["tokens"]}
    return "PASS" if set(gold) == got else "FAIL"                                            # FN/FN_PARTIAL/FP → FAIL


@pytest.mark.parametrize("cid,text,base,gold", CASES, ids=[c[0] for c in CASES])
def test_mechanika_zgodna_z_regulami(results, cid, text, base, gold):
    r, exp = results[cid], MECH[cid]
    if isinstance(exp, str):
        assert r["status"] == "STOP" and r["reason_code"] == exp and r["masked"] is None and r["tokens"] == []
        assert r["guard_flags"] == []
    else:
        assert r["status"] == "RENDERED" and r["reason_code"] is None, r["reason_code"]
        assert [(t["start"], t["end"], t["kind"]) for t in r["tokens"]] == exp
        assert invariants_ok(text, r)


@pytest.mark.parametrize("cid,text,base,gold", CASES, ids=[c[0] for c in CASES])
def test_ochrona_liczona_z_gold(results, cid, text, base, gold):
    assert judge(cid, gold, results[cid]) == PROTECTION[cid]


def test_guard_dron(results):
    flags = {cid: [(f["kind"], f["start"], f["end"]) for f in r["guard_flags"]] for cid, r in results.items()}
    assert flags["A11"] == [("ID_LABEL_REMAINS", 0, 18)]
    f16 = flags["A16"]
    assert [f[0] for f in f16] == ["ID_LABEL_REMAINS"] and results["A16"]["masked"][f16[0][1]:].startswith("PESEL")
    assert flags["A07"] == [] and flags["A01"] == []                                           # Guard nie ratuje FN A07
    assert flags["A06"] == [] and flags["A15"] == []                                           # @/ul. zamaskowane


def test_wspolny_token_dla_identycznej_wartosci(results):
    t = results["A14"]["tokens"]
    assert t[0]["token"] == t[1]["token"] == "EMAIL_001"


def test_trace_bez_wartosci(results):
    for cid, *_ in CASES:
        trace = results[cid]["trace"]
        assert all(set(e) == {"phase", "kind", "start", "end", "decision"} for e in trace)
        dump = json.dumps(trace, ensure_ascii=False)
        assert "firma" not in dump and "Polna" not in dump, (cid, dump[:200])


def test_metamorfizmy_kolejnosc_zrodla_determinizm():
    rng = random.Random(7)
    text = "Kontakt: ala@firma .pl, ul. Polna l2/8"
    base = [{"start": 9, "end": 18, "kind": "EMAIL", "source": "A", "evidence": ["FORMAT"]},
            {"start": 9, "end": 18, "kind": "EMAIL", "source": "B", "evidence": ["FORMAT", "NER_SPACY"]},
            {"start": 24, "end": 38, "kind": "ADRES", "source": "AddressEngine", "evidence": ["FORMAT"]}]
    variants = []
    for _ in range(5):
        b = [dict(c, source=f"S{rng.randint(0, 99)}") for c in base]
        rng.shuffle(b)
        variants.append(_inp(text, b))
    out = run(variants + variants[:1])
    first = {k: out[0][k] for k in ("status", "masked", "tokens", "guard_flags")}
    assert first["status"] == "RENDERED" and all({k: o[k] for k in first} == first for o in out)


def test_niepoprawne_wejscie_bez_ujawniania():
    marker = "SEKRETNYZNACZNIK"
    bad = [_inp(marker, [{"start": 0, "end": 99, "kind": "OSOBA"}]), _inp(marker, [{"start": 0, "end": 3, "kind": "X"}]),
           {"text": marker, "mode": "other"}, {"text": 5}, _inp(marker, "nie-lista"),
           _inp(marker, [{"start": True, "end": 3, "kind": "OSOBA"}])]
    inp = "".join(json.dumps(c) + "\n" for c in bad) + "{to nie json " + marker + "\n"
    p = subprocess.run([sys.executable, SIM], input=inp.encode("utf-8"), capture_output=True, timeout=60)
    out = p.stdout.decode("utf-8")
    lines = out.splitlines()
    assert len(lines) == len(bad) + 1 and marker not in out and not p.stderr
    assert all(json.loads(x)["status"] == "STOP" and json.loads(x)["reason_code"] == "INVALID_INPUT" for x in lines)


def test_kotwica_bez_prawej_strony_to_anchor_uncertain():
    r = run([_inp("Napisz na adres ala@ jutro", [])])[0]
    assert r["status"] == "STOP" and r["reason_code"] == "ANCHOR_UNCERTAIN"


def test_granica_w_srodku_wyrazu_to_odmowa_nie_sklejenie():
    """Codex r4 F1 (N2): ucięty kandydat BASE nie może dać tokenu sklejonego z literą; nie poszerzamy spanu bez dowodu."""
    t = "Jan Kowalski"
    cut_right = run([_inp(t, [{"start": 0, "end": 2, "kind": "OSOBA"}])])[0]
    cut_left = run([_inp(t, [{"start": 1, "end": 3, "kind": "OSOBA"}])])[0]
    whole = run([_inp(t, [{"start": 0, "end": 12, "kind": "OSOBA"}])])[0]
    for r in (cut_right, cut_left):
        assert r["status"] == "STOP" and r["reason_code"] == "WORD_BOUNDARY" and r["masked"] is None
    assert whole["status"] == "RENDERED" and whole["masked"] == "OSOBA_001" and invariants_ok(t, whole)
