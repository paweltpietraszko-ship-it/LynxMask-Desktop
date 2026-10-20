# DELIVERY — LYNX-OCR-GATE-COMPARE, ETAP 1 (CC, 2026-10-20)

Brief v3.3 `27f1880`, precheck Codexa PASS `09b1e25`. Implementacja ETAPU 1 przez pomocnika CC (Opus) pod nadzorem CC; przegląd
przypadków, werdykt i ten opis — CC. Reguły zamrożone przed holdoutem: `c1c484d` (pomiar uruchomiony na tym SHA,
`script_dirty_vs_head: false`). Po pomiarze jedyna zmiana skryptu: usunięta jedna pusta linia (601 → 600, limit gate) — bez zmiany
działania i reguł. Raport JSON poza repo (`stage1_report.json`, lokalnie u CC); digesty zbiorów: znany `b2e580ae…`, holdout `d01b11c4…`,
`dataset_clean` `f1bf5916…`; modele PP = faza A.

## Izolacja (C3)
Każdy przebieg: kopia `git archive` backendu, pełny `_lifespan` (`/health`: anonymizer, spaCy, Morfeusz native, crypto OK),
migawka 4 chronionych katalogów — `startup: OK`, `isolation: OK`, `changed_paths: 0` we wszystkich krokach; kopie usunięte.

## Wybór N (tylko 50 znanych, funkcja C4)
| N | dopuszczalne | przyjęte | HOLE kryt. | odrzucone L0 |
|---|---|---|---|---|
| 15 | nie | 41 | 0 | 2 |
| 20 | nie | 45 | 0 | 2 |
| 30 | tak | 50 | 0 | 0 |
| 40 | tak | 50 | 0 | 0 |
| ∞ | tak | 50 | 0 | 0 |
Remis 30/40/∞ (50 przyjętych) → większe N → **N = ∞** (reguła odmowy nie odrzuca żadnego syntetyku).

## Wynik bazowy (REAL_MASKING_PIPELINE + symulacja Guard-reszty), N = ∞
| | znany 50 | holdout 100 | `dataset_clean` 300 (odniesienie, inne dok.) | dziś: Tesseract, holdout |
|---|---|---|---|---|
| przyjęte / odrzucone / zablokowane | 50 / 0 / 0 | 100 / 0 / 0 | 300 / 0 / 0 | 83 / 16 (OCR) / 1 |
| wartości gold | 342 | 619 | 1988 | 619 |
| MASKED / ASKED | 304 / 9 | 541 / 33 | 1892 / 55 | 451 / 39 |
| HOLE (mechanicznie) / krytyczne | 6 / 0 | 10 / 0 | 30 / 0 | 14 / 0 |
| UNKNOWN_REVIEW / krytyczne | 8 / 5 | 10 / 4 | 9 / 1 | 7 / 0 |
| NOT_IN_OCR (kompletność) | 15 | 25 | 2 | 7 |
| mediana / max pytań na dok. | 10,5 / 30 | 9 / 31 | 5 / 29 | 11 / – |
Czas na stronę (mediana, holdout): decyzja o obrocie P1 5,7 s, odczyt PP 1,9 s, `/preview` 0,02 s.

## Przegląd CC wszystkich HOLE i UNKNOWN_REVIEW (syntetyki; odtworzone: PP przy obrocie z raportu → `/preview` dev 8765 → `evidence()` ze skryptu)
**HOLE — prawdziwe (niekrytyczne):**
- miasto `Bielsko-Biała` jawne przy tokenie ADRES — OCR czyta „Biala” (ł→l), silnik nie łączy miasta z adresem: znany doc_00006, 00029,
  00032, 00038; holdout doc_00062, 00085 (6);
- e-mail `…@poczta.pì` (OCR l→ì w domenie) — w ogóle niezamaskowany: holdout doc_00063 (1);
- końcówka numeru działki `NUMER_007.9795`: znany doc_00027 (1).
**HOLE — fałszywe alarmy miarki:** słowo „UMOWA” z tytułu dokumentu (wartość gold `UMOWA/…/NR/…` zamaskowana jako `nr NUMER_009`):
znany doc_00021, holdout 00039, 00062, 00096; rok „2023” z „Dz. U. z 2023 r.” (sygnatury z rokiem 2023): holdout 00007, 00080; nazwa
sądu „SR dla Wrocławia-Fabrycznej” ≠ adres osoby: holdout 00015, 00031. Ta sama klasa daje wszystkie 30 HOLE na `dataset_clean`
(„UMOWA”, „2023”, sama nazwa miasta w nagłówku „Kielce, dnia …” — miasta samego polityka nie maskuje).
→ **Prawdziwe dziury: znany 5/50, holdout 3/100, czysty tekst 0/300.**
**UNKNOWN_REVIEW (18) — rozstrzygnięcie: żaden nie jest wyciekiem.** W żadnym nie ma widocznej wartości ani jej fragmentu ≥ 4;
dowody to pojedyncze cyfry/„2a” albo resztki roku sygnatury („NUMER_008 18”, „… 17”). 16 z 18 pochodzi z dokumentów, które P1
obrócił błędnie (rot ≠ 0 na prostych syntetykach) — odczyt bokiem, wartości rozbite/nieobecne, nie wyciek.

## P1 (prostowanie) — niepowodzenie
- Na **prostych** syntetykach P1 wybrał obrót ≠ 0 w **15/50 (znany) i 33/100 (holdout)** → trafność przy 0° ≈ 68% (cel ≥ 98%).
- Czas decyzji: mediana 5,7–6,0 s na syntetyku, 8,4 s na realnych zdjęciach (cel ≤ 3 s).
- Krok `p1` (obrócone kopie 600 decyzji) przerwany po ~2 h za zgodą OWNERA — wynik celu już rozstrzygnięty; brak liczby
  trafności na kopiach 90/180/270.
- Skutek dla pomiaru: dokumenty błędnie obrócone niosą większość strat kompletności (NOT_IN_OCR: 12/15 znany, 19/25 holdout)
  i 16/18 UNKNOWN. → **P2_NEEDED.** OWNER 20.10: zgoda na dedykowany mały model orientacji, jeśli pomiar pokaże, że jest lepszy.

## HerBERT
`NOT_RUN(HerBERT)` — odłożony przez pomocnika, bo skrypt przekroczyłby 600 linii (brief: „HerBERT do kolejnej rundy, nie upychany”).

## Realne zdjęcia OWNERA (8, tylko agregaty)
5 przetworzonych, 3 zablokowane przez obecny Output Guard; mediana pytań 40 (max 147); obrót: 0° ×3, 90° ×4, 270° ×1;
decyzja o obrocie 8,4 s, odczyt PP 4,0 s (mediana). Ocena poprawności — oko OWNERA (lokalnie).

## Werdykt ETAPU 1 (kryteria C4, holdout, N = ∞): **NOT_READY**
| kryterium | wynik |
|---|---|
| (1) 0 HOLE krytycznych | ✅ 0 |
| (2) HOLE niekrytyczne ≤ 1/100 | ❌ mechanicznie 10; po przeglądzie 3 |
| (3) UNKNOWN rozstrzygnięte, bez wycieku krytycznego | ✅ 10/10, 0 wycieków |
| (4) odrzucone L0 = 0, L1 ≤ 5%, przyjęte ≥ 80% | ✅ 0 / 0% / 100% |
| (5) mediana pytań ≤ 8 | ❌ 9 (dokumenty prosto: 9; obrócone: 10 — nie wynika z obrotu) |
| (6) izolacja | ✅ |
**Główne przyczyny:** (a) OCR/prostowanie — P1 nietrafny i wolny (→ porównanie orientacji: model `PP-LCNet_x1_0_doc_ori` vs
detektor PP + jego klasyfikator 180°); (b) silnik — trzy klasy „kotwica + wartość uszkodzona przez OCR” (miasto z utraconym
znakiem diakrytycznym przy adresie, e-mail z uszkodzoną domeną, ogon numeru) + znane wcześniej (`ur. 12.O3.1985`, ogon NIP) → ETAP 2;
(c) reguła Guard-reszty: ~9 pytań na zdjęciu vs 5 na czystym tekście — do oceny po (a) i (b).
Dla porównania dzisiejszy produkt (Tesseract, bez prostowania) na tym samym holdoucie: 16 odmów OCR, HOLE 14, pytań 11.

## Miarka — ograniczenie do odnotowania (bez zmiany zamrożonej reguły)
Reguła fragmentu ≥ 4 (`_fragment_hit`: rdzeń słowa wartości) liczy jako HOLE słowa wspólne z treścią dokumentu („UMOWA”, rok,
miasto w nagłówku). Mechaniczne liczby HOLE są zawyżone; rozstrzyga przegląd powyżej. Zmiana reguły — tylko w nowej rundzie,
nie po obejrzeniu wyników.

## GATE ETAPU 1 (`gate.py … 09b1e25 32ea383 …/gate_stage1.txt`, stdout dosłownie; commit ETAP1-FROZEN = `32ea383`)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 32ea383d3e4a77b1c0381e67b798c3313048dce3
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 197 lines changed (threshold 150)
IMPORTERS_FOR_REVIEW:
  - backend\pipeline_new.py
  - backend\smoke_test.py
  - tasks\LYNX-IBAN-FOREIGN-ALNUM\round_01\tests\tests_r2_repro.py
  - backend\tests\test_layers.py
  - backend\tests\test_pipeline_v2.py
EXCLUDED_ARTIFACTS:
  - tasks/LYNX-OCR-GATE-COMPARE/measure/chain_compare.py
  - tasks/LYNX-OCR-GATE-COMPARE/round_01/implementation/DELIVERY.md
```
TOTAL_LINES: zgoda OWNERA (20.10, „zleć”) na ~650 l. całego Tasku; ETAP 1 = 797 l. (skrypt 600 w artefakcie `tasks/` + testy 197) — przekroczenie zgłoszone OWNEROWI.

---

# ETAP 2 i 2b (CC, 2026-10-20) — po `ETAP1-FROZEN` `32ea383`

## Orientacja (P2) — rozstrzygnięta pomiarem, poza zamrożonym skryptem
Skrypt etapu 1 ma 600 linii (limit), więc porównanie orientacji wykonane narzędziem poza repo (`orient_cmp.py`, lokalnie u CC),
na tych samych syntetykach obróconych w pamięci (0/90/180/270), mapowanie etykiet wybrane na zbiorze znanym:
- `PP-LCNet_x1_0_doc_ori`, dwie niezależne konwersje ONNX (HF `marsena/paddleocr-test` sha256 `5dcaf4e3…`, `monkt/paddleocr-onnx`
  sha256 `f5516822…`), preprocessing wg oficjalnego `inference.yml` (resize_short 256, crop 224, ImageNet), etykiety 0/90/180/270;
- **trafność 600/600 (znany 200/200, holdout 400/400), wszystkie poziomy degradacji, 2–5 ms/str.; obie konwersje — identyczne predykcje**
  (test zgodności zamiast instalacji Paddle);
- realne zdjęcia OWNERA (8): oko OWNERA — 7 wyprostowanych poprawnie; błąd tylko na zdjęciu słabym (krzywe, jedna strona prawie
  niewidoczna), gdzie model był niepewny: max-prob 0,35 (pozostałe 0,83–0,93; syntetyki min 0,76).
→ Propozycja do kontraktu produktu: model orientacji z progiem pewności (~0,6); poniżej — odmowa „Popraw ujęcie: skorzystaj ze
skanera, ustaw lepsze światło i kąt aparatu” / wklej tekst. OWNER 20.10: zgoda na mały dedykowany model, jeśli lepszy (jest).

## ETAP 2 — kotwica + wartość uszkodzona przez OCR (`16c3f0a`)
Reproduktory RED przed poprawką (6 + test `_ascii_fold`), GREEN po: `test_ocr_chain_compare.py::test_stage2_*`.
| przyczyna (plik) | poprawka |
|---|---|
| `layers/address.py::_ascii_fold` gubi ł/Ł → „Bielsko-Biała”→„Bielsko-Biaa”, OCR „Biala”, „Lodz”, „Glogow” bez SIMC | ł→l przed NFD |
| `layers/contact.py::_EMAIL_OCR_RE` TLD tylko `[a-zA-Z]` — OCR „.pì” | TLD: litery Unicode |
| `layers/contact.py::_PHONE_322_RE` urywa 9-cyfrowy NIP („NUMER-90”) | dalsze grupy `[-.]\d{1,4}` w całości |
| `layers/identity.py::_NIP_RE_OCR` urywa numer działki („NUMER.9795”) | j.w. |
| wzorzec „ur.” wymaga `\d` — `ur. 12.O3.1985` jawne | `_DOB_OCR_RE`: kotwica „ur”, klasa cyfropodobnych jak Mobile A.7, ≥1 prawdziwa cyfra |
`ur 12.03.1985` (bez kropki) był już maskowany — zostaje jako test regresji.

## ETAP 2b — samotne imię/nazwisko ze słownika (`86809df`, rozszerzenie bloku na polecenie OWNERA)
Test Mobile `testy/test_imiona_nazwiska_100_11_07.txt`: Desktop zostawiał jawne Grażyna, Sergiej, Diego, Wiktoria, Kalina, Jankowski,
Kwiatkowski (Mobile golden: wszystkie zakryte). Port `NameEngine` 3a do `layers/ner_adapter.py::_apply_dictionary_names` (wywołanie
w miejscu istniejącej linii — `apply_ner_layer` nie rośnie) z `OSOBA_DENYLIST` i białymi listami Mobile; `names_inflected.json` =
słownik Mobile (3609) ∪ 11 zdrobnień Desktop, forma podstawowa dopisana do listy odmian (konwencja Desktop — inaczej
`ocr_normalizer._de_leet` gubił „Paulina”). Nazwiska: bez zmian (`surnames_top1000.json`; 39 tys. Mobile — osobna decyzja).
Po poprawce cały plik Mobile: 0 jawnych imion/nazwisk; jawne zostają tylko słowa z listy wyjątków (Data, Dane, Osoba, Zapłaty…).
Zmienione 2 testy `test_ner_multiline.py` (dopisany do TASK_SCOPE): (1) C047 — inne osoby mają teraz własne tokeny, sprawdzane wprost,
że token „Piotr Masłowski” stoi tylko w jego miejscu; (2) samotna „Róża” jest teraz zakryta (świadome nadmaskowanie jak „Malina” w Mobile).

## Kontrola regresji
- Szeroki zestaw testów silnika (`test_layers`, `test_pipeline_v2`, `test_anonymizer_adversarial`, `test_pipeline_adversarial`,
  `test_map_fidelity`, `test_engine_quality_layout`, `test_addr_email_leaks`, `test_ner_multiline`, `test_ocr_chain_compare`):
  wszystkie zielone; jedyne porażki — te same 30 w `test_pseudominizer.py` przed i po (testy łączą się z serwerem 8765 z innego
  katalogu; środowiskowe, niezależne od zmian).
- Strażnik `benchmark.py` (`dataset_20260627_095419`, serwer z kodu main vs gałęzi, ten sam świeży profil testowy): **identyczne** —
  Privacy Recall 94,5% (274/290), Critical Leakage 0,0%, FP 38,8%, `[OCR-DIAG]` 0/13/3, przyjęte 43/50.
- `dataset_clean` (300 tekstów Mobile), tokeny OSOBA main vs gałąź: +2 wartości gold zakryte, 1 nadmaskowanie („Góra”), 0 utraconych.
- Ponowny pomiar łańcucha zamrożonym skryptem na `86809df`: krok `clean` (300) — izolacja OK, HOLE mech. 28 (było 30, ta sama klasa
  fałszywych alarmów), UNKNOWN_REVIEW 17 (było 9 — do wyjaśnienia, prawdopodobnie tokeny OSOBA z 2b obok cyfr liczone przez `_weak_hit`),
  mediana pytań 5. Kroki `known`/`holdout` **nie wykonane**: pierwsza próba unieważniona przez izolację (CC zrestartował serwer OWNERA
  w trakcie — 1 zmieniony plik w chronionym katalogu, poprawne zadziałanie C3), druga przerwana przez system z braku pamięci RAM.
  Do powtórzenia na polecenie OWNERA.

## Wniosek CC i dalszy kierunek (OWNER 20.10)
Etapy 2/2b gaszą konkretne klasy, ale test Mobile `test_b_word_boundary_diacritics_08_07.txt` pokazał, że wykrywanie OSOBA w Desktop jest
źle zbudowane u podstaw (to samo na main: spaCy oznacza nagłówki WIELKIMI LITERAMI i słowa „KWOTA/OSOBA/TOKEN” jako osoby → fałszywe
MAP_LEAK Guarda; samotne „Kowaliński” jawne). OWNER: koniec łatania pojedynczych błędów OSOBA — osobne, jedno miejsce decyzji o osobie
(propozycja CC: `LYNX-OSOBA-REDESIGN`, HerBERT jako główny sygnał obok spaCy, słowniki/Morfeusz/kontekst, decyzja zakryj/zapytaj/zostaw,
strojenie na wielu zbiorach naraz). Dalsze poprawki OSOBA w tym bloku — wstrzymane.

## GATE ETAPU 2/2b (`gate.py … 09b1e25 dbad756 …/gate_stage2.txt`, nagłówek dosłownie; pełna lista importerów w pliku)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: dbad756fe4edda2face36b2b3da0a4eff35d057c
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 6512 lines changed (threshold 150)
```
TOTAL_LINES 6512 to w ~95% słownik `names_inflected.json` (dane: 3622 nowe / 2570 usunięte linii); kod ETAPU 2/2b ≈ 120 linii + testy. Brak FAIL (ratchet rozmiaru/ruff spełniony).
