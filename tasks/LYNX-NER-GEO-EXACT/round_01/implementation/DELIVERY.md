# LYNX-NER-GEO-EXACT — DELIVERY round_01

BEFORE_SHA: `19083548c2771f49307c810c8ceaa92319a34839` · IMPLEMENTATION_SHA: `8d208455667023f9b141d9a79ecf18f109a310ff` (fix `4b9a935` + helper `c9499df` + rozszerzenie E1/E2 `faf8525`, `8d20845`)
Zmienione pliki (TASK_SCOPE): `backend/ner_blocklist.py`, `backend/ner_layer.py`, `backend/tests/test_audyt_2026_10.py` + rozszerzenie CC: `backend/layers/ner_adapter.py`, `backend/pseudominizer_api.py`.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED) — odbiorcy: `_load_geo_words` tylko `ner_blocklist.py:96`; `_GEO_WORDS` tylko `ner_layer` (`_is_person_word`); `_NER_BLOCKLIST` także `layers/ner_adapter.py:178` i `pseudominizer_api.py:762` — patrz Zgłoszenia. Dane: |ulica ∩ `_PERSON_FORMS`| = 649, z tego wyłącznie ulica (bez miasta/placówki/ręcznego wpisu) = **561** (audytowe 1008 liczyło przecięcie z całym geo, także z miastami). „Piątek”, „Zając” są miastami → nadal odrzucane. Morfeusz nie nadaje się do odsiewu słów pospolitych w tym zbiorze („Nowaka” ma kwalifikator `nazwa_pospolita`, „Kowalskiego” `nazwa_geograficzna`) — zgodnie z briefem decyduje konkretny słownik, nie Morfeusz.

## Co zrobione
- `ner_blocklist.py`: `_load_geo_words()` zwraca pochodzenie osobno `{"city","street","med"}` (wspólny `_load_geo_file`, reguły ładowania bez zmian: ≥4 znaki, bez cyfr poza placówkami, wariant ASCII). `_GEO_WORDS` = suma — **identyczna jak przed** (sprawdzone `==`). Nowy `_STREET_ONLY_PERSON_FORMS = (ulica ∩ _PERSON_FORMS) − miasta − placówki − ręczna blocklista`, liczony przed złączeniem blocklisty z geo. `_NER_BLOCKLIST` i prefiksy bez zmian.
- `ner_layer.py`: helper `_street_person(label, text)` = `OSOBA` + wielka litera + forma w zbiorze. W `_filter_institutions` pomija exact geo i dopuszcza encję w gałęzi T01 (zamiast strict geo w `_is_person_word`). `_is_person_word` nietknięte — FIRMA i wielowyrazowe ścieżki bez zmian (bypass wyłącznie OSOBA). Helper zamiast zmiennej lokalnej: inaczej `_filter_institutions` rośnie 72→74 (gate SIZE_FUNC).
- Testy (`test_audyt_2026_10.py`, bez nowych plików): `test_filtr_ner_nazwisko_z_nazwy_ulicy` ×3 („Kowalskiego”, „Nowaka”, „Adamczyka” — asercje pochodzenia: osoba ∧ ulica, ∉ miasto/placówka, ∈ zbiór); 4 nowe negatywy w `test_filtr_ner_nadal_odrzuca_nie_osoby` („Radom”/OSOBA, „Zając”/OSOBA, „ul. Kowalskiego 7”/OSOBA, „Kowalskiego”/FIRMA; „Warszawie”, „Piątek”, „ZUS” już tam były); `test_nazwisko_z_ulicy_w_pipeline` ×2 — pion `run_pipeline_new` z kontrolowanym `spacy_ner.detect_entities`. „Zapłata” — tylko obserwacja baseline (przepuszczana przed i po), bez asercji.

## Dowody
- Filtr przed → po (OSOBA kept): Kowalskiego/Nowaka/Adamczyka False → True; „kowalskiego” (mała litera), Radom, Warszawie, Piątek, Zając, „ul. Kowalskiego 7”, ZUS/FIRMA, Kowalskiego/FIRMA — False → False; Zapłata True → True (baseline).
- Nowe testy na kodzie sprzed zmiany: 4 failed (3× pozytyw, pion „Wniosek …”), negatywy i pion adresowy zielone.
- Pion z **realnym** spaCy (`implementation/geo_vertical.py`, z `backend/`): przed — „Wniosek Kow******** został przyjęty.”, mapa pusta (wyciek); po — „Wniosek OSOBA_001 …”, `{OSOBA_001: Kow********}`. Adres przed i po: `ADRES_001` = „ul. Kow******** 7”, brak OSOBA — także gdy kontrolowany spaCy oznaczy nazwisko wewnątrz adresu.
- Pomiar FN/FP (`implementation/geo_measure.py`): próbka 40 form (co 14. z posortowanego `_STREET_ONLY_PERSON_FORMS`), te same formy w dwóch rozłącznych zdaniach syntetycznych, realny spaCy. Pozytyw „Wniosek {X} został przyjęty przez urząd.”: **FN 40 → 2** (2 pozostałe — spaCy nie rozpoznaje osoby; poza zakresem). Adres „Mieszka przy ul. {X} 7 w Radomiu.”: **FP (OSOBA w adresie) 0 → 0**. Bez deklaracji szczelności.
- `test_audyt_2026_10.py`: `49 passed, 15 xfailed` (przed: 40 passed). Filtry T01 w `test_pseudominizer.py -k Filter`: 4 passed. Pełna suita (uruchomiona jako tani bezpiecznik, profil tymczasowy): `1 failed, 126 passed, 40 skipped, 1 xfailed` — jedyny FAIL IBAN-RECEPTA, jak na main. Benchmark nie uruchamiany (brief: tylko na wniosek audytu/OWNERA).

## gate.py (stdout dosłownie, finalny SHA)
```
STATUS: PASS
HEAD_SHA: 8d208455667023f9b141d9a79ecf18f109a310ff
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - audyt\trace_layers.py
  - backend\pipeline_new.py
  - tasks\LYNX-T12-ARCHIVE-TESTS\round_01\implementation\t12_same_process.py
  - tasks\LYNX-T12-ARCHIVE-TESTS\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T10-BUILD-TS\round_01\implementation\header_capture.py
  - tasks\LYNX-T03-TOKEN-ALLOC\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-T02-CORS-EXPRESS\round_01\tests\tests_r4_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-NER-GEO-EXACT\round_01\implementation\geo_measure.py
  - backend\tests\test_archive_adversarial.py
  - backend\tests\test_pipeline_v2.py
  - backend\tests\test_pseudominizer.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-NER-GEO-EXACT/round_01/implementation/DELIVERY.md
  - tasks/LYNX-NER-GEO-EXACT/round_01/implementation/gate.txt
  - tasks/LYNX-NER-GEO-EXACT/round_01/implementation/geo_measure.py
  - tasks/LYNX-NER-GEO-EXACT/round_01/implementation/geo_vertical.py
  - tasks/LYNX-NER-GEO-EXACT/round_01/tests/tests_r2.txt
  - tasks/LYNX-NER-GEO-EXACT/brief.md
```
Wcześniejsze przebiegi: `4b9a935` FAIL `SIZE_FUNC _filter_institutions 74 (before 72)` → helper w `c9499df` (PASS); `faf8525` FAIL `SIZE_FILE pseudominizer_api.py 1124 (before 1123)` + `SIZE_FUNC profile_add_entity 54 (before 53)` → warunek E2 w jednej linii w `8d20845` (PASS).

## Rozszerzenie CC — wykonane (brief, sekcja „ROZSZERZENIE CC”, commit `7452a1e` przed kodem)
Zasada Pawła 2026-10-17: ta sama klasa błędu naprawiana na tej samej gałęzi z jawnym rozszerzeniem briefu; oba pliki dopisane do TASK_SCOPE.
- **E1** `layers/ner_adapter.py::_apply_initials`: nazwisko ∈ `_STREET_ONLY_PERSON_FORMS` nie jest pomijane przez blocklistę. Reproduktor przed: z wyłączonym spaCy „Zgoda K. Nowaka na zabieg.” bez zmian (jawne); po: `{OSOBA_001: "K. Nowaka"}`. Z realnym spaCy te zdania były maskowane już wcześniej (przez NER) — E1 domyka warstwę zapasową.
- **E2** `pseudominizer_api.py::profile_add_entity`: blocklista nie odrzuca formy ∈ `_STREET_ONLY_PERSON_FORMS`, tylko dla `token_type == "OSOBA"`. Stop-words, miasta, placówki, ręczna blocklista i inne typy — bez zmian.
- Testy: `test_inicjal_z_nazwiskiem_z_ulicy_bez_spacy`; `test_profil_dodaje_nazwisko_z_ulicy` ×3 (Kowalskiego/OSOBA → 200 i zapis; Radom/OSOBA → 400; Kowalskiego/FIRMA → 400; profil podmieniony atrapą, bez lifespanu). Na kodzie sprzed E1/E2: 2 failed (oba pozytywy), negatywy zielone.
- Po rozszerzeniu: `test_audyt_2026_10.py` `53 passed, 15 xfailed`; pełna suita `1 failed (IBAN-RECEPTA), 126 passed, 40 skipped, 1 xfailed`.
