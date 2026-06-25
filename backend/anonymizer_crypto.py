"""
Triangulum — anonymizer_crypto.py  v1
======================================
Szyfrowanie mapy anonimizacji: AES-256-GCM + DPAPI (Windows) + MAC per wpis.

Architektura kluczy:
  Klucz szyfrowania (ENC_KEY, 32 bajty)  → chroni treść mapy
  Klucz MAC         (MAC_KEY, 32 bajty)  → podpisuje każdy wpis encji

  Oba klucze generowane losowo przy pierwszym uruchomieniu.
  Przechowywane w keystore szyfrowanym DPAPI (Windows) lub
  pliku z uprawnieniami 0600 (Linux/dev fallback).

Zasady:
  - Mapa zapisywana jako plik binarny .enc (nie JSON w plain text)
  - Przy odczycie: weryfikacja MAC każdego wpisu przed użyciem
  - Brak zgodności MAC = odrzucenie wpisu + ostrzeżenie
  - Klucze nigdy nie wychodzą poza pamięć procesu i keystore

Ograniczenia:
  - DPAPI chroni klucze tylko przed innymi kontami Windows —
    nie chroni przed procesami działającymi jako ten sam użytkownik
  - Fallback plikowy (Linux) daje tylko ochronę uprawnień systemu plików
  - Rotacja kluczy per tenant: zaplanowana na PRO tier
"""

import os
import json
import hmac
import struct
import hashlib
import logging
import platform
import secrets
from pathlib import Path
from typing import Optional

logger = logging.getLogger("triangulum.crypto")

# ============================================================
# Stałe
# ============================================================

KEY_SIZE       = 32          # AES-256 = 32 bajty
NONCE_SIZE     = 12          # GCM standard nonce
TAG_SIZE       = 16          # GCM authentication tag
MAGIC          = b"TRGM\x01" # nagłówek pliku — wersja 1
KEYSTORE_FILE  = "triangulum_keystore.bin"

# ============================================================
# DPAPI (Windows) — ochrona keystore
# ============================================================

def _dpapi_protect(data: bytes) -> bytes:
    """
    Szyfruje bajty kluczem powiązanym z kontem użytkownika Windows (DPAPI).
    Działa tylko na Windows. Rzuca RuntimeError na innych systemach.
    """
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    p = ctypes.create_string_buffer(data, len(data))
    blobin  = DATA_BLOB(len(data), p)
    blobout = DATA_BLOB()

    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blobin),
        None, None, None, None,
        0,  # CRYPTPROTECT_UI_FORBIDDEN = 0x1, ale 0 też działa bez UI
        ctypes.byref(blobout)
    )
    if not ok:
        raise RuntimeError(
            f"DPAPI CryptProtectData failed: {ctypes.GetLastError()}"
        )

    result = ctypes.string_at(blobout.pbData, blobout.cbData)
    ctypes.windll.kernel32.LocalFree(blobout.pbData)
    return result


def _dpapi_unprotect(data: bytes) -> bytes:
    """
    Deszyfruje bajty zabezpieczone przez DPAPI.
    Rzuca RuntimeError przy niezgodności lub błędzie.
    """
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    p = ctypes.create_string_buffer(data, len(data))
    blobin  = DATA_BLOB(len(data), p)
    blobout = DATA_BLOB()

    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blobin),
        None, None, None, None,
        0,
        ctypes.byref(blobout)
    )
    if not ok:
        raise RuntimeError(
            f"DPAPI CryptUnprotectData failed: {ctypes.GetLastError()}"
        )

    result = ctypes.string_at(blobout.pbData, blobout.cbData)
    ctypes.windll.kernel32.LocalFree(blobout.pbData)
    return result


def _is_windows() -> bool:
    return platform.system() == "Windows"


# ============================================================
# Keystore — przechowywanie kluczy ENC + MAC
# ============================================================

def _keystore_path(profile_dir: Path) -> Path:
    return profile_dir / KEYSTORE_FILE


def _save_keystore(profile_dir: Path, enc_key: bytes, mac_key: bytes) -> None:
    """
    Zapisuje dwa klucze do keystore.
    Windows: cały blob chroniony DPAPI.
    Linux:   plik z uprawnieniami 0600 (ochrona OS).
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    payload = enc_key + mac_key  # 64 bajty

    if _is_windows():
        protected = _dpapi_protect(payload)
    else:
        # Linux/dev: brak DPAPI — plik z restrykcyjnymi uprawnieniami
        protected = payload
        logger.warning(
            "anonymizer_crypto: DPAPI niedostępne (nie-Windows). "
            "Klucze przechowywane bez ochrony sprzętowej — tylko uprawnienia pliku."
        )

    ks_path = _keystore_path(profile_dir)
    tmp = ks_path.with_suffix(".tmp")
    tmp.write_bytes(protected)

    if not _is_windows():
        os.chmod(tmp, 0o600)

    tmp.replace(ks_path)
    logger.info(f"anonymizer_crypto: keystore zapisany: {ks_path}")


def _load_keystore(profile_dir: Path) -> tuple[bytes, bytes]:
    """
    Ładuje klucze ENC i MAC z keystore.
    Rzuca FileNotFoundError jeśli keystore nie istnieje.
    Rzuca RuntimeError przy błędzie DPAPI lub uszkodzeniu pliku.
    """
    ks_path = _keystore_path(profile_dir)
    if not ks_path.exists():
        raise FileNotFoundError(f"Keystore nie istnieje: {ks_path}")

    protected = ks_path.read_bytes()

    if _is_windows():
        payload = _dpapi_unprotect(protected)
    else:
        payload = protected

    if len(payload) != KEY_SIZE * 2:
        raise RuntimeError(
            f"Keystore uszkodzony: oczekiwano {KEY_SIZE * 2} bajtów, "
            f"got {len(payload)}"
        )

    enc_key = payload[:KEY_SIZE]
    mac_key = payload[KEY_SIZE:]
    return enc_key, mac_key


def get_or_create_keys(profile_dir: Path) -> tuple[bytes, bytes]:
    """
    Zwraca (enc_key, mac_key). Tworzy nowe klucze jeśli keystore nie istnieje.
    Klucze generowane przez secrets.token_bytes — kryptograficznie losowe.
    """
    try:
        return _load_keystore(profile_dir)
    except FileNotFoundError:
        enc_key = secrets.token_bytes(KEY_SIZE)
        mac_key = secrets.token_bytes(KEY_SIZE)
        _save_keystore(profile_dir, enc_key, mac_key)
        logger.info("anonymizer_crypto: wygenerowano nowe klucze ENC + MAC")
        return enc_key, mac_key


# ============================================================
# AES-256-GCM — szyfrowanie całej mapy
# ============================================================

def encrypt_map(data: dict, enc_key: bytes) -> bytes:
    """
    Szyfruje słownik mapy jako AES-256-GCM.

    Format pliku .enc:
      MAGIC (5 bajtów)
      nonce (12 bajtów)
      ciphertext + tag (zmienna długość, tag ostatnie 16 bajtów)

    Używa cryptography.hazmat — wymagana zależność.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    plaintext = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    nonce = secrets.token_bytes(NONCE_SIZE)
    aesgcm = AESGCM(enc_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)  # AAD=None

    return MAGIC + nonce + ciphertext


def decrypt_map(ciphertext_blob: bytes, enc_key: bytes) -> dict:
    """
    Deszyfruje blob z pliku .enc.
    Rzuca ValueError przy błędzie integralności lub złym formacie.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    if not ciphertext_blob.startswith(MAGIC):
        raise ValueError(
            "Nieprawidłowy nagłówek pliku — możliwe uszkodzenie lub zły format."
        )

    blob = ciphertext_blob[len(MAGIC):]
    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Plik za krótki — uszkodzony.")

    nonce      = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]

    aesgcm = AESGCM(enc_key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise ValueError(
            "Weryfikacja integralności nieudana — plik mógł zostać zmodyfikowany."
        )

    return json.loads(plaintext.decode("utf-8"))


# ============================================================
# MAC per wpis — podpis każdej encji
# ============================================================

def sign_entry(token_id: str, entity: dict, mac_key: bytes) -> str:
    """
    Oblicza HMAC-SHA256 dla pojedynczego wpisu encji.
    Podpisuje: token_id + base + posortowane forms.
    Zwraca hex string.
    """
    forms_sorted = sorted(entity.get("forms", []))
    content = json.dumps(
        {"id": token_id, "base": entity.get("base", ""), "forms": forms_sorted},
        ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hmac.new(mac_key, content, hashlib.sha256).hexdigest()


def verify_entry(token_id: str, entity: dict, mac_key: bytes) -> bool:
    """
    Weryfikuje MAC wpisu. Zwraca True jeśli zgodny, False jeśli nie.
    Używa hmac.compare_digest — odporny na timing attacks.
    """
    stored_mac = entity.get("_mac", "")
    if not stored_mac:
        return False
    expected = sign_entry(token_id, entity, mac_key)
    return hmac.compare_digest(stored_mac, expected)


def add_mac_to_entry(token_id: str, entity: dict, mac_key: bytes) -> dict:
    """
    Dodaje pole _mac do wpisu encji. Zwraca nowy słownik (nie modyfikuje w miejscu).
    """
    entry = {k: v for k, v in entity.items() if k != "_mac"}
    entry["_mac"] = sign_entry(token_id, entry, mac_key)
    return entry


def strip_mac(entity: dict) -> dict:
    """Usuwa _mac z wpisu — do przekazania do trie/anonymizer."""
    return {k: v for k, v in entity.items() if k != "_mac"}


# ============================================================
# Ścieżki plików
# ============================================================

def enc_map_path(profile_dir: Path) -> Path:
    return profile_dir / "mapa.enc"


def plain_map_path(profile_dir: Path) -> Path:
    return profile_dir / "mapa.json"