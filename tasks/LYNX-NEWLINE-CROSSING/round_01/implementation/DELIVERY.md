# LYNX-NEWLINE-CROSSING — DELIVERY round_01

BEFORE_SHA (gate): `cbfa3c1` (synchronizacja z main na starcie; brief `d6cebef`) · IMPLEMENTATION_SHA: `2619eabfc7382278b8e9111002ba1923625ba495`
Pliki: TASK_SCOPE (`layers/ocr_normalizer.py`, `layers/contact.py`, `tests/test_layers.py`) + ROZSZERZENIE CC E1 `layers/identity.py` (w briefie `0729124` przed kodem — pierwszy błędny etap dla reproduktora NIP).

## Ustalenie pierwszego etapu (trace warstwa po warstwie, NER wyłączony)
- e-mail\ne-mail → `ocr_normalizer._EMAIL_SPACE_BEFORE_AT_DOT` (`\s+`, grupa 1 bez lewej granicy łapie domenę poprzedniego adresu).
- NIP\ntelefon → `identity`: wzorzec NIP 3-2-2-3 z `anonymizer_init.STRUCTURAL_PATTERNS` (`[-\s]?`, lewa granica tylko `(?<!\d)`) bierze „000-12-46\n512” (start po „526-”); potem `contact` bierze „001 987 654” startując w cyfrach tokenu.
- PESEL\ntelefon → `contact`: telefon „001\n512 987” z cyfr tokenu przez `\n`.
- Nowe, ta sama klasa: PESEL\n„Tel.”/„Opis” → `ocr_normalizer._PESEL_SPLIT_RE` (wnętrze `\s`) zjada pierwszą literę następnej linii („7el.”, „0pis”).

## Co zrobione
- `contact.line_matches(pattern, text)`: wzorce LICZBOWE dopasowywane w obrębie jednej linii i odrzucane, gdy start leży w cyfrach tokenu (`…_\d*`) albo tuż po „cyfra-”. Użyte w `contact` (telefony: kontekstowy, 3-2-2, STRUCTURAL NUMER) i `identity` (wszystkie wzorce identity). E-mail (`_EMAIL_OCR_RE`, STRUCTURAL EMAIL) bez zmian — OCR-newline przy `@` zachowany. Wzorce `anonymizer_init` bez zmian.
- `ocr_normalizer` (bez nowych linii, 696): `_EMAIL_SPACE_BEFORE_AT_DOT/_DIGITS` — odstęp `[^\S\n]+` + lewa granica `(?<![\w.@%+-])`; `_PESEL_SPLIT_RE` — wnętrze numeru `[ \t]` (separator po etykiecie nadal może przejść przez `\n`); `_PHONE_AFTER_KW_RE` — wnętrze numeru bez `\n`.

## Dowody
- `implementation/line_pairs_sweep.py` (z `backend/`): 12 typowych wartości tabel (e-maile, telefon z/bez etykiet, NIP z/bez, PESEL z/bez, IBAN, kwota, tekst) → 132 uporządkowane pary × full/Express; kontrola: liczba linii, token w tokenie, wartość-token w mapie, jawne fragmenty, etykiety po Przywróć. **Przed: 16 problemów (12 granica/token, 4 zjedzona litera następnej linii), po: 0.**
- Regresje — wcześniejsze przeglądy na finalnym kodzie: `phone_sweep` 30 000 (0 regresji, 0 zmienionych słów), `number_sweep` 724 (0 regresji), `iban_sweep` 420 (0 regresji, 0 wycieków), `email_sweep` 1980 (0 regresji, 0 jawnych fragmentów).
- Zachowane OCR wewnątrz jednej encji: „jan@\nexample.pl”, „jan\n@example.pl” → jeden EMAIL (full/Express); „PESEL:\n44051401359” → NUMER. Zmiana zachowania (świadoma): „Tel.:\n512 987 654” — przed: etykieta+\n+numer w jednym tokenie, po: numer tokenem, etykieta jawna w swojej linii (nie PII).
- Testy `test_layers.py::TestNewlineCrossing` (7 par w obu trybach: 2 linie, 2 tokeny, brak tokenu w tokenie; normalizator nie rusza następnej linii ×2; OCR-newline w e-mailu ×2). Na bazie: 6 FAIL, teraz zielone. `test_layers.py` `94 passed`; `test_audyt` + `test_engine_quality_layout` `139 passed, 10 xfailed`; pełna suita `129 passed, 40 skipped, 1 xfailed` (0 failed). Autotesty: ocr_normalizer 40/40, contact 16/16, identity 15/15.

## Znane, poza zakresem (F3 / istniejące)
- IBAN rozbity nową linią po etykiecie („…0000\n0712…”) — maskowany w całości, ale spacja przed następnym słowem zjadana (normalizacja IBAN newline, przed tym Taskiem).
- „PESEL:\n…” → „PESEL: NUMER” (normalizator kanonizuje etykietę; F3).

## gate.py (stdout dosłownie)
```
STATUS: PASS
HEAD_SHA: 2619eabfc7382278b8e9111002ba1923625ba495
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - backend\ner_layer.py
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\implementation\phone_sweep.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r4_repro.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r5_repro.py
  - tasks\LYNX-IBAN-FOREIGN-ALNUM\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-EMAIL-LOCALPART-OCR\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-EMAIL-LOCALPART-OCR\round_01\tests\tests_r7_repro.py
  - backend\tests\test_audyt_2026_10.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-NEWLINE-CROSSING/round_01/implementation/line_pairs_sweep.py
  - tasks/LYNX-NEWLINE-CROSSING/brief.md
```

## Następny krok (osobna decyzja)
Po merge: aktualizacja WIP `task/LYNX-DOCX-TABLES` na nowym main, ponowienie czerwonych testów integracyjnych tabel i oddanie Codexowi.
