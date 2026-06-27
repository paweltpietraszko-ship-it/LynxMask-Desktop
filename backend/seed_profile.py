"""
seed_profile.py  v1.0
Seeduje profil trie przy pierwszym starcie aplikacji.

Ładuje z plików JSON wbudowanych w pakiet:
  - names_inflected.json   → OSOBA (imiona + odmiany)
  - surnames_top1000.json  → OSOBA (nazwiska + odmiany)

Miasta, ulice i placówki medyczne trafiają do ner_blocklist (nie do trie)
bo trie maskuje encje niezależnie od kontekstu — "Leśna" w środku zdania
byłoby traktowane jak osoba. Blocklist chroni przed FP SpaCy, co jest
wystarczające: adres jako całość i tak łapie warstwa address.

Wywoływany raz przy starcie jeśli profil pusty lub wersja seedu nieaktualna.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("lynxmask.seed_profile")

_BACKEND_DIR = Path(__file__).parent
_SEED_VERSION = "v1.0"
_SEED_VERSION_KEY = "__seed_version__"


def _load_json(name: str) -> object:
    path = _BACKEND_DIR / name
    if not path.exists():
        logger.warning("[SEED] Brak pliku: %s", path)
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_if_needed(anon_map) -> bool:
    """
    Zwraca True jeśli seedowanie zostało wykonane.
    anon_map: AnonymizerMap z anonymizer.py
    """
    if anon_map is None:
        return False

    current = anon_map.data.get(_SEED_VERSION_KEY, "")
    if current == _SEED_VERSION:
        logger.info("[SEED] Profil aktualny (%s), pomijam.", _SEED_VERSION)
        return False

    logger.info("[SEED] Seeduję profil (%s → %s)…", current or "brak", _SEED_VERSION)
    _do_seed(anon_map)

    anon_map.data[_SEED_VERSION_KEY] = _SEED_VERSION
    anon_map._save()
    logger.info("[SEED] Gotowe.")
    return True


def _do_seed(anon_map) -> None:
    entries: list[tuple[str, str]] = []

    # ── Imiona ────────────────────────────────────────────────────────────────
    names = _load_json("names_inflected.json")
    if isinstance(names, dict):
        for base, forms in names.items():
            all_forms = set([base] + (forms if isinstance(forms, list) else []))
            for f in all_forms:
                if f.strip():
                    entries.append((f.strip(), "OSOBA"))
        logger.info("[SEED] Imiona: %d wpisów", len(entries))

    # ── Nazwiska ──────────────────────────────────────────────────────────────
    before = len(entries)
    surnames = _load_json("surnames_top1000.json")
    if isinstance(surnames, dict):
        for base, forms in surnames.items():
            all_forms = set([base] + (forms if isinstance(forms, list) else []))
            for f in all_forms:
                if f.strip():
                    entries.append((f.strip(), "OSOBA"))
        logger.info("[SEED] Nazwiska: %d wpisów", len(entries) - before)

    if not entries:
        logger.warning("[SEED] Brak danych do seedowania.")
        return

    # add_entities_batch obsługuje deduplication i buduje trie
    result = anon_map.add_entities_batch(entries)
    logger.info("[SEED] Dodano %d tokenów do trie.", len(result))
