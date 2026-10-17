# LYNX-NER-GEO-EXACT — DELIVERY round_01

BEFORE_SHA: `19083548c2771f49307c810c8ceaa92319a34839` · IMPLEMENTATION_SHA: `c9499dfebff1f1f3c64d50ad9733fc8d2b53ed19` (fix `4b9a935` + helper `c9499df`)
Zmienione pliki (TASK_SCOPE): `backend/ner_blocklist.py`, `backend/ner_layer.py`, `backend/tests/test_audyt_2026_10.py`.

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

## gate.py (stdout dosłownie)
```
STATUS: PASS
HEAD_SHA: c9499dfebff1f1f3c64d50ad9733fc8d2b53ed19
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
IMPORTERS_FOR_REVIEW:
  - audyt\bench_offline.py
  - audyt\docs_variants.py
  - backend\pseudominizer_api.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-T01-NER-PREFIX\round_01\tests\tests_r3_repro.py
  - backend\layers\ner_adapter.py
  - backend\tests\test_pseudominizer.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-NER-GEO-EXACT/round_01/tests/tests_r2.txt
```
Pierwszy przebieg (`4b9a935`): FAIL `SIZE_FUNC _filter_institutions 74 (before 72)` → naprawione helperem w `c9499df`.

## Zgłoszenia (nie wykonane, poza TASK_SCOPE)
- **Ta sama klasa wycieku w inicjałach:** `layers/ner_adapter.py:178` `_apply_initials` odrzuca „K. Kowalskiego” gdy nazwisko ∈ `_NER_BLOCKLIST` (zawiera ulice) → inicjał + nazwisko-z-ulicy zostaje jawne. Naturalna poprawka: ten sam `_STREET_ONLY_PERSON_FORMS`.
- **Dodawanie do słownika:** `pseudominizer_api.py:762` odmawia dodania „Kowalskiego” jako słowa pospolitego (bo jest w blockliście przez ulice) — użytkownik nie może ręcznie dopisać takiego nazwiska.
