# LYNX-SEC-DISK-PII: dane osobowe nie leżą jawnie na dysku (F1), reset usuwa wszystko, co obiecuje (F2),
# logi bez wartości na każdym poziomie (F3). Uruchamiać jawnie: py -3 -m pytest tests/test_disk_pii.py -q
import contextlib
import io
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
_ISO = Path(tempfile.mkdtemp(prefix="lynx_disk_pii_import_"))
os.environ.setdefault("ARCHIVE_DIR", str(_ISO / "archive"))      # import API inicjalizuje archiwum (jak test_archive_adversarial)

_LOCAL = "http://127.0.0.1:8765"
_FULL = "a" * 64
NAME, NAME_GEN = "Jan Kowalski", "Jana Kowalskiego"                  # znane Morfeuszowi (odmiana w profilu)
MARK = "ZNACZNIKSYNT"                                                   # syntetyczny znacznik w nazwach plików i wyjątkach


def _files_with(root: Path, needle: str):
    raw = needle.encode("utf-8")
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and raw in p.read_bytes()]


@pytest.fixture
def iso(tmp_path, monkeypatch):
    """Izolacja: profil, osobny PROFILE_DIR allowlisty, archiwum, rejestr, hardware profile i log launchera."""
    import db_store
    import pseudominizer_api as api
    from anonymizer import build_anonymizer
    from fastapi.testclient import TestClient
    import spacy_ner
    prof, allow, arch = tmp_path / "profil", tmp_path / "allow", tmp_path / "archive"
    (arch / "mapy").mkdir(parents=True)
    monkeypatch.setenv("PROFILE_DIR", str(allow))
    for k, v in {"ANON_PROFILE_DIR": str(prof), "HARDWARE_PROFILE": str(tmp_path / "hw.json"), "ARCHIVE_DIR": arch,
                 "MAPS_DIR": arch / "mapy", "DB_PATH": arch / "rejestr.db", "_LAUNCHER_LOG": tmp_path / "pseudominizer.log",
                 "_API_TOKEN": _FULL}.items():
        monkeypatch.setattr(api, k, v, raising=False)   # raising=False: ten sam test daje czytelny RED na main
    old_db = db_store._DB_PATH
    db_store.init(arch / "rejestr.db")
    st = api.AppState()
    st.spacy_ner_mod = spacy_ner
    with contextlib.redirect_stdout(io.StringIO()):
        st.anonymizer, _, st.anon_map, st.morf_env = build_anonymizer(prof, tmp_path / "hw.json")
    monkeypatch.setattr(api, "_app_state", st)
    yield TestClient(api.app, base_url=_LOCAL, raise_server_exceptions=False), api, tmp_path
    db_store.init(old_db)


def _h():
    return {"X-Api-Token": _FULL}


def _profile_masks(api, text):
    out, _ = api._app_state.anonymizer._layer1_trie(text, {})
    return out


# ── F1 ─────────────────────────────────────────────────────────────────────────
def test_f1_automat_tylko_w_pamieci(iso):
    cl, api, root = iso
    r = cl.post("/profile/add-entity", json={"text": NAME, "token_type": "OSOBA"}, headers=_h())
    assert r.status_code == 200, r.text[:200]
    assert not (root / "profil" / "trie.pkl").exists()
    assert _files_with(root / "profil", "Kowalsk") == []                 # mapa.enc zaszyfrowana, brak jawnej kopii
    assert "Kowalsk" not in _profile_masks(api, f"Wezwano {NAME_GEN} na rozprawę.")
    from anonymizer import AnonymizerMap, Anonymizer                      # „po restarcie”: nowa instancja z dysku
    fresh = Anonymizer(AnonymizerMap(root / "profil", api._app_state.morf_env))
    assert "Kowalsk" not in fresh._layer1_trie(f"Wezwano {NAME_GEN} na rozprawę.", {})[0]


def test_f1_migracja_usuwa_stary_trie_pkl(iso):
    cl, api, root = iso
    cl.post("/profile/add-entity", json={"text": NAME, "token_type": "OSOBA"}, headers=_h())
    (root / "profil" / "trie.pkl").write_bytes(b"stary jawny cache: " + NAME.encode())
    from anonymizer import AnonymizerMap, Anonymizer
    fresh = Anonymizer(AnonymizerMap(root / "profil", api._app_state.morf_env))
    assert not (root / "profil" / "trie.pkl").exists()
    assert "Kowalsk" not in fresh._layer1_trie(f"Wezwano {NAME_GEN}.", {})[0]


# ── F2 ─────────────────────────────────────────────────────────────────────────
def test_f2_reset_usuwa_wszystko_i_dziala_od_razu(iso):
    cl, api, root = iso
    import db_store
    assert cl.post("/profile/add-entity", json={"text": NAME, "token_type": "OSOBA"}, headers=_h()).status_code == 200
    assert cl.post("/profile/guard-allowlist", json={"phrase": f"{MARK} wyjątek"}, headers=_h()).status_code == 200
    (root / "profil" / "trie.pkl").write_bytes(MARK.encode())            # stary cache sprzed migracji
    api._LAUNCHER_LOG.write_text(f"log {MARK}", encoding="utf-8")         # log starego launchera (na main: plik w tmp, nikt go nie kasuje)
    db_store.save("PSE-2026-9999", 3, description=b"opis")
    db_store.record_audit("PSE-2026-9999", "save")
    with sqlite3.connect(db_store._DB_PATH) as c:                         # tabela z migracji pre-v1.22 z nazwami plików
        c.execute("CREATE TABLE documents_backup_filename (pse TEXT, filename TEXT)")
        c.execute("INSERT INTO documents_backup_filename VALUES (?, ?)", ("PSE-1", f"{MARK}.pdf"))
    assert "Kowalsk" not in _profile_masks(api, f"Wezwano {NAME_GEN}.")

    r = cl.post("/profile/reset", json={"confirm": True}, headers=_h())
    assert r.status_code == 200, r.text[:200]
    assert _files_with(root, MARK) == [] and _files_with(root, "Kowalsk") == []
    assert not (root / "profil" / "trie.pkl").exists() and not api._LAUNCHER_LOG.exists()
    assert not (root / "allow" / "guard_allowlist.json").exists()        # brak pliku = sukces (nie FileNotFoundError)
    with sqlite3.connect(db_store._DB_PATH) as c:
        tables = {t for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "documents_backup_filename" not in tables
        assert c.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert [a for (a,) in c.execute("SELECT action FROM audit_log")] == ["reset"]
    # warstwa profilu po resecie: stara encja nie jest maskowana Z PROFILU, nowa — jest
    assert "Kowalsk" in _profile_masks(api, f"Wezwano {NAME_GEN}.")
    assert cl.post("/profile/add-entity", json={"text": "Anna Nowak", "token_type": "OSOBA"}, headers=_h()).status_code == 200
    assert "Nowak" not in _profile_masks(api, "Świadek Anna Nowak zeznała.")


def test_f2_zablokowany_log_to_reset_czesciowy_nie_sukces(iso):
    """Codex r2 A1: stary log otwarty przez inny proces (Windows) → reset nie zgłasza pełnego sukcesu; po zamknięciu — tak."""
    cl, api, root = iso
    api._LAUNCHER_LOG.write_text(f"log {MARK}", encoding="utf-8")
    with api._LAUNCHER_LOG.open("a", encoding="utf-8"):
        r = cl.post("/profile/reset", json={"confirm": True}, headers=_h())
        if api._LAUNCHER_LOG.exists():                                        # Windows: plik otwarty = nieusuwalny
            assert r.status_code == 500 and not r.json().get("ok") and "plik logu silnika" in r.json()["error"], r.text
    r = cl.post("/profile/reset", json={"confirm": True}, headers=_h())
    assert r.status_code == 200 and r.json()["ok"] is True and not api._LAUNCHER_LOG.exists(), r.text


# ── F3 ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def debug_logs():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setLevel(logging.DEBUG)
    root = logging.getLogger()
    old = root.level
    root.addHandler(h)
    root.setLevel(logging.DEBUG)
    names = [n for n in logging.root.manager.loggerDict]
    saved = {n: logging.getLogger(n).level for n in names}
    for n in names:
        logging.getLogger(n).setLevel(logging.DEBUG)
    yield buf
    root.removeHandler(h)
    root.setLevel(old)
    for n, lv in saved.items():
        logging.getLogger(n).setLevel(lv)


def _png_with_text():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 120), "white")
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((10, 30), f"Pozew: {NAME}, PESEL 44051401359", fill="black", font=font)
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def test_f3_logi_bez_wartosci_na_poziomie_debug(iso, debug_logs):
    cl, api, root = iso
    doc = f"Pozew złożył {NAME} wobec Testowa Budowa Sp. z o.o., PESEL 44051401359, dwa tysiące złotych."
    calls = [
        cl.post("/profile/add-entity", json={"text": NAME, "token_type": "OSOBA"}, headers=_h()),
        cl.post("/preview", files={"file": (f"Pozew_{MARK}.txt", doc.encode(), "text/plain")}, headers=_h()),
        cl.post("/preview", files={"file": (f"Skan_{MARK}.png", _png_with_text(), "image/png")}, headers=_h()),
        cl.post("/export-pdf", json={"text": "Pozew złożył OSOBA_001.", "filename": f"Pozew_{MARK}.pdf"}, headers=_h()),
        cl.post("/profile/guard-allowlist", json={"phrase": f"{MARK} wyjątek"}, headers=_h()),
        cl.post("/profile/reset", json={"confirm": True}, headers=_h()),
    ]
    assert [c.status_code for c in calls[:2]] == [200, 200], [c.text[:120] for c in calls]
    text = debug_logs.getvalue()
    assert text.strip(), "brak rekordów logu — test nic nie sprawdził"
    for needle in (MARK, "Kowalsk", "44051401359", "Testowa Budowa"):
        assert needle not in text, (needle, [ln for ln in text.splitlines() if needle in ln][:3])


def test_f3_launcher_bez_zapisu_logu_na_dysk():
    """Jedyny starter (LYNX-ONE-LAUNCHER): silnik bez okna i bez przekierowania wyjścia do pliku (S5)."""
    vbs = (Path(__file__).resolve().parents[2] / "LynxMask.vbs").read_text(encoding="utf-8")
    run = [ln for ln in vbs.splitlines() if "pseudominizer_api.py" in ln and "sh.Run" in ln]
    assert run and all(">" not in ln for ln in run), run
    assert ".log" not in vbs.lower()
    assert not (Path(__file__).resolve().parents[1] / "uruchom.vbs").exists()
