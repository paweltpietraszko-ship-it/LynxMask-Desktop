# Re-check F1-F3, copied from immutable 6cbd0ab; only DEBUG and absent-file harness assumptions updated.
"""Bounded security review; isolated synthetic profile/archive, no product edits.
Run with project Python. JSON evidence contains flags/counts, never token/PII values.
"""
import contextlib
import io
import json
import logging
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(REPO / "backend"), str(REPO / "audyt")]
ROOT = Path(tempfile.mkdtemp(prefix="lynx_security_r1_"))
os.environ.update(ANONYMIZER_PROFILE_DIR=str(ROOT / "profile"),
                  PROFILE_DIR=str(ROOT / "allowlist"),
                  HARDWARE_PROFILE=str(ROOT / "hw.json"),
                  ARCHIVE_DIR=str(ROOT / "archive"), PSE_REGISTRY=str(ROOT / "pse.json"))
OUT = {}
traffic = []
real_connect = socket.socket.connect


def connect(sock, address):
    traffic.append(str(address))
    return real_connect(sock, address)


socket.socket.connect = connect
capture = io.StringIO()
handler = logging.StreamHandler(capture)
handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import anonymizer_crypto as crypto
    import engine_quality as eq
    import pseudominizer_api as api
    import db_store
    import fitz
    from fastapi.testclient import TestClient
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import document_processor
    import ocr_engine

    state = eq.build_state(str(ROOT / "profile"))
    api._app_state = state
    api._API_TOKEN, api._EXPRESS_TOKEN = "a" * 64, "b" * 64
    api._GUARD_AVAILABLE = True
    client = TestClient(api.app, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)
    full = {"X-Api-Token": api._API_TOKEN}
    expr = {"X-Api-Token": api._EXPRESS_TOKEN}

    def preview(name, content, headers=full):
        return client.post("/preview", files={"file": (name, content, "application/octet-stream")}, headers=headers)

    marker = "AudytowiczBezpieczenstwo"
    entity = "Zenobiusz " + marker
    add = client.post("/profile/add-entity", json={"text": entity, "token_type": "OSOBA"}, headers=full)
    assert add.status_code == 200
    profile_files = [p for p in (ROOT / "profile").rglob("*") if p.is_file()]
    enc = ROOT / "profile/mapa.enc"
    trie = ROOT / "profile/trie.pkl"
    OUT["profile_plaintext"] = {
        "encrypted_map_has_marker": marker.encode() in enc.read_bytes(),
        "trie_exists": trie.exists(),
        "trie_has_marker": trie.exists() and marker.encode() in trie.read_bytes(),
        "files": [p.name for p in profile_files],
    }

    key = crypto.get_or_create_keys(ROOT / "profile")[0]
    blob = crypto.encrypt_map({"OSOBA_001": entity}, key)
    crypto_cases = {"roundtrip": crypto.decrypt_map(blob, key) == {"OSOBA_001": entity}}
    for label, bad, candidate_key in (
        ("wrong_key_rejected", blob, b"x" * 32),
        ("tamper_rejected", blob[:-1] + bytes([blob[-1] ^ 1]), key),
        ("truncated_rejected", blob[:12], key),
    ):
        try:
            crypto.decrypt_map(bad, candidate_key)
        except ValueError:
            crypto_cases[label] = True
        else:
            crypto_cases[label] = False
    OUT["crypto"] = crypto_cases

    # Ordinary inputs, common parse failure, and actual guard chain.
    normal = preview("syntetyk.txt", f"Powód {entity}, PESEL: 44051401359.".encode())
    assert normal.status_code == 200
    OUT["preview"] = {"http": normal.status_code,
                      "marker_in_masked_text": marker in normal.json().get("anonymized_preview", ""),
                      "blocked": normal.json().get("blocked")}
    malformed = preview(marker + ".docx", b"not-a-docx")
    OUT["parse_error"] = {"http": malformed.status_code, "marker_in_log": marker in capture.getvalue()}

    # Metadata + filename logging on a real API export, with safe masked body.
    capture.truncate(0)
    capture.seek(0)
    pdf = client.post("/export-pdf", json={"text": "Powód OSOBA_001.", "filename": marker + ".pdf"}, headers=full)
    assert pdf.status_code == 200
    with fitz.open(stream=pdf.content, filetype="pdf") as doc:
        meta = doc.metadata
    OUT["pdf"] = {"title_has_marker": marker in meta.get("title", ""),
                  "author_empty": not meta.get("author"), "creator_empty": not meta.get("creator"),
                  "filename_in_log": marker in capture.getvalue()}

    # Real synthetic raster through OCR when Tesseract is available.
    capture.truncate(0)
    capture.seek(0)
    if ocr_engine._tesseract_available():
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (1600, 300), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 40)
        draw.text((60, 90), "Termin skladania ofert uplywa jutro.", fill="black", font=font)
        raster = io.BytesIO()
        image.save(raster, format="PNG")
        image_response = preview(marker + ".png", raster.getvalue())
        OUT["ocr_filename_log"] = {"run": "REAL_OCR", "http": image_response.status_code,
                                   "filename_in_log": marker in capture.getvalue()}
    else:
        OUT["ocr_filename_log"] = {"run": "NOT_CHECKED_NO_TESSERACT"}

    # HTTP model: no full token, Express restricted, DNS rebinding, browser CORS.
    OUT["http_access"] = {
        "no_token_profile": client.get("/profile/entities").status_code,
        "express_profile": client.get("/profile/entities", headers=expr).status_code,
        "host_rebinding": client.get("/health", headers={"Host": "attacker.invalid"}).status_code,
        "old_route": client.post("/preview-express", headers=full).status_code,
    }
    preflight = client.options("/preview", headers={"Origin": "https://attacker.invalid",
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "X-Api-Token"})
    public = client.get("/express/token", headers={"Origin": "https://attacker.invalid"})
    simple = client.post("/profile/reset", content='{"confirm":true}',
        headers={"Origin": "https://attacker.invalid", "Content-Type": "text/plain"})
    OUT["browser"] = {"untrusted_preflight": preflight.status_code,
        "untrusted_token_cors_read_allowed": public.headers.get("access-control-allow-origin") == "https://attacker.invalid",
        "simple_csrf_reset": simple.status_code}

    # Authentic encrypted archive, then logical deletion.
    import base64
    archive_blob = AESGCM(b"q" * 32).encrypt(b"n" * 12, entity.encode(), None)
    encoded = base64.b64encode(b"n" * 12 + archive_blob).decode()
    payload = {"pse": "PSE-2026-9876", "enc_blob": encoded, "token_count": 1}
    saved = client.post("/archive", json=payload, headers=full)
    assert saved.status_code == 200
    path = api.MAPS_DIR / "PSE-2026-9876.enc"
    OUT["archive"] = {"saved_encrypted_bytes": path.read_bytes() == base64.b64decode(encoded),
                      "marker_in_file": marker.encode() in path.read_bytes()}
    deleted = client.delete("/archive/PSE-2026-9876", headers=full)
    OUT["archive"]["delete_removed_file_and_record"] = (
        deleted.status_code == 200 and not path.exists()
        and not any(d["pse"] == payload["pse"] for d in db_store.list_documents()))

    # Ordinary reset, observe whether profile cache/allowlist retains synthetic PII.
    capture.truncate(0)
    capture.seek(0)
    allow = client.post("/profile/guard-allowlist", json={"phrase": entity}, headers=full)
    assert allow.status_code == 200
    OUT["allowlist"] = {"plaintext_file": (api._guard_allowlist_path().exists() and marker.encode() in api._guard_allowlist_path().read_bytes()),
                        "value_in_log": marker in capture.getvalue()}
    reset = client.post("/profile/reset", json={"confirm": True}, headers=full)
    leftovers = [p.name for p in (ROOT / "profile").rglob("*")
                 if p.is_file() and marker.encode() in p.read_bytes()]
    OUT["reset"] = {"http": reset.status_code, "plaintext_marker_files_remaining": leftovers,
        "allowlist_marker_remains": (api._guard_allowlist_path().exists() and marker.encode() in api._guard_allowlist_path().read_bytes())}

socket.socket.connect = real_connect
logging.getLogger().removeHandler(handler)
OUT["python_socket_connects"] = sorted(set(traffic))
OUT["synthetic_root"] = str(ROOT)
print(json.dumps(OUT, ensure_ascii=True, indent=2))