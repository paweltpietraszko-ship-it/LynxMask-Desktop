# LYNX-XPASS-MARKERS — zdjęcie 3 markerów xfail po LYNX-FAILCLOSED-S3

STATUS: drobna poprawka mechaniczna (CLAUDE.md: gate PASS + Codex PASS wystarcza). Polecenie Pawła: „zdejmij markery”.
POCHODZENIE: LYNX-FAILCLOSED-S3 (merge `627569a`) naprawił BUG-EXPRESS-FAIL-OPEN, BUG-GUARD-MAPLEAK-UNREDACTED, BUG-ALLOWLIST-SUBSTRING; ich reproduktory w `test_audyt_2026_10.py` dają XPASS(strict) = „failed”. Plik był wtedy OUT_OF_SCOPE (brief FAILCLOSED), więc markery zostały na osobny krok.

## Zmiana
Trzy dekoratory `@pytest.mark.xfail(strict=True, ...)` zastąpione komentarzem `# BUG-… — naprawione w LYNX-FAILCLOSED-S3 (xfail zdjęty).` — wzór jak dla wcześniej naprawionych BUG-ów w tym pliku. Treść testów bez zmian.

TASK_SCOPE:
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: kod produktu, inne markery xfail (pozostałe 7 nadal wykrywają realne błędy).

## Falsyfikacja
`cd backend && py -3 -m pytest tests/test_audyt_2026_10.py -q`: przed 131 passed / 7 xfailed / 3 failed (XPASS strict) → po 134 passed / 7 xfailed / 0 failed.
