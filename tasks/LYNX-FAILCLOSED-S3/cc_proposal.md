# PROPOZYCJA CC DO BRIEFU — LYNX-FAILCLOSED-S3 — awaria lub obejście nigdy nie oddaje surowego tekstu jako „zamaskowanego”

STATUS: PROPOZYCJA CC → Architekt pisze `brief.md` → Codex audytuje brief → CC ocenia i implementuje → Codex audyt exact SHA → merge wyłącznie na polecenie OWNERA.
AUTOR PROPOZYCJI: CC (Paweł 2026-10-18: „pisz propozycje … łącz poprawki”). Łączy 5 zgłoszeń jednej klasy (granica zaufania / fail-closed) z ultrareview PR #3 i realizuje niewykonany Task audytu **LYNX-T06-GUARD-BLOCK** (`arch/FINDING_2026-10_AUDYT.md`: „Guard i fail-closed także w Express”). BOARD: `LYNX-FAILCLOSED-S3`.
PRODUCT_TRUTH: arch/spec.md **S3** (awaria silnika = blokada, nigdy cichy surowy wynik), S1, S2, S5. **S4 bez zmian** — ta propozycja nie rozstrzyga LYNX-SPEC-S4-GUARD-WARN; po ewentualnej zmianie S4 (Guard ostrzega) blokada przy AWARII (S3) zostaje, zgodnie z uwagą Pawła 2026-10-17 („blokada tylko przy awarii”).

## Defekty (odtworzone przez CC na main `d6a8a15`, syntetyki)

| # | Miejsce | Skutek | Reproduktor |
|---|---|---|---|
| F1 | `pipeline_new.run_pipeline_express` `except Exception: return text, {}, False`; `/preview-express` ignoruje trzecią wartość i nie ma Guarda | wyjątek dowolnej warstwy → **surowy dokument (PESEL) w `anonymized_preview`, `blocked=False`**; odtworzone: `('PESEL: 44051401359', {}, False)` | istniejący xfail `BUG-EXPRESS-FAIL-OPEN` (`test_audyt_2026_10.py:241`) |
| F1b | `pipeline.pseudonymize_document` `except Exception: return PipelineResult(text=text, error=…)`; API zwraca `anonymized_preview` = oryginał + `error`; `Pseudonimizuj.tsx` robi `setResult(data)` także przy `data.error` | surowy tekst wyświetlony jako wynik do skopiowania, `guard_blocked=False`; odtworzone: `_run_pipeline` rzuca → `guard_blocked=False`, tekst = oryginał | nowy |
| F2 | `ner_layer.process_ner` (`except Exception → ({}, {})`, poza NERBlockError), `spacy_ner.detect_entities` (`except Exception → []`, poza RuntimeError) | błąd SpaCy (MemoryError, ValueError, uszkodzony model) → dokument bez osób/firm, `ner_error` nigdy nie ustawiony, brak blokady; odtworzone: `_get_nlp` rzuca ValueError → `force_block=False`, „Kowalski” jawny | nowy |
| F3 | `output_guard.guard_output_with_map` przy MAP_LEAK buduje wynik z `redacted_text=text` | podgląd zablokowanego wyniku pokazuje surowy PESEL/IBAN, które `guard_output` już zamazał | istniejący xfail `BUG-GUARD-MAPLEAK-UNREDACTED` |
| F4 | allowlista Guarda: `any(a in v.lower() …)` na całym komunikacie naruszenia, także `GUARD_ERROR` | wpis „Jan” wycisza MAP_LEAK „Janina Kowalska”; słowo z szablonu („mapy”, „encja”) wycisza wszystko; awaria Guarda filtrowana | istniejący xfail `BUG-ALLOWLIST-SUBSTRING` |
| F5 | kontrola wstrzyknięcia tokenu (AUD-01, `pseudominizer_api` `_TOKEN_RE` na surowym tekście) przed `ocr_normalizer` krok 12 (`(?<=\d)[lOIo]+(?=…\d)`) | „OSOBA_0O1” przechodzi 422, normalizacja robi „OSOBA_001”, alokator daje go prawdziwej osobie → Przywróć wstawia prawdziwe nazwisko w miejscu wybranym przez autora tekstu; odtworzone: „Pełnomocnik: OSOBA_001, pozwany OSOBA_001.” | nowy |

## Wymagane zachowanie
1. **Każdy wyjątek w pipeline (Full i Express) → wynik zablokowany bez treści**: `blocked=True`, brak `anonymized_preview`/tokenów/mapy (albo pusty), czytelny komunikat „Nie udało się bezpiecznie zamaskować dokumentu” + kategoria błędu w logu bez PII. `/preview-express` respektuje `force_block`. Frontend nie wyświetla tekstu wyniku, gdy `blocked` lub `error` (oba ekrany).
2. **Awaria NER = awaria silnika (S3)**: wyjątki SpaCy/`process_ner` docierają do adaptera (`state.ner_error = True` → force_block), zamiast pustego wyniku. Brak encji przy poprawnym działaniu — bez zmian.
3. **Podgląd zablokowanego wyniku nie zawiera surowych wartości HIGH** — wynik MAP_LEAK bazuje na tekście już zamazanym przez `guard_output`.
4. **Allowlista porównywana z wartością encji** (dokładnie, bez wielkości liter), nigdy z treścią komunikatu; `GUARD_ERROR` nigdy nie filtrowany.
5. **Kontrola wstrzyknięcia także po normalizacji OCR** (Full i Express): token powstały w normalizacji → odmowa jak 422 dziś (albo force_block), zanim alokator rozda numery.

## Minimalny szew (propozycja)
`backend/pipeline_new.py` (Express: `except` → `(text, {}, True)`; kontrola TOKEN po `apply_ocr_normalizer` w obu ścieżkach), `backend/pipeline.py` (`pseudonymize_document` except → `guard_blocked=True`, bez tekstu), `backend/pseudominizer_api.py` (Express: `force_block` → `blocked`; przy blokadzie/błędzie bez `anonymized_preview`), `backend/ner_layer.py` + `backend/spacy_ner.py` (propagacja wyjątków — `ner_layer.py` 600/600 linii: zmiana netto ≤0 albo zgoda Pawła), `backend/output_guard.py` (F3, F4), `frontend/src/screens/Pseudonimizuj.tsx` + `ExpressModeScreen.tsx` (nie pokazywać tekstu przy `blocked`/`error`), test `backend/tests/test_failclosed.py` + zdjęcie trzech markerów xfail w `test_audyt_2026_10.py` po XPASS.
Rozmiar: `pseudominizer_api.py` 1129 linii (ratchet; zgłoszenie LYNX-API-SIZE) — zmiana netto ≤0 albo zgoda Pawła.

TASK_SCOPE:
- backend/pipeline_new.py
- backend/pipeline.py
- backend/pseudominizer_api.py
- backend/ner_layer.py
- backend/spacy_ner.py
- backend/output_guard.py
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src/screens/ExpressModeScreen.tsx
- backend/tests/test_failclosed.py
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: zmiana roli Guarda (S4 — osobna decyzja), `TOKEN_RE` i jego granice (LYNX-T08-TOKEN-RE, decyzja wspólna z Mobile), treść reguł normalizacji OCR (K3), wartości mapy (LYNX-MAP-FIDELITY), archiwum (T13), UI poza wyświetlaniem wyniku.

## Test falsyfikujący
1. RED→GREEN, Full i Express: wyjątek wstrzyknięty w warstwę (`patch`), w `nlp(text)` (MemoryError/ValueError) i w `_run_pipeline` → odpowiedź API `blocked=True`, brak surowego PESEL/nazwiska w całej odpowiedzi JSON, brak `anonymized_preview` z treścią.
2. F3/F4: trzy istniejące xfail przechodzą (XPASS → zdjąć marker); dodatkowo allowlista „Jan” nie wycisza „Janina Kowalska”, `GUARD_ERROR` nie znika przy żadnym wpisie.
3. F5: „OSOBA_0O1”, „FIRMA_1l2” w Full i Express → odmowa/blokada; zwykłe OCR cyfr („l2O3”) bez zmian.
4. UI: syntetyk z wymuszonym błędem w działającej aplikacji (backend z gałęzi, jak przy TEXT-LIMIT-15K) — ekran pokazuje komunikat, brak tekstu do skopiowania.
5. Regresje: suita z backendem, `test_layers`, `test_ner_multiline`, `test_text_limit_15k`; 17 dokumentów diagnozy przez `/preview` — blokady i wyniki bez zmian (żaden poprawny przebieg nie zaczyna się blokować).

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_express
- TARGETS: backend/pipeline.py --symbol pseudonymize_document
- TARGETS: backend/ner_layer.py --symbol process_ner
- TARGETS: backend/spacy_ner.py --symbol detect_entities
- TARGETS: backend/output_guard.py --symbol guard_output_with_map
- REASON: wszystkie ścieżki, w których wyjątek lub filtr zamienia się w cichy surowy wynik.
GATE: >150 linii lub ratio >5:1 = WYMAGA_DECYZJI; pliki legacy/przy limicie — ratchet.
