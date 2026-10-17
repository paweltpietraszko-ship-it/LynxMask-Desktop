# LYNX-EMAIL-LOCALPART-OCR — DELIVERY round_01

BEFORE_SHA: `5dd5c6ece1ebb511695c763524d5193f00a2b944` · IMPLEMENTATION_SHA: `fc75f1410c865acaa74e4ca2c9058aa81b16b5ed`
Pliki (TASK_SCOPE): `backend/layers/contact.py`, `backend/tests/test_layers.py`, `backend/tests/test_audyt_2026_10.py`. Rozszerzenia CC: brak.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED): `_EMAIL_OCR_RE` używany tylko w `apply_contact_layer`; contact działa w obu trybach przed NER, więc punktowa zmiana wzorca wystarcza (bez przesuwania normalizatora/warstw). `_normalize_email` nie usuwa spacji w lokalnej części, więc wartość w mapie zostaje oryginalnym zapisem → Przywróć znak w znak.

## Co zrobione
- `_EMAIL_OCR_RE`: opcjonalny początek lokalnej części z OCR-ową spacją po kropce — `(?<![\w.])` + małe litery/cyfry ASCII od początku słowa (`(?-i:…)`, bo wzorzec ma IGNORECASE) + `.` + 1–2 spacje/taby, z lookaheadem na resztę lokalnej części aż do `@`/`©`. Ta sama granica co T11 F1: „Kontakt. jan@…”, „Podpisano. Jan@…” — kropka kończy zdanie, nie wchodzi do adresu.
- Bez zmian: domena/TLD (granica T11 E1), reguła T07 (`cuts_long_number` dotyczy tylko NUMER), kolejność warstw, Guard.

## Dowody
- Reproduktor z briefu, oba tryby: „Kontakt: anna. nowak@example.pl. Termin płatności.” → „Kontakt: EMAIL_001. Termin płatności.”, `{EMAIL_001: "anna. nowak@example.pl"}`, Przywróć (`unmask_sim`) = wejście znak w znak; przed: „Kontakt: anna. EMAIL_001…” (fragment jawny).
- Testy: `test_layers.py::TestContactEmailLocalpartOcr` — całe adresy (localpart OCR 1 i 2 spacje, zwykły, 15 cyfr w lokalnej części), negatywy końca zdania (Kontakt./Podpisano./„example.pl. Termin”/nowa linia), OCR przy `@` i TLD nadal jeden e-mail; `test_audyt_2026_10.py::test_email_localpart_ocr_bez_jawnego_fragmentu` ×2 tryby (plik dokładnie 600 linii — limit). Na kodzie bazowym: 3 FAIL przy pierwszym przebiegu (pozytyw OCR + 2 piony); dodany później przypadek podwójnej spacji też pada na bazie. Celowane `test_audyt` + `test_layers` + `test_pipeline_v2`: `243 passed, 10 xfailed`; pełna suita `127 passed, 40 skipped, 1 xfailed` (0 failed); autotest contact 16/16. T07 K1 (15 cyfr w e-mailu + osobna liczba) w obu trybach bez zmian.
- **Przegląd** `implementation/email_sweep.py` (z `backend/`; baza w tymczasowym worktree): 1620 wariantów = 5 kontekstów przed × 9 lokalnych części × 3 zapisy `@` × 2 domeny × 3 konteksty po × 2 tryby. **Regresje 0, naprawione 960, zmieniony tekst za adresem 0.** Pozostałe 180 jawnych to wyłącznie lokalna część WIELKIMI literami („ANNA. NOWAK@…”) — świadomie: nie do odróżnienia od końca zdania pisanego wersalikami, brief wymaga nietykania „Podpisano. Jan@…”.
- Pomiar `audyt/engine_quality.py --seed 2026` + holdout, ten sam digest: 0 zmian statusu, M3 84/96 (zestaw nie zawiera tej postaci e-maila — jak zastrzega brief, to nie jest dowód naprawy; dowodem są testy i przegląd).

## Osobno (nie pozorne PASS)
- Przywróć NIE oddaje znak w znak przy OCR-owych spacjach przy `@` i w TLD („jan @example.pl”, „jan@ example.pl”, „jan@wp. pl”) oraz „a.b. nowak@” — wartość w mapie jest kanoniczna (istniejące `_normalize_email` / normalizator OCR, przed tym Taskiem). Wierność, nie wyciek — klasa F3 (LYNX-TEXT-FIDELITY-F3).

## gate.py (stdout dosłownie)
```
STATUS: PASS
HEAD_SHA: fc75f1410c865acaa74e4ca2c9058aa81b16b5ed
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/implementation/email_sweep.py
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r1.txt
```

## Runda 2 — korekta wg kontraktu OWNER_ACCEPTED (brief, `b331151`; raporty r2–r6)
IMPLEMENTATION_SHA: `3fc5c7b05a40e1bbfaf3cad04fd91c659b76a181`. Zastępuje granice z rundy 1 (tam „Kontakt. jan@”/„Podpisano. Jan@” zostawały i WERSALIKI przeciekały).
- `_EMAIL_OCR_RE`: początek lokalnej części `(?<![\w.])[a-z0-9][a-z0-9_%+\-]*\.[ \t]{1,3}` z IGNORECASE (małe/WIELKIE/mieszane), lookahead do `@`/`©`. Tylko spacje/taby — słowo z poprzedniego wiersza nigdy nie dołączane (K1). Istniejąca obsługa OCR-newline przy `@` (`[ \t\n]{0,2}`) bez zmian.
- Zachowanie wg kontraktu (full = Express, sprawdzone parami): „anna. nowak@”, „ANNA. NOWAK@”, „ANNA.  NOWAK@”, „Anna. Nowak@”, „anna.   nowak@”, „anna.\tnowak@” → jeden EMAIL, surowy span w mapie, Przywróć 1:1. Nadmaskowanie zaakceptowane: „Prosimy o kontakt. jan@example.pl” → „Prosimy o EMAIL_001”, mapa „kontakt. jan@example.pl”; „Podpisano. Jan@…” → cały pod EMAIL; Przywróć 1:1. Granice: „Kontakt.\njan@…” — słowo z poprzedniego wiersza zostaje; „jan@example.pl. Termin płatności” — nic po adresie; „Kontakt. nie podano adresu.” — nietknięte; „jan@\nexample.pl”, „jan\n@example.pl” — nadal jeden EMAIL (wartość kanoniczna, F3).
- **Jawne ograniczenia (zaakceptowane, możliwy wyciek prefiksu):** 4+ odstępy — „anna.    nowak@” → „anna.    EMAIL_001” (jawne „anna.”); kilka rozbić — „anna. b. nowak@” → „anna. EMAIL_001” (jawne „anna.”). Nie naprawiane w tym Tasku.
- Testy: `test_layers.py::TestContactEmailLocalpartOcr` przepisany pod kontrakt (10 pozytywów w tym 2 nadmaskowania, 2 granice wiersza/końca, 1 bez e-maila, 4 OCR przy @/TLD); `test_audyt` pion ×2 tryby bez zmian. Celowane `249 passed, 10 xfailed`; pełna suita `127 passed, 40 skipped, 1 xfailed` (0 failed); autotest contact 16/16.
- `email_sweep.py` (dodane „Anna. Nowak”, „anna.   nowak”): **1980 wariantów, regresje 0, naprawione 1500, jawny fragment lokalnej części 0, zmieniony tekst za adresem 0.** Pomiar seed 2026 + holdout: bez zmian (M3 84/96).

gate.py (stdout dosłownie, finalny SHA):
```
STATUS: PASS
HEAD_SHA: 3fc5c7b05a40e1bbfaf3cad04fd91c659b76a181
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-EMAIL-LOCALPART-OCR\round_01\tests\tests_r2_repro.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/implementation/DELIVERY.md
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/implementation/email_sweep.py
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/implementation/gate.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r1.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r2.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r2_repro.py
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r3.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r4.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r5.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/round_01/tests/tests_r6.txt
  - tasks/LYNX-EMAIL-LOCALPART-OCR/brief.md
```
