# LYNX-FIRMA-SILENT2 — ciche FIRMA: nazwa JDG z opisem działalności, forma „s.c.”, rozcięte powtórzenie nazwy

23.10.2026, CC. Poprawka bez Architekta. Źródła: GOLD dev — wszystkie 20 cichych FIRMA (`human_view.py`, dev; test tylko agregat 52);
opinia Qwena 23.10 (diagnoza z kodu, bez pomiaru) — zweryfikowana na danych: trafne pkt 1 (rozproszone definicje formy) i 5 (granice/kolejność),
reszta (HerBERT, trie, stara ścieżka, odmiana firm) nie występuje w cichych wyciekach GOLD dev. Teksty syntetyczne.

## Klasy (GOLD dev, 20/20 cichych FIRMA; reprodukcja na main `f617ef6`, pełny `pseudonymize_document`)
| klasa | ile | przykład wejścia | wynik main |
|---|---|---|---|
| A. JDG: opis działalności + imię i nazwisko | 14 | „Wykonawca: Usługi Konserwatorskie Cezary Jeż” | „Usługi Konserwatorskie OSOBA_001” (opis jawny; Guard pyta tylko w nagłówku) |
| B. forma „s.c.” nierozpoznana | 5 | „Zamawiający: Perłowy Nawias s.c.” + „nazwę Perłowy Nawias stosuje się…” | całość jawna (Guard R5 pyta tylko o „… s.c.”); powtórzenie cicho |
| C. powtórzenie rozcięte krótszą encją | 1 | „Ulotny Rys sp. z o.o.” + „nazwę Ulotny Rys stosuje się…” | „FIRMA_002 Rys” (spaCy: samo „Ulotny” = FIRMA_002; „Rys” jawne) |

## Zasady (słowami)
- **A — propozycja CC (zakryć za dużo > wyciek), Paweł 23.10 wybrał „Tak”:** nazwa jednoosobowej działalności = rzeczownik działalności
  (Usługi, Biuro, Zakład, Pracownia, Studio, Kancelaria, Gabinet, Warsztat, Firma, Przedsiębiorstwo, Sklep, Hurtownia, Serwis, Salon, Atelier,
  Agencja) + dalsze słowa z wielkiej litery w tej samej linii + **imię i nazwisko** (imię z listy imion) → jedna FIRMA obejmująca całość.
  Bez imienia i nazwiska na końcu — bez zmian („Biuro Rzecznika Praw Pacjenta”, „Zakład Ubezpieczeń Społecznych”).
  Każde wystąpienie tej samej pełnej nazwy w dokumencie — ten sam token. Osoba z tej nazwy wymieniona osobno dalej — jak dziś (OSOBA).
- **B:** „s.c.” po nazwie (≥1 słowo z wielkiej litery przed formą, wg `_name_start`) = forma prawna jak „sp. z o.o.”; nie gdy przed „s.c.”
  stoją same inicjały („J. S.C.”) ani bez nazwy. Powtórzenie rdzenia bez formy — istniejący mechanizm SILENT-PACK1 (`firma_core_variants`).
- **C:** krótsza encja zawarta w wystąpieniu dłuższej znanej wartości (rdzeń pełnej firmy) nie blokuje dłuższej — wygrywa dłuższe
  (ta sama zasada co `LYNX-AMOUNT-OCR-MULT` w kwotach).
- Guard bez zmian.

## Właściciele (do potwierdzenia w prechecku)
- A, B: `backend/firma_context.py` (153 l.) — nowa funkcja JDG obok `scan_legal_forms`; „s.c.” w skanie form.
- Wpięcie: `backend/ner_layer.py` (597 l., limit 600 — tylko podmiana istniejącej linii w `_firma_entities`, bez wzrostu).
- C: tam, gdzie rdzeń z `firma_core_variants` przegrywa z krótszą encją spaCy (`ner_layer`/`layers/ner_adapter.py`, kolejność podmian) —
  owner wskazany po diagnozie w implementacji; bez wzrostu `ner_layer.py`.

## Bez zmian (negatywy)
„Biuro Rzecznika Praw Pacjenta”, „Zakład Ubezpieczeń Społecznych”, „Usługi informatyczne świadczy Jan Nowak” (mała litera — nie nazwa),
„Kancelaria Notarialna w Krakowie” (bez osoby), „J. S.C.” (inicjały), istniejące testy FIRMA (`test_firma_context`, `test_silent_pack1`,
`test_formats_pack2`) i OSOBA (`test_osoba_layout`).

TASK_SCOPE:
- backend/firma_context.py
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/tests/test_firma_silent2.py
- tasks/LYNX-FIRMA-SILENT2/brief.md
- tasks/LYNX-FIRMA-SILENT2/repo_before.hash
- tasks/LYNX-FIRMA-SILENT2/round_01/implementation/DELIVERY.md

Szacunek: kod ~50 l., testy ~60 l.

## Odbiór
- `tests/test_firma_silent2.py`: przykłady A/B/C → całość zakryta (na main failują); negatywy bez zmian.
- Regresja: `test_firma_context`, `test_silent_pack1`, `test_formats_pack2`, `test_map_fidelity`, `test_osoba_layout`, `test_layers` (2 znane).
- Pomiar GOLD dev/test (`human_view.py`): ciche FIRMA dev 20 → oczekiwane ≤2, test 52 → spadek; zbędne zakrycia nie rosną;
  `testset_owner` bez pogorszenia.
