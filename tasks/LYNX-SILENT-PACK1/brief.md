# LYNX-SILENT-PACK1 — ciche wycieki: FIRMA (podwójna forma, powtórzenie skrótem), KWOTA z groszami, końcówki numerów

22.10.2026, CC. Poprawki bez Architekta. Źródła:
- przegląd stanu (`%TEMP%\lynx_cc_review\status_2210\raport.md`): w GOLD test ciche FIRMA 110/320, KWOTA 71/240, NUMER 36/671;
- zgłoszenie OWNERA 22.10 („Jutrzenka sp. z o.o. sp. z o.o.”).

Diagnoza i prototyp: pomocnik CC, `%TEMP%\lynx_cc_review\silent_pack1\` (`raport.md`, `proto.diff`, `test_silent_pack1.py`).
Teksty przykładów syntetyczne (GOLD dev).

## Klasy (przyczyna → poprawka w istniejącym właścicielu)
1. **FIRMA z podwójną formą prawną / zniekształconą nazwą.**
   - Przykłady: „Wykonawca: Jutrzenka sp. z o.o. sp. z o.o.” → dziś „Jutrzenka sp. FIRMA_001” (nazwa jawna); „Zamawiający: Jurzerznka sp. z o.o.” → OSOBA „Jurzerznka sp” + jawne „z o.o.”.
   - Przyczyna:
     - `firma_context._form_start` nie uznaje podwójnej formy za formę, więc encja bez nazwy;
     - `scan_legal_forms` pomija formę nachodzącą na DOWOLNĄ encję (tu OSOBA ze spaCy).
   - Poprawka (`firma_context.py`):
     - łańcuch form (`_FORM_CHAIN_RE`) w `_form_start`;
     - OSOBA zaczynająca się przed formą nie blokuje skanu.
   - Oczekiwane: cała nazwa z formą = jedna FIRMA.
2. **FIRMA powtórzona skrótem bez formy** (`LYNX-FIRMA-BARE-REPEAT`).
   - Przykład: „Filar Północy sp. z o.o. … nazwę Filar Północy stosuje się…” → powtórzenie jawne albo jako OSOBA.
   - Poprawka:
     - helper `firma_core_variants` w `firma_context.py`: rdzeń bez formy, ≥2 słowa z wielkiej litery albo 1 słowo ≥4 litery niebędące zwykłym słowem (Morfeusz); rdzeń wyłącznie z imion/nazwisk pomijany;
     - podmiana całym wyrazem z zachowaniem wielkości liter na TEN SAM token co pełna firma (jedna firma = jeden token; Przywróć daje pełną nazwę — jak przy osobach);
     - OSOBA o wartości równej rdzeniowi → token firmy;
     - `ner_layer.py`: tylko 2 istniejące linie (import + `return` w `process_ner`), plik i `_process_ner` bez wzrostu.
   - Bez zmian: „Most na rzece”, „Punkt 3 umowy”.
3. **KWOTA z groszami bez waluty.**
   - Przykład: „W kolumnie „do zwrotu” zapisano 1049,63; walutą…” → jawne.
   - Przyczyna: `layers/amount._AMOUNT_NOCUR_RE` wymaga spacji tysięcy (`\d{1,3}( \d{3})*,\d{2}`), więc „575,63” tak, „1049,63” nie.
   - Poprawka: `\d{4,6},\d{2}` albo `\d{1,3}(\.\d{3})+,\d{2}` tylko przy słowie kwotowym w tym samym zdaniu (kwota, zwrot, zapłata, należność, saldo, brutto, netto, wartość, cena, wynagrodzenie, opłata, kara, koszt, zł/złoty/PLN, waluta, zaliczka, odsetki, rata, podatek, faktura, wpłata, wypłata, przelew). Wykluczenia jak na main: %, jednostki, „/”, „-”, wersja.
   - Bez zmian: „Wersja 2026,01”, „1234,56 mm”, „1234,50%”, „Pozycja 1049,63 w tabeli”.
4. **Końcówki numerów.**
   - (a) „PO/2026/0329”: wzorzec legitymacji radcy w `credential_patterns.json` kończy się `\b` i tnie dłuższy numer → `(?<![/\w])…/\d{3,6}(?![/\w])`, całość bierze warstwa legal.
   - (b) „numerklienta: K L 7017 O” (numer rozbity spacjami po OCR): `layers/numeric.py` `_NUM_SPACED_RE` — etykieta nr/numer (+ klienta/polisy/umowy/faktury/zamówienia/zlecenia/sprawy, także sklejona), 3–8 członów `[A-Z0-9]{1,4}`, ≥3 cyfry z rzędu. Maskowany sam numer.
   - Bez zmiany tekstu (bez normalizacji spacji) — Przywróć 1:1.

## Poza zakresem (osobne zadania, w BOARD)
- firmy „X Y s.c.” (5 cichych w dev);
- człon opisowy jednoosobowej działalności („Usługi Konserwatorskie …”, 14 w dev — osoba zakryta, opis jawny);
- „Nietoperz” (1);
- e-maile z „@” zepsutym przez OCR (przegląd: 12/13 cichych na obrazach);
- szum R1 na realnych dokumentach.

TASK_SCOPE:
- backend/firma_context.py
- backend/ner_layer.py
- backend/layers/amount.py
- backend/layers/numeric.py
- backend/credential_patterns.json
- backend/tests/test_silent_pack1.py
- tasks/LYNX-SILENT-PACK1/brief.md
- tasks/LYNX-SILENT-PACK1/repo_before.hash
- tasks/LYNX-SILENT-PACK1/round_01/implementation/DELIVERY.md

Szacunek: kod ~80 l. + testy ~115 l. ≈ 200 l. (>150 — zgoda OWNERA przed kodem).

## Odbiór
- `tests/test_silent_pack1.py`: 12 przypadków pozytywnych (na main failują) + 11 negatywnych (bez zmian).
- Regresja bez zmian: `test_firma_context`, `test_layers` (2 znane faile), `test_amounts_numbers`, `test_formats_pack2`, `test_addr_email_leaks`, `test_map_fidelity`, `test_audyt_2026_10` (1 znany fail).
- Pomiar „widok człowieka” GOLD (`tasks/LYNX-GOLD-SET/measure/human_view.py`, dev / test agregaty):
  - prototyp dev: ciche 102 → 20, zbędne 69/440 bez zmian, pytania 1,62 → 1,23;
  - wymagane: 0 nowych zbędnych zakryć, OSOBA/ADRES/EMAIL bez pogorszenia.

## Doprecyzowanie po Codex BRIEF_ONLY r1 (`4a9262a`)
- **B1 — decyzja OWNERA 22.10 („1, jeden token i pełna nazwa”):** gdy dokument zawiera pełną firmę z formą i później jej rdzeń bez formy, oba wystąpienia dostają ten sam `FIRMA_NNN`. Przywróć zwraca w obu miejscach pełną nazwę z formą („Filar Północy” → „Filar Północy sp. z o.o.”). Odbiór jawnie dopuszcza ten wynik. Bez nowej mapy wariantów.
- **B2 — konflikt rdzeni:**
  - dwie różne pełne firmy z tym samym rdzeniem („Filar Północy sp. z o.o.” i „Filar Północy S.A.”): rdzeń nie jest przypisywany do żadnej z nich, tylko dostaje własny token `FIRMA_MMM` z wartością rdzenia (zakryty, bez scalania podmiotów);
  - OSOBA o wartości równej temu rdzeniowi → ten sam własny token rdzenia;
  - rdzeń bez pełnej firmy w dokumencie → bez zmian względem main;
  - test: dwie firmy + skrót → trzy różne tokeny FIRMA; żadna pełna wartość nie zawiera drugiej formy.
- **B3 — rdzeń jednowyrazowy:** istniejący predykat `osoba_not_person._common_or_person(word)`:
  - jakiekolwiek znaczenie pospolite (`common is True`) → nie podmieniamy („Most”, „Punkt”, „Jutrzenka” = świt);
  - brak znaczenia pospolitego (nieznane albo tylko nazwa własna/geograficzna) → podmieniamy;
  - błąd Morfeusza (`None`) → nie podmieniamy;
  - rdzeń ≥2 słów z wielkiej litery — bez sprawdzania Morfeuszem (jak w briefie).

## ROZSZERZENIE CC (po Codex r3 F1, `0979c83`)
- Co: F1 — „Wartość pomiaru 1234,56 mm” → KWOTA (lista jednostek bez „mm”). Ta sama luka istnieje w starym `_AMOUNT_NOCUR_RE` na main („Wartość pomiaru 575,63 mm” → KWOTA) — ta sama klasa (wykluczenie jednostki w kwocie bez waluty).
- Gdzie: `backend/layers/amount.py` — wspólna lista `_UNIT` dla obu wzorców: dodane mm, cm, dm, mg, m3/m³, ml, min, kWh, kW, MWh. Bez jednostek jednoliterowych mylących się z polskim słowem przy IGNORECASE („w”, „t”).
- Reproduktor: `round_01/tests/repro_r3.py` (Codex) + w `test_silent_pack1.py` 5 nowych negatywnych (w tym „575,63 mm” i „2 450,00 cm”) i 1 pozytywny („Kwota 1234,56 w terminie” — „w” nie jest jednostką).
- Pliki: już w TASK_SCOPE.
