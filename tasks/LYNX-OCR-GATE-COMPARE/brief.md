# Brief — LYNX-OCR-GATE-COMPARE: czy łańcuch PP → silnik → (HerBERT) → Guard-reszta działa na zdjęciach?

STATUS: BRIEF v3 (CC, po recenzji Architekta `ARCH_REVIEW_2026-10-20.md` @ `5154057`: C1–C4 i uwagi niefatalne wprowadzone)
→ Codex BRIEF_ONLY → zgoda OWNERA na rozmiar → CC implementuje → Codex audytuje exact SHA. Pomiar offline, produkt bez zmian.
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
uszkodzone identyfikatory po etykiecie bez sumy kontrolnej (dziury → `LYNX-ANCHOR-PARITY`, osobny Task, poza tym zakresem).

## C1 — dane i punkty odniesienia (bez parytetu)
- **Zdjęcia (decyzja):** `backend/dataset_20260627_095419` (50, znany — wybór N), `backend/dataset_20261016_fresh` (100, holdout —
  jeden raz, po zamrożeniu reguł commitem); wyniki per dokument i per poziom degradacji L0–L3.
- **Odniesienie orientacyjne (osobno, bez relacji procentowej):** ten sam pomiar w trybie tekstowym na `dataset_clean` z repo Mobile
  (`paweltpietraszko-ship-it/LynxMask`, lokalnie u CC/Codexa; inne dokumenty niż zdjęcia). Służy kalibracji narzędzia, nie kryterium.
- **Dzisiejszy produkt** (Tesseract bez prostowania, bramka 70) tym samym narzędziem — kontekst, nie kryterium.
- **Realne zdjęcia OWNERA** `backend/dataset_real/images/*.jpg`: tylko agregaty (obrót, would_ask, odmowa, czas), bez nazw plików
  i tekstu; poprawność ocenia oko OWNERA na pliku lokalnym poza repo. Bez gold → poza kryterium.

## C2 — rzeczywisty łańcuch vs symulacja (rozdzielone w raporcie)
- **REAL_PIPELINE:** odpowiedź prawdziwego `/preview` (tekst `anonymized_preview`, `blocked`, `guard_blocked`, `guard_reasons`,
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

## C3 — izolacja pomiaru (bez backendu OWNERA na 8765)
`/preview` zmienia stan (`_next_pse()` → `pse_registry.json`, `record_preview()` → `pseudominizer_audit.jsonl` względem cwd,
archiwum `ARCHIVE_DIR`, profil `ANONYMIZER_PROFILE_DIR`, `HARDWARE_PROFILE`). Dlatego:
- pomiar woła **prawdziwy handler `/preview` w osobnym procesie** przez FastAPI `TestClient` (bez portu, `base_url`
  `http://127.0.0.1:8765` dla `_ALLOWED_HOSTS`), uruchomionym z **cwd = świeży katalog tymczasowy** i zmiennymi `PSE_REGISTRY`,
  `ANONYMIZER_PROFILE_DIR`, `ARCHIVE_DIR`, `HARDWARE_PROFILE` wskazującymi do niego; profil = **pusty profil testowy** (bez
  danych OWNERA), odtwarzany od zera dla każdego wariantu i każdego zbioru; kod = exact SHA repo;
- przed i po przebiegu: migawka (ścieżka, rozmiar, mtime) katalogu `backend/` repo i katalogu backendu OWNERA; **każda zmiana poza
  katalogiem tymczasowym → `NOT_RUN(ISOLATION)`**, nie PASS;
- bez refaktoru API; jeżeli izolacja wymagałaby zmiany kodu produktu → zatrzymanie i zgłoszenie przed kodem.
Uwaga CC (jawnie): 20.10 CC wysłał ~13 krótkich syntetycznych tekstów na działający backend OWNERA (sprawdzenie kotwic) — licznik
PSE i audyt OWNERA zostały przez to zmienione; zgłoszone OWNEROWI.

## Guard-reszta w symulacji (reguła zamrożona przed pomiarem, w kodzie skryptu)
Słowo po `/preview`, niebędące tokenem, trafia do `would_ask`, chyba że jest bezsporne: zwykłe słowo Morfeusza bez interpretacji
imienia/nazwiska/nazwy własnej, skrót z listy, liczba ≤ 4 cyfry, data bez kotwicy. **Zawsze pytamy:** słowo z wielkiej litery
z interpretacją imienia/nazwiska, słowo nieznane Morfeuszowi, ciągi z cyframi/kodami, sąsiadujące krótkie grupy cyfr (≥ 2 grupy
w odległości ≤ 1 słowa), data przy „ur.”. Reguła = walidacja CC 20.10 (`LYNX-GUARD-RESIDUE`); różnice w DELIVERY.

## Prostowanie (P1) — P2 przeniesione
P1: dla obrotów 0/90/180/270 odczyt PP; wybór = najwyższy **odsetek** słów (≥ 3 litery) znanych Morfeuszowi, przy minimum 20 słów;
poniżej minimum lub remis (różnica < 0,02) → kolejność 0, 90, 270, 180. Trafność na kopiach syntetyków obróconych w pamięci
(90/180/270) + czas. **P2 (klasyfikator `PP-LCNet_x1_0_doc_ori`) przeniesione do `LYNX-OCR-ORIENTATION`** (decyzja CC po przeglądzie
redukcyjnym: brak lokalnego zweryfikowanego ONNX, nie jest potrzebny do pytania o łańcuch); bez pobierania/konwersji wag w tym Tasku.

## C4 — reguła odmowy N i kryteria (zapisane przed implementacją)
- **Reguła wewnętrzna:** dokument odrzucony, gdy `would_ask` / liczba stron > N. Użytkownik nie widzi liczby; komunikat odmowy
  (propozycja OWNERA, do kontraktu produktu): „Popraw ujęcie: skorzystaj ze skanera, ustaw lepsze światło i kąt aparatu” + „albo wklej tekst dokumentu”.
- **Wybór N (deterministyczny, tylko 50 znanych):** siatka N ∈ {15, 20, 30, 40, ∞}. Dopuszczalne N: 0 `HOLE` krytycznych w
  przyjętych, 0 odrzuconych L0. Spośród dopuszczalnych wybierz N z **największą liczbą przyjętych dokumentów**; remis → większe N.
  Brak dopuszczalnego → `NO_RULE` (pomiar holdoutu i tak raportowany przy N = ∞, werdykt `NOT_READY`).
- **Pełne mianowniki zawsze:** 50/100 dokumentów: przyjęte / odrzucone przez N / zablokowane (REAL_PIPELINE) / błąd; wartości gold:
  w odczycie / `NOT_IN_OCR`; statusy C2 per typ, krytyczne osobno, per poziom L0–L3.
- **Kryteria `READY_FOR_PRODUCT_BRIEF` (holdout, wybrane N):** (1) 0 `HOLE` krytycznych; (2) `HOLE` niekrytyczne ≤ 1 na 100
  przyjętych; (3) każdy `UNKNOWN_REVIEW` rozstrzygnięty w DELIVERY i żaden nie okazał się wyciekiem krytycznym; (4) odrzucone:
  L0 = 0, L1 ≤ 5%; przyjętych łącznie ≥ 80%; (5) mediana `would_ask` na dokument ≤ 8 (≈ 2 × 4 z odniesienia orientacyjnego, liczba
  absolutna); (6) izolacja wykazana. Bezpieczeństwo (1–3), uciążliwość (5) i kompletność (`NOT_IN_OCR`) raportowane osobno;
  „0 dziur” osiągnięte przez odrzucenie > 20% dokumentów nie spełnia (4). Inaczej `NOT_READY` z główną przyczyną
  (OCR / silnik / reguła Guarda / próg) — następny krok wynika z przyczyny, nie z kolejnego progu.

## Implementacja — pomiar, nie produkt
`tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py`: reużywa przez import `ocr_rapid`, `pp_quality` (hashe/preflight),
`benchmark` (`_CRITICAL_KEYS`, `_ENTITY_TYPE_MAP`), `benchmark_ocr_diagnostics` (`classify_miss`, `norm`); handler `/preview`
przez `TestClient` w izolowanym podprocesie (C3); HerBERT minimalnym wywołaniem ONNX. Raport JSON tylko do `--out` poza repo:
ID syntetyków, klucze/typy, statusy, liczby, czasy, SHA kodu/modeli/danych; zero wartości, tekstu OCR, nazw plików realnych.
Testy `backend/tests/test_ocr_chain_compare.py` (bez modeli, na sztucznych tekstach i atrapie odpowiedzi `/preview`): reguła
Guard-reszty (nazwisko-zwykłe słowo z wielkiej litery → pytanie; rozbity telefon → pytanie; zwykłe słowo → nie); statusy C2 na
uszkodzonym NIP, IBAN i telefonie w grupach (`HOLE` vs `UNKNOWN_REVIEW` vs `ASKED`); zablokowany dokument nie liczy się jako
przyjęty; wybór N wg funkcji C4 (w tym `NO_RULE`); P1 tie-break; wykrycie zapisu poza katalogiem tymczasowym → `NOT_RUN(ISOLATION)`;
`NOT_RUN(HerBERT)` bez modelu; odmowa `dataset_real` w trybie gold i `--out` w repo; determinizm dwóch przebiegów (poza czasem).

TASK_SCOPE:
- tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py
- backend/tests/test_ocr_chain_compare.py

OUT_OF_SCOPE: zmiany produkcyjne (OCR, `/preview`, warstwy, kotwice, Guard, HerBERT w produkcie, progi, UI/onboarding, S4),
`LYNX-ANCHOR-PARITY`, P2/klasyfikator orientacji, aktywacja PP, przeniesienie N do polityki produktu, realne dane w repo, pełna suita.

GATE: dwa nowe pliki ≤ 600 l., funkcje ≤ 50 l. **Przegląd redukcyjny CC:** po usunięciu P2 i z HerBERT jako ramieniem opcjonalnym
pomiar jest wykonalny bez fałszywego uproszczenia; szacunek skrypt ~420 l. + testy ~160 l. ≈ 580 l. (> 150) → zgoda OWNERA przed kodem.
Jeżeli w implementacji skrypt przekroczy 600 l., HerBERT wydzielany jest do kolejnej rundy, nie upychany.

PRZEKAZANIE: Codex → BRIEF_ONLY precheck `tasks/LYNX-OCR-GATE-COMPARE/round_01/tests/tests_r1.txt` (bez uruchamiania modeli, bez
zmian produktu); CC po PASS pyta OWNERA o rozmiar; implementacja dopiero po zgodzie.
