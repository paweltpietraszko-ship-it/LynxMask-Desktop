# LYNX-ADDR-EMAIL-LEAKS — adresy i e-maile jawne w obecnym LynxMask (znalezione w porównaniu z Areną)

STATUS: brief CC, obieg skrócony (CC → Codex precheck → CC implementacja → Codex audyt → merge na słowo Pawła). Paweł: „Tak, zrób małe zadanie z adresami i e-mailami”.
POCHODZENIE: BOARD `LYNX-ARCH-ARENA-VS-REAL` (`72ca0c7`). Te same syntetyki przez działający `/preview` (main, profil Pawła).
ZASADA KOLEJNOŚCI: warstwy regex `address` i `contact` nowy model zachowa jako silniki-kandydaci (`LYNX-ARCH-CANDIDATES`), więc naprawa w starym łańcuchu jest dozwolona. **Normalizacji OCR nie ruszamy** (klasa zakazana w starym łańcuchu, SHADOW-NORMALIZE), dlatego „Spotkanie @ 10:00” → „Spotkanie@10:00” zostaje poza zakresem.
PRODUCT_TRUTH: S1 (bez PII w wyniku). Bez zmian S2–S5, TOKEN_RE, taksonomii, alokatora i Guarda.

## Wycieki (syntetyki, obecny main)
| # | Wejście | Wynik dziś | Przyczyna (właściciel) |
|---|---|---|---|
| L1 | „Adres: ul. Polna l2/8” | cały jawny | `layers/address._ADDR_RE`: numer domu `\d+` — OCR „l2” (litera zamiast 1) nie pasuje |
| L2 | „Adres: ul. Św. Marcin 5” | cały jawny | `_ADDR_RE`: nazwa ulicy bez kropki — skrót „Św.” przerywa dopasowanie |
| L3 | „Adres: ul. 3 Maja 12/4; tel.” | cały jawny | `_ADDR_RE`: nazwa musi zaczynać się literą — „3 Maja”, „11 Listopada” odpadają |
| L4 | „Kontakt: żaneta@firma.pl” | „żEMAIL_001” | `contact._EMAIL_OCR_RE` i wzorce EMAIL w `anonymizer_init.STRUCTURAL_PATTERNS`: część lokalna tylko ASCII, bez lewej granicy → polska litera zostaje jawna, a token przykleja się do niej |
| L5 | „Kontakt: aléx@firma.pl” (NFD, znak łączący) | „aléEMAIL_001” | jw. — znaki łączące U+0300–U+036F poza klasą |

## Kontrakt
1. Faza 1 adresu (`_ADDR_RE`) rozpoznaje dodatkowo — bez zmiany pozostałych faz:
   - numer domu z jedną literą OCR na początku członu (`l`, `I`, `O` przed cyfrą), także po `/`;
   - jeden skrót z kropką przed nazwą ulicy (1–4 litery + `.`, np. „Św.”, „Gen.”, „Ks.”);
   - nazwę zaczynającą się liczbą 1–2 cyfr i spacją („3 Maja”, „11 Listopada”).
   Wartość w mapie to dosłowny wycinek tekstu, więc Przywróć oddaje 1:1.
2. E-mail: część lokalna dopuszcza litery Unicode (np. polskie) i znaki łączące U+0300–U+036F. Zaczyna się na granicy (nie wewnątrz słowa), więc cała część lokalna trafia do tokenu, bez jawnego fragmentu i bez sklejenia. Domena bez zmian (ASCII). Dotyczy wszystkich trzech wzorców e-mail: OCR-tolerancyjnego w `contact.py` oraz dwóch w `STRUCTURAL_PATTERNS`.
3. Bez regresji: dotychczasowe adresy i e-maile maskowane jak dziś. Kontrpróby bez PII nie stają się adresem: „Dz. U. Nr 223” (znane C5 — nie pogorszyć), „ul. w instrukcji”, zwykłe zdanie z „al.”/„pl.” bez numeru. „@administrator” i „@jan_kowalski” nadal nie są e-mailem.

TASK_SCOPE:
- backend/layers/address.py
- backend/layers/contact.py
- backend/anonymizer_init.py
- backend/tests/test_addr_email_leaks.py

OUT_OF_SCOPE: `layers/ocr_normalizer.py` (spacje wokół @, X02), C5 „Dz. U.” (K3), domeny IDN, „al.”/„ul” bez kropki (obecny program już je maskuje), adresy bez prefiksu, NER, Arena.

## Falsyfikacja
- Nowy `tests/test_addr_email_leaks.py`:
  - L1–L5 przez warstwy i przez `/preview` (TestClient, prawdziwy silnik): wartość nie występuje w wyniku, brak sklejenia tokenu z literą, Przywróć = wejście dla fragmentu;
  - kontrpróby bez PII z pkt 3;
  - warianty rodziny: „ul. Gen. Andersa 4a/12”, „al. 11 Listopada 7”, „ul. Polna O5”, „ul. Polna 12/l4”, „łukasz.żak@firma.pl”, „Ąnna@firma.pl” (wielka litera), e-mail po polskim słowie bez spacji („doŻaneta@…” → bez maskowania wnętrza słowa, sprawdzić zachowanie).
- RED na main: L1–L5 wyciekają.
- Regresje: `tests/` na backendzie gałęzi, `test_layers`, `test_map_fidelity`, `test_audyt_2026_10`, `test_failclosed`.
- **178 dok. przez `/preview` z profilem Pawła:** każda różnica względem main wypisana i oceniona (nowe adresy/e-maile — czy to PII). Do repo tylko liczby.

GATE: 1 nowy plik testu; zmiany w regexach. Szacunek: program ok. +10/−5, test ok. +80 (poniżej progu 150).
