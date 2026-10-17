# LYNX-T11-TEXT-FIDELITY — DELIVERY round_01

BEFORE_SHA: `576d133e21035ad5c34f7bf1216da6ab02086720` · IMPLEMENTATION_SHA: `0bd2a57946b383e11024c6a7694c235a5271d55d` (rozszerzenie w briefie `48a162b` przed kodem; kod `9c284c0`; zagęszczenie `0bd2a57`)
Pliki (TASK_SCOPE): `backend/layers/ner_adapter.py`, `backend/layers/ocr_normalizer.py`, `backend/tests/test_audyt_2026_10.py` + ROZSZERZENIE CC: `backend/layers/contact.py`.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED): `_fix_ocr_email` wywoływane w `ner_adapter.py:198` i `:241` (+ autotest :429-430, test audytu); `_PHONE_AFTER_KW_RE` tylko w `normalize_ocr` krok 11. Obserwacja: `_fix_ocr_email` działa PO warstwie kontaktów, więc jego sklejanie lokalnej części e-maila („anna. nowak@”) nie pomaga wykryciu adresu — patrz Zgłoszenia.

## Co zrobione
- **F1** `_fix_ocr_email`: sklejanie „x. y” tylko gdy przed kropką jest lokalna część adresu (małe litery ASCII/cyfry od początku słowa), a po spacji ciąg znaków adresu aż do `@`. „12/2026. Termin”, „szpitalu. Dłużnik”, „nieokreślony.\n2.”, „Kontakt. jan@…” — bez zmian; „anna. nowak@…” → „anna.nowak@…”; poprawki spacji przy `@` bez zmian. Świadome zawężenie: lokalna część z wielką literą przed kropką („Anna. nowak@”) nie jest już sklejana — nie da się jej odróżnić od końca zdania.
- **F2** krok 11: `_phone_number_len` — zamiana liter OCR→cyfry tylko w członach numeru; końcowe człony bez cyfry („T” z „Termin”, „z” z „zglosil”) i człon urwany w środku słowa zostają nietknięte. „Tel: +48 606 219 T2T” → „727” nadal. Usunięta martwa zagnieżdżona `_fix_phone` (nieużywana) — pozwoliło nie powiększyć `normalize_ocr`.
- **ROZSZERZENIE CC E1** (`contact.py::_EMAIL_OCR_RE`, sekcja w briefie przed kodem): TLD po separatorze ze spacją OCR tylko małymi literami. Przed: „nowak@example.pl. Termin płatności” → „EMAIL_001 płatności”, mapa „nowak@example.pl.Termin” (słowo znikało z tekstu, Przywróć oddawał sklejkę). Po: „EMAIL_001. Termin płatności”, mapa „nowak@example.pl”. OCR „jan@wp. pl”, „jan@wp ,pl” nadal jeden e-mail.
- Testy: zdjęte `xfail(strict)` z `test_fix_ocr_email_nie_skleja_zdan` (2 → 5 przypadków) i `test_ocr_normalizer_nie_psuje_slow` (1 → 3, w tym T2T→727); nowy `test_wiernosc_tekstu_i_maskowanie` ×3 — pion `run_pipeline_new` (NER wyłączony): tekst poza tokenem wierny, wartość e-maila/telefonu w reverse_map bez „Termin”, wartość nie jawna w wyniku. Na kodzie sprzed zmian: 9 z 11 nowych/odblokowanych przypadków FAIL (2 zielone to pozytywy, które mają działać przed i po).

## Dowody
- `test_audyt_2026_10.py`: `69 passed, 12 xfailed` (przed: 58 passed, 15 xfailed). Autotesty warstw: ner_adapter 19/19, ocr_normalizer 40/40, contact 16/16; `tests/test_layers.py` 60 passed. Pełna suita (profil TEMP): `1 failed (IBAN-RECEPTA), 126 passed, 40 skipped, 1 xfailed`.
- **Pomiar `audyt/engine_quality.py --seed 2026` + holdout (Mobile `surnames_extended.json`), ten sam `input_digest e089762029f7a27b`:**
  - M1, HOLDOUT, M2: identyczne przed/po (0 zmian statusu w 96 przypadkach; brak nowych leak/blocked/fp).
  - **M3: 51/96 → 84/96 identycznych**; `diff_outside_spans` 45 → 4.
  - Pozostałe 12 różnic, jawnie: NUMER-pesel ×4 (dopisany dwukropek — F3, jedyne 4 różnice poza spanami), NUMER-telefon ×4 (`+` i spacje po Przywróć — F3), NUMER-iban ×4 (BUG-IBAN-RECEPTA). F3 nie jest naprawiony.

## gate.py (stdout dosłownie, finalny SHA)
```
STATUS: PASS
HEAD_SHA: 0bd2a57946b383e11024c6a7694c235a5271d55d
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - audyt\trace_layers.py
  - backend\ner_layer.py
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T03-TOKEN-ALLOC\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\tests\tests_r3_repro.py
  - backend\tests\test_layers.py
  - backend\tests\test_pipeline_v2.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/tests/tests_r1.txt
  - tasks/LYNX-T11-TEXT-FIDELITY/brief.md
```
Wcześniej `9c284c0`: FAIL `SIZE_FILE ocr_normalizer.py 708 (before 703)` → helper zagęszczony w `0bd2a57`.

## Zgłoszenia (inna klasa — nie wykonane)
- **E-mail z OCR w lokalnej części**: „anna. nowak@example.pl” → warstwa kontaktów wykrywa tylko „nowak@example.pl”, „anna.” zostaje jawne (przed i po T11). Sklejanie w `_fix_ocr_email` działa dopiero po warstwie kontaktów, więc nie pomaga. Do osobnego zadania (kolejność/ownership normalizacji e-maila).

## Runda 2 — po FAIL Codexa r2 (`tests_r2.txt`, `2f97f4c`)
IMPLEMENTATION_SHA: `b3d09f81dda037eb905418fb532a6d3c8f6dcf9b`.
- **R1 (trafne, regresja prywatności — mój błąd):** reguła „człon musi mieć cyfrę” odcinała ostatnią grupę złożoną wyłącznie ze znaków OCR („+48 606 219 TTT/OOO/III”) → numer nie był maskowany, końcówka jawna. Nowa `_phone_number_len`: liczy cyfry krajowe (prefiks `+48`/`0048` pomijany); człon bez cyfry należy do numeru, gdy domyka 9 cyfr albo stoi przed członem z cyfrą; człony po 9 cyfrach i człon urwany w słowie zostają tekstem. TTT/OOO/III → 777/000/111 i `NUMER` w mapie; „654. Termin”, „654) zglosil”, T2T → 727 bez zmian; „123 45 To jest” — „To” zostaje słowem.
- **R2 (WYMAGA_DECYZJI w raporcie — rozstrzygnięte w granicach E1, bez zmiany kontraktu):** spacja OCR przy separatorze TLD dopuszczana tylko gdy domena nie ma jeszcze kropki (i TLD małymi literami). „nowak@example.pl. termin/dalej” → e-mail „nowak@example.pl”, słowo zostaje w tekście; „jan@wp. pl”, „jan@wp ,pl” nadal jeden e-mail. Pozostaje nierozstrzygalne z samego tekstu: domena bez kropki + „. słowo” małą literą („jan@wp. dalej”) — traktowane jak OCR TLD.
- Miejsce na regułę bez powiększania pliku: usunięte martwe `_fix_dowod`, `_NIP_SPLIT_RE`, `_NUMERIC_CHARS` w `ocr_normalizer.py` (0 odwołań w repo, sprawdzone grep) — 694 linie (przed Taskiem 703).
- Testy: reproduktory Codexa jako stałe przypadki — TTT/OOO/III w normalizatorze i pionie (zamaskowane, końcówka niejawna), „To jest” negatyw, „. termin”/„. dalej” w pionie wierności (słowo nie trafia do mapy). Na `0bd2a57`: 8 FAIL z nich; teraz zielone. `test_audyt_2026_10.py` + `test_layers.py`: `138 passed, 12 xfailed`; autotesty warstw 19/40/16 PASS; pełna suita `1 failed (IBAN-RECEPTA), 126 passed, 40 skipped, 1 xfailed`.
- Pomiar seed 2026 + holdout, ten sam digest: M1/HOLDOUT/M2 identyczne z bazą (0 zmian statusu), M3 84/96 (bez zmian względem rundy 1).

gate.py (stdout dosłownie, finalny SHA):
```
STATUS: PASS
HEAD_SHA: b3d09f81dda037eb905418fb532a6d3c8f6dcf9b
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - audyt\trace_layers.py
  - backend\ner_layer.py
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-T11-TEXT-FIDELITY\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T03-TOKEN-ALLOC\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\tests\tests_r3_repro.py
  - backend\tests\test_layers.py
  - backend\tests\test_pipeline_v2.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/implementation/DELIVERY.md
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/implementation/gate.txt
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/tests/tests_r1.txt
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/tests/tests_r2.txt
  - tasks/LYNX-T11-TEXT-FIDELITY/round_01/tests/tests_r2_repro.py
  - tasks/LYNX-T11-TEXT-FIDELITY/brief.md
```
