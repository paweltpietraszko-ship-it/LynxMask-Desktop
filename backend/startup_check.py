"""
startup_check.py — [LYNX-STARTUP-COMPONENTS] próby funkcjonalne każdego elementu ochrony przy starcie.

Paweł 2026-10-18: program nie może startować z fałszywym poczuciem, że wszystko działa.
Każda próba działa na syntetyku (nie sam import). Którakolwiek nie przejdzie → start zablokowany (_lifespan).
Brak trybu „degraded”. Profil użytkownika nie jest dotykany: próba profilu działa na izolowanym
profilu tymczasowym. Komunikaty i logi bez treści wyjątków (S5) — tylko nazwa elementu i typ wyjątku.
"""
from __future__ import annotations

import ctypes
import logging
import shutil
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("lynxmask.startup_check")

# Syntetyk: nazwisko musi być znane Morfeuszowi (zmyślone daje tylko formę podstawową → fałszywa porażka).
_NAME = "Jan Kowalski"
_NAME_INFLECTED = "Jana Kowalskiego"
_SURNAME = "Kowalski"
_SURNAME_GEN = "Kowalskiego"
_PESEL = "44051401359"  # syntetyczny, poprawna suma kontrolna


def _check_pipeline(state, guard_available, crypto_ok) -> bool:
    from smoke_test import run_smoke_test
    ok, _errors = run_smoke_test()
    return ok


def _check_guard(state, guard_available, crypto_ok) -> bool:
    from output_guard import guard_output, guard_output_with_map, GuardMode
    if not guard_available:
        return False
    hit = guard_output(f"Numer PESEL {_PESEL} w treści.", GuardMode.REDACT)
    if not (hit.blocked and hit.high_hit) or any("GUARD_ERROR" in r for r in hit.reasons):
        return False
    leak = guard_output_with_map(f"Pozew złożył {_NAME}.", None, mode=GuardMode.REDACT, known_plain=[_NAME])
    return leak.blocked and not leak.error and any("MAP_LEAK" in r for r in leak.reasons)


def _check_crypto(state, guard_available, crypto_ok) -> bool:
    return bool(crypto_ok)


def _check_ner(state, guard_available, crypto_ok) -> bool:
    mod = state.spacy_ner_mod
    if mod is None:
        return False
    found = mod.detect_entities(f"Pozew złożył {_NAME} z Krakowa.")  # ładuje model teraz, nie przy 1. dokumencie
    return any(e.label == mod.TOKEN_OSOBA and _SURNAME in e.text for e in found)


def _check_morfeusz(state, guard_available, crypto_ok) -> bool:
    from anonymizer import MorfEnv
    env = state.morf_env
    if env is None or env.mode not in (MorfEnv.NATIVE, MorfEnv.WSL2):
        return False
    return _SURNAME_GEN in env.get_forms(_SURNAME)  # dowód odmiany, nie wpis w cache


def _check_profile(state, guard_available, crypto_ok) -> bool:
    if state.anonymizer is None or state.morf_env is None:  # profil użytkownika wczytany przez build_anonymizer
        return False
    from anonymizer import AnonymizerMap, Anonymizer
    tmp = Path(tempfile.mkdtemp(prefix="lynx_startup_"))
    try:
        probe = AnonymizerMap(tmp / "profil", state.morf_env)  # izolowany profil z własnym keystore
        token = probe.add_entity(_NAME, "OSOBA")
        out, _ = Anonymizer(probe)._layer1_trie(f"Wezwano {_NAME_INFLECTED} na rozprawę.", {})
        return token in out and _SURNAME[:6] not in out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _check_herbert(state, guard_available, crypto_ok) -> bool:
    """[LYNX-HERBERT-NET] tylko gdy siatka włączona: model ładuje się i wykrywa osobę w syntetyku (off → nie dotyczy)."""
    import herbert_net
    if not herbert_net.enabled():
        return True
    return any(kind == "PER" for _, _, kind, _ in herbert_net.detect(f"Umowę podpisał {_NAME} w Krakowie."))


_CHECKS = (
    ("maskowanie numerów i adresów", _check_pipeline),
    ("Output Guard", _check_guard),
    ("szyfrowanie", _check_crypto),
    ("rozpoznawanie osób (SpaCy)", _check_ner),
    ("odmiana nazw (Morfeusz)", _check_morfeusz),
    ("profil biura", _check_profile),
    ("dodatkowa kontrola HerBERT", _check_herbert),
)


def keep_full_speed() -> bool:
    """[LYNX-PHOTO-CHAIN] Windows 11 spowalnia proces w tle bez okna (EcoQoS) ~3–4× po kilku sekundach pracy —
    silnik uruchamiany ikoną jest takim procesem (zmierzone 20.10: PP 7–8 s → 2,2–3,8 s/str.). Wyłącza to tylko dla
    tego procesu; poza Windows nic nie robi. Niepowodzenie nie blokuje startu (to wydajność, nie ochrona)."""
    if sys.platform != "win32":
        return False

    class _Throttling(ctypes.Structure):   # PROCESS_POWER_THROTTLING_STATE
        _fields_ = [("Version", ctypes.c_ulong), ("ControlMask", ctypes.c_ulong), ("StateMask", ctypes.c_ulong)]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
    state = _Throttling(1, 0x1 | 0x4, 0)   # EXECUTION_SPEED | IGNORE_TIMER_RESOLUTION, stan 0 = bez dławienia
    ok = bool(k32.SetProcessInformation(k32.GetCurrentProcess(), 4, ctypes.byref(state), ctypes.sizeof(state)))
    logger.info("[STARTUP] pełna szybkość procesu (bez EcoQoS): %s", "OK" if ok else "niedostępne")
    return ok


def run(state, guard_available: bool, crypto_ok: bool) -> list[str]:
    """Zwraca nazwy elementów, które NIE przeszły próby (pusta lista = wszystko działa)."""
    keep_full_speed()
    failed = []
    for name, check in _CHECKS:
        try:
            ok = check(state, guard_available, crypto_ok)
        except Exception as e:
            logger.error("[STARTUP] próba „%s”: wyjątek %s", name, type(e).__name__)
            ok = False
        if not ok:
            failed.append(name)
    if failed:
        logger.critical("[STARTUP] nie przeszły próby: %s — start zablokowany", ", ".join(failed))
    else:
        logger.info("[STARTUP] próby OK: %s", ", ".join(n for n, _ in _CHECKS))
    return failed
