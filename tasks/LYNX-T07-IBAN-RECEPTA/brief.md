# LYNX-T07-IBAN-RECEPTA — pełne maskowanie rachunku przed numerem recepty

STATUS: BRIEF_ONLY. Precheck Codexa → ocena CC → implementacja CC → niezależny audyt SHA. Bez merge.
PRODUCT_TRUTH: `arch/spec.md` S1 (identyfikatory nie opuszczają komputera), S2 (format NUMER_NNN i wierność odstępów), S3 (fail-closed), S4 (IBAN = HIGH w Output Guard), S5 (brak PII w logach). Źródło reprodukcji: `backend/tests/test_audyt_2026_10.py::test_iban_pl_bez_jawnej_resztki`, `backend/tests/test_pipeline_v2.py::TestIbanWithSpace::test_iban_reverse_map_entry`; `arch/FINDING_2026-10_MOBILE_PORT.md` § IBAN_EARLY; `arch/PLAN_2026-10.md` pkt 5; `BOARD.md` LYNX-THREAT-MODEL.
OWNER_PROPOSAL: po T11 naprawiać najpierw bezpośrednie wycieki, wybrać IBAN-RECEPTA lub EMAIL-LOCALPART-OCR. Ocena Architekta: najpierw IBAN — odtwarzany test produkcyjnej ścieżki i znany FAIL pełnej suity. To zgoda na przygotowanie briefu, NIE polecenie merge.

## Wada i minimalne rozwiązanie
- `pipeline_new.py` wykonuje `apply_credentials_layer` PRZED `apply_financial_layer`, zarówno w `run_pipeline_new`, jak i `run_pipeline_express`. `credential_patterns.json` zawiera wzorzec numeru recepty z opcjonalną etykietą i dowolnymi 22 cyframi: wycina końcówkę rachunku, zanim warstwa `financial` może objąć pełny IBAN. Efekt: jawne `PL6110…` i fragmentaryczna mapa tokenu.
- **Najpierw próba najmniejszej naprawy: istniejąca `apply_financial_layer` ma działać przed `apply_credentials_layer`** w obu pipeline'ach. Nie dodawać drugiego rozpoznawania IBAN, nie ingerować w wzorzec recepty tylko po to, by naprawić kolejność, nie kopiować Mobile StructuralEngine.
- Drugi reproduktor ma **26 cyfr polskiego NRB bez prefiksu PL** (tekst „Konto 61109010140000071219812874 w banku”). Dzisiejsze `financial.py` ma wpis 24 cyfr i wzorce z separatorami, ale brak jawnego 26-cyfrowego NRB bez separatorów; dlatego **sama zmiana kolejności może nie usunąć tej resztki**. Jeżeli punktowy reproduktor potwierdzi ten stan na exact SHA, dopuścić **jedną wąską regułę w istniejącym `layers/financial.py`**: 26 cyfr jako cały span polskiego rachunku przy jednoznacznym kontekście rachunku/przelewu. Nie maskować dowolnej sekwencji cyfr w dowolnym tekście jako rachunku. Nie projektować uniwersalnego parsera finansowego ani dodatkowej warstwy.
- Granica właścicieli: `financial` ma przejąć **całą** wartość konta przed `credentials`; `credentials` nadal ma obsługiwać prawdziwe 22-cyfrowe numery recept z etykietą. Nie rozciągać w tym Tasku naprawy na obcy IBAN OCR/niepewne długości, dopóki nie ma reproduktora z tej samej klasy.

## Zachowanie użytkownika
Przy „Zamaskuj” tekst zawierający prawidłowo rozpoznawalny polski IBAN z `PL` i odstępami albo 26-cyfrowy NRB w jawnym kontekście bankowym jest zastąpiony **jednym istniejącym tokenem `NUMER_NNN`** obejmującym cały identyfikator, bez jawnej resztki w wyniku ani sztucznego dodawania cyfr. `reverse_map` zawiera odpowiadającą pełną wartość znormalizowaną do tego, co faktycznie poddano maskowaniu; nie może być samym 22-cyfrowym ogonem.
Przy niewystarczającym rozpoznaniu/awarii obowiązują istniejące S3/S4 — Guard HIGH nie może zostać osłabiony ani wyłączony; wynik częściowy nie może być traktowany jako bezpieczny i gotowy do kopiowania. Nie dodawać komunikatów ani ustawień UI. Rozszerzone Przywracanie oryginalnej interpunkcji i formatu przed normalizacją to osobny `LYNX-TEXT-FIDELITY-F3`.

TASK_SCOPE:
- backend/pipeline_new.py
- backend/layers/financial.py
- backend/tests/test_audyt_2026_10.py
- backend/tests/test_pipeline_v2.py

OUT_OF_SCOPE: `backend/credential_patterns.json` (najpierw nie zmieniać słownika recept), `backend/layers/credentials.py`, `output_guard.py`, `anonymizer_init.py`, `layers/ocr_normalizer.py`, frontend, T11/F3, EMAIL-LOCALPART-OCR, dowolne zmiany S2/TOKEN_RE, automatyczne przechodzenie do Express, nowy parser IBAN, obsługa realnych plików i profilu użytkownika.

## Najmniejszy test i kryteria PASS
1. **Przed/po na exact SHA:** dwa istniejące przykłady `test_iban_pl_bez_jawnej_resztki` (PL + spacje i 26 cyfr bez PL w kontekście). Usuń `xfail(strict=True)` dopiero po naprawie. Nie sprawdzaj tylko, że „6110” zniknęło: dla każdego przykładu `reverse_map` zawiera **całe** konto pod jednym tokenem, a `out` ma ten token **zamiast całego** spanu; brak `PL61`/prefiksu/końcówki poza tokenem. Sprawdź niezablokowany wynik oraz brak jawnego identyfikatora; zgłoszony `force_block=True` nie zalicza sukcesu maskowania.
2. **Regresja suity:** `TestIbanWithSpace::test_iban_reverse_map_entry` na dotychczasowym polskim IBAN oraz `test_iban_with_spaces_masked` i `test_iban_with_spaces_token_in_output` — wszystkie PASS. W tym samym szwie kontrola `run_pipeline_express` (wykrywanie IBAN bez NER), bo zamiana kolejności musi dotyczyć obu funkcji.
3. **Kontrpróby:** prawidłowy `Numer recepty: <22 cyfry>` nadal tokenizowany; obcy IBAN (np. DE/GB) nadal maskowany; `NIP`/PESEL nie zmieniają kategorii ani wyniku; przypadkowy tekst zawierający 26 cyfr BEZ kontekstu bankowego nie powinien otrzymać nowego rozpoznania przez regułę NRB (weryfikować osobno zachowanie innych istniejących reguł). Zachować spacje i interpunkcję **poza spanem** identyfikatora, bez pochłaniania końca linii lub następnego słowa.
4. **Dwa właściciele i wspólny szew:** porównaj na tych samych danych `run_pipeline_new` oraz `run_pipeline_express`. Pozostałe endpointy/Guard bez zmian. Do audytu dowód wynik → token → pełna wartość w `reverse_map`, z syntetycznych danych.
5. Testy celowane: `cd backend && py -3 -m pytest tests/test_audyt_2026_10.py tests/test_pipeline_v2.py -q -o log_file=NUL` (Windows). Raportuj odrębne istniejące xfail, jeśli nie dotyczą T07; pełna suita co najwyżej raz, jeśli jest konieczna do oceny, bez rozszerzania Tasku.
6. `audyt/engine_quality.py --seed 2026` M1 z tym samym digestem wejść przed/po: IBAN już nie `partial_mask` w naprawionym wariancie, brak nowego `leak` i nieuzasadnionego M2 `fp`. Nie deklarować „0 wycieków w świecie” na podstawie syntetycznych przykładów.

PASS: brak jakichkolwiek jawnych fragmentów **testowanych** rachunków, pełna wartość w mapie jednego `NUMER_NNN`, recepta zachowana, oba tryby działają, Guard S3/S4 i brak PII w logach bez zmian. Jeśli przełożenie warstw daje niepożądaną nową kolizję, Codex/CC zgłasza wąski finding; nie poszerzać samodzielnie wzorców lub list.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_new
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_express
- TARGETS: backend/layers/financial.py --symbol apply_financial_layer
- REASON: przełożenie istniejących ownerów i ewentualne wąskie 26-cyfrowe NRB; zweryfikować konsumentów i kolejność przed zmianą.
GATE: zero nowych plików, `TASK_SCOPE` zamknięty, >150 zmienionych linii lub ratio >5:1 wymaga decyzji; nie usuwać ważnych testów dla przejścia gate. Codex: BRIEF_ONLY precheck bez uruchamiania testów i bez implementacji; CC oceni wykonalność i falsyfikuje zakres przed zmianą kodu.
