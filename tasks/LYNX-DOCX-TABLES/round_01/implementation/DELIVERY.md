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
