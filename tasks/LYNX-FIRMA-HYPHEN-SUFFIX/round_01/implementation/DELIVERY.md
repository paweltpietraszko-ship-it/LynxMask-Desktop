# LYNX-FIRMA-HYPHEN-SUFFIX — DELIVERY round_01 (CC)

Gałąź `task/LYNX-FIRMA-HYPHEN-SUFFIX`, zsynchronizowana z `main` (merge `ff09336`, zawiera ZUS-BOXED-IDS). Gate base: `5ae6f8dd5b5b9c4eea8851ddf5aca4c1a12d32e8`. Implementacja: `07504c8d9282f1c70347ec3a39f8a389a14bfd5b`.
Pliki (TASK_SCOPE): `backend/ner_layer.py` (+38/−1, 578 l.), `backend/tests/test_layers.py` (+62). `ner_adapter.py` bez zmian. Artefakt: `round_01/implementation/firma_sweep.py`. Rozszerzenia CC: brak.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED): `_process_ner` wołane tylko przez `process_ner`; `apply_ner_layer` tylko przez pipeline i własne testy. Detekcja: `spacy_ner.detect_entities` → `_filter_institutions` → `_process_ner` (rstrip, `_TRUNC_ENDINGS`) → adapter (podmiana wariantów, `_FIRMA_CLEANUP_RE`).

## Krok 0 — diagnoza (lokalna próbka, 6 pól FIRMA, tylko statusy)
| klasa | pola | szczegół |
|---|---|---|
| poprawne | 1 | encja pełna |
| **ucięta granica** | 2 | SpaCy zaczyna encję PO łączniku (człon przed `-` jawny); w jednym polu przez to `_prefix_rejects` odrzuca resztę (pierwsze słowo w prefiksach geo) → pełny wyciek; w drugim rozcina „S.\|A.” (A. jako OSOBA) → częściowy |
| **brak użytecznego kandydata** | 3 | SpaCy nic nie zwraca (2) albo tylko „z o.o.” (1 — powstaje samodzielny FIRMA na formie) |

Przegląd rodziny (niżej) pokazał czwartą przyczynę z listy briefu: **utrata formy prawnej przez cleanup**. Gdy encja kończy się przed „Sp.k.”/„Sp. j.”, adapter (`_FIRMA_CLEANUP_RE`) usuwa formę stojącą za tokenem, a w mapie jej nie ma, więc Przywróć jej nie odtwarza (baza: 8/160).
Zła klasyfikacja nie wystąpiła. Klasa „brak kandydata” spełnia warunek STOP z briefu (SpaCy nie daje użytecznego fragmentu). Nie dodałem regexu przed „Sp.k.”, tylko finding niżej.

## Zmiana (`ner_layer.py`)
`_firma_entities(text, ner_results)` wołane w `_process_ner` przed `_filter_institutions`:
- `_firma_bounds`: tylko etykieta FIRMA. (a) Dołącza przyległy człon przed łącznikiem: bez spacji, zaczyna się wielką literą lub cyfrą, np. „Apex-”, „Trans-Bud-”. (b) Dołącza formę prawną zaczętą w encji („S.|A.”) albo leżącą tuż za nią („Sp.k.”, „Sp. j.”). Słów oddzielonych spacją nigdy nie dołącza.
- Fragment samej formy prawnej („z o.o.”, „A.”) leżący wewnątrz rozpoznanej firmy nie dostaje osobnego tokenu. Taki sam fragment poza firmą zostaje bez zmian.
Express nie używa NER, więc jego wynik się nie zmienia. Guard bez zmian.

## Dowody
1. **`firma_sweep.py`** (z `backend/`, prawdziwy NER, Full): 10 nazw (8 z łącznikiem, 2 bez) × 4 formy (Sp.k., S.A., Sp. z o.o., Sp. j.) × 4 konteksty = 160. Baza = ten sam kod z `_firma_entities` wyłączonym, czyli kod sprzed Tasku.
   - baza: `masked 23, partial_mask 40, leak_partial 36, leak 61`;
   - po: `masked 96, leak_partial 12, leak 52`;
   - **regresje 0**; Przywróć lub token w tokenie: baza 8, po **0**.
   - 7 kontrprób: biało-czerwona i samo „S.A.”, ZUS/KNF, nagłówek WERSALIKAMI, „Forma prawna: Sp. z o.o.”, Bielsko-Biała, OSOBA Nowak-Kowalski, dwie firmy w zdaniu + kropka i kolejne zdanie. Wynik bez zmian poza jedną poprawą: druga firma „Eko-Tech S.A.” wcześniej „Eko-Tech S” → teraz pełna. Przywróć dokładny we wszystkich.
   - Pozostałe 64: wyłącznie brak kandydata. SpaCy zwraca nic albo sam fragment („A.”, „j.”, „z o.o.”), głównie w kontekście „Etykieta: Nazwa” w osobnej linii. To klasa STOP.
2. **Próbka layout** (`engine_quality.py --seed 2026 --layout`, raport poza repo). Porównanie z raportem kodu równego `main` po ZUS: ten sam `input_digest` i sha256 20 plików; M1/M2/M3/HOLDOUT identyczne; M3 dokumentów bez zmian.
   - pdf/tabela: `masked 28, blocked 3, leak_partial 1, leak 1, EXTRACTION_MISSING 1` → `masked 29, blocked 3, leak 1, EXTRACTION_MISSING 1`;
   - pdf/tekst: `masked 10, leak_partial 1, leak 1` → `masked 11, leak_partial 1`;
   - docx bez zmian.
   - FIRMA: **5 złych → 3** (2 z uciętą granicą naprawione). 3 pozostałe = brak kandydata, NIE zamknięte.
3. **Testy** `backend/tests/test_layers.py` (uruchamiane jawnie): 113 passed. Bez poprawki 14 failed (RED → GREEN):
   - jednostkowe granice: 8 wariantów + test OSOBA i fragmentu formy;
   - Full z prawdziwym NER: 6 nazw — jeden FIRMA na całość, wartość w mapie, Przywróć 1:1. „Apex-Transport … Sp. z o.o.” przechodził już na bazie (kontrola).
4. **Pozostałe suity:**
   - standardowa: 129 passed, 40 skipped, 1 xfailed;
   - **z backendem** (profil w TEMP): 167 passed, 2 skipped, 1 xfailed, 0 failed;
   - `test_audyt_2026_10.py`: 131 passed, 10 xfailed;
   - `test_engine_quality_layout.py`: 15 passed;
   - ruff: czysto.

## gate.py (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 07504c8d9282f1c70347ec3a39f8a389a14bfd5b
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 100/1 = 100.0:1 (threshold 5:1)
```
(IMPORTERS_FOR_REVIEW i EXCLUDED_ARTIFACTS w `gate.txt`.) RATIO wynika z dwóch nowych funkcji i testów przy jednej zmienionej linii. Rozmiar 100 < 150. Potrzebna akceptacja rozmiaru.

## Findingi (nie naprawiane)
- **LYNX-FIRMA-NO-CANDIDATE** (STOP z briefu): SpaCy nie daje użytecznego kandydata. Dotyczy 3 pól próbki i 64/160 w przeglądzie, najczęściej „Etykieta: Nazwa-X Sp.k.” w osobnej linii. Naprawa wymaga detekcji zakotwiczonej w formie prawnej, czyli nowej reguły typu AnchorEngine. To jest poza zakresem i wymaga decyzji Architekta oraz progu FN/FP przed pomiarem. Przy tym samo „z o.o.” bez nazwy dostaje dziś osobny FIRMA (L-009: „Sp. FIRMA_001.”): nic nie chroni, a psuje tekst. Rozstrzygnąć razem.
- **`_FIRMA_CLEANUP_RE` (ner_adapter) nadal stratny, gdy zadziała**. Usuwa formę prawną za tokenem, której nie ma w mapie. Po tej poprawce w przeglądzie nie zadziałał ani razu (8 → 0), ale nadal może: np. ta sama firma raz bez formy (encja), raz z formą (podmiana wariantu). Pytanie produktowe: forma prawna jawna za tokenem (wierny tekst) czy dołączona do wartości. Nie zmieniałem tego bez decyzji.
