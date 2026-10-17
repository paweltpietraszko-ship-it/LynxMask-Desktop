# LYNX-DOCX-TABLES — STOP / WYMAGA_DECYZJI (round_01, implementacja wstrzymana przed audytem)

IMPLEMENTATION_SHA (WIP): `83c94b4c5d28c91c5b0fa20d78e15886b1ba5a9e`. Zgodnie z briefem („gdy zwykła tabela body nie jest możliwa bez dodatkowego ownera: STOP + wąski finding”) — nie oddaję do audytu jako gotowe.

## Co zrobione (działa)
- `document_processor._docx_body_text`: akapity + zwykłe tabele treści w kolejności dokumentu, każda komórka raz (scalenia poziome/pionowe), akapity/komórki/wiersze rozdzielone `\n`; nagłówki/stopki/zagnieżdżone poza zakresem. Kontrakt `_extract_text` bez zmian.
- Test produkcyjnego extractora (tabela przed akapitem, scalenia, komórka wieloakapitowa, pusta komórka, akapit między tabelami) — zielony.
- Pomiar `--layout` na lokalnej próbce gov.pl: **DOCX/tabela 3 EXTRACTION_MISSING → 3 masked**, DOCX/akapit 1 masked, PDF 3 masked (bez regresji). Pełna suita `129 passed, 40 skipped, 1 xfailed`.

## Dlaczego STOP
Czytanie tabel wprowadza do silnika wartości w **sąsiednich liniach** (każda komórka = linia). Silnik ma istniejące (sprawdzone na bazie przed zmianą) błędy przechodzenia przez nową linię — dotąd rzadkie, z tabelami powszechne. Przegląd 56 par typowych wartości tabel w kolejnych liniach (NER wyłączony): 4 problemy:
- 2× e-mail nad e-mailem: `ocr_normalizer._EMAIL_SPACE_BEFORE_AT_DOT` (`\s+` obejmuje `\n`, a pierwszą grupą bywa domena poprzedniego adresu) skleja „…@example.pl\nm.nowicka@…” → częściowo jawne adresy.
- NIP / PESEL nad telefonem: wzorzec telefonu łapie cyfry przez `\n` → jawne „526-”, **token w tokenie** („NUMER_NUMER_002”), utracony podział linii.
Przed zmianą treść tabel w ogóle nie trafiała do wyniku; po zmianie trafia — z tymi wyciekami. Dwa nowe testy (`test_komorka_tabeli…` z dwoma e-mailami w sąsiednich liniach, `test_powtorzona_wartosc_akapit_i_tabela…`) są czerwone właśnie z tego powodu i zostają jako dowód.

## Do decyzji (Architekt/Paweł)
Rekomendacja CC: najpierw osobny Task **LYNX-NEWLINE-CROSSING** (normalizator e-mail + wzorce telefonu/numerów nie przechodzą przez `\n`; strażnik przed dopasowaniem cyfr tokenu), potem dokończenie DOCX-TABLES na tej gałęzi i audyt. Alternatywa: rozszerzenie TASK_SCOPE tego Tasku o te ownery.

gate.py (stdout dosłownie, WIP):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 83c94b4c5d28c91c5b0fa20d78e15886b1ba5a9e
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 76/13 = 5.8:1 (threshold 5:1)
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\engine_quality.py
  - backend\pseudominizer_api.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r4_repro.py
EXCLUDED_ARTIFACTS: NONE
```

## Runda 2 — dokończenie po merge NEWLINE-CROSSING (decyzja Pawła 2026-10-17: „Tak”)
IMPLEMENTATION_SHA: `57e39fbb6e30cccdce87103b9f72f066c4126c2a` (kod Tasku bez zmian od WIP `83c94b4`; gałąź zaktualizowana o main `3373ce6`; dodany `implementation/table_sweep.py`). Gate liczony od `f95d1b9` (merge-base z main) — zakres obejmuje wyłącznie pliki Tasku.
- Czerwone testy z rundy 1 są zielone: `test_engine_quality_layout.py` `10 passed` (tabela → masked, ta sama wartość w akapicie i komórce → 2× masked z pełną mapą, extractor: kolejność/scalenia/wieloakapitowa/pusta; scenariusze r2/r3 runnera przez nieczytany nagłówek).
- **`table_sweep.py`** (z `backend/`): 8 typowych wartości tabel w parach w sąsiednich komórkach (poziomo) i wierszach (pionowo), prawdziwy DOCX → `_extract_text` → pipeline, full/Express = 224 — **problemy 0** (brak jawnych fragmentów, tokenu w tokenie, utraty linii, zmiany tekstu po tabeli).
- **Pomiar `--layout` na lokalnej próbce LAYOUT-SAMPLES (20 dokumentów, 70 pól; te same SHA dokumentów)**, main `f95d1b9` → ta gałąź: **docx/tabela 7 EXTRACTION_MISSING → 7 masked**; wszystkie pozostałe kategorie identyczne (docx/tekst, pdf/tekst, pdf/tabela bez zmian). M3 dokumentów 11/20 → 11/20; jedna zmiana: L-006 (DOCX dwujęzyczny PL/UA, tekst ukraiński w tabelach) identical → diff — teraz czytany tekst ukraiński daje ~15 fałszywych OSOBA z polskiego NER, a jeden token przypięty do dwóch form („…дитини”) powoduje, że Przywróć dopisuje słowo. Wierność, nie wyciek — finding LYNX-FOREIGN-LANG-FP.
- `line_pairs_sweep.py` 0 problemów; pełna suita `129 passed, 40 skipped, 1 xfailed`; `test_audyt` + `test_layers` + layout `239 passed, 10 xfailed`.
- Poza zakresem (bez zmian): nagłówki/stopki, tabele zagnieżdżone, kształty, przypisy, pola formularzy DOCX; brak deklaracji „DOCX 100%”.

gate.py (stdout dosłownie, base `f95d1b9`):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 57e39fbb6e30cccdce87103b9f72f066c4126c2a
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 76/13 = 5.8:1 (threshold 5:1)
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\engine_quality.py
  - backend\pseudominizer_api.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r4_repro.py
  - tasks\LYNX-DOCX-TABLES\round_01\implementation\table_sweep.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-DOCX-TABLES/brief.md
  - tasks/LYNX-DOCX-TABLES/round_01/implementation/DELIVERY.md
  - tasks/LYNX-DOCX-TABLES/round_01/implementation/gate.txt
  - tasks/LYNX-DOCX-TABLES/round_01/implementation/table_sweep.py
  - tasks/LYNX-DOCX-TABLES/round_01/tests/tests_r1.txt
```
WYMAGA_DECYZJI tylko RATIO 76/13=5.8 (testy extractora i aktualizacja testów layout).
