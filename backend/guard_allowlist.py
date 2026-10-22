"""guard_allowlist.py — [LYNX-GUARD-ALLOWLIST-S5] trwałe „Zawsze jawne” dla ŻÓŁTYCH ostrzeżeń Guarda (S4/S5).

Wpis = para (fragment, reguła) jak w Mobile `GuardAllowlist.kt`; reguła `*` = stary jawny wpis (dowolna żółta reguła).
Plik `guard_allowlist.enc` w profilu anonimizatora, AES-256-GCM kluczem profilu (`anonymizer_crypto`). RED (HIGH, MAP_LEAK)
nigdy nie trafia na listę i nigdy nie jest wyciszany. Uszkodzony plik: odczyt = pusta lista, zapis odmawia, `clear` naprawia.
Logi bez wartości (S5)."""
import json
import logging
import os
from pathlib import Path

import anonymizer_crypto as _crypto

logger = logging.getLogger(__name__)

MAX_ENTRIES = 500
ANY_YELLOW = "*"
_RED = ("HIGH", "MAP_LEAK")


class AllowlistError(Exception):
    """Odmowa zapisu z komunikatem dla użytkownika (co zrobić dalej) i kodem HTTP."""

    def __init__(self, msg: str, status: int):
        super().__init__(msg)
        self.status = status


def is_red(rule: str) -> bool:
    return rule.startswith(_RED)


def _profile_dir() -> Path:
    return Path(os.getenv("ANONYMIZER_PROFILE_DIR", str(Path(__file__).parent / "anon_profiles" / "pseudominizer")))


def _enc_path() -> Path:
    return _profile_dir() / "guard_allowlist.enc"


def _legacy_paths() -> list[Path]:
    """Stary jawny `guard_allowlist.json` (przed S5)."""
    return [Path(os.environ.get("PROFILE_DIR", str(Path.home() / ".pseudominizer" / "profile"))) / "guard_allowlist.json"]


def paths() -> list[Path]:
    """Wszystkie pliki listy (reset profilu)."""
    return [_enc_path(), *_legacy_paths()]


def _key() -> bytes:
    return _crypto.get_or_create_keys(_profile_dir())[0]


def _save(entries: list[tuple[str, str]]) -> None:
    path = _enc_path()
    if not entries:
        path.unlink(missing_ok=True)
        return
    data = {"v": 1, "entries": [{"value": v, "rule": r} for v, r in entries]}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(_crypto.encrypt_map(data, _key()))
    os.replace(tmp, path)


def _migrate() -> None:
    """Jawny plik → wpisy `*` w zaszyfrowanym; jawny usuwany dopiero po udanym zapisie (nieczytelny — usuwany od razu)."""
    for old in _legacy_paths():
        if not old.exists():
            continue
        try:
            values = [v.strip() for v in json.loads(old.read_text(encoding="utf-8")) if isinstance(v, str) and v.strip()]
        except Exception:
            logger.warning("[GUARD-ALLOWLIST] Nieczytelny stary plik wyjątków — usunięty")
            old.unlink(missing_ok=True)
            continue
        entries, damaged = _read()
        if damaged:
            return
        for v in values:
            if not _has(entries, v, ANY_YELLOW) and len(entries) < MAX_ENTRIES:
                entries.append((v, ANY_YELLOW))
        _save(entries)
        old.unlink(missing_ok=True)
        logger.info("[GUARD-ALLOWLIST] Przeniesiono %d starych wpisów do zaszyfrowanej listy", len(values))


def _read() -> tuple[list[tuple[str, str]], bool]:
    """(wpisy, uszkodzony)."""
    path = _enc_path()
    if not path.exists():
        return [], False
    try:
        data = _crypto.decrypt_map(path.read_bytes(), _key())
        return [(e["value"], e["rule"]) for e in data["entries"]], False
    except Exception as e:
        logger.warning("[GUARD-ALLOWLIST] Nie można odczytać listy wyjątków: %s", type(e).__name__)
        return [], True


def _has(entries, value: str, rule: str) -> bool:
    v = value.strip().casefold()
    return any(ev.casefold() == v and er == rule for ev, er in entries)


def state() -> tuple[list[tuple[str, str]], bool]:
    """(wpisy, uszkodzony) po migracji starego pliku."""
    try:
        _migrate()
    except Exception as e:
        logger.warning("[GUARD-ALLOWLIST] Migracja nieudana: %s", type(e).__name__)
    return _read()


def load() -> list[tuple[str, str]]:
    return state()[0]


def _writable() -> list[tuple[str, str]]:
    entries, damaged = state()
    if damaged:
        raise AllowlistError("Lista wyjątków jest uszkodzona — wyczyść ją w Ustawieniach → Wyjątki Guard.", 409)
    return entries


def add(value: str, rules: list[str]) -> int:
    value = value.strip()
    rules = [r for r in dict.fromkeys(rules) if isinstance(r, str) and r]
    if not value or not rules:
        raise AllowlistError("Brak fragmentu albo reguły.", 400)
    if any(is_red(r) or r == ANY_YELLOW for r in rules):
        raise AllowlistError("Czerwonych ostrzeżeń nie można zapamiętać jako „Zawsze jawne”.", 400)
    entries = _writable()
    new = [(value, r) for r in rules if not _has(entries, value, r)]
    if len(entries) + len(new) > MAX_ENTRIES:
        raise AllowlistError("Lista wyjątków jest pełna (500) — usuń stare wpisy w Ustawieniach → Wyjątki Guard.", 400)
    _save(entries + new)
    logger.info("[GUARD-ALLOWLIST] Dodano wyjątek [len=%d, reguł=%d]", len(value), len(new))
    return len(entries) + len(new)


def remove(value: str, rule: str) -> bool:
    entries = _writable()
    v = value.strip().casefold()
    kept = [(ev, er) for ev, er in entries if not (ev.casefold() == v and er == rule)]
    if len(kept) == len(entries):
        return False
    _save(kept)
    return True


def clear() -> None:
    """Usuwa tylko listę wyjątków (także uszkodzoną); mapa, słownik i keystore bez zmian."""
    for p in paths():
        p.unlink(missing_ok=True)


def silenced(fragment: str, rule: str, entries: list[tuple[str, str]]) -> bool:
    """Czy trafienie (fragment, reguła) jest wyciszone; RED — nigdy."""
    return not is_red(rule) and (_has(entries, fragment, rule) or _has(entries, fragment, ANY_YELLOW))
