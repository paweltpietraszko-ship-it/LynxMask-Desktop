# Brief — LYNX-OCR-GATE-COMPARE: czy pełny łańcuch działa na zdjęciach tak jak na czystym tekście?

STATUS: PROJEKT BRIEFU CC na prośbę OWNERA (20.10, wersja 2 — zastępuje wersję 1 z `d359021`, która mierzyła sam OCR w oderwaniu
od celu) → Architekt akceptuje lub poprawia → Codex PREIMPLEMENTATION → zgoda OWNERA na rozmiar → CC implementuje → Codex audytuje
exact SHA. Pomiar offline, produkt bez zmian. Bez merge bez polecenia OWNERA.
PRODUCT_TRUTH: `arch/spec.md` S1, S3, S5; `BOARD.md` → TERAZ (cel: każde słowo wysyłane dalej jest zakryte albo pokazane człowiekowi)
i wiersze `LYNX-GUARD-RESIDUE`, `LYNX-K1-PERSONS-FIRMS`, `LYNX-OCR-QUALITY-GATE`, `LYNX-OCR-ORIENTATION`, `LYNX-ANCHOR-PARITY`;
wyniki C1 (`tasks/LYNX-OCR-CASCADE/round_01/implementation/DELIVERY.md`).

## Cel produktu (bez zmian od rana 20.10)
Silnik (warstwy + Morfeusz + kotwice) zakrywa to, co rozpoznaje; **HerBERT** jako siatka zakrywa część resztek; **Guard pokazuje
człowiekowi wszystko, co zostało** (`LYNX-GUARD-RESIDUE`). Na czystym tekście zmierzone: 0 realnych dziur, ~4 pytania na dokument.
Na skanach z Tesseractem: 5 dziur, ~9 pytań — bo OCR niszczy tekst. HerBERT też potrzebuje dobrego odczytu.

## Pytanie tego Tasku
**Czy łańcuch obraz → wyprostowanie → PP-OCRv6 → silnik → (HerBERT) → Guard-reszta daje na zdjęciach wynik bliski czystemu
tekstowi: 0 realnych dziur i rozsądną liczbę pytań?** Punkty odniesienia mierzone tym samym narzędziem: (1) czysty tekst tych samych
dokumentów (z gold), (2) dzisiejszy Tesseract bez prostowania.

Ustalone wcześniej i tu NIE ponownie badane: PP czyta (Tesseract nie poprawia PP i nie mierzy jakości — C1 i oko OWNERA);
silnik zakrywa uszkodzone identyfikatory po etykiecie bez sumy kontrolnej (dziury w `LYNX-ANCHOR-PARITY` — osobny Task).

## Miary (osobno, bez jednej sumy)
1. **Realna dziura** = wartość gold (lub jej fragment ≥ 4 znaki alfanumeryczne) widoczna w tekście po silniku (i HerBERT),
   **której Guard-reszta nie pokazałby** człowiekowi. Krytyczne (`benchmark._CRITICAL_KEYS`) osobno.
2. **Pytania Guarda na dokument** (mediana, max) i ich rodzaje.
3. **Wartość gold zakryta / pokazana / dziura / nieobecna w odczycie** (ostatnie = kompletność, nie wyciek).
4. **Odmowy** wg reguły „za dużo pytań” (niżej) i odrzucone obrazy bez degradacji (L0).
5. Czas na stronę i RAM (PP, HerBERT, orientacja osobno).

## Guard-reszta w pomiarze (reguła zamrożona przed pomiarem, w kodzie skryptu)
Słowo po silniku, które nie jest tokenem, idzie do pytania, chyba że jest bezsporne: zwykłe słowo Morfeusza bez interpretacji
imienia/nazwiska/nazwy własnej, skrót z listy, krótka liczba (≤ 4 cyfry) lub data bez kotwicy. **Zawsze pytamy:** słowo z wielkiej
litery z interpretacją imienia/nazwiska (479/986 nazwisk to zwykłe słowa), słowa nieznane Morfeuszowi, ciągi z cyframi/kodami,
**sąsiadujące krótkie grupy cyfr** (telefon rozbity przez OCR), data przy „ur.”. Reguła = ta zwalidowana przez CC 20.10
(`LYNX-GUARD-RESIDUE`); różnice wpisać do DELIVERY. To symulacja do pomiaru, nie implementacja Guarda.

## Warianty (małe elementy, nie nowa architektura)
- **Prostowanie:** (P1) obrót wybierany przez największą liczbę słów znanych Morfeuszowi z 4 odczytów PP; (P2) klasyfikator
  `PP-LCNet_x1_0_doc_ori` + jeden PP. Trafność obu na obróconych kopiach syntetyków (90/180/270, w pamięci).
- **HerBERT:** bez / z (`~/lynx_models/herbert-polish-legal-ner`, ONNX lokalnie; encje PER/ORG/LOC na tekście po silniku
  zakrywają te słowa przed Guardem). Brak modelu → NOT_RUN wariantu z powodem.
- **Odmowa:** zamiast osobnej miarki jakości — **liczba pytań Guarda na stronę** (zdjęcie śmieciowe = prawie wszystko niejasne).
  Próg N wybierany na zbiorze znanym z siatki (np. 15/20/30/40), przed holdoutem; obok raportować dla porównania miarkę słownikową
  z pomiaru CC 20.10 (bez decydowania nią).
  **Liczba pytań to wyłącznie wewnętrzna reguła decyzji — użytkownik jej nie widzi.** Komunikat odmowy (propozycja OWNERA 20.10,
  prosty przekaz, co zrobić): „Popraw ujęcie: skorzystaj ze skanera, ustaw lepsze światło i kąt aparatu.” + droga zastępcza
  „albo wklej tekst dokumentu”. Bez procentów i liczb w komunikacie. Tekst komunikatu do kontraktu produktu, nie do tego pomiaru.

## Dane
- `backend/dataset_20260627_095419` (50, znany — wybór N), `backend/dataset_20261016_fresh` (100, holdout — raz, po zamrożeniu
  reguł commitem). **Czystego tekstu tych samych dokumentów nie da się odtworzyć** (sprawdzone przez CC: `ground_truth.json` ma tylko
  `entities`, ziarno generatora nie zapisane). Punkt odniesienia „czysty tekst” = **ten sam skrypt w trybie tekstowym na
  `dataset_clean` z repo Mobile (`paweltpietraszko-ship-it/LynxMask`, lokalnie u CC/Codexa) (Mobile, 100 dok. z gold; pomiar CC 20.10: 0 dziur / ~4 pytania)** + podzbiór obrazów
  bez degradacji (L0) jako najlepszy przypadek zdjęcia.
- Realne zdjęcia OWNERA `backend/dataset_real/images/*.jpg` (lokalnie, bez gold): wybrany obrót, liczba pytań, odmowa tak/nie,
  czas — **tylko agregaty**; poprawność ocenia oko OWNERA na pliku lokalnym (nie w repo).

## Implementacja — pomiar, nie produkt
`tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py`: reużywa przez import `ocr_rapid`, `pp_quality` (hashe/preflight),
`benchmark` (token, `_CRITICAL_KEYS`, `_ENTITY_TYPE_MAP`), `benchmark_ocr_diagnostics` (`classify_miss`, `norm`); tekst do silnika
przez `/preview` jako `.txt` na działającym silniku (SHA backendu w raporcie; musi odpowiadać kodowi main); HerBERT minimalnym
wywołaniem ONNX (bez kopiowania produktu, którego jeszcze nie ma). Raport JSON tylko do `--out` poza repo: ID syntetyków, klucze/typy,
liczby, czasy, SHA modeli/kodu/danych; zero wartości, tekstu OCR, nazw plików realnych.
Testy `backend/tests/test_ocr_chain_compare.py` (bez modeli i silnika, na sztucznych tekstach): reguła Guard-reszty (nazwisko-zwykłe
słowo z wielkiej litery → pytanie; rozbity telefon → pytanie; zwykłe słowo → bez pytania), definicja dziury (fragment ≥ 4 znaki;
wartość pokazana w pytaniu ≠ dziura), wybór N tylko ze zbioru znanego, NOT_RUN bez modeli, odmowa `dataset_real` w trybie gold
i `--out` w repo, determinizm dwóch przebiegów (poza czasem).

TASK_SCOPE:
- tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py
- backend/tests/test_ocr_chain_compare.py

OUT_OF_SCOPE: zmiany produkcyjne (OCR, `/preview`, warstwy, kotwice, Guard, HerBERT w produkcie, progi, UI/onboarding),
port reguł AnchorEngine (`LYNX-ANCHOR-PARITY`), aktywacja PP, S3/S4, realne dane w repo, pełna suita.

GATE: dwa nowe pliki ≤ 600 l., funkcje ≤ 50 l. Szacunek CC: skrypt ~380 l. + testy ~140 l. ≈ 520 l. (> 150) → zgoda OWNERA przed kodem.

KRYTERIUM WYNIKU (przed pomiarem): łańcuch na zdjęciach jest **gotowy do kontraktu produktu**, jeśli na holdoucie po wyborze N:
0 realnych dziur krytycznych, realne dziury niekrytyczne ≤ 1 na 100 dokumentów (czysty tekst: 0),
mediana pytań ≤ 2 × czysty tekst, odmowy L0 = 0. Inaczej `NOT_READY` z listą przyczyn (OCR / silnik / reguła Guarda / HerBERT)
— wtedy następny krok wynika z największej przyczyny, nie z kolejnego progu.

PRZEKAZANIE: Architekt → akceptacja/poprawki; Codex → precheck `tasks/LYNX-OCR-GATE-COMPARE/round_01/tests/tests_r1.txt`;
CC po PASS i zgodzie OWNERA implementuje. Merge tylko na polecenie OWNERA.
