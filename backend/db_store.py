"""
db_store.py  v1.0
Historia zmian (od najnowszej):
  v1.0 (2026-05-19): Wydzielony z pseudominizer_api.py.
    Izoluje wszystkie operacje SQLite — _api.py nie importuje sqlite3 bezpośrednio.
    Nowy schemat: dodano kolumnę description BLOB.
    description = blob zaszyfrowany po stronie klienta (ten sam model co enc_blob w mapach).
    Backend trzyma nieprzezroczysty blob — nigdy nie widzi plaintext opisu.
    RODO Art. 25: jedyne PII potencjalnie w bazie (opis) zaszyfrowane przed zapisem.
    Migracja addytywna: stary schemat bez description → ALTER TABLE ADD COLUMN.
    Migracja z filename: DROP TABLE (dane testowe, nie produkcyjne).

Schemat docelowy tej wersji:
  documents:  pse, description BLOB, token_count, created_at
  audit_log:  id, pse, action, timestamp

Uwaga: map_blob (przeniesienie .enc z dysku do DB) planowane przy budowie Biblioteki (v2).
"""

import sqlite3
import threading
import logging
import base64
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pseudominizer.db_store")

_db_lock = threading.Lock()
_DB_PATH: Path | None = None


# ── Inicjalizacja ─────────────────────────────────────────────────────────────

def init(db_path: Path) -> None:
    """
    Inicjalizuje bazę: tworzy katalog, uruchamia migrację, tworzy tabele.
    Wywoływane raz przy starcie serwera.
    """
    global _DB_PATH
    _DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _migrate(db_path)
    _create_tables(db_path)
    logger.info(f"[DB] Zainicjowana: {db_path}")


def _migrate(db_path: Path) -> None:
    """
    Migracje schematu — bezpieczne, addytywne.
    Kolejność: najpierw destruktywne (filename → DROP), potem addytywne (ADD COLUMN).
    """
    if not db_path.exists():
        return
    try:
        with sqlite3.connect(db_path) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]

            # Migracja z pre-v1.22: kolumna filename to PII — upuść tabelę (dane testowe)
            if "filename" in cols:
                conn.execute("DROP TABLE documents")
                conn.commit()
                logger.info("[DB] Migracja: DROP TABLE documents (stary schemat z filename)")
                cols = []

            # Migracja do v1.0 db_store: dodaj description jeśli tabela istnieje bez niej
            if cols and "description" not in cols:
                conn.execute(
                    "ALTER TABLE documents ADD COLUMN description BLOB NOT NULL DEFAULT ''"
                )
                conn.commit()
                logger.info("[DB] Migracja: ADD COLUMN description")

    except Exception as e:
        logger.warning(f"[DB] Błąd migracji: {e}")


def _create_tables(db_path: Path) -> None:
    """Tworzy tabele jeśli nie istnieją. Idempotentne."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                pse          TEXT PRIMARY KEY,
                description  BLOB NOT NULL DEFAULT '',
                token_count  INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pse          TEXT NOT NULL,
                action       TEXT NOT NULL,
                timestamp    TEXT NOT NULL
            )
        """)
        conn.commit()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def save(pse: str, token_count: int, description: bytes = b"") -> str:
    """
    Zapisuje lub nadpisuje rekord dokumentu.
    description: zaszyfrowany blob przesłany przez klienta — backend nie interpretuje.
    Zwraca created_at (ISO string).
    """
    _assert_init()
    created_at = datetime.now().isoformat(timespec="seconds")
    with _db_lock:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO documents (pse, description, token_count, created_at)
                   VALUES (?,?,?,?)""",
                (pse, description, token_count, created_at)
            )
            conn.commit()
    return created_at


def list_documents() -> list[dict]:
    """
    Zwraca wszystkie rekordy z documents.
    description zwracany jako base64 string (zaszyfrowany blob — bez dekodowania).
    """
    _assert_init()
    with _db_lock:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT pse, description, token_count, created_at "
                "FROM documents ORDER BY created_at DESC"
            ).fetchall()
    result = []
    for r in rows:
        rec = dict(r)
        # description jest BLOB (bytes) — zakoduj do base64 dla JSON
        desc_bytes = rec["description"] or b""
        rec["description"] = base64.b64encode(desc_bytes).decode("ascii") if desc_bytes else ""
        result.append(rec)
    return result


def delete(pse: str) -> None:
    """Usuwa rekord dokumentu z bazy."""
    _assert_init()
    with _db_lock:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("DELETE FROM documents WHERE pse = ?", (pse,))
            conn.commit()


# ── Audit ─────────────────────────────────────────────────────────────────────

def record_audit(pse: str, action: str) -> None:
    """
    Zapisuje zdarzenie do audit_log.
    Zero PII — tylko PSE + akcja + timestamp.
    Dowód staranności RODO Art. 25.
    """
    _assert_init()
    ts = datetime.now().isoformat(timespec="seconds")
    try:
        with _db_lock:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO audit_log (pse, action, timestamp) VALUES (?,?,?)",
                    (pse, action, ts)
                )
                conn.commit()
    except Exception as e:
        logger.warning(f"[AUDIT] Błąd zapisu: {e}")


def list_audit(limit: int = 200) -> list[dict]:
    """Zwraca log audytu (bez PII)."""
    _assert_init()
    with _db_lock:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT pse, action, timestamp FROM audit_log "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


# ── Pomocnicze ────────────────────────────────────────────────────────────────

def _assert_init() -> None:
    if _DB_PATH is None:
        raise RuntimeError("db_store.init() nie zostało wywołane przed użyciem bazy")
