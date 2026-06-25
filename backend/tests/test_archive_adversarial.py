# tests/test_archive_adversarial.py  v1.0
"""
Testy adversarialne endpointów archiwum (pseudominizer_api.py v1.13).

Pokrycie:
  D1  POST /archive — poprawny zapis
  D2  POST /archive — nieprawidłowy PSE (path traversal, za krótki, za długi)
  D3  POST /archive — token_count jako string (FIX-TC-1)
  D4  POST /archive — enc_blob nie jest base64
  D5  GET  /archive — lista dokumentów
  D6  GET  /archive/{pse}/blob — pobranie blobu
  D7  GET  /archive/nieprawidlowy — walidacja PSE przy pobraniu
  D8  DELETE /archive/{pse} — usuwanie
  D9  DELETE /archive/nieprawidlowy — walidacja PSE przy usuwaniu
  D10 POST /archive/reencrypt — atomowa zmiana hasła
  D11 POST /archive/reencrypt — nieprawidłowy PSE w blobach
  D12 GET  /archive/audit — log zdarzeń
"""

import unittest
import asyncio
import base64
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Testy wymagają httpx i działającego serwera — używamy TestClient FastAPI
try:
    from fastapi.testclient import TestClient
    from pseudominizer_api import app, MAPS_DIR, DB_PATH, _init_db
    _API_AVAILABLE = True
except ImportError as e:
    _API_AVAILABLE = False
    _IMPORT_ERROR = str(e)


def make_valid_blob() -> str:
    """Dummy base64 — symuluje zaszyfrowany blob (backend nie deszyfruje)."""
    return base64.b64encode(b"FAKE_ENCRYPTED_DATA_" + b"\x00" * 32).decode()


@unittest.skipUnless(_API_AVAILABLE, f"pseudominizer_api niedostępna: {_API_AVAILABLE or ''}")
class TestArchiveSave(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_db()
        cls.client = TestClient(app)

    def test_d1_valid_save(self):
        """Poprawny zapis — 200 + ok:True."""
        r = self.client.post("/archive", json={
            "pse": "PSE-2026-9001",
            "filename": "test_dokument.txt",
            "token_count": 5,
            "enc_blob": make_valid_blob(),
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        self.assertEqual(r.json().get("pse"), "PSE-2026-9001")

    def test_d2a_path_traversal_pse(self):
        """PSE z path traversal — musi być odrzucone."""
        r = self.client.post("/archive", json={
            "pse": "PSE-2026-../secret",
            "filename": "x.txt",
            "token_count": 0,
            "enc_blob": make_valid_blob(),
        })
        self.assertEqual(r.status_code, 400)

    def test_d2b_short_pse(self):
        """Za krótkie PSE."""
        r = self.client.post("/archive", json={
            "pse": "PSE-26-01",
            "filename": "x.txt",
            "token_count": 0,
            "enc_blob": make_valid_blob(),
        })
        self.assertEqual(r.status_code, 400)

    def test_d2c_empty_pse(self):
        """Puste PSE."""
        r = self.client.post("/archive", json={
            "pse": "",
            "filename": "x.txt",
            "token_count": 0,
            "enc_blob": make_valid_blob(),
        })
        self.assertEqual(r.status_code, 400)

    def test_d3_token_count_as_string(self):
        """
        FIX-TC-1: token_count jako string powinien zwrócić 400, nie 500.
        Przed fixem: ValueError nieobsłużony → 500.
        """
        r = self.client.post("/archive", json={
            "pse": "PSE-2026-9002",
            "filename": "test.txt",
            "token_count": "abc",
            "enc_blob": make_valid_blob(),
        })
        self.assertEqual(
            r.status_code, 400,
            f"token_count='abc' powinien dać 400, dostano {r.status_code}. "
            f"FIX-TC-1 nie działa."
        )

    def test_d4_invalid_base64(self):
        """enc_blob nie jest base64 — 400."""
        r = self.client.post("/archive", json={
            "pse": "PSE-2026-9003",
            "filename": "test.txt",
            "token_count": 0,
            "enc_blob": "to_nie_jest_base64!!!",
        })
        self.assertEqual(r.status_code, 400)

    def test_d4b_oversized_blob(self):
        """
        [FIX-DOS-1] Blob powyżej MAX_BLOB_BYTES (512 KB) — 400.
        Poprzednio brak limitu → atakujący mógł zapełnić dysk.
        """
        big_blob = base64.b64encode(b"X" * (513 * 1024)).decode()
        r = self.client.post("/archive", json={
            "pse": "PSE-2026-9004",
            "filename": "duzy.txt",
            "token_count": 0,
            "enc_blob": big_blob,
        })
        self.assertEqual(r.status_code, 400,
            f"Blob 513 KB powinien być odrzucony (400), dostano {r.status_code}. "
            f"FIX-DOS-1 nie działa."
        )


@unittest.skipUnless(_API_AVAILABLE, "pseudominizer_api niedostępna")
class TestArchiveRead(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_db()
        cls.client = TestClient(app)
        # Zapisz jeden dokument do testów odczytu
        cls.client.post("/archive", json={
            "pse": "PSE-2026-9010",
            "filename": "dokument_odczyt.txt",
            "token_count": 3,
            "enc_blob": make_valid_blob(),
        })

    def test_d5_list_documents(self):
        """GET /archive zwraca listę dokumentów."""
        r = self.client.get("/archive")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("documents", data)
        pse_list = [d["pse"] for d in data["documents"]]
        self.assertIn("PSE-2026-9010", pse_list)

    def test_d6_get_blob(self):
        """GET /archive/{pse}/blob zwraca blob."""
        r = self.client.get("/archive/PSE-2026-9010/blob")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("enc_blob", data)
        # Blob musi być poprawnym base64
        try:
            base64.b64decode(data["enc_blob"])
        except Exception:
            self.fail("enc_blob w odpowiedzi nie jest poprawnym base64")

    def test_d7_get_blob_invalid_pse(self):
        """GET /archive/../secret/blob — walidacja PSE."""
        r = self.client.get("/archive/PSE-2026-../blob")
        self.assertIn(r.status_code, [400, 404, 422])

    def test_d12_audit_log(self):
        """GET /archive/audit zwraca log."""
        r = self.client.get("/archive/audit")
        self.assertEqual(r.status_code, 200)
        self.assertIn("log", r.json())


@unittest.skipUnless(_API_AVAILABLE, "pseudominizer_api niedostępna")
class TestArchiveDelete(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_db()
        cls.client = TestClient(app)
        cls.client.post("/archive", json={
            "pse": "PSE-2026-9020",
            "filename": "do_usuniecia.txt",
            "token_count": 1,
            "enc_blob": make_valid_blob(),
        })

    def test_d8_delete_valid(self):
        """DELETE /archive/{pse} usuwa rekord."""
        r = self.client.delete("/archive/PSE-2026-9020")
        self.assertIn(r.status_code, [200, 204])

    def test_d8b_delete_nonexistent(self):
        """DELETE na nieistniejący PSE — nie crashuje."""
        r = self.client.delete("/archive/PSE-2026-9999")
        self.assertIn(r.status_code, [200, 204, 404])

    def test_d9_delete_invalid_pse(self):
        """
        DELETE z path traversal — backend musi odrzucić.
        Starlette normalizuje URL przed routingiem: '../../etc/passwd' → '/etc/passwd'
        co nie pasuje do żadnego endpointu i zwraca 404.
        Akceptujemy [400, 404, 422] — każdy z nich oznacza że operacja nie przeszła.
        """
        r = self.client.delete("/archive/../../etc/passwd")
        self.assertIn(r.status_code, [400, 404, 422],
            f"Path traversal w PSE powinien być odrzucony (400/404/422), dostano {r.status_code}")


@unittest.skipUnless(_API_AVAILABLE, "pseudominizer_api niedostępna")
class TestArchiveReencrypt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _init_db()
        cls.client = TestClient(app)
        cls.client.post("/archive", json={
            "pse": "PSE-2026-9030",
            "filename": "reencrypt_test.txt",
            "token_count": 2,
            "enc_blob": make_valid_blob(),
        })

    def test_d10_reencrypt_valid(self):
        """POST /archive/reencrypt z poprawnym blobem — 200."""
        new_blob = base64.b64encode(b"NEW_ENCRYPTED_DATA_" + b"\x01" * 32).decode()
        r = self.client.post("/archive/reencrypt", json={
            "blobs": [{"pse": "PSE-2026-9030", "enc_blob": new_blob}]
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        self.assertEqual(r.json().get("updated"), 1)

    def test_d11_reencrypt_invalid_pse(self):
        """Nieprawidłowy PSE w blobach — rollback, 500 lub 400."""
        r = self.client.post("/archive/reencrypt", json={
            "blobs": [{"pse": "PSE-HACK/../../../etc", "enc_blob": make_valid_blob()}]
        })
        self.assertNotEqual(r.status_code, 200,
            "Nieprawidłowy PSE w reencrypt musi być odrzucony.")

    def test_d11b_empty_blobs(self):
        """Pusta lista blobów — 400."""
        r = self.client.post("/archive/reencrypt", json={"blobs": []})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=False)
