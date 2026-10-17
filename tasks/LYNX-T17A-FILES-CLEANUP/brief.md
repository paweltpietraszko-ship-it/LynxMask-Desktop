# LYNX-T17A-FILES-CLEANUP — usunięcie plików bez odwołań

STATUS: wąski wycinek T17 (`arch/PLAN_2026-10.md` pkt 16 — odrzucony jako refaktor). Ten wycinek wykonany na wyraźne polecenie Pawła po przedstawieniu oceny CC i wcześniejszego odrzucenia architekta (2026-10-17: „usuwaj wszystko co zbędne w repo … przyjmuję to ryzyko”). Kod produktu bez zmian.
FINDING: `arch/FINDING_2026-10_AUDYT.md` §5 „Stare pliki” / „Duplikaty”.

TASK_SCOPE:
- backend/python
- backend/package.json
- backend/package-lock.json
- backend/tsconfig.json
- backend/URUCHOMIENIE.md
- backend/RAPORT_Coverage_Fix.txt
- backend/gus_simc.zip
- backend/test_docs/doc_test_guard.txt
- backend/test_docs/doc_test_nowe_encje.txt
- PROJEKT_KONTEKST.md
- CLAUDE.md
- AGENTS.md

OUT_OF_SCOPE: martwy kod `pipeline.py`/`anonymizer.py`, `backend/*.html` (wymaga zmiany API), `MASTER_*`/`MAPA_*`, `ocr_testy/`, launchery .bat/.vbs, historyczne wzmianki w `arch/` i `tasks/`.

## Kryteria PASS
1. Każdy usunięty plik: 0 trafień `git grep` w *.py/*.bat/*.vbs/*.sh/*.ts/*.tsx/*.rs/*.json/*.ini.
2. `backend/test_docs/*` bajtowo identyczne z `Pliki testowe/` (przed usunięciem).
3. Suita bez zmian względem main (8 failed na main sprzed T12: IBAN-RECEPTA + 7 archiwum).
4. Docs: odwołania `backend/test_docs/` w PROJEKT_KONTEKST/CLAUDE/AGENTS zamienione na `Pliki testowe/`.
