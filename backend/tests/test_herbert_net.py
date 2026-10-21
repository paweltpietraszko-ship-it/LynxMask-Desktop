# [LYNX-HERBERT-NET] Siatka HerBERT przed Guardem: tylko jawne spany, PER→OSOBA, ORG→FIRMA, odsiew instytucji, mapa dokumentu.
# Atrapa detektora sprawdza logikę; test na prawdziwym modelu skipuje się bez plików w backend/models/herbert. Syntetyki.
# Uruchamianie: py -3 -m pytest tests/test_herbert_net.py -q (plik spoza pytest.ini python_files).
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import herbert_net  # noqa: E402
import pipeline  # noqa: E402


@pytest.fixture
def net(monkeypatch):
    """Włącza siatkę z atrapą modelu: zwraca podane (wartość, typ, pewność) wszędzie, gdzie występują w tekście."""
    def use(found, mode="PER,ORG"):
        monkeypatch.setenv("LYNX_HERBERT", mode)
        monkeypatch.setattr(herbert_net, "detect", lambda text: sorted(
            (i, i + len(v), k, p) for v, k, p in found for i in _all(text, v)))
    return use


def _all(text, value):
    i = text.find(value)
    while i >= 0:
        yield i
        i = text.find(value, i + 1)


def restore(text, rmap):
    for token in sorted(rmap, key=len, reverse=True):
        text = text.replace(token, rmap[token])
    return text


def test_off_returns_input_unchanged_without_loading_model(monkeypatch):
    monkeypatch.delenv("LYNX_HERBERT", raising=False)
    monkeypatch.setattr(herbert_net, "detect", lambda t: pytest.fail("model nie może być użyty przy off"))
    rmap = {"OSOBA_001": "Jan Nowak"}
    assert herbert_net.apply_net("Jan Kowalski i OSOBA_001.", rmap) == ("Jan Kowalski i OSOBA_001.", {"OSOBA_001": "Jan Nowak"})
    code = "import sys; sys.path.insert(0, '.'); import pipeline, herbert_net; print('onnxruntime' in sys.modules, 'tokenizers' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert out.stdout.split()[-2:] == ["False", "False"]


def test_per_and_org_map_to_existing_types_and_switches_separate(net):
    found = [("Tomasz Wiśniewski", "PER", 0.9), ("Kwiatex Sp. z o.o.", "ORG", 0.9)]
    text = "Umowę z Kwiatex Sp. z o.o. podpisał Tomasz Wiśniewski."
    net(found)
    out, rmap = herbert_net.apply_net(text, {})
    assert out == "Umowę z FIRMA_001 podpisał OSOBA_001." and restore(out, rmap) == text
    net(found, mode="ORG")
    assert herbert_net.apply_net(text, {})[0] == "Umowę z FIRMA_001 podpisał Tomasz Wiśniewski."
    net(found, mode="PER")
    assert herbert_net.apply_net(text, {})[0] == "Umowę z Kwiatex Sp. z o.o. podpisał OSOBA_001."


def test_two_firms_same_name_twice_and_no_collision_with_document_or_profile(net):
    net([("Alfa-Med", "ORG", 0.8), ("Bud-Expert", "ORG", 0.8)])
    profile = SimpleNamespace(data={"entities": {"FIRMA_007": {"base": "Inna"}}})
    rmap = {"FIRMA_001": "z o.o", "OSOBA_001": "Anna Nowak"}
    text = "Alfa-Med zleca, Bud-Expert wykonuje. FIRMA_001 i OSOBA_001. Alfa-Med płaci."
    out, rmap = herbert_net.apply_net(text, rmap, profile)
    assert out == "FIRMA_008 zleca, FIRMA_009 wykonuje. FIRMA_001 i OSOBA_001. FIRMA_008 płaci."
    assert rmap["FIRMA_001"] == "z o.o" and rmap["OSOBA_001"] == "Anna Nowak"   # stare tokeny nietknięte
    assert restore(out, rmap) == restore(text, {"FIRMA_001": "z o.o", "OSOBA_001": "Anna Nowak"})   # Przywróć 1:1


def test_span_crossing_existing_token_is_left_as_is(net):
    net([("ALFA Sp. FIRMA_001", "ORG", 0.9)])
    text = "Sprzedawca: ALFA Sp. FIRMA_001"
    assert herbert_net.apply_net(text, {"FIRMA_001": "z o.o."}) == (text, {"FIRMA_001": "z o.o."})   # PARTIAL_FIRMA_UNFIXED


def test_public_institutions_filtered_full_firm_masked(net):
    net([("Urząd Skarbowy", "ORG", 0.9), ("Sąd Rejonowy", "ORG", 0.9), ("ALFA Sp. z o.o.", "ORG", 0.9)])
    out, _ = herbert_net.apply_net("Urząd Skarbowy i Sąd Rejonowy wezwały ALFA Sp. z o.o.", {})
    assert out == "Urząd Skarbowy i Sąd Rejonowy wezwały FIRMA_001"


def test_low_confidence_not_masked(net):
    net([("Kowalczyk", "PER", herbert_net.MIN_SCORE - 0.01)])
    assert herbert_net.apply_net("Rozmawiał Kowalczyk.", {})[0] == "Rozmawiał Kowalczyk."


def test_net_failure_is_s3_and_force_block_comes_first(monkeypatch):
    monkeypatch.setenv("LYNX_HERBERT", "PER")
    monkeypatch.setattr(herbert_net, "detect", lambda t: (_ for _ in ()).throw(FileNotFoundError("brak")))
    r = pipeline._apply_guard("Jan Kowalski", {}, SimpleNamespace(anon_map=None))
    assert (r.text, r.guard_blocked, r.guard_reasons) == ("", True, ["[HERBERT_ERROR] dodatkowa kontrola HerBERT niedostępna"])
    assert r.error and not r.reverse_map
    r = pipeline._apply_guard("Jan Kowalski", {}, SimpleNamespace(anon_map=None), force_block=True)
    assert r.guard_reasons == ["[FORCE_BLOCK] awaria wcześniejszego etapu"]


_HAVE_MODEL = all((herbert_net.model_dir() / f).is_file() for f in herbert_net.MODEL_SHA256)


@pytest.mark.skipif(not _HAVE_MODEL, reason="brak modelu HerBERT lokalnie")
def test_real_model_offline_finds_person_and_handles_long_text(monkeypatch):
    real = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", lambda s, a: real(s, a) if not isinstance(a, tuple)
                        or a[0] in ("127.0.0.1", "::1", "localhost") else pytest.fail("połączenie wychodzące"))
    spans = herbert_net.detect("Pozew złożył Tomasz Wiśniewski przeciwko spółce Kwiatex Sp. z o.o. z Krakowa.")
    assert any(k == "PER" for _, _, k, _ in spans)
    long_text = ("1234567 " * 900) + "Umowę podpisała Katarzyna Zielińska."   # >512 subtokenów w oknie → dzielenie, nie obcięcie
    assert any(k == "PER" and long_text[s:e].startswith("Katarzyna") for s, e, k, _ in herbert_net.detect(long_text))
