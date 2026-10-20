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

## GATE (stdout dosłownie — poniżej, sekcja dopisywana po commicie)
