# LYNX-STARTUP-COMPONENTS: start tylko wtedy, gdy każdy element ochrony przechodzi próbę funkcjonalną.
# Uruchamiać jawnie: py -3 -m pytest tests/test_startup_check.py -q (plik spoza pytest.ini python_files).
import asyncio
import hashlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import startup_check  # noqa: E402

SECRET = "SYNTETYCZNY_44051401359"


@pytest.fixture(scope="module")
def state():
    import spacy_ner
    from anonymizer import build_anonymizer
    root = Path(tempfile.mkdtemp(prefix="lynx_startup_test_"))
    anonymizer, _, anon_map, morf_env = build_anonymizer(root / "profil", root / "hw.json")
    return SimpleNamespace(spacy_ner_mod=spacy_ner, anonymizer=anonymizer, anon_map=anon_map, morf_env=morf_env, root=root)


def _run(st, guard=True, crypto=True):
    return startup_check.run(st, guard, crypto)


def test_wszystko_sprawne(state):
    assert _run(state) == []


def _boom(*a, **k):
    raise ValueError(SECRET)


class _Broken:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.mark.parametrize("name,setup", [
    ("maskowanie numerów i adresów", lambda st: patch("smoke_test.run_smoke_test", return_value=(False, ["x"]))),
    ("Output Guard", lambda st: patch("output_guard.guard_output", _boom)),
    ("Output Guard", lambda st: patch("output_guard.guard_output_with_map",
                                      return_value=_Broken(blocked=True, error=True, reasons=["GUARD_ERROR"]))),
    ("rozpoznawanie osób (SpaCy)", lambda st: patch.object(st.spacy_ner_mod, "detect_entities", return_value=[])),
    ("rozpoznawanie osób (SpaCy)", lambda st: patch.object(st.spacy_ner_mod, "detect_entities", _boom)),
    ("odmiana nazw (Morfeusz)", lambda st: patch.object(st.morf_env, "get_forms", lambda w: [w])),
    ("odmiana nazw (Morfeusz)", lambda st: patch.object(st.morf_env, "mode", "blocked")),
    ("profil biura", lambda st: patch("anonymizer.Anonymizer._layer1_trie", lambda self, t, m: (t, m))),
])
def test_awaria_elementu_blokuje(state, caplog, name, setup):
    with setup(state), caplog.at_level(logging.DEBUG):
        failed = _run(state)
    assert name in failed, failed
    assert SECRET not in caplog.text


@pytest.mark.parametrize("field", ["spacy_ner_mod", "anonymizer", "morf_env"])
def test_brak_modulu_blokuje(state, field):
    st = SimpleNamespace(**{**vars(state), field: None})
    assert _run(st), field


def test_guard_niezaladowany_i_crypto_fail(state):
    assert _run(state, guard=False, crypto=False) == ["Output Guard", "szyfrowanie"]


def _snapshot(*paths):
    out = {}
    for base in paths:
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for p in files:
            st = p.stat()
            out[str(p)] = (st.st_size, st.st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
    return out


@pytest.mark.parametrize("filled", [False, True])
def test_profil_uzytkownika_bez_zapisow(filled):
    """Próby nie zapisują nic w profilu użytkownika ani w hardware_profile.json; katalog próby usunięty."""
    import spacy_ner
    from anonymizer import build_anonymizer
    root = Path(tempfile.mkdtemp(prefix="lynx_startup_user_"))
    anonymizer, _, anon_map, morf_env = build_anonymizer(root / "profil", root / "hw.json")
    if filled:
        anon_map.add_entity("Anna Nowak", "OSOBA")
    st = SimpleNamespace(spacy_ner_mod=spacy_ner, anonymizer=anonymizer, anon_map=anon_map, morf_env=morf_env)
    before = _snapshot(root / "profil", root / "hw.json")
    made = []
    real_mkdtemp = tempfile.mkdtemp

    def spy(*a, **k):
        made.append(real_mkdtemp(*a, **k))
        return made[-1]
    with patch("startup_check.tempfile.mkdtemp", spy):
        assert _run(st) == []
    assert _snapshot(root / "profil", root / "hw.json") == before
    assert made and not any(Path(m).exists() for m in made)


# ── _lifespan: token = gotowość, awaria → startup_error.json bez tokenu ────────
@pytest.fixture
def api_paths(tmp_path):
    import pseudominizer_api as api
    token, error = tmp_path / "api_token.txt", tmp_path / "startup_error.json"
    token.write_text("stary-token", encoding="utf-8")
    with patch.object(api, "_API_TOKEN_PATH", token), patch.object(api, "_STARTUP_ERROR_PATH", error), \
            patch.object(api, "ANON_PROFILE_DIR", str(tmp_path / "profil")), \
            patch.object(api, "HARDWARE_PROFILE", str(tmp_path / "hw.json")):
        yield api, token, error


def test_lifespan_awaria_bez_tokenu(api_paths, caplog):
    api, token, error = api_paths
    with patch("startup_check.run", return_value=["Output Guard"]), caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError):
            asyncio.run(api._lifespan(api.app).__aenter__())
    assert not token.exists()
    info = json.loads(error.read_text(encoding="utf-8"))
    assert info["code"] == "STARTUP-COMPONENTS" and "Output Guard" in info["message"]


def test_lifespan_token_dopiero_po_probach_i_usuwany_przy_zamknieciu(api_paths):
    api, token, error = api_paths
    seen = {}

    def fake_run(*a):
        seen["token_during_checks"] = token.exists()
        return []

    async def go():
        cm = api._lifespan(api.app)
        with patch("startup_check.run", fake_run):
            await cm.__aenter__()
        seen["token_ready"] = token.read_text(encoding="utf-8")
        await cm.__aexit__(None, None, None)
    asyncio.run(go())
    assert seen["token_during_checks"] is False
    assert seen["token_ready"] == api._API_TOKEN and seen["token_ready"] != "stary-token"
    assert not token.exists() and not error.exists()
