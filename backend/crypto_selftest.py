"""
Triangulum — crypto_selftest.py  v1.0
======================================
Self-test modułu anonymizer_crypto.
Uruchamiać ręcznie lub przy starcie serwera.

Testy NIE wymagają DPAPI ani dysku — operują wyłącznie w pamięci.
Każdy test jest niezależny. Fail = konkretny komunikat co poszło źle.

Uruchomienie:
    python crypto_selftest.py

Wyjście:
    0 (OK) — wszystkie testy przeszły
    1 (FAIL) — co najmniej jeden test nie przeszedł
"""

import sys
import json
import hmac
import hashlib
import secrets
import logging

logging.basicConfig(level=logging.WARNING)  # wycisz INFO podczas testów

# ── Import modułu ────────────────────────────────────────────────────────────

try:
    from anonymizer_crypto import (
        encrypt_map,
        decrypt_map,
        sign_entry,
        verify_entry,
        add_mac_to_entry,
        strip_mac,
        KEY_SIZE,
        NONCE_SIZE,
        TAG_SIZE,
        MAGIC,
    )
except ImportError as e:
    print(f"[FATAL] Nie można zaimportować anonymizer_crypto: {e}")
    sys.exit(1)

# ── Helpers ───────────────────────────────────────────────────────────────────

_PASSED = []
_FAILED = []


def _ok(name: str):
    _PASSED.append(name)
    print(f"  OK   {name}")


def _fail(name: str, reason: str):
    _FAILED.append(name)
    print(f"  FAIL {name}")
    print(f"       {reason}")


def _run(name: str, fn):
    try:
        fn()
        _ok(name)
    except AssertionError as e:
        _fail(name, str(e))
    except Exception as e:
        _fail(name, f"{type(e).__name__}: {e}")


# ── Testy: encrypt_map / decrypt_map ─────────────────────────────────────────

def _test_roundtrip_basic():
    """Szyfrowanie → deszyfrowanie zwraca identyczny słownik."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    original = {"OSOBA_001": {"base": "Jan Kowalski", "forms": ["Jana Kowalskiego"]}}
    blob = encrypt_map(original, enc_key)
    recovered = decrypt_map(blob, enc_key)
    assert recovered == original, f"Niezgodność: {recovered!r} != {original!r}"


def _test_roundtrip_empty():
    """Pusta mapa przechodzi przez cykl bez błędu."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = encrypt_map({}, enc_key)
    recovered = decrypt_map(blob, enc_key)
    assert recovered == {}, f"Oczekiwano {{}}, got {recovered!r}"


def _test_roundtrip_unicode():
    """Polskie znaki nie są tracone."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    original = {"OSOBA_001": {"base": "Józef Żółwiński", "forms": ["Józefa Żółwińskiego"]}}
    blob = encrypt_map(original, enc_key)
    recovered = decrypt_map(blob, enc_key)
    assert recovered == original, f"Utrata znaków: {recovered!r}"


def _test_magic_header():
    """Blob zaczyna się od MAGIC."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = encrypt_map({"x": 1}, enc_key)
    assert blob[:len(MAGIC)] == MAGIC, f"Brak MAGIC na początku bloba"


def _test_min_length():
    """Blob ma co najmniej MAGIC + NONCE + TAG bajtów."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = encrypt_map({}, enc_key)
    min_len = len(MAGIC) + NONCE_SIZE + TAG_SIZE
    assert len(blob) >= min_len, f"Blob za krótki: {len(blob)} < {min_len}"


def _test_wrong_key_raises():
    """Deszyfrowanie złym kluczem rzuca ValueError (zły tag GCM)."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    wrong_key = secrets.token_bytes(KEY_SIZE)
    blob = encrypt_map({"secret": "data"}, enc_key)
    try:
        decrypt_map(blob, wrong_key)
        raise AssertionError("Oczekiwano ValueError, nic nie rzucono")
    except ValueError:
        pass  # oczekiwane


def _test_tampered_ciphertext_raises():
    """Modyfikacja bajtu ciphertextu → ValueError (integralność GCM)."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = bytearray(encrypt_map({"x": "y"}, enc_key))
    blob[-1] ^= 0xFF  # zmień ostatni bajt tagu
    try:
        decrypt_map(bytes(blob), enc_key)
        raise AssertionError("Oczekiwano ValueError po manipulacji")
    except ValueError:
        pass


def _test_wrong_magic_raises():
    """Blob z złym nagłówkiem → ValueError z czytelnym komunikatem."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = b"BADMAGIC" + secrets.token_bytes(32)
    try:
        decrypt_map(blob, enc_key)
        raise AssertionError("Oczekiwano ValueError dla złego nagłówka")
    except ValueError:
        pass


def _test_truncated_blob_raises():
    """Zbyt krótki blob → ValueError."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    blob = MAGIC + b"\x00" * 4  # za mało bajtów na nonce + tag
    try:
        decrypt_map(blob, enc_key)
        raise AssertionError("Oczekiwano ValueError dla skróconego bloba")
    except ValueError:
        pass


def _test_nonce_is_random():
    """Każde wywołanie encrypt_map używa innego nonce."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    data = {"k": "v"}
    blobs = [encrypt_map(data, enc_key) for _ in range(10)]
    nonces = {b[len(MAGIC):len(MAGIC) + NONCE_SIZE] for b in blobs}
    assert len(nonces) == 10, f"Nonce się powtarza — użyto {len(nonces)} unikalnych z 10"


# ── Testy: sign_entry / verify_entry / add_mac_to_entry ───────────────────────

def _test_mac_verify_ok():
    """Podpisany wpis weryfikuje się poprawnie."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Anna Nowak", "forms": ["Anny Nowak", "Annie Nowak"]}
    signed = add_mac_to_entry("OSOBA_001", entry, mac_key)
    assert verify_entry("OSOBA_001", signed, mac_key), "Weryfikacja prawidłowego MAC nie powiodła się"


def _test_mac_wrong_key_fails():
    """Weryfikacja innym kluczem MAC zwraca False."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    wrong_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Anna Nowak", "forms": []}
    signed = add_mac_to_entry("OSOBA_001", entry, mac_key)
    assert not verify_entry("OSOBA_001", signed, wrong_key), "Fałszywa weryfikacja przy złym kluczu"


def _test_mac_tampered_base_fails():
    """Zmiana pola 'base' po podpisaniu → weryfikacja False."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Jan Kowalski", "forms": []}
    signed = add_mac_to_entry("OSOBA_001", entry, mac_key)
    signed["base"] = "Zły Kowalski"
    assert not verify_entry("OSOBA_001", signed, mac_key), "Zmiana base nie wykryta przez MAC"


def _test_mac_tampered_token_id_fails():
    """Podmiana token_id → weryfikacja False."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Jan Kowalski", "forms": []}
    signed = add_mac_to_entry("OSOBA_001", entry, mac_key)
    assert not verify_entry("OSOBA_002", signed, mac_key), "Podmiana token_id nie wykryta"


def _test_mac_missing_field_fails():
    """Wpis bez _mac → verify_entry zwraca False (nie rzuca)."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Jan Kowalski", "forms": []}
    result = verify_entry("OSOBA_001", entry, mac_key)
    assert result is False, f"Oczekiwano False dla brakującego _mac, got {result!r}"


def _test_strip_mac_removes_field():
    """strip_mac usuwa _mac i nie modyfikuje oryginału."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Test", "forms": []}
    signed = add_mac_to_entry("OSOBA_001", entry, mac_key)
    stripped = strip_mac(signed)
    assert "_mac" not in stripped, "_mac nadal w stripped"
    assert "_mac" in signed, "strip_mac zmodyfikował oryginał"


def _test_add_mac_is_idempotent():
    """Dwukrotne add_mac_to_entry daje ten sam wynik (determinizm podpisu)."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry = {"base": "Test", "forms": ["Testu"]}
    signed1 = add_mac_to_entry("NUMER_001", entry, mac_key)
    signed2 = add_mac_to_entry("NUMER_001", entry, mac_key)
    assert signed1["_mac"] == signed2["_mac"], "MAC nie jest deterministyczny"


def _test_mac_forms_order_independent():
    """Kolejność form nie wpływa na MAC (sortowanie wewnętrzne)."""
    mac_key = secrets.token_bytes(KEY_SIZE)
    entry_a = {"base": "X", "forms": ["forma_a", "forma_b"]}
    entry_b = {"base": "X", "forms": ["forma_b", "forma_a"]}
    mac_a = sign_entry("TOK_001", entry_a, mac_key)
    mac_b = sign_entry("TOK_001", entry_b, mac_key)
    assert mac_a == mac_b, "MAC zależy od kolejności form — powinien sortować"


# ── Testy: właściwości kryptograficzne ───────────────────────────────────────

def _test_enc_key_size():
    """KEY_SIZE wynosi 32 (AES-256)."""
    assert KEY_SIZE == 32, f"KEY_SIZE = {KEY_SIZE}, oczekiwano 32"


def _test_nonce_size():
    """NONCE_SIZE wynosi 12 (standard GCM)."""
    assert NONCE_SIZE == 12, f"NONCE_SIZE = {NONCE_SIZE}, oczekiwano 12"


def _test_tag_size():
    """TAG_SIZE wynosi 16 (GCM 128-bit tag)."""
    assert TAG_SIZE == 16, f"TAG_SIZE = {TAG_SIZE}, oczekiwano 16"


def _test_plaintext_not_in_blob():
    """Plaintext danych wrażliwych nie pojawia się w blobie."""
    enc_key = secrets.token_bytes(KEY_SIZE)
    sensitive = "85010112345"
    data = {"NUMER_001": {"base": sensitive, "forms": []}}
    blob = encrypt_map(data, enc_key)
    assert sensitive.encode() not in blob, "Plaintext PESEL znaleziony w zaszyfrowanym blobie"


# ── Uruchomienie ──────────────────────────────────────────────────────────────

_TESTS = [
    ("encrypt_map/decrypt_map: roundtrip podstawowy",       _test_roundtrip_basic),
    ("encrypt_map/decrypt_map: pusta mapa",                 _test_roundtrip_empty),
    ("encrypt_map/decrypt_map: polskie znaki",              _test_roundtrip_unicode),
    ("encrypt_map: nagłówek MAGIC",                         _test_magic_header),
    ("encrypt_map: minimalna długość bloba",                _test_min_length),
    ("decrypt_map: zły klucz → ValueError",                 _test_wrong_key_raises),
    ("decrypt_map: zmodyfikowany ciphertext → ValueError",  _test_tampered_ciphertext_raises),
    ("decrypt_map: zły nagłówek → ValueError",              _test_wrong_magic_raises),
    ("decrypt_map: skrócony blob → ValueError",             _test_truncated_blob_raises),
    ("encrypt_map: nonce losowy (10 wywołań)",              _test_nonce_is_random),
    ("sign/verify: poprawny MAC",                           _test_mac_verify_ok),
    ("sign/verify: zły klucz MAC → False",                  _test_mac_wrong_key_fails),
    ("sign/verify: zmiana base → False",                    _test_mac_tampered_base_fails),
    ("sign/verify: podmiana token_id → False",              _test_mac_tampered_token_id_fails),
    ("verify: brak pola _mac → False",                      _test_mac_missing_field_fails),
    ("strip_mac: usuwa _mac, nie modyfikuje oryginału",     _test_strip_mac_removes_field),
    ("add_mac_to_entry: deterministyczny",                  _test_add_mac_is_idempotent),
    ("sign_entry: kolejność form nie zmienia MAC",          _test_mac_forms_order_independent),
    ("stałe: KEY_SIZE == 32",                               _test_enc_key_size),
    ("stałe: NONCE_SIZE == 12",                             _test_nonce_size),
    ("stałe: TAG_SIZE == 16",                               _test_tag_size),
    ("szyfrowanie: plaintext nie w blobie",                 _test_plaintext_not_in_blob),
]


def run_all() -> int:
    print("=" * 60)
    print("  crypto_selftest.py  v1.0")
    print("=" * 60)
    for name, fn in _TESTS:
        _run(name, fn)
    print("-" * 60)
    total = len(_PASSED) + len(_FAILED)
    print(f"  {len(_PASSED)}/{total} passed", end="")
    if _FAILED:
        print(f"  |  FAILED: {len(_FAILED)}")
        for f in _FAILED:
            print(f"    - {f}")
        return 1
    else:
        print("  — wszystkie OK")
        return 0


if __name__ == "__main__":
    sys.exit(run_all())
