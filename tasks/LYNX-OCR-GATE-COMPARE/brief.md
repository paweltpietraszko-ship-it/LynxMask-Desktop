# Brief — LYNX-OCR-GATE-COMPARE: łańcuch zdjęcie → PP → silnik → (HerBERT) → Guard-reszta (jeden blok: pomiar + naprawy z niego)

STATUS: BRIEF v3.3 (CC; v3.3 = C3 doprecyzowane po prechecku Codexa r1 `caf7faa`; po recenzjach Architekta `ARCH_REVIEW_2026-10-20.md` @ `5154057` — C1–C4 — i `ARCH_REVIEW_V3_2026-10-20.md`
@ `5eea65b` — F1, F2 i dwie uwagi redakcyjne wprowadzone)
→ Codex BRIEF_ONLY → zgoda OWNERA na rozmiar → CC implementuje ETAP 1 (pomiar) → ETAP 2 (naprawy w silniku wskazane pomiarem) →
Codex audytuje exact SHA. **Jeden Task zamiast kilku** (OWNER 20.10: „nie mnóż zadań, jeśli mogą iść w jednym bloku — im więcej
szwów, tym większy patchwork”): wchłania wiersze BOARD `LYNX-OCR-QUALITY-GATE`, `LYNX-OCR-ORIENTATION`, `LYNX-ANCHOR-PARITY`.
PASS Codexa ≠ zgoda OWNERA na implementację/merge. Merge tylko na polecenie OWNERA.
PRODUCT_TRUTH: `arch/spec.md` S1, S2, S3, S5 (S4 zamrożone — bez zmian); `BOARD.md` → TERAZ (cel: każde słowo wysyłane dalej jest
zakryte albo pokazane człowiekowi), wiersze `LYNX-GUARD-RESIDUE`, `LYNX-K1-PERSONS-FIRMS`, `LYNX-OCR-ORIENTATION`, `LYNX-ANCHOR-PARITY`;
C1 (`tasks/LYNX-OCR-CASCADE/round_01/implementation/DELIVERY.md`).

## Cel produktu i pytanie
Silnik (warstwy + Morfeusz + kotwice) zakrywa, co rozpoznaje; HerBERT jako siatka; Guard pokazuje człowiekowi resztę. Na skanach
z Tesseractem łańcuch zawodzi (walidacja CC 20.10: 5 dziur, ~9 pytań/dok.), bo OCR niszczy tekst.
**Pytanie:** czy łańcuch zdjęcie → wyprostowanie → PP-OCRv6 → istniejący `/preview` → (HerBERT) → Guard-reszta mieści się na
zdjęciach w **zapisanych niżej kryteriach** — na tyle, by napisać brief implementacji produktu (`READY_FOR_PRODUCT_BRIEF`)?
Wynik **nie** oznacza „bezpieczne / gotowe do wydania” ani parytetu z czystym tekstem (C1).

Ustalone wcześniej, nie badane ponownie: PP czyta, Tesseract nie poprawia PP i nie mierzy jakości (C1, oko OWNERA); silnik zakrywa
uszkodzone identyfikatory po etykiecie bez sumy kontrolnej; znane dziury (data „ur.” z literą zamiast cyfry, końcówka NIP) → ETAP 2.

## C1 — dane i punkty odniesienia (bez parytetu)
- **Zdjęcia (decyzja):** `backend/dataset_20260627_095419` (50, znany — wybór N), `backend/dataset_20261016_fresh` (100, holdout —
  jeden raz, po zamrożeniu reguł commitem); wyniki per dokument i per poziom degradacji L0–L3.
- **Odniesienie orientacyjne (osobno, bez relacji procentowej):** ten sam pomiar w trybie tekstowym na `dataset_clean` z repo Mobile
  (`paweltpietraszko-ship-it/LynxMask`, lokalnie u CC/Codexa; inne dokumenty niż zdjęcia). Służy kalibracji narzędzia, nie kryterium.
- **Dzisiejszy produkt** (Tesseract bez prostowania, bramka 70) tym samym narzędziem — kontekst, nie kryterium.
- **Realne zdjęcia OWNERA** `backend/dataset_real/images/*.jpg`: tylko agregaty (obrót, would_ask, odmowa, czas), bez nazw plików
  i tekstu; poprawność ocenia oko OWNERA na pliku lokalnym poza repo. Bez gold → poza kryterium.

## C2 — rzeczywisty łańcuch vs symulacja (rozdzielone w raporcie)
- **REAL_MASKING_PIPELINE:** prawdziwy silnik maskowania i obecny Output Guard — `/preview` dostaje **tekst `.txt` z osobno
  uruchomionego OCR (PP + P1)**, nie zdjęcie; to **nie** jest produkcyjne E2E „obraz → `/preview`” (to zostaje do briefu wdrożenia).
  Odpowiedź `/preview` (tekst `anonymized_preview`, `blocked`, `guard_blocked`, `guard_reasons`,
  `tokens`). Dokument z `blocked`/`guard_blocked=true` lub błędem = **zablokowany** (osobna kategoria), jego podgląd nie jest
  liczony jako wynik do skopiowania ani jako potwierdzenie maskowania.
- **HYPOTHETICAL_GUARD:** `would_ask` — słowa, o które Guard-reszta zapytałby (reguła niżej). To symulacja: nie dowodzi, że
  użytkownik zobaczy pytanie ani że wyjście jest wstrzymane do jego decyzji.
- **HYPOTHETICAL_HERBERT** (ramię opcjonalne): encje PER/ORG/LOC z lokalnego ONNX na tekście po `/preview` → `would_mask`.
  Nie dodaje tokenów do zaszyfrowanej mapy (S1/S2) — mierzy **potencjał** zmniejszenia pytań/dziur, nie gotowość produktu.
  Brak modelu (`~/lynx_models/herbert-polish-legal-ner`) lub błąd inferencji → `NOT_RUN(HerBERT)`; pomiar bazowy się nie zmienia.
- **Statusy wartości gold** (rozłączne, dla dokumentów niezablokowanych): `MASKED` (brak w tekście, jest w `tokens`), `ASKED`
  (widoczna, ale w `would_ask`), `HOLE` (widoczna całość lub fragment ≥ 4 znaki alfanumeryczne i nie w `would_ask`),
  `UNKNOWN_REVIEW` (reguła fragmentu nie rozstrzyga: OCR zmienił większość znaków, cyfry rozbite na grupy < 4, wartość nieobecna
  w odczycie PP, ale coś podobnego zostało w tekście), `NOT_IN_OCR` (brak w odczycie PP — kompletność, nie wyciek).
  `UNKNOWN_REVIEW` nigdy nie liczy się jako sukces; **listę przegląda CC** (syntetyki — wolno) i wpisuje rozstrzygnięcie każdego
  przypadku do DELIVERY przed werdyktem; Codex weryfikuje w audycie.

## C3 — izolacja pomiaru (v3.3 po prechecku Codexa r1 C1: start API)
`/preview` i start API zmieniają stan. Zapisy względem `__file__` (nie cwd/env): `_API_TOKEN_PATH` (`api_token.txt`, kasowany i
zapisywany w `_lifespan`), `_STARTUP_ERROR_PATH` (`startup_error.json`), `PSE_REGISTRY` domyślnie, `dict_auto_builder.BACKEND_DIR`;
względem cwd: `pseudominizer_audit.jsonl` (`record_preview`), `ARCHIVE_DIR`, `HARDWARE_PROFILE`; profil `ANONYMIZER_PROFILE_DIR`;
odczyt allowlisty Guarda z `PROFILE_DIR` (domyślnie `~/.pseudominizer/profile`). Dlatego:
- **Jednorazowa kopia backendu:** dla każdego przebiegu (wariant × zbiór) harness tworzy świeży katalog tymczasowy i rozpakowuje do
  niego `git archive <exact SHA> backend` (tylko pliki śledzone, ~13 MB). Proces pomiaru importuje API **z tej kopii** — wszystkie
  ścieżki zależne od `__file__` (token, błąd startu, PSE, `BACKEND_DIR`) trafiają do kopii, bez nadpisywania stałych modułów.
- **Pełny start rzeczywistego silnika:** `with TestClient(app, base_url="http://127.0.0.1:8765") as c:` — kontekst uruchamia
  `_lifespan` (anonimizator, mapa, Morfeusz, moduły) dokładnie jak w produkcie. Brak udanego startu (np. `startup_error.json` w kopii,
  wyjątek, `/health` ≠ OK) → `NOT_RUN(STARTUP)`, nie wynik.
- **Env procesu pomiaru:** cwd = kopia; `ANONYMIZER_PROFILE_DIR`, `PROFILE_DIR`, `PSE_REGISTRY`, `ARCHIVE_DIR`, `HARDWARE_PROFILE`
  wskazują do kopii; profil = pusty profil testowy tworzony od zera. Modele (`~/lynx_models`, pakiety Pythona) tylko odczyt.
- **Zakaz atrap:** nie wolno stubować, monkeypatchować ani pomijać maskowania, Guarda, `_lifespan`, OCR ani `/preview`; jedyne
  „override” to zmienne środowiskowe i cwd wymienione wyżej. Wynik z jakąkolwiek atrapą ≠ `REAL_MASKING_PIPELINE`.
- **Migawka przed/po** (ścieżka, rozmiar, mtime): `backend/` repo, katalog backendu OWNERA, `~/.pseudominizer/`, `~/lynx_models/`;
  **każda zmiana poza kopią tymczasową → `NOT_RUN(ISOLATION)`**, nie PASS. Kopia usuwana po przebiegu (po zapisaniu raportu).
- Bez zmian kodu produktu; jeżeli start w kopii okaże się niemożliwy bez zmiany produktu → STOP i zgłoszenie przed kodem.
- **Próba wykonalności CC (20.10, przed kodem, poza repo):** `git archive 052f1d7 backend` → kopia tymczasowa; env jak wyżej;
  `with TestClient(app)` → `_lifespan` pełny: `/health` 200 (`anonymizer: True, spacy_ner: True, morfeusz: native, crypto_ok: True`),
  `/preview` na syntetycznym `.txt` zamaskował osobę, PESEL i datę „ur.”, licznik PSE w kopii od `0001`; start ~7 s.
  `find -mmin -3` na `backend/` repo, katalogu backendu OWNERA i `~/.pseudominizer` — brak zmienionych plików; kopia usunięta.
Powód izolacji = **porównywalność** (identyczny stan początkowy każdego wariantu), nie prywatność: OWNER 20.10 potwierdził, że
backend 8765 to wersja deweloperska z danymi testowymi. Sprawdzenia ręczne CC mogą iść na 8765; pomiar — w izolacji.

## Guard-reszta w symulacji (reguła zamrożona przed pomiarem, w kodzie skryptu)
Słowo po `/preview`, niebędące tokenem, trafia do `would_ask`, chyba że jest bezsporne: zwykłe słowo Morfeusza bez interpretacji
imienia/nazwiska/nazwy własnej, skrót z listy, liczba ≤ 4 cyfry, data bez kotwicy. **Zawsze pytamy:** słowo z wielkiej litery
z interpretacją imienia/nazwiska, słowo nieznane Morfeuszowi, ciągi z cyframi/kodami, sąsiadujące krótkie grupy cyfr (≥ 2 grupy
w odległości ≤ 1 słowa), data przy „ur.”. Reguła = walidacja CC 20.10 (`LYNX-GUARD-RESIDUE`); różnice w DELIVERY.

## Prostowanie (P1; P2 tylko gdy P1 za wolny)
P1: dla obrotów 0/90/180/270 odczyt PP; wybór = najwyższy **odsetek** słów (≥ 3 litery) znanych Morfeuszowi, przy minimum 20 słów;
poniżej minimum lub remis (różnica < 0,02) → kolejność 0, 90, 270, 180. Trafność na kopiach syntetyków obróconych w pamięci
(90/180/270) + czas. **Decyzja o obrocie liczona na pomniejszonych kopiach** (dłuższy bok 1000 px), pełny odczyt PP tylko raz,
na wybranym obrocie. Cel użytkowy (zapisany przed pomiarem): **czas samej decyzji o obrocie ≤ 3 s na stronę** (maszyna OWNERA,
i7/32 GB) i trafność ≥ 98% na obróconych kopiach. P2 (klasyfikator `PP-LCNet_x1_0_doc_ori`) w tym samym Tasku tylko gdy P1 nie
spełni któregoś warunku — z lokalnym ONNX o jawnym źródle/SHA/licencji i testem zgodności; brak wiarygodnego ONNX → `NOT_RUN(P2)`,
zapisane jako ryzyko produktu; bez pobierania/konwersji wag „po cichu” w trakcie badania; inaczej niepotrzebny. Wynik P1 to zarazem specyfikacja prostowania w produkcie (kontrakt produktu po pomiarze).

## C4 — reguła odmowy N i kryteria (zapisane przed implementacją)
- **Reguła wewnętrzna:** dokument odrzucony, gdy `would_ask` / liczba stron > N. Użytkownik nie widzi liczby; komunikat odmowy
  (propozycja OWNERA, do kontraktu produktu): „Popraw ujęcie: skorzystaj ze skanera, ustaw lepsze światło i kąt aparatu” + „albo wklej tekst dokumentu”.
- **Wybór N (deterministyczny, tylko 50 znanych):** siatka N ∈ {15, 20, 30, 40, ∞}. Dopuszczalne N: 0 `HOLE` krytycznych w
  przyjętych, 0 odrzuconych L0. Spośród dopuszczalnych wybierz N z **największą liczbą przyjętych dokumentów**; remis → większe N.
  Brak dopuszczalnego → `NO_RULE` (pomiar holdoutu i tak raportowany przy N = ∞, werdykt `NOT_READY`).
- **Pełne mianowniki zawsze:** 50/100 dokumentów: przyjęte / odrzucone przez N / zablokowane (REAL_MASKING_PIPELINE) / błąd; wartości gold:
  w odczycie / `NOT_IN_OCR`; statusy C2 per typ, krytyczne osobno, per poziom L0–L3.
- **Kryteria `READY_FOR_PRODUCT_BRIEF` (holdout, wybrane N):** (1) 0 `HOLE` krytycznych; (2) `HOLE` niekrytyczne ≤ 1 na 100
  przyjętych; (3) każdy `UNKNOWN_REVIEW` rozstrzygnięty w DELIVERY i żaden nie okazał się wyciekiem krytycznym; (4) odrzucone:
  L0 = 0, L1 ≤ 5%; przyjętych łącznie ≥ 80%; (5) mediana `would_ask` na dokument ≤ 8 (≈ 2 × 4 z odniesienia orientacyjnego, liczba
  absolutna); (6) izolacja wykazana. Bezpieczeństwo (1–3), uciążliwość (5) i kompletność (`NOT_IN_OCR`) raportowane osobno;
  „0 dziur” osiągnięte przez odrzucenie > 20% dokumentów nie spełnia (4). Inaczej `NOT_READY` z główną przyczyną
  (OCR / silnik / reguła Guarda / próg) — następny krok wynika z przyczyny, nie z kolejnego progu.

## ETAP 1 — pomiar (produkt bez zmian)
`tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py`: reużywa przez import `ocr_rapid`, `pp_quality` (hashe/preflight),
`benchmark` (`_CRITICAL_KEYS`, `_ENTITY_TYPE_MAP`), `benchmark_ocr_diagnostics` (`classify_miss`, `norm`); handler `/preview`
przez `TestClient` w izolowanym podprocesie (C3); HerBERT minimalnym wywołaniem ONNX. Raport JSON tylko do `--out` poza repo:
ID syntetyków, klucze/typy, statusy, liczby, czasy, SHA kodu/modeli/danych; zero wartości, tekstu OCR, nazw plików realnych.
Testy `backend/tests/test_ocr_chain_compare.py` (bez modeli, na sztucznych tekstach i atrapie odpowiedzi `/preview`): reguła
Guard-reszty (nazwisko-zwykłe słowo z wielkiej litery → pytanie; rozbity telefon → pytanie; zwykłe słowo → nie); statusy C2 na
uszkodzonym NIP, IBAN i telefonie w grupach (`HOLE` vs `UNKNOWN_REVIEW` vs `ASKED`); zablokowany dokument nie liczy się jako
przyjęty; wybór N wg funkcji C4 (w tym `NO_RULE`); P1 tie-break; wykrycie zapisu poza katalogiem tymczasowym → `NOT_RUN(ISOLATION)`;
`NOT_RUN(HerBERT)` bez modelu; odmowa `dataset_real` w trybie gold i `--out` w repo; determinizm dwóch przebiegów (poza czasem).

## Bramka wewnętrzna między etapami (jeden Task, dwie rundy)
1. **ETAP 1 zamknięty przed ETAPEM 2:** skrypt, reguły (Guard-reszta, definicje statusów, fragment ≥ 4), funkcja wyboru N i raport
   50/100 zamrożone na exact SHA (commit `ETAP1-FROZEN`, SHA w DELIVERY); zapisane: werdykt bazowy, wszystkie `HOLE`/`UNKNOWN_REVIEW`
   z rozstrzygnięciem, odrzucone obrazy i przyczyny. Po tym commicie **nie wolno zmieniać** N, definicji dziury ani reguł symulacji;
   Codex wykrywa to porównaniem `chain_compare.py` / reguł z SHA `ETAP1-FROZEN`.
2. **ETAP 2 — tylko potwierdzone błędy silnika** klasy „kotwica + wartość uszkodzona przez OCR”, przypisane do istniejącego właściciela
   (`layers/identity.py`, `layers/numeric.py`), wzorem AnchorEngine Mobile (kotwica + klasa cyfropodobnych `[0-9OolIiSsBbZz]`, bez sumy).
   Każdy: test padający **przed** poprawką i przechodzący po niej. Nie poprawiać wszystkiego, co jest `UNKNOWN_REVIEW`; `HOLE` może być
   błędem OCR, metryki albo symulacji Guarda — wtedy wniosek w DELIVERY, nie kod. Brak potwierdzonych błędów tej klasy → `ETAP2 = NO_CHANGE`.
   Znane już przed pomiarem (kandydaci, nadal wymagają reproduktora): `ur. 12.O3.1985` niezamaskowane (`layers/identity.py`, wzorzec
   „ur.” wymaga `\d`); `NIP: 742-33-75-90 | PESEL: …` → `NUMER_006-90` (końcówka jawna).
3. **Po poprawkach:** testy celowane + strażnik `benchmark.py` (274/290, krytyczne 0/107, bez spadku) + ponowne porównanie 50/100 tym
   samym zamrożonym skryptem. Ponowne 100 to **regresja na już obejrzanym zbiorze**, nie nowy holdout dowodzący uogólnienia.
   DELIVERY podaje werdykt `READY_FOR_PRODUCT_BRIEF`/`NOT_READY` **osobno dla wyniku bazowego (ETAP 1) i po poprawkach (ETAP 2)**,
   z tym ograniczeniem dowodowym. Codex audytuje końcowy exact SHA z oboma zestawami dowodów.
Testy ETAPU 2 trafiają do `backend/tests/test_ocr_chain_compare.py` (limit gate: 2 nowe pliki).
**ETAP 2 — przyczyny potwierdzone reproduktorem przed kodem (CC, 20.10, po `ETAP1-FROZEN` `32ea383`):** (1) `layers/address.py::_ascii_fold` gubi „ł/Ł” (NFD nie rozkłada ł) → „Bielsko-Biała”→„Bielsko-Biaa”, OCR „Biala”/„Lodz”/„Glogow” nie pasuje do SIMC → miasto jawne przy tokenie ADRES; (2) `layers/contact.py::_EMAIL_OCR_RE` — TLD tylko `[a-zA-Z]`, OCR „.pì” → e-mail w całości jawny; (3) `layers/identity.py::_NIP_RE_OCR` dopasowuje „373251.0081” z numeru działki i urywa „.9795”; (4) `layers/contact.py::_PHONE_322_RE` dopasowuje „742-33-75” z 9-cyfrowego NIP i urywa „-90”; (5) wzorzec „ur.” wymaga `\d` → `ur. 12.O3.1985` jawne. Pliki `contact.py`, `address.py` dopisane do TASK_SCOPE przed kodem; `numeric.py` bez zmian.
**ETAP 2b (OWNER 20.10: „Tak” — dopisać do tego bloku zamiast osobnego Tasku):** samotne imię/nazwisko ze słownika (test Mobile `testy/test_imiona_nazwiska_100_11_07.txt`: Desktop zostawia jawne Grażyna, Sergiej, Diego, Wiktoria, Kalina, Jankowski, Kwiatkowski; Mobile golden — wszystkie zakryte). Przyczyny: (a) Desktop używa słowników imion/nazwisk tylko obok osoby rozpoznanej przez spaCy, Mobile `NameEngine` 3a maskuje słowo ze słownika także samotnie (z `OSOBA_DENYLIST` i białymi listami); (b) Desktop `names_inflected.json` ma 199 imion, Mobile 3609. Port: reguła 3a w `layers/ner_adapter.py` (wywołanie zamiast istniejącej linii `_apply_first_names`, funkcja `apply_ner_layer` nie rośnie) + słownik imion Mobile ∪ 11 zdrobnień Desktop (format: jedno imię na linię). Nazwiska: zostaje `surnames_top1000.json` (39 tys. Mobile — osobna decyzja: pamięć/nadmaskowanie). Inna klasa niż „kotwica + OCR” — świadome rozszerzenie bloku na polecenie OWNERA.

TASK_SCOPE:
- tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py
- backend/tests/test_ocr_chain_compare.py
- backend/layers/identity.py
- backend/layers/numeric.py
- backend/layers/contact.py
- backend/layers/address.py
- backend/layers/ner_adapter.py
- backend/names_inflected.json
- backend/tests/test_ner_multiline.py

OUT_OF_SCOPE: zmiany produkcyjne poza ETAPEM 2 (OCR, `/preview`, Guard, HerBERT w produkcie, progi, prostowanie w produkcie,
UI/onboarding, S4), aktywacja PP, przeniesienie N do polityki produktu, realne dane w repo, pełna suita. Wdrożenie łańcucha w produkcie
(PP + prostowanie + reguła odmowy + komunikat) = kontrakt po werdykcie `READY_FOR_PRODUCT_BRIEF`.

GATE: dokładnie dwa nowe pliki (`chain_compare.py`, `test_ocr_chain_compare.py`) ≤ 600 l., funkcje ≤ 50 l.; `identity.py`/`numeric.py` istniejące. **Przegląd redukcyjny CC:** z P2 warunkowym i HerBERT jako ramieniem opcjonalnym
pomiar jest wykonalny bez fałszywego uproszczenia; szacunek ETAP 1: skrypt ~420 l. + testy ~160 l.; ETAP 2: ~60–100 l. (wzorce +
testy); razem ≈ 650 l. (> 150) → zgoda OWNERA przed kodem. Pliki istniejące (`identity.py`, `numeric.py`) — reguła ratchet gate.
Jeżeli w implementacji skrypt przekroczy 600 l., HerBERT wydzielany jest do kolejnej rundy, nie upychany.

PRZEKAZANIE: Codex → BRIEF_ONLY precheck `tasks/LYNX-OCR-GATE-COMPARE/round_01/tests/tests_r1.txt` (bez uruchamiania modeli, bez
zmian produktu); CC po PASS pyta OWNERA o rozmiar; implementacja dopiero po zgodzie.
