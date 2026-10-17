# LYNX-IBAN-FOREIGN-ALNUM — pełny zagraniczny IBAN, bez jawnego prefiksu

STATUS: BRIEF_ONLY; Codex precheck → CC niezależna ocena → CC implementacja → Codex audyt exact SHA → merge tylko OWNER.
PRODUCT_TRUTH: `arch/spec.md` S1–S5; `BOARD.md` LYNX-IBAN-FOREIGN-ALNUM / LYNX-IBAN-OCR-PREFIX; `tasks/LYNX-T07-IBAN-RECEPTA/round_01/tests/tests_r4.txt` O2. OWNER_PROPOSAL 2026-10-17: po merge EMAIL-LOCALPART-OCR rozwiązać znany wyciek zagranicznego IBAN, potem PUBLIC-DATA-TESTS. Ocena Architekta: przyjąć kolejność; obecny Task tylko O2, bez merge ani zmiany zamrożonej spec.

## Wada i przyczyna — dowód z T07
Codex O2 na exact SHA T07 `9f9eefc7e3931aa3c4839238559dbab9e00c8869` i jego bazie: `Konto: GB82 WEST 1234 5698 7654 32` w full i Express → jawny uszkodzony prefiks `6882` i `NUMER_NNN` zawierający tylko część danych (22 znaki); `force_block=False`. To wcześniejsza wada, nie regresja T07. `backend/layers/ocr_normalizer.py::_IBAN_DIGITS_RE/_fix_iban_digits` traktuje po etykiecie bankowej prawidłowe litery obcego IBAN jak pomyłki OCR (np. G→6, B→8, S→5, T→7). `layers/financial.py::_IBAN_FOREIGN_RE` ma już obsługę obcych IBAN z alfanumerycznym BBAN; bez zachowanego prefiksu nie może rozpoznać całości. Przed implementacją CC odtwarza reproduktor na swojej bazie, ustala dokładny pierwszy etap utraty prefiksu i weryfikuje, czy istniejący financial rozpoznaje niezmieniony komplet.

## Żądane zachowanie użytkownika
Dla kompletnego rozpoznawalnego zagranicznego IBAN (litery w BBAN, rozdzielone grupy lub compact), także po etykiecie `Konto:`/`IBAN:`, zwykłe `Zamaskuj` daje **jeden istniejący `NUMER_NNN` na CAŁY IBAN**, bez jawnego prefiksu, kodu kraju, cyfr kontrolnych lub fragmentu BBAN. `reverse_map` zawiera pełną wartość spanu przekazaną do tokenizacji, z prawidłowymi literami i wewnętrznymi separatorami; brak zagnieżdżonych tokenów; Przywróć odtwarza źródłowy przykład, o ile wcześniejsza niezależna normalizacja nie zmieniała formatowania (wtedy osobno wskazać F3, nie uznawać fragmentarycznej mapy za PASS). Gdy wzorzec nie potwierdza całego IBAN, nie maskować samej jego części; nie rozluźniać fail-closed Guarda, nie traktować `blocked` jako udanej tokenizacji.

## Minimalne rozwiązanie — istniejący owner
1. **Najpierw `backend/layers/ocr_normalizer.py`**, jego wąska reguła IBAN po etykiecie bankowej: nie zamieniać poprawnych liter kodu kraju ani legalnych liter alfanumerycznego BBAN zagranicznego IBAN na cyfry. Zmiana ma być warunkowa dla kompletnego zagranicznego wzorca, bez globalnego zakazu poprawiania OCR. Zachować dotychczasowe naprawy błędów `PL` i czysto cyfrowych numerów rachunków. Nie przepisywać normalizatora; nie zmieniać kolejności pipeline.
2. `backend/layers/financial.py` tylko **jeśli test po prawidłowej normalizacji dowiedzie braku pełnego dopasowania**: lokalnie naprawić granicę istniejącego zagranicznego wzorca tak, aby nie ucinał kodu kraju/ogonów; nie dodawać nowego parsera IBAN ani międzynarodowej walidacji bankowej. Reguła T07 „cała wartość albo nic” pozostaje bez wyjątków. Nie zmieniać `fallback.py` (jest ostatni, wykrywa długie ciągi numeryczne, a nie wszystkie alfanumeryczne IBAN).
3. Granice: brak nadmiernego pochłaniania etykiety `Konto/IBAN`, następnego zdania, końcowej kropki, sąsiednich słów lub linii; nie tokenizować przypadkowych krótkich ciągów w rodzaju `GB82 WEST`. Bez zmian tokenów, S2–S5, Guard i OCR lokalnej części e-maila.

TASK_SCOPE:
- backend/layers/ocr_normalizer.py
- backend/layers/financial.py
- backend/tests/test_layers.py
- backend/tests/test_pipeline_adversarial.py

OUT_OF_SCOPE: inne detektory, `pipeline_new.py`, `fallback.py`, `output_guard.py`, `anonymizer_init.py`, `TOKEN_RE`, OCR e-maili, T07, UI, profil, nowe zależności/pliki, port Mobile, kompletny parser norm ISO 13616, dowolne zagraniczne identyfikatory poza IBAN, PUBLIC-DATA-TESTS. Każdy dodatkowy owner tylko z dowodem i decyzją w trybie ROZSZERZENIE CC.

## Najmniejszy test / PASS
- **O2 przed/po** w full + Express: syntetyczny `Konto: GB82 WEST 1234 5698 7654 32. Dalej.`, także `IBAN: ...`. Przed: z raportu r4 jawny `6882` + fragment w mapie. Po: jeden `NUMER_NNN` obejmuje całe `GB82 WEST 1234 5698 7654 32`; mapa ma cały span; prefiks/BBAN nigdzie jawnie, `force_block=False`, brak pochłonięcia `Konto:` lub `. Dalej.`. Sprawdź `financial` w izolacji i end-to-end po OCR, bo sam unit test `financial.py` był zielony już przed naprawą.
- Kontrole tej samej klasy: GB z compact BBAN, obcy IBAN z literami i spacjami bez etykiety, DE (same cyfry w BBAN) z/bez etykiety; regresje PL z OCR (np. zamiana J→0), pełne PL/NRB T07 i zwykły e-mail EMAIL-LOCALPART-OCR. Nie wymagać nowej klasyfikacji numerów. Negatyw `Konto: GB82 WEST` nie może otrzymać tokenu za fikcyjny pełny IBAN; tekst po rachunku nietknięty.
- Testy warstwy `backend/tests/test_layers.py` (jawne uruchomienie, bo poza `pytest.ini`) + przynajmniej jeden test pionu full/Express w `backend/tests/test_pipeline_adversarial.py` (zbierany standardowo, obecnie <600 linii). Testy sprawdzają **jedną pełną wartość w mapie**, a nie tylko nieobecność prefiksu w `out`. Symulowane jednoprzejściowe Przywróć, test bez blokady i regresje Guarda. Dokumenty wyłącznie syntetyczne.
- Wyniki: testy celowane, jedna standardowa suita, gate exact SHA; opcjonalnie `audyt/engine_quality.py --seed 2026` porównanie tego samego digest, **nie** traktować braku O2 w M1 jako dowodu naprawy. Bez logowania PII. Jeśli gate (>150 linii albo ratio >5:1) zgłasza decyzję, nie wykonywać samodzielnego poszerzenia.

PASS: pełny O2 i warianty zagraniczne jednym `NUMER_NNN` z kompletną mapą i zachowanym prefiksem kraju; brak regresji polskich i innych istniejących warstw, Guard/force_block nieosłabione, pełny tekst poza tokenem bez zmian. Jeśli samo zabezpieczenie OCR wystarcza, `financial.py` zostawić nietknięty.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/ocr_normalizer.py --symbol _fix_iban_digits
- TARGETS: backend/layers/ocr_normalizer.py --symbol normalize_ocr
- TARGETS: backend/layers/financial.py --symbol apply_financial_layer
- REASON: ustalić dokładne miejsce utraty liter przed detekcją; zachować już istniejącego ownera finansowego bez dublowania.
GATE: 0 nowych plików, ≤600 linii dla nieprzekraczających limitu plików, stare pliki tylko nie pogarszać; >150 linii/ratio >5:1 → decyzja. Codex: BRIEF_ONLY precheck, redukcja zakresu, bez implementacji.
