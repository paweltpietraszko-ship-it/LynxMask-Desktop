# LYNX-PUBLIC-DATA-TESTS etap 1 — DELIVERY round_01

BEFORE_SHA: `b074fa69793ce169a898dfdb2d479c899f211a22` · IMPLEMENTATION_SHA: `d7a08689af663f422e8ed7e3cb1d5a204e3b46f3`
Pliki (TASK_SCOPE): `audyt/engine_quality.py` (+56 l.), nowy `backend/tests/test_engine_quality_layout.py` (82 l.). Produkcja bez zmian (`document_processor._extract_text` tylko odczyt). Rozszerzenia CC: brak.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED): `_extract_text` wołane przez API (/preview, ekstrakcja) i audyt; gałąź DOCX łączy tylko `doc.paragraphs` — komórki tabel nie trafiają do tekstu (potwierdzone pomiarem niżej). PDF: PyMuPDF `page.get_text()`.

## Co zrobione — tryb `--layout <katalog>`
- `measure_layout` + `_layout_doc`: czyta lokalny `manifest.json` (plik, typ, pola: kategoria, dokładna syntetyczna wartość, czy w tabeli), dla każdego pliku produkcyjny `_extract_text(bytes, nazwa)`, potem produkcyjny `pipeline.pseudonymize_document` (ten sam stan TEMP co reszta runnera). Pole: jeśli wartości nie ma w tekście z pliku → `EXTRACTION_MISSING` albo `EXTRACTION_CHANGED` (jest po usunięciu spacji/interpunkcji) — **nigdy `masked`**; jeśli jest → istniejący `classify_m1`. M3 (`roundtrip`) na całym tekście dokumentu. Brak manifestu / pliku / błąd ekstrakcji → `NOT_RUN`; zero zmierzonych pól → `NO_FIELDS_MEASURED` (nie PASS).
- Raport (sekcja `LAYOUT`): ID `L-NNN`, typ, SHA-256 (16 znaków) pliku, status, M3; liczności `typ/miejsce → status`. Bez wartości, nazw plików, tekstu dokumentu. Bez sieci w trakcie pomiaru.
- **Bez `--layout` raport bitowo identyczny** z bazą (sprawdzone: ten sam seed + holdout, porównanie JSON poza datą/SHA → identyczny).

## Próbka (lokalnie, `backend/dataset_layout/` — ignorowane przez git, nic nie commitowane)
- Źródła (oficjalne puste wzory, ręczny wybór, pobrane pojedynczo): gov.pl/web/psse-przemysl/dokumenty-wnioski → „Załącznik nr 2 – Informacja o substancjach chemicznych…” (DOCX, SHA-256 `8d9872675c2723f2…`, 17 tabel, 72 puste komórki) oraz „Pełnomocnictwo” (PDF tekstowy, SHA-256 `d91dba13206eff2f…`, rubryki z wielokropków, bez pól AcroForm). Weryfikacja pustości (tylko liczniki): 0 znaków „@”, 0 ciągów ≥9 cyfr, 0 „Pan/Pani + nazwisko”. Odrzucone kandydatury: 3 inne DOCX z tej strony i wzór umowy z uw-mazowiecki — brak tabel. Strony z briefu działały.
- Wypełnienie: lokalny `backend/dataset_layout/fill_layout.py` (python-docx MIT, pdfplumber MIT, reportlab/pypdf BSD — bez PyMuPDF): DOCX — 3 wartości w pierwszych pustych komórkach 3 różnych tabel (OSOBA, EMAIL, NUMER/NIP) + 1 w akapicie z wykropkowaniem (OSOBA); PDF — 3 wartości (OSOBA, EMAIL, NUMER/PESEL) nadrukowane nad 3 najdłuższymi rubrykami (warstwa tekstowa). Wartości syntetyczne, zapisane w lokalnym manifeście w chwili wypełniania (klucz niezależny od silnika).

## Wynik (exact SHA, seed 2026, dwa przebiegi identyczne)
| typ / miejsce | pól | wynik |
|---|---|---|
| DOCX / tabela | 3 | **EXTRACTION_MISSING 3** — komórki tabel nie trafiają do tekstu |
| DOCX / akapit | 1 | masked 1 |
| PDF / tekst (rubryki formularza) | 3 | masked 3 |
Dokumenty: 2/2 MEASURED, 0 NOT_RUN; pól zmierzonych 7. M3 obu dokumentów: identical (Przywróć 1:1 na całym tekście z pliku).

## Testy
`backend/tests/test_engine_quality_layout.py` (uruchamiany jawnie; produkcyjny extractor + pipeline, NER lokalnie dostępny): DOCX z akapitem i komórką tabeli + PDF (reportlab) → `docx/tabela: EXTRACTION_MISSING`, `docx/tekst: masked`, `pdf/tekst: masked`; raport bez wartości/nazw plików/tekstu; brak manifestu → NOT_RUN, brak pliku → `NO_FIELDS_MEASURED`; klucz w innym zapisie → `EXTRACTION_CHANGED`. Wynik `3 passed`. Testy runnera w `test_audyt` (`-k quality`) `5 passed`; pełna suita `129 passed, 40 skipped, 1 xfailed` (0 failed).

## gate.py (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: d7a08689af663f422e8ed7e3cb1d5a204e3b46f3
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 137/1 = 137.0:1 (threshold 5:1)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r4_repro.py
  - backend\tests\test_audyt_2026_10.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r1.txt
```
WYMAGA_DECYZJI tylko RATIO 137/1: zmiana w całości addytywna (nowy tryb + nowy plik testów), 137 linii < 150.

## Findings (nie naprawiane — brief)
- **LYNX-DOCX-TABLES**: `_extract_text` dla DOCX pomija tabele (oraz nagłówki/stopki) — w realnym wzorze 3/3 wartości z komórek nie docierają do silnika. Skutek dla użytkownika: tekst z tabel w ogóle nie jest analizowany ani pokazywany — przy kopii dokumentu (LYNX-LAYOUT-COPY) byłby to wyciek.
- PDF formularz z polami AcroForm nie był w próbce (wybrany wzór ich nie ma) — wartość wpisana w pole formularza (widget) to osobny wariant do zmierzenia; skan/OCR — osobny wariant.

## Runda 2 — po FAIL r2 (`tests_r2.txt`, `33c7423`)
IMPLEMENTATION_SHA: `638b31813962d2ba071ac02bc7d21cb98481dd9a`.
- **F1 (trafne):** status pola liczony z samego „wartość jest gdzieś w tekście” — ta sama wartość w akapicie i w nieodczytanej komórce dawała oba pola `masked`. Teraz `_layout_doc` porównuje liczbę wystąpień w tekście z liczbą pól klucza o tej samej wartości: wystarczająco → `classify_m1`; mniej (ale >0) → **`EXTRACTION_UNVERIFIED` dla wszystkich tych pól** (nie sukces, brief pkt 3); 0 → `EXTRACTION_MISSING`/`CHANGED` jak dotąd.
- Test `test_powtorzona_wartosc_bez_dowodu_wystapienia` = scenariusz `tests_r2_repro.py` (ten sam e-mail w akapicie i komórce) → oba pola `EXTRACTION_UNVERIFIED`; na `d7a0868` FAIL, teraz PASS. Kontrola z unikalną wartością (`test_komorka_tabeli_to_brak_ekstrakcji_nie_maskowanie`) bez zmian: tabela `EXTRACTION_MISSING`, akapit `masked`. `test_engine_quality_layout.py` `4 passed`; runner `-k quality` `5 passed`; pełna suita `129 passed, 40 skipped, 1 xfailed` (0 failed).
- Pomiar na lokalnej próbce (wartości unikalne) bez zmian: DOCX/tabela 3 EXTRACTION_MISSING, DOCX/akapit 1 masked, PDF 3 masked.
- Rozmiar: 154 linie zmienione (4 ponad próg 150) — kod nieupychany pod próg (zgodnie z uwagą Codexa); decyzja o rozmiarze dla OWNERA.

gate.py (stdout dosłownie, finalny SHA):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 638b31813962d2ba071ac02bc7d21cb98481dd9a
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 153/1 = 153.0:1 (threshold 5:1)
  - TOTAL_LINES: 154 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_evidence.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r4_repro.py
  - backend\tests\test_audyt_2026_10.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/implementation/DELIVERY.md
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/implementation/gate.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r1.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2_evidence.py
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2_repro.py
```

## Runda 3 — po FAIL r3 (`tests_r3.txt`, `d5ad279`)
IMPLEMENTATION_SHA: `d82709c11b77dc51d8cca1107776aa3355674182`.
- **F1 resztkowe (trafne — za wąska poprawka w rundzie 2):** `str.count` liczył wystąpienie krótszej wartości wewnątrz dłuższej („k.zalewska@…” w „anna.k.zalewska@…”). Tym razem poprawka na całą rodzinę: `_own_occurrences` liczy tylko wystąpienia (a) samodzielne — nie przyklejone do znaków słowa/adresu (`[\w.@%+-]` przed, `[\w@%+-]` lub „.znak” po) i (b) nie leżące wewnątrz dłuższej wartości tego samego klucza. Reszta logiki bez zmian (za mało → `EXTRACTION_UNVERIFIED`, zero → `MISSING/CHANGED`).
- Testy rodziny (komórka tabeli nieodczytana, jej wartość jest tylko fragmentem wartości z akapitu): sufiks e-maila (scenariusz r3), nazwisko w „imię + nazwisko”, prefiks dłuższego numeru → tabela nigdy `masked`. Kontrole: dwa osobne wystąpienia tej samej wartości → oba `masked`; unikalna brakująca komórka → `EXTRACTION_MISSING`; scenariusz r2 → `EXTRACTION_UNVERIFIED`. Na `638b318`: 2 z nowych FAIL (sufiks e-maila, nazwisko), teraz wszystkie PASS. `test_engine_quality_layout.py` `8 passed`; runner `-k quality` `5 passed`; pełna suita `129 passed, 40 skipped, 1 xfailed` (0 failed).
- Próbka z gov.pl bez zmian (DOCX tabela 3 MISSING, akapit 1 masked, PDF 3 masked).
- Rozmiar: 191 linii (próg 150) — przyrost to głównie testy rodziny przypadków, nie upychane. Decyzja rozmiaru dla OWNERA.

gate.py (stdout dosłownie, finalny SHA):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: d82709c11b77dc51d8cca1107776aa3355674182
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 190/1 = 190.0:1 (threshold 5:1)
  - TOTAL_LINES: 191 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_evidence.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-PUBLIC-DATA-TESTS\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r2_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r3_repro.py
  - tasks\LYNX-DICT-LEAKTEST\round_01\tests\tests_r4_repro.py
  - backend\tests\test_audyt_2026_10.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/implementation/DELIVERY.md
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/implementation/gate.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r1.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2_evidence.py
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r2_repro.py
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r3.txt
  - tasks/LYNX-PUBLIC-DATA-TESTS/round_01/tests/tests_r3_repro.py
```
