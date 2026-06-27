"""
pseudominizer_api.py  v1.35-TAURI
Historia zmian (od najnowszej):
  v1.35-TAURI (2026-06-27):
    [DICT-EXPORT] GET /profile/export-dict — eksport biblioteki encji jako JSON (.lynxdict).
    [DICT-IMPORT] POST /profile/import-dict — import encji z pliku .lynxdict.
    [PROFILE-RESET] POST /profile/reset — usunięcie wszystkich danych użytkownika.
  v1.34-TAURI (2026-06-27):
    [EXPR-TOKEN] Express Mode token sesji — _EXPRESS_TOKEN generowany przy starcie.
                 GET /express/token zwraca token bez auth (dostępny przed logowaniem).
                 Middleware akceptuje _API_TOKEN LUB _EXPRESS_TOKEN — Express Mode
                 ma dostęp do pełnego pipeline (/preview, /profile/add-entity itp.)
  v1.33-TAURI (2026-06-27):
    [EXPR-API] Endpoint /preview-express — Express Mode bez SpaCy/NER.
               Wywołuje run_pipeline_express() zamiast run_pipeline_new().
               Taki sam interfejs jak /preview, bez pola anonymizer_active.
               force_block zawsze False — brak NER = brak możliwości NER crash.
  v1.32-TAURI (2026-06-26):
    [CRASH-UX] Zapis startup_error.json przed śmiercią procesu.
               Frontend czyta ten plik przez Tauri read_startup_error() i pokazuje
               CrashScreen z kodem błędu, instrukcją restartu i mailto do zgłoszenia.
               Plik jest kasowany na początku _lifespan — stare błędy nie blokują nowego uruchomienia.
  v1.31-TAURI (2026-06-26):
    [MED-4] Logger w /profile/add-entity ujawniał token_type (np. "OSOBA").
             To metadata — usunięte z logu, zostaje tylko token_id.
    [CRIT-1] POST /archive odbiera guard_blocked od klienta i zapisuje do DB.
             GET /archive/{pse}/blob zwraca 403 gdy guard_blocked=True.
  v1.30-TAURI (2026-06-12):
    [AUD-01] Token injection attack — walidacja w /preview przed pipeline.
             Jeśli tekst wejściowy zawiera token w formacie FIRMA_001 (lub
             dowolny inny token z _TOKEN_RE) — odrzuć 422 z komunikatem.
             _TOKEN_RE już obejmuje wszystkie 7 typów (INSTYTUCJA, EMAIL włącznie).
             Dotknięte linie: endpoint /preview, 13 linii po sprawdzeniu pustego tekstu.
    [AUD-02] PII usunięte z logów produkcyjnych — RODO Art. 5(1)(f).
             Linia ~651 (add-entity): logger.info logował text[:40] czyli treść encji
             dodawanej do profilu biura. Zamienione na [token_id=X] gdzie X to
             identyfikator przypisany przez anonymizer (np. FIRMA_003).
             token_id jest dostępny w tym kontekście — przypisywany linię wyżej.
    [FIX-SPLIT-RE] Split regex w /profile/add-entity uzupełniony o INSTYTUCJA i EMAIL.
             Linia ~627: regex chronił przed wstrzyknięciem tokenów przy ręcznym
             dodawaniu encji, ale pomijał INSTYTUCJA_NNN i EMAIL_NNN.
             Niespójność z _TOKEN_RE w tym samym pliku (linia 187).
  v1.29-TAURI (2026-06-10):
    [OCR-REJECT] Odmowa przetwarzania gdy ocr.quality === "reject" (conf < 70%).
                 Zwraca HTTP 422 z polem ocr_rejected=True i komunikatem dla użytkownika.
                 Pipeline nie jest wywoływany — brak ryzyka wycieku przez błędne maskowanie.
                 Empiryczne uzasadnienie: conf=66.7% dawało katastrofalne wyniki NER.
                 Dotknięte linie: endpoint /preview, ~15 linii po sprawdzeniu pustego tekstu.
    [FIX-LOG-400] Dodano logowanie przyczyny błędu ekstrakcji tekstu.
                  Poprzednio 400 Bad Request z /preview nie zostawiał żadnego
                  śladu w logu poza kodem HTTP — niemożliwe było ustalenie
                  przyczyny bez debuggera. Teraz logger.warning loguje
                  extract_err przed zwróceniem odpowiedzi.
                  Dotknięte linie: ~preview endpoint, 1 linia dodana.
    [TASK-3] API_VERSION wyrównana do nagłówka pliku (było "1.26-TAURI", linia 178).
             Zmiana kosmetyczna — stała używana przez FastAPI w /version i /docs.
  v1.27-TAURI (2026-06-07):
    [BUG-6] EMAIL dodany do _TYPE_LABELS, _TYPE_ORDER, _TOKEN_RE.
            Email tokenizowany jako EMAIL_NNN zamiast NUMER_NNN.
            _TYPE_ORDER: EMAIL na pozycji 4 (między NUMER a KWOTA).
            Dotknięte linie: _TYPE_LABELS (~157), _TYPE_ORDER (~165), _TOKEN_RE (~167).
  v1.26-TAURI (2026-06-06 — aktualizacja):
    [BUG-12] _TOKEN_RE rozszerzony o INSTYTUCJA (linia 165).
  v1.26-TAURI (2026-06-06):
    [BUG-13] ANON_PROFILE_DIR zmieniony na sciezke bezwzgledna przez __file__
             (linia 81). Tylko zmiana defaultu — logika endpointow niezmieniona.
    [BUG-8]  Synchronizacja naglowka pliku z API_VERSION (linia 3).
  v1.23 (2026-05-19):
    [DB-STORE-1] Cały SQLite wydzielony do db_store.py.
                 pseudominizer_api.py nie importuje sqlite3 — wywołuje db_store.*.
                 Usuwa: _db_lock, _migrate_db(), _init_db(), _audit() z tego pliku.
    [DB-STORE-2] POST /archive: nowe pole description (base64 zaszyfrowany blob, opcjonalne).
                 GET /archive: zwraca description jako base64 string.
    [HEALTH-CRYPTO] GET /health: dodano crypto_ok z crypto_selftest.run_all().
                 Sprawdzane raz przy starcie — nie przy każdym żądaniu.
  v1.22 (2026-05-19):
    [LEAK-DB-1] Usunięto kolumnę filename z tabeli documents (SQLite).
  v1.21:
    [LEAK-LOG-2] Usunięto PII z logów INFO.
  v1.20:
    [VARIANT-A] POST /profile/add-entity: persystuje ręcznie dodane encje.
  v1.19--v1.11: patrz wcześniejsza historia.
==========================
Minimalny backend FastAPI dla Pseudominizera.
Endpointy:
  POST /preview              — ekstrakcja tekstu + pseudonimizacja
  GET  /health               — status serwera + crypto_ok
  POST /archive              — zapisz zaszyfrowany blob + opis
  GET  /archive              — lista dokumentów
  GET  /archive/{pse}/blob   — pobierz blob sesji
  DELETE /archive/{pse}      — usuń dokument
  POST /archive/reencrypt    — zmiana hasła (podmiana blobów)
  GET  /archive/audit        — log zdarzeń
  POST /export-pdf           — generuj PDF server-side
  POST /profile/add-entity   — [VARIANT-A] persystuj encję biura
  GET  /                     — frontend HTML

Invarianty bezpieczeństwa:
  - Fail-closed: brak anonymizera = brak eksportu
  - Dane nie wychodzą poza localhost
  - Brak logowania treści dokumentów
  - description zaszyfrowane po stronie klienta — backend nie widzi plaintext
"""

import os
import re
import base64
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

import db_store
from audit_log import record_preview

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pseudominizer")

# ── Stałe ────────────────────────────────────────────────────────────────────

MAX_FILE_BYTES   = 5 * 1024 * 1024   # 5 MB
MAX_TEXT_CHARS   = 15_000
MAX_BLOB_BYTES   = 512 * 1024         # 512 KB

# [SECURITY-TOKEN] Token API generowany raz przy starcie — losowy, 32 bajty hex.
# Tauri przekazuje go w nagłówku X-Api-Token przy każdym żądaniu.
# Chroni przed dostępem z innych procesów na tym samym localhost.
# Zapis do pliku tymczasowego (api_token.txt) żeby Tauri mógł go odczytać
# przed pierwszym żądaniem.
# [FIX-DOUBLE-TOKEN] Token generowany w _lifespan() — NIE na poziomie modułu.
# Na Windows uvicorn używa spawn: moduł jest importowany dwukrotnie (main + worker).
# Każdy import generował inny token i nadpisywał plik — worker miał inny token
# niż ostatni zapis do pliku → 401 na wszystkich requestach.
# _lifespan() uruchamia się wyłącznie w procesie workera, dokładnie raz.
import secrets as _secrets
_API_TOKEN_PATH = Path(__file__).parent / "api_token.txt"
_API_TOKEN: str         = ""  # ustawiany w _lifespan()
_EXPRESS_TOKEN: str     = ""  # token dla Express Mode (bez logowania), ustawiany w _lifespan()
FRONTEND_FILE    = Path(__file__).parent / "pseudominizer.html"
ANON_PROFILE_DIR = os.getenv("ANONYMIZER_PROFILE_DIR", str(Path(__file__).parent / "anon_profiles" / "pseudominizer"))
HARDWARE_PROFILE = os.getenv("HARDWARE_PROFILE", "./hardware_profile.json")

# ── Archiwum ──────────────────────────────────────────────────────────────────

ARCHIVE_DIR = Path(os.getenv("ARCHIVE_DIR", "./archive"))
MAPS_DIR    = ARCHIVE_DIR / "mapy"

# Inicjalizacja bazy — przez db_store (nie bezpośrednio sqlite3)
MAPS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = ARCHIVE_DIR / "rejestr.db"
db_store.init(DB_PATH)

def _init_db() -> None:
    """Alias kompatybilności — DB inicjalizowana przy imporcie modułu."""
    pass

# ── Rejestr PSE + ekstrakcja tekstu ──────────────────────────────────────────

from document_processor import _next_pse, _extract_text

# ── Inicjalizacja modułów ─────────────────────────────────────────────────────

from pipeline import AppState, pseudonymize_document

_app_state = AppState()
_GUARD_AVAILABLE = False
SYSTEM_PROMPT_SECURITY = None
_crypto_ok = False


# [FIX-DOUBLE-START] Inicjalizacja modułów przeniesiona do lifespan.
# Poprzednio kod wykonywał się na poziomie modułu — uvicorn na Windows używa
# spawn zamiast fork, co powoduje dwukrotny import modułu (proces główny +
# worker). Lifespan gwarantuje jednokrotne wykonanie w procesie workera.
_STARTUP_ERROR_PATH = Path(__file__).parent / "startup_error.json"


def _write_startup_error(code: str, message: str) -> None:
    import json as _json_mod
    from datetime import datetime as _dt
    try:
        _STARTUP_ERROR_PATH.write_text(
            _json_mod.dumps({"code": code, "message": message,
                             "timestamp": _dt.now().isoformat()},
                            ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as _e:
        logger.error(f"[CRASH-UX] Nie można zapisać startup_error.json: {_e}")


@asynccontextmanager
async def _lifespan(app):
    global _GUARD_AVAILABLE, SYSTEM_PROMPT_SECURITY, _crypto_ok, _API_TOKEN, _EXPRESS_TOKEN

    # [CRASH-UX] Kasujemy stary plik błędu na początku każdego startu.
    try:
        _STARTUP_ERROR_PATH.unlink(missing_ok=True)
    except Exception:
        pass

    _API_TOKEN     = _secrets.token_hex(32)
    _EXPRESS_TOKEN = _secrets.token_hex(32)
    try:
        _API_TOKEN_PATH.write_text(_API_TOKEN, encoding="utf-8")
    except Exception as _e:
        logger.warning(f"[SECURITY] Nie można zapisać api_token.txt: {_e}")

    try:
        import spacy_ner as _spacy_ner_mod
        _app_state.spacy_ner_mod = _spacy_ner_mod
        logger.info("[STARTUP] spacy_ner załadowany")
    except ImportError:
        logger.warning("[STARTUP] spacy_ner niedostępny — pseudonimizacja NER wyłączona")

    try:
        from anonymizer import build_anonymizer as _build_anonymizer
        _app_state.anonymizer, _, _app_state.anon_map, _app_state.morf_env = \
            _build_anonymizer(ANON_PROFILE_DIR, HARDWARE_PROFILE)
        logger.info(f"[STARTUP] Anonymizer załadowany: {ANON_PROFILE_DIR}")
        try:
            from seed_profile import seed_if_needed as _seed
            _seed(_app_state.anon_map)
        except Exception as _se:
            logger.warning(f"[STARTUP] seed_profile pominięty: {_se}")
    except Exception as e:
        logger.warning(f"[STARTUP] Anonymizer niedostępny: {e}")

    try:
        from output_guard import SYSTEM_PROMPT_SECURITY as _sps
        SYSTEM_PROMPT_SECURITY = _sps
        _GUARD_AVAILABLE = True
        logger.info("[STARTUP] output_guard załadowany")
    except ImportError:
        logger.warning("[STARTUP] output_guard niedostępny — blokada wyjściowa wyłączona")

    try:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            from crypto_selftest import run_all as _crypto_selftest
            _crypto_ok = (_crypto_selftest() == 0)
        logger.info(f"[STARTUP] crypto_selftest: {'OK' if _crypto_ok else 'FAIL'}")
    except Exception as e:
        logger.warning(f"[STARTUP] crypto_selftest niedostępny: {e}")

    try:
        from smoke_test import assert_smoke_test as _assert_smoke
        _assert_smoke()
    except RuntimeError as _re:
        _code = "SMOKE-" + (str(_re)[:30].replace(" ", "-").upper()
                            if str(_re) else "PIPELINE-ERROR")
        _write_startup_error(_code, str(_re))
        raise
    except Exception as _e:
        _write_startup_error("SMOKE-UNEXPECTED", str(_e))
        raise RuntimeError(f"[SMOKE] Nieoczekiwany błąd smoke testu: {_e}")

    yield  # aplikacja działa

# ── Stałe dla tabeli tokenów ──────────────────────────────────────────────────

_TYPE_LABELS = {
    "OSOBA":      "Osoba",
    "FIRMA":      "Firma / Organizacja",
    "NUMER":      "Numer identyfikacyjny",
    "KWOTA":      "Kwota",
    "ADRES":      "Adres",
    "INSTYTUCJA": "Instytucja publiczna",
    "EMAIL":      "Adres e-mail",
}
_TYPE_ORDER = {"OSOBA": 0, "FIRMA": 1, "INSTYTUCJA": 2, "NUMER": 3, "EMAIL": 4, "KWOTA": 5, "ADRES": 6}

_TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b")


# ── App ───────────────────────────────────────────────────────────────────────

API_VERSION = "1.35-TAURI"  # [DICT-EXPORT/IMPORT/RESET] Zarządzanie profilem

app = FastAPI(
    lifespan=_lifespan,
    title="Pseudominizer API",
    description="Lokalny backend pseudonimizacji dokumentów. Brak chmury, brak telemetrii.",
    version=API_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # localhost-only server — wildcard bezpieczny
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# [SECURITY-TOKEN] Middleware sprawdzający token API.
# /health pomijany — Tauri sprawdza go przed odczytem tokenu.
# OPTIONS pomijany — preflight CORS nie niesie tokenu, musi przejść do CORSMiddleware.
# Nagłówek: X-Api-Token: <token>
@app.middleware("http")
async def _require_api_token(request, call_next):
    if request.url.path in ("/health", "/express/token") or request.method == "OPTIONS":
        return await call_next(request)
    token = request.headers.get("x-api-token", "")
    ok = _secrets.compare_digest(token, _API_TOKEN) or (
        bool(_EXPRESS_TOKEN) and _secrets.compare_digest(token, _EXPRESS_TOKEN)
    )
    if not ok:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


# ── Endpointy ─────────────────────────────────────────────────────────────────

@app.get("/version")
async def version():
    return {"api": API_VERSION, "ocr": "1.0"}


@app.get("/express/token")
async def express_token():
    """Zwraca token sesji Express Mode (bez logowania).
    Endpoint nie wymaga auth — token jest tymczasowy, ważny do restartu backendu.
    """
    return {"token": _EXPRESS_TOKEN}


@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "anonymizer": bool(_app_state.anonymizer),
        "spacy_ner":  bool(_app_state.spacy_ner_mod),
        "morfeusz":   _app_state.morf_env.mode if _app_state.morf_env else "unavailable",
        "crypto_ok":  _crypto_ok,
    }


@app.post("/preview")
async def preview(request: Request, file: UploadFile = File(...)):
    """
    Przyjmuje plik (PDF/DOCX/TXT/obraz), zwraca pseudonimizowany tekst i mapę tokenów.
    Nie wysyła danych do żadnych zewnętrznych serwisów.
    """
    content = await file.read()

    if len(content) > MAX_FILE_BYTES:
        return JSONResponse(
            {"error": "Plik za duży (max 5 MB)", "blocked": True},
            status_code=400,
        )

    pse_code = _next_pse()
    logger.info(f"[PREVIEW] {pse_code} — plik: {len(file.filename or '')} znaków")

    text, extract_err, ocr_meta = _extract_text(content, file.filename or "")
    if extract_err:
        # [FIX-LOG-400] Loguj przyczynę błędu ekstrakcji — bez tego 400
        # nie zostawia żadnego śladu poza kodem HTTP w access logu.
        logger.warning(f"[PREVIEW] {pse_code} — błąd ekstrakcji: {extract_err}")
        return JSONResponse(
            {"error": extract_err, "blocked": False, "ocr": ocr_meta},
            status_code=400,
        )

    text = text.strip()[:MAX_TEXT_CHARS]
    if not text:
        return JSONResponse(
            {"error": "Plik jest pusty lub nie zawiera tekstu", "blocked": False},
            status_code=400,
        )

    # [AUD-01] Token injection attack — odrzuć tekst zawierający tokeny maskujące.
    # Użytkownik mógłby wstrzyknąć FIRMA_001 i po depseudonimizacji podmienić go
    # na prawdziwą encję z mapy bieżącej sesji. Walidacja przed pipeline.
    if _TOKEN_RE.search(text):
        logger.warning("[PREVIEW] %s — odmowa: token injection w treści dokumentu", pse_code)
        return JSONResponse(
            {
                "error":   "Tekst wejściowy zawiera tokeny maskujące. Wyczyść tekst przed pseudonimizacją.",
                "blocked": True,
            },
            status_code=422,
        )

    # [OCR-REJECT] Odmowa przetwarzania gdy jakość OCR zbyt niska.
    # Empirycznie ustalone: conf < 70% → maskowanie katastrofalne (test 10.06.2026:
    # conf=66.7% → nazwisko niewykryte, IBAN rozpadł się, fałszywe encje).
    # Zwracamy 422 zamiast 400 — to nie błąd formatu, to świadoma odmowa.
    if ocr_meta and ocr_meta.get("quality") == "reject":
        logger.warning(
            f"[PREVIEW] {pse_code} — odmowa OCR: "
            f"conf={ocr_meta.get('confidence', 0):.1f}%"
        )
        return JSONResponse(
            {
                "error":   ocr_meta.get("warning", "Jakość OCR zbyt niska do maskowania."),
                "blocked": False,
                "ocr":     ocr_meta,
                "ocr_rejected": True,
            },
            status_code=422,
        )

    result        = pseudonymize_document(text, _app_state)
    anon_text     = result.text
    reverse_map   = result.reverse_map
    pseudo_err    = result.error
    guard_blocked = result.guard_blocked
    guard_reasons = result.guard_reasons

    tokens = []
    for token, original in reverse_map.items():
        prefix = token.split("_")[0] if "_" in token else "INNE"
        tokens.append({
            "token":    token,
            "original": original,
            "type":     prefix,
            "label":    _TYPE_LABELS.get(prefix, "Inne"),
        })
    tokens.sort(key=lambda t: (_TYPE_ORDER.get(t["type"], 9), t["token"]))

    record_preview(
        pse_code      = pse_code,
        original_text = text,
        anon_text     = anon_text,
        tokens        = tokens,
        guard_blocked = guard_blocked,
        guard_reasons = guard_reasons,
        error         = pseudo_err,
    )

    # [PSE-HEADER] Dodaj PSE kod jako pierwszy wiersz wyjscia —
    # Depseudonimizuj.tsx autodetektuje go i wie ktorej mapy uzyc.
    anon_text_with_pse = (
        f"[Dokument pseudonimizowany. Kod sesji: {pse_code}.\n"
        f"W odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n"
        f"{anon_text}"
    )

    return {
        "blocked":            guard_blocked,
        "error":              pseudo_err,
        "guard_reasons":      guard_reasons,
        "tokens":             tokens,
        "total":              len(tokens),
        "has_sensitive":      len(tokens) > 0,
        "anonymizer_active":  bool(_app_state.anonymizer and _app_state.spacy_ner_mod),
        "anonymized_preview": anon_text_with_pse,
        "original_text":      text,
        "ocr":                ocr_meta,
        "system_prompt":      SYSTEM_PROMPT_SECURITY if _GUARD_AVAILABLE else None,
        "pse_code":           pse_code,
    }


@app.post("/archive")
async def archive_save(request: Request):
    """
    Zapisuje zaszyfrowany blob mapy na dysku i tworzy rekord w SQLite.
    Szyfrowanie 100% po stronie klienta — backend nie widzi hasła ani danych.

    Body JSON: {pse, token_count, enc_blob, description?, guard_blocked?}
      enc_blob:      base64 — zaszyfrowana mapa sesji (AES-256-GCM, klient)
      description:   base64 — zaszyfrowany opis dokumentu (opcjonalne, klient)
      guard_blocked: bool — True jeśli output_guard zablokował sesję (CRIT-1)
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)

    pse      = str(body.get("pse", "")).strip()
    enc_blob = str(body.get("enc_blob", "")).strip()
    try:
        token_count = int(body.get("token_count") or 0)
    except (ValueError, TypeError):
        return JSONResponse({"error": "token_count musi być liczbą całkowitą"}, status_code=400)

    if not pse or not enc_blob:
        return JSONResponse({"error": "Brak wymaganych pól: pse, enc_blob"}, status_code=400)

    if not re.match(r"^PSE-\d{4}-\d{4}$", pse):
        return JSONResponse({"error": "Nieprawidłowy format PSE"}, status_code=400)

    try:
        blob_bytes = base64.b64decode(enc_blob)
    except Exception:
        return JSONResponse({"error": "enc_blob nie jest poprawnym base64"}, status_code=400)

    if len(blob_bytes) > MAX_BLOB_BYTES:
        return JSONResponse(
            {"error": f"Blob za duży (max {MAX_BLOB_BYTES // 1024} KB)"},
            status_code=400,
        )

    # [DB-STORE-2] description — opcjonalny zaszyfrowany blob opisu
    description_bytes = b""
    raw_desc = str(body.get("description", "")).strip()
    if raw_desc:
        try:
            description_bytes = base64.b64decode(raw_desc)
        except Exception:
            return JSONResponse({"error": "description nie jest poprawnym base64"}, status_code=400)

    # Zapis pliku .enc — atomowy przez .tmp
    enc_path = MAPS_DIR / f"{pse}.enc"
    tmp_path = enc_path.with_suffix(".tmp")
    try:
        tmp_path.write_bytes(blob_bytes)
        shutil.move(str(tmp_path), str(enc_path))
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.error(f"[ARCHIVE] Błąd zapisu pliku {pse}: {e}")
        return JSONResponse({"error": "Błąd zapisu pliku mapy"}, status_code=500)

    # [CRIT-1] Odbierz guard_blocked od klienta — zapis do DB, sprawdzany przy pobieraniu blobu
    guard_blocked_flag = bool(body.get("guard_blocked", False))

    # Zapis rekordu do SQLite przez db_store
    try:
        db_store.save(pse, token_count, description_bytes, guard_blocked=guard_blocked_flag)
    except Exception as e:
        logger.error(f"[ARCHIVE] Błąd zapisu DB {pse}: {e}")
        return JSONResponse({"error": "Błąd zapisu do bazy"}, status_code=500)

    db_store.record_audit(pse, "created")
    logger.info(f"[ARCHIVE] Zapisano: {pse} ({token_count} tokenów)")
    return {"ok": True, "pse": pse}


@app.get("/archive")
async def archive_list():
    """
    Zwraca listę dokumentów z archiwum.
    description zwracany jako base64 (zaszyfrowany blob — klient deszyfruje).
    """
    try:
        documents = db_store.list_documents()
        for doc in documents:
            doc["enc_exists"] = (MAPS_DIR / f"{doc['pse']}.enc").exists()
        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        logger.error(f"[ARCHIVE] Błąd odczytu listy: {e}")
        return JSONResponse({"error": "Błąd odczytu archiwum"}, status_code=500)


@app.get("/archive/{pse}/blob")
async def archive_get_blob(pse: str):
    """
    Zwraca zaszyfrowany blob mapy dla podanego PSE.
    Frontend deszyfruje lokalnie — backend nie widzi hasła.
    """
    if not re.match(r"^PSE-\d{4}-\d{4}$", pse):
        return JSONResponse({"error": "Nieprawidłowy format PSE"}, status_code=400)

    enc_path = MAPS_DIR / f"{pse}.enc"
    if not enc_path.exists():
        return JSONResponse({"error": f"Mapa {pse} nie istnieje"}, status_code=404)

    # [CRIT-1] Nie wydawaj blobu jeśli guard zablokował tę sesję
    if db_store.get_guard_blocked(pse):
        logger.warning(f"[ARCHIVE] Próba pobrania zablokowanego blobu: {pse}")
        return JSONResponse(
            {"error": "Sesja zablokowana przez guard — pobieranie niedozwolone"},
            status_code=403,
        )

    try:
        blob_bytes = enc_path.read_bytes()
        enc_blob   = base64.b64encode(blob_bytes).decode("ascii")
    except Exception as e:
        logger.error(f"[ARCHIVE] Błąd odczytu blobu {pse}: {e}")
        return JSONResponse({"error": "Błąd odczytu pliku mapy"}, status_code=500)

    db_store.record_audit(pse, "opened")
    return {"pse": pse, "enc_blob": enc_blob}


@app.delete("/archive/{pse}")
async def archive_delete(pse: str):
    """
    Usuwa rekord z SQLite i plik .enc z dysku.
    """
    if not re.match(r"^PSE-\d{4}-\d{4}$", pse):
        return JSONResponse({"error": "Nieprawidłowy format PSE"}, status_code=400)

    enc_path     = MAPS_DIR / f"{pse}.enc"
    file_deleted = False

    try:
        if enc_path.exists():
            enc_path.unlink()
            file_deleted = True
    except Exception as e:
        logger.error(f"[ARCHIVE] Błąd usuwania pliku {pse}: {e}")
        return JSONResponse({"error": "Błąd usuwania pliku mapy"}, status_code=500)

    try:
        db_store.delete(pse)
    except Exception as e:
        logger.error(f"[ARCHIVE] Błąd usuwania rekordu DB {pse}: {e}")
        return JSONResponse({"error": "Błąd usuwania z bazy"}, status_code=500)

    db_store.record_audit(pse, "deleted")
    logger.info(f"[ARCHIVE] Usunięto: {pse}")
    return {"ok": True, "pse": pse, "file_deleted": file_deleted}


@app.post("/archive/reencrypt")
async def archive_reencrypt(request: Request):
    """
    Atomowa zmiana hasła archiwum.
    Klient deszyfruje wszystkie mapy starym hasłem i szyfruje nowym.
    Body JSON: {blobs: [{pse, enc_blob}, ...]}
    """
    try:
        body = await request.json()
        blobs = body.get("blobs", [])
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)

    if not blobs:
        return JSONResponse({"error": "Brak blobów do zmiany hasła"}, status_code=400)

    tmp_files: list[tuple[Path, Path]] = []

    # Faza 1: zapisz wszystko jako .tmp
    try:
        for item in blobs:
            pse      = str(item.get("pse", "")).strip()
            enc_blob = str(item.get("enc_blob", "")).strip()

            if not re.match(r"^PSE-\d{4}-\d{4}$", pse):
                raise ValueError(f"Nieprawidłowy PSE: {pse}")

            blob_bytes = base64.b64decode(enc_blob)
            if len(blob_bytes) > MAX_BLOB_BYTES:
                raise ValueError(f"Blob dla {pse} za duży")

            final_path = MAPS_DIR / f"{pse}.enc"
            tmp_path   = MAPS_DIR / f"{pse}.tmp"
            tmp_path.write_bytes(blob_bytes)
            tmp_files.append((tmp_path, final_path))

    except Exception as e:
        for tmp_path, _ in tmp_files:
            tmp_path.unlink(missing_ok=True)
        logger.error(f"[ARCHIVE] Błąd reencrypt (faza 1): {e}")
        return JSONResponse({"error": f"Błąd przygotowania nowych kluczy: {e}"}, status_code=500)

    # Faza 2: atomowa podmiana .tmp → .enc
    try:
        for tmp_path, final_path in tmp_files:
            shutil.move(str(tmp_path), str(final_path))
    except Exception as e:
        for tmp_path, _ in tmp_files:
            tmp_path.unlink(missing_ok=True)
        logger.error(f"[ARCHIVE] Błąd reencrypt (faza 2): {e}")
        return JSONResponse({"error": "Błąd podmiany plików — stare hasło nadal aktywne"}, status_code=500)

    db_store.record_audit("ARCHIWUM", "password_changed")
    logger.info(f"[ARCHIVE] Zmiana hasła — {len(blobs)} pliki(ów) zaktualizowane")
    return {"ok": True, "updated": len(blobs)}


@app.get("/archive/audit")
async def archive_audit():
    """Zwraca log zdarzeń archiwum (bez PII)."""
    try:
        return {"log": db_store.list_audit()}
    except Exception as e:
        return JSONResponse({"error": f"Błąd odczytu logu: {e}"}, status_code=500)


# ── Export PDF ────────────────────────────────────────────────────────────────

try:
    from export_pdf import generate_pdf as _generate_pdf
    _EXPORT_PDF_AVAILABLE = True
    logger.info("[STARTUP] export_pdf załadowany")
except ImportError:
    _EXPORT_PDF_AVAILABLE = False
    logger.warning("[STARTUP] export_pdf niedostępny — endpoint /export-pdf wyłączony")


@app.post("/export-pdf")
async def export_pdf(request: Request):
    """
    Generuje PDF z pseudonimizowanego tekstu server-side.
    Metadane: author="", creator="" — brak wycieku loginu Windows.
    """
    if not _EXPORT_PDF_AVAILABLE:
        return JSONResponse(
            {"error": "PyMuPDF niedostępny — zainstaluj: pip install pymupdf"},
            status_code=503,
        )
    try:
        body     = await request.json()
        text     = body.get("text", "")
        filename = body.get("filename", "pseudonimizowany.pdf")

        if not text.strip():
            return JSONResponse({"error": "Brak tekstu do eksportu"}, status_code=400)

        pdf_bytes = _generate_pdf(text, filename)
        safe_name = filename.rsplit(".", 1)[0][:80] + "_anon.pdf"

        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        logger.error("[EXPORT-PDF] Błąd: %s", e)
        return JSONResponse({"error": f"Błąd generowania PDF: {e}"}, status_code=500)


# ── Profil biura ──────────────────────────────────────────────────────────────

@app.post("/profile/add-entity")
async def profile_add_entity(request: Request):
    """
    [VARIANT-A] Persystuje ręcznie dodaną encję do profilu biura (AnonymizerMap).
    Idempotentne — ta sama encja zwraca istniejący token_id.
    Body JSON: {text, token_type}
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)

    text       = str(body.get("text", "")).strip()
    token_type = str(body.get("token_type", "")).strip().upper()

    # [FIX-TRIE-TRIM] Przycinaj encję do pierwszej nowej linii lub tokenu PSE —
    # użytkownik mógł zaznaczyć za dużo tekstu (np. nazwę firmy + adres).
    # Obcinamy przy pierwszym \n, \r lub sekwencji TOKEN_xxx.
    import re as _re
    text = _re.split(r"[\n\r]|\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b", text)[0].strip()

    if not text:
        return JSONResponse({"error": "Brak pola text"}, status_code=400)
    if len(text) < 3:
        return JSONResponse({"error": "Encja zbyt krótka (min. 3 znaki)"}, status_code=400)
    # [BUG-NEW-4] Nie pozwól na dodanie słowa pospolitego lub skrótu systemowego
    from ner_blocklist import _NER_BLOCKLIST
    try:
        from spacy_ner import _PL_STOPWORDS
    except Exception:
        _PL_STOPWORDS = set()
    if text.lower() in _NER_BLOCKLIST or text.lower() in _PL_STOPWORDS:
        return JSONResponse(
            {"error": f"Słowo pospolite lub skrót systemowy: {text!r}"},
            status_code=400,
        )
    if token_type not in ("OSOBA", "FIRMA", "NUMER", "ADRES"):
        return JSONResponse(
            {"error": f"Nieznany typ tokenu: {token_type!r}"},
            status_code=400,
        )

    try:
        token_id = _app_state.anon_map.add_entity(text, token_type)
        logger.info("[PROFILE] Dodano encję [token_id=%s]", token_id)  # [MED-4] token_type usunięty z logu
        return {"ok": True, "token_id": token_id}
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"[PROFILE] Błąd add_entity: {e}")
        return JSONResponse({"error": "Błąd zapisu profilu"}, status_code=500)


@app.get("/profile/entities")
async def profile_list_entities():
    """
    [DICT-LIST] Zwraca listę wszystkich encji profilu biura.
    Response: {entries: [{token_id, value, type}]}
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)
    entries = _app_state.anon_map.list_entities()
    return {"entries": entries}


@app.delete("/profile/entity/{token_id}")
async def profile_delete_entity(token_id: str):
    """
    [DICT-DELETE] Usuwa encję z profilu biura po token_id.
    Response: {ok: true} lub 404.
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)
    removed = _app_state.anon_map.remove_entity(token_id)
    if not removed:
        return JSONResponse({"error": f"Encja {token_id!r} nie istnieje"}, status_code=404)
    logger.info(f"[DICT-DELETE] Usunięto encję {token_id}")
    return {"ok": True}


# ── Guard allowlist ────────────────────────────────────────────────────────────

def _guard_allowlist_path() -> "Path":
    from pathlib import Path as _Path
    profile_dir = Path(os.environ.get("PROFILE_DIR", Path.home() / ".pseudominizer" / "profile"))
    return profile_dir / "guard_allowlist.json"

def _load_guard_allowlist() -> list[str]:
    p = _guard_allowlist_path()
    if not p.exists():
        return []
    try:
        import json as _j
        return _j.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_guard_allowlist(entries: list[str]) -> None:
    import json as _j
    p = _guard_allowlist_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_j.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/profile/guard-allowlist")
async def guard_allowlist_list():
    """Zwraca listę fraz ignorowanych przez Guard."""
    return {"entries": _load_guard_allowlist()}


@app.post("/profile/guard-allowlist")
async def guard_allowlist_add(request: Request):
    """
    Dodaje frazę do allowlisty Guarda.
    Body: {phrase: str}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)
    phrase = str(body.get("phrase", "")).strip()
    if not phrase:
        return JSONResponse({"error": "Brak pola phrase"}, status_code=400)
    entries = _load_guard_allowlist()
    if phrase not in entries:
        entries.append(phrase)
        _save_guard_allowlist(entries)
    logger.info(f"[GUARD-ALLOWLIST] Dodano: {phrase!r}")
    return {"ok": True, "total": len(entries)}


@app.delete("/profile/guard-allowlist/{phrase}")
async def guard_allowlist_remove(phrase: str):
    """Usuwa frazę z allowlisty Guarda."""
    from urllib.parse import unquote
    phrase = unquote(phrase)
    entries = _load_guard_allowlist()
    if phrase not in entries:
        return JSONResponse({"error": "Fraza nie istnieje w allowliście"}, status_code=404)
    entries.remove(phrase)
    _save_guard_allowlist(entries)
    return {"ok": True}


@app.post("/preview-express")
async def preview_express(request: Request, file: UploadFile = File(...)):
    """Express Mode — pipeline bez SpaCy/NER (~5-10x szybszy).

    Maskuje: PESEL, NIP, REGON, dowód, paszport, IBAN, konta, email, telefon,
    sygnatury, kwoty, daty, numery zawodowe, instytucje, adresy.
    NIE maskuje: imion/nazwisk i nazw firm bez kontekstu słownikowego (brak NER).
    """
    from pipeline_new import run_pipeline_express

    content = await file.read()

    if len(content) > MAX_FILE_BYTES:
        return JSONResponse(
            {"error": "Plik za duży (max 5 MB)", "blocked": False},
            status_code=400,
        )

    pse_code = _next_pse()
    logger.info(f"[EXPRESS] {pse_code} — plik: {len(file.filename or '')} znaków")

    text, extract_err, ocr_meta = _extract_text(content, file.filename or "")
    if extract_err:
        logger.warning(f"[EXPRESS] {pse_code} — błąd ekstrakcji: {extract_err}")
        return JSONResponse(
            {"error": extract_err, "blocked": False, "ocr": ocr_meta},
            status_code=400,
        )

    text = text.strip()[:MAX_TEXT_CHARS]
    if not text:
        return JSONResponse(
            {"error": "Plik jest pusty lub nie zawiera tekstu", "blocked": False},
            status_code=400,
        )

    if _TOKEN_RE.search(text):
        logger.warning("[EXPRESS] %s — odmowa: token injection", pse_code)
        return JSONResponse(
            {
                "error":   "Tekst wejściowy zawiera tokeny maskujące. Wyczyść tekst przed pseudonimizacją.",
                "blocked": False,
            },
            status_code=422,
        )

    anon_text, reverse_map, _ = run_pipeline_express(
        text,
        _app_state.anon_map or {},
        _app_state.anonymizer,
    )

    tokens = []
    for token, original in reverse_map.items():
        prefix = token.split("_")[0] if "_" in token else "INNE"
        tokens.append({
            "token":    token,
            "original": original,
            "type":     prefix,
            "label":    _TYPE_LABELS.get(prefix, "Inne"),
        })
    tokens.sort(key=lambda t: (_TYPE_ORDER.get(t["type"], 9), t["token"]))

    anon_text_with_pse = (
        f"[Dokument pseudonimizowany (Express). Kod sesji: {pse_code}.\n"
        f"W odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n"
        f"{anon_text}"
    )

    return {
        "blocked":            False,
        "error":              None,
        "guard_reasons":      [],
        "tokens":             tokens,
        "total":              len(tokens),
        "has_sensitive":      len(tokens) > 0,
        "anonymized_preview": anon_text_with_pse,
        "original_text":      text,
        "ocr":                ocr_meta,
        "system_prompt":      SYSTEM_PROMPT_SECURITY if _GUARD_AVAILABLE else None,
        "pse_code":           pse_code,
        "express_mode":       True,
    }


@app.get("/profile/export-dict")
async def profile_export_dict():
    """
    [DICT-EXPORT] Zwraca bibliotekę encji profilu biura jako plik JSON (.lynxdict).
    Format: [{\"value\": \"...\", \"type\": \"...\"}]
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)

    import json as _json
    from fastapi.responses import Response

    entities = _app_state.anon_map.data.get("entities", {})
    entries = []
    for token_id, entity in entities.items():
        token_type = token_id.rsplit("_", 1)[0] if "_" in token_id else "INNE"
        entries.append({"value": entity["base"], "type": token_type})

    payload = _json.dumps(entries, ensure_ascii=False, indent=2)
    logger.info(f"[DICT-EXPORT] Eksport {len(entries)} encji")
    return Response(
        content=payload.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="slownik.lynxdict"'},
    )


@app.post("/profile/import-dict")
async def profile_import_dict(request: Request):
    """
    [DICT-IMPORT] Importuje encje z pliku .lynxdict (JSON array).
    Body JSON: {\"entries\": [{\"value\": \"...\", \"type\": \"...\"}]}
    Response: {\"added\": N, \"skipped\": M, \"total\": T}
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)

    entries = body.get("entries", [])
    if not isinstance(entries, list):
        return JSONResponse({"error": "Pole 'entries' musi być listą"}, status_code=400)

    existing_names = _app_state.anon_map.get_entity_names()
    added = 0
    skipped = 0

    VALID_TYPES = {"OSOBA", "FIRMA", "NUMER", "ADRES", "INSTYTUCJA", "EMAIL", "KWOTA"}

    for item in entries:
        value = str(item.get("value", "")).strip()
        token_type = str(item.get("type", "")).strip().upper()

        if not value or token_type not in VALID_TYPES:
            skipped += 1
            continue

        if value in existing_names:
            skipped += 1
            continue

        try:
            _app_state.anon_map.add_entity(value, token_type)
            existing_names.add(value)
            added += 1
        except Exception:
            skipped += 1

    total = len(_app_state.anon_map.data.get("entities", {}))
    logger.info(f"[DICT-IMPORT] Dodano: {added}, pominięto: {skipped}, razem w profilu: {total}")
    return {"added": added, "skipped": skipped, "total": total}


@app.post("/profile/reset")
async def profile_reset(request: Request):
    """
    [PROFILE-RESET] Usuwa WSZYSTKIE dane użytkownika. Nieodwracalne.
    Body JSON: {\"confirm\": true} — wymagane.
    Response: {\"ok\": true, \"deleted_sessions\": N}
    """
    if not _app_state.anon_map:
        return JSONResponse({"error": "Profil biura niedostępny"}, status_code=503)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Nieprawidłowy JSON"}, status_code=400)

    if not body.get("confirm"):
        return JSONResponse({"error": "Wymagane pole confirm: true"}, status_code=400)

    import glob as _glob
    from anonymizer import build_anonymizer as _build_anonymizer

    # 1. Policz i usuń sesje PSE z DB + pliki .enc
    docs = db_store.list_documents()
    deleted_sessions = 0
    for doc in docs:
        pse = doc["pse"]
        enc_path = MAPS_DIR / f"{pse}.enc"
        try:
            enc_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"[RESET] Nie można usunąć {enc_path}: {e}")
        try:
            db_store.delete(pse)
            deleted_sessions += 1
        except Exception as e:
            logger.warning(f"[RESET] Nie można usunąć DB {pse}: {e}")

    # 2. Usuń pozostałe pliki PSE-*.enc (na wypadek braku rekordu DB)
    for enc_file in _glob.glob(str(MAPS_DIR / "PSE-*.enc")):
        try:
            Path(enc_file).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"[RESET] Nie można usunąć pliku {enc_file}: {e}")

    # 3. Wyczyść bibliotekę encji — usuń mapa.enc i reinicjalizuj
    profile_path = Path(ANON_PROFILE_DIR)
    mapa_enc = profile_path / "mapa.enc"
    mapa_json = profile_path / "mapa.json"
    try:
        mapa_enc.unlink(missing_ok=True)
        mapa_json.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"[RESET] Nie można usunąć pliku mapy: {e}")

    # 4. Reinicjalizuj anon_map jako pusty obiekt
    try:
        _, _, _app_state.anon_map, _app_state.morf_env = \
            _build_anonymizer(ANON_PROFILE_DIR, HARDWARE_PROFILE)
        logger.info(f"[RESET] Profil zreinicjalizowany po resecie")
    except Exception as e:
        logger.error(f"[RESET] Błąd reinicjalizacji profilu: {e}")
        return JSONResponse({"error": f"Reset częściowy — błąd reinicjalizacji: {e}"}, status_code=500)

    db_store.record_audit("PROFIL", "reset")
    logger.info(f"[RESET] Usunięto {deleted_sessions} sesji. Profil wyczyszczony.")
    return {"ok": True, "deleted_sessions": deleted_sessions}


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    if FRONTEND_FILE.exists():
        return FileResponse(FRONTEND_FILE, media_type="text/html")
    return JSONResponse({"error": "pseudominizer.html nie znaleziony"}, status_code=404)


# ── Uruchomienie ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "pseudominizer_api:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
