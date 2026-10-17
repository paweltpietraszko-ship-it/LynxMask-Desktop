# LYNX-ZUS-BOXED-IDS — DELIVERY round_01 (CC)

Gałąź `task/LYNX-ZUS-BOXED-IDS`. **Synchronizacja (wymóg r1):** merge `main` 29f130b → `5837c3c` (zawiera NEWLINE-CROSSING 61ef3a8 i DOCX-TABLES 57e39fb). Baza diagnozy i gate: `29f130b2f15f3bc32eb39d48658d49d07bc4d9eb` (= merge-base z origin/main). Implementacja: `fc084aff9b5731ab54929dcd2dcb45d7ee3747e9`.
Pliki (TASK_SCOPE): `backend/document_processor.py` (+24/−1), `backend/tests/test_engine_quality_layout.py` (+55). Artefakt: `round_01/implementation/comb_sweep.py`. Rozszerzenia CC: brak.

## Ocena briefu
Zgodny z kodem; przyjęty. `where.py` (REQUIRED): `_extract_text` wołane przez API (/preview, ekstrakcja), audyt i repro; gałąź PDF = `"\n".join(page.get_text() for page in doc)`, bez odczytu pól.

## Krok 0 — diagnoza (lokalna próbka, tylko liczby)
- 4 pliki ZUS AcroForm, 6 pól NUMER (2 NIP, 4 PESEL). **Źródło: WIDGET_GROUP 6/6** — każdy identyfikator to JEDNO pole tekstowe AcroForm z flagą comb (Ff bit 25), `MaxLen` = długość wartości (10/11), `field_value` = pełna wartość.
- Mechanizm: wygląd pola comb rysuje znak w każdej kratce; `page.get_text()` zwraca je cyfrą na linię. Dla 6/6: `get_text(clip=rect pola)` == znaki wartości po jednym na linię, a ten ciąg występuje w tekście strony dokładnie raz. TEXT_LAYER 0, AMBIGUOUS 0.
- Świeża baza (29f130b), produkcyjny pion `_extract_text` → `pipeline.pseudonymize_document` (NER/Morfeusz włączone): **4 jawne, 2 bez pełnej wartości w mapie** (zgodne z historycznym findingiem). Granice: jednoznaczne, z samego pola — bez łączenia linii, bez innego ownera. Brak STOP.

## Zmiana
`_pdf_page_text(page)` w gałęzi PDF: dla pól comb z wartością 10/11 cyfr ASCII, jeśli tekst wyglądu pola (clip) to dokładnie te cyfry po jednej na linię, ciąg od początku linii zastępowany wartością pola + `\n` — tylko gdy liczba wystąpień = liczba pól z tą wartością (inaczej tekst bez zmian). Dłuższe wartości najpierw (NIP będący początkiem PESEL-u). Kontrakt `_extract_text` bez zmian; PDF bez formularza, inne pola comb, zwykłe pola, DOCX/TXT/OCR bez zmian.
**F3 (wierność):** extractor zmienia reprezentację pola z „cyfra na linię” na jedną linię z wartością. Przywróć odtwarza dokładnie tekst przekazany do maskowania (M3 identical), nie układ wizualny PDF.

## Dowody
1. **Próbka przed/po** (`audyt/engine_quality.py --seed 2026 --layout backend/dataset_layout`, raport poza repo): ten sam `input_digest`, te same sha256 wszystkich 20 plików; M1/M2/M3/HOLDOUT identyczne.
   pdf/tabela: przed `masked 22, blocked 3, leak_partial 1, leak 1, EXTRACTION_CHANGED 6, EXTRACTION_MISSING 1` → po `masked 28, blocked 3, leak_partial 1, leak 1, EXTRACTION_MISSING 1`. Pozostałe lokalizacje identyczne; M3 czterech plików ZUS: identical.
   Pion produkcyjny dla 6 pól: przed `raw 4, partial/other 2` → po `masked_whole 6` (jeden NUMER na całość, pełna wartość w mapie, żadna cyfra pola jawna).
2. **Testy** `backend/tests/test_engine_quality_layout.py` (uruchamiane jawnie): 15 passed. Na bazowym extractorze 4 nowe failed (RED → GREEN); kontrola „zwykłe pole” przechodzi w obu. Reproduktor: pusty formularz reportlab + wypełnienie pypdf (ten sam mechanizm co próbka ZUS), nie PDF tekstowy.
   Kontrpróby: PESEL i NIP w sąsiednich polach (cyfry w kolejnych liniach) — każdy osobno; telefon comb 9, data comb 8 i 11 osobnych pól jednoznakowych nie są łączone; ten sam PESEL w dwóch polach; NIP = początek PESEL-u; PESEL w zwykłym polu; PESEL także w 11 osobnych kratkach → granica niepewna, tekst bez zmian (bez zgadywania).
3. **`comb_sweep.py`** (z `backend/`): 9 rodzajów pól (PESEL, NIP, NIP-prefiks PESEL-u, powtórzony PESEL, telefon/data/REGON comb, PESEL zwykły, tekst comb 11) — każda para w obu kolejnościach + pojedyncze + 11 osobnych kratek + formularz dwustronicowy = 83 dokumenty × full/Express = 166 — **problemy 0** (tekst = bazowy z podmienionymi tylko polami PESEL/NIP, wartość raz w całości, brak jawnej wartości, jeden wpis w mapie, liczba linii zachowana, Przywróć dokładny, brak tokenu w tokenie). Na bazie: 57/57 dokumentów z PESEL/NIP comb bez pełnej wartości (przegląd wykrywa stary błąd).
4. Wcześniejsze przeglądy: `table_sweep` 224 — problemy 0; `line_pairs_sweep` 132×2 — problemy 0.
5. Pełna suita `cd backend && py -3 -m pytest tests/ -q`: 129 passed, 40 skipped, 1 xfailed. `test_audyt_2026_10.py`: 131 passed, 10 xfailed. Ruff: 2 błędy istniejące już na bazie (F401/E731 w bloku OCR), nowych 0.

## gate.py (stdout dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: fc084aff9b5731ab54929dcd2dcb45d7ee3747e9
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 79/1 = 79.0:1 (threshold 5:1)
```
(IMPORTERS_FOR_REVIEW i EXCLUDED_ARTIFACTS w `gate.txt`.) RATIO: nowa funkcja + testy, zmieniona 1 linia; rozmiar 79 < 150. Wymaga akceptacji rozmiaru.

## Findingi (nie naprawiane)
- **LYNX-COMB-OTHER-FIELDS:** inne pola comb (REGON 9/14, daty, kody, nazwiska litera-na-kratkę) nadal dają znak na linię — poza zakresem briefu (tylko PESEL/NIP). Ten sam mechanizm i ta sama funkcja; nazwisko litera-na-linię nie zostanie rozpoznane przez NER. Propozycja: osobny brief — grupować każde pole comb z wartością (jest wartością pola, nie zgadywaniem), z pomiarem na próbce.
- **PDF bez pola (spłaszczony formularz / skan):** granic z pola brak — poza tym Taskiem; wymaga osobnej diagnozy (układ kratek) i progu FN/FP.
- **LYNX-PDF-LICENSE:** poprawka używa API pól PyMuPDF w istniejącej gałęzi `_extract_text` (bez nowej zależności). Przy wymianie biblioteki odpowiedniki w pypdf (BSD): `/FT`, `/Ff`, `/MaxLen`, `/V`, `/Rect` — test `test_pole_kratkowe_*` musi przejść także po wymianie.
