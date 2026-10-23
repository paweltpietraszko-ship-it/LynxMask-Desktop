# LYNX-GUARD-ALLOWLIST-S5: „Zawsze jawne” — zaszyfrowana lista (fragment, reguła), tylko żółte.
# Uruchamianie (cwd = backend): python -m pytest tests/test_guard_allowlist_s5.py -q -p no:cacheprovider --rootdir .
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())


@pytest.fixture()
def ga(tmp_path, monkeypatch):
    monkeypatch.setenv("ANONYMIZER_PROFILE_DIR", str(tmp_path / "anon"))
    monkeypatch.setenv("PROFILE_DIR", str(tmp_path / "legacy"))
    import guard_allowlist
    return guard_allowlist


def test_zapis_zaszyfrowany(ga):
    ga.add("Kowalczyk Budownictwo", ["R5"])
    raw = ga._enc_path().read_bytes()
    assert b"Kowalczyk" not in raw and "Kowalczyk".encode("utf-16-le") not in raw
    assert ga.load() == [("Kowalczyk Budownictwo", "R5")]
    assert not ga._legacy_paths()[0].exists()


def test_migracja_jawnego_pliku(ga):
    from guard_residue import collect_warnings
    old = ga._legacy_paths()[0]
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps(["Kawa"]), encoding="utf-8")
    assert ga.load() == [("Kawa", "*")] and not old.exists()
    assert collect_warnings("Wczoraj Kawa zlecił wysłanie paczki.", allowlist=ga.load()) == []
    ws = collect_warnings("Pismo: Kawa.", map_values=["Kawa"], allowlist=ga.load())
    assert [w["rules"] for w in ws] == [["MAP_LEAK"]]          # RED nie wyciszany starym wpisem „*”


@pytest.mark.parametrize("rules", [["HIGH PESEL"], ["MAP_LEAK"], ["R1", "MAP_LEAK"], ["*"], []])
def test_red_i_puste_odrzucone(ga, rules):
    with pytest.raises(ga.AllowlistError):
        ga.add("12345678901", rules)
    assert not ga._enc_path().exists()


def test_limit(ga, monkeypatch):
    monkeypatch.setattr(ga, "MAX_ENTRIES", 2)
    ga.add("a1", ["R1"])
    ga.add("a2", ["R1"])
    with pytest.raises(ga.AllowlistError):
        ga.add("a3", ["R1"])


def test_wyciszenie_para_fragment_regula():
    from guard_residue import collect_warnings
    text = "Wczoraj Kawa zlecił wysłanie paczki."
    assert collect_warnings(text, allowlist=[("KAWA", "R1")]) == []
    assert collect_warnings(text, allowlist=[("Kawa", "R5")]) != []


def test_wiele_regul_i_cofnij(ga):
    ga.add("Kawa", ["R1", "R5"])
    assert sorted(r for _, r in ga.load()) == ["R1", "R5"]
    assert ga.remove("kawa", "R1") and ga.remove("Kawa", "R5")
    assert ga.load() == [] and not ga._enc_path().exists()


def test_uszkodzony_plik(ga):
    ga.add("Kawa", ["R1"])
    p = ga._enc_path()
    p.write_bytes(p.read_bytes()[:-3] + b"xyz")
    before = p.read_bytes()
    assert ga.state() == ([], True)
    for call in (lambda: ga.add("Inna", ["R1"]), lambda: ga.remove("Kawa", "R1")):
        with pytest.raises(ga.AllowlistError) as e:
            call()
        assert e.value.status == 409
    assert p.read_bytes() == before
    ga.clear()
    assert ga.state() == ([], False)


def test_pipeline_bez_allowlisty_w_guardzie_mapy(ga, monkeypatch, tmp_path):
    """MAP_LEAK nie jest wyciszany: guard mapy nie dostaje listy, a stary wpis „*” nie gasi czerwonego."""
    import contextlib
    import io
    import pipeline
    import spacy_ner
    from anonymizer import build_anonymizer
    seen = []
    real = pipeline.guard_output_with_map
    monkeypatch.setattr(pipeline, "guard_output_with_map", lambda *a, **kw: seen.append(kw) or real(*a, **kw))
    ga.add("Kowalczyk", ["R1"])
    st = pipeline.AppState()
    st.spacy_ner_mod = spacy_ner
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(str(tmp_path / "p"), str(tmp_path / "hw.json"))
        pipeline.pseudonymize_document("Pan Jan Kowalczyk złożył wniosek.", st)
    assert seen and all(kw.get("allowlist") is None for kw in seen), seen


class _Req:
    def __init__(self, body):
        self._b = body

    async def json(self):
        return self._b


def test_api(ga):
    api = pytest.importorskip("pseudominizer_api")
    run = asyncio.run
    paths = {(r.path, m) for r in api.app.routes for m in getattr(r, "methods", ())}
    assert ("/profile/guard-allowlist/{phrase}", "DELETE") not in paths
    assert run(api.guard_allowlist_add(_Req({"value": "Kawa", "rules": ["R1"]})))["ok"]
    assert run(api.guard_allowlist_add(_Req({"value": "Kawa", "rules": ["MAP_LEAK"]}))).status_code == 400
    assert run(api.guard_allowlist_list()) == {"entries": [{"value": "Kawa", "rule": "R1"}], "damaged": False}
    assert run(api.guard_allowlist_remove(_Req({"value": "Kawa", "rule": "R1"})))["removed"]
    ga.add("Kawa", ["R1"])
    ga._enc_path().write_bytes(b"zepsute")
    assert run(api.guard_allowlist_list())["damaged"] is True
    assert run(api.guard_allowlist_add(_Req({"value": "X", "rules": ["R1"]}))).status_code == 409
    run(api.guard_allowlist_clear())
    assert run(api.guard_allowlist_list()) == {"entries": [], "damaged": False}
