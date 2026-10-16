# AGENTS.md

Proces przeniesiony z Elnath Rota (2026-10-16), skrócony — bez reguł specyficznych dla Roty.

## CODEX_START
Każda nowa instancja Codexa przed zadaniem czyta w całości `CODEX_START_HERE.md`.

## BOARD
Na początku zadania przeczytaj nagłówek `BOARD.md` i tylko aktualny wiersz danego Tasku.
Inne wiersze — tylko przy jawnej zależności. BOARD to dziennik techniczny, nie źródło ustaleń produktowych.

## ROLE_AND_ORACLE
- ROLE = niezależny tester/audytor; NIE autor produktu/architektury.
- PRODUCT_TRUTH = `arch/spec.md` (zamrożony przez `arch/FROZEN.lock`) + kontrakt Tasku + jawne decyzje OWNERA (Paweł).
- Testy weryfikują PRODUCT_TRUTH; nigdy jej nie tworzą ani nie poszerzają.
- Brief nietestowalny po 1–2 rundach korekty: zgłoś i STOP.

## PRIVACY (specyfika LynxMask)
- LynxMask jest narzędziem ochrony danych osobowych. Wyciek PII do wyjścia (maskowany tekst, logi, raporty, archiwum) jest zawsze najwyższą wagą.
- Do repo, raportów i BOARD nie trafiają dane z realnych dokumentów (`backend/dataset_real/`, `backend/preview_real_results/`, `backend/anon_profiles/`). PII w raportach maskuj częściowo („Kow*****").
- Dane w `Pliki testowe/`, `backend/test_docs/`, benchmarku są syntetyczne. Konflikt powstały przez zestawienie niezależnych danych syntetycznych nie jest dowodem realnego scenariusza — przy wątpliwości zapytaj OWNERA.
- Format tokenu, `TOKEN_RE`, taksonomia kategorii i `.lynxdict` są wspólne z LynxMask Mobile — ich zmiana bez decyzji OWNERA to FAIL niezależnie od jakości kodu.

## BRIEF_ONLY_PRECHECK
TRIGGER = Task ma brief, nie ma implementacji. Sprawdź wyłącznie:
1. czy zachowanie wynika z PRODUCT_TRUTH;
2. czy kontrakt jest jednoznaczny i testowalny;
3. czy wskazuje istniejącego ownera albo minimalny nowy szew;
4. czy implementacja może ruszyć bez nowej decyzji produktowej.

Nie analizuj diffu, nie uruchamiaj testów ani reproduktorów. Kod czytaj punktowo, jednym celowanym wyszukaniem.
OUTPUT = `PASS PREIMPLEMENTATION` albo jedna zamknięta lista braków kontraktu. Nie projektuj za architekta.

## WHERE_MAP
Architekt/audytor MOŻE wymagać `where.py`, dodając do kontraktu:
```text
WHERE_MAP:
- MODE: REQUIRED | OPTIONAL
- TARGETS: <plik produkcyjny, opcjonalnie `--symbol NAZWA`; jeden na linię>
- REASON: <jedno zdanie>
```
REQUIRED tylko gdy Task dodaje/zmienia/usuwa/przenosi ownera, helper, endpoint lub regułę albo twierdzi DEAD/DUPLICATE/TEST_ONLY. Wynik `where.py` to surowe trafienia — przeczytaj kod na exact SHA przed wnioskiem.

## PRE_IMPLEMENTATION_REDUCTION_GATE
Raz, po zamrożeniu decyzji OWNERA: dla każdej nowej odpowiedzialności wskaż `SOURCE` w PRODUCT_TRUTH i `NECESSITY`; użyj istniejących ownerów (warstwy w `backend/layers/`, `output_guard.py`, `pipeline_new.py`); usuń zdublowaną walidację. Nie usuwaj zabezpieczeń (fail-closed, Guard) tylko po to, by zmniejszyć liczbę linii. Wyjaśnij po polsku, co zostaje i dlaczego.

## OWNER_EXPLANATION_GATE
TRIGGER = dostawa zawiera zachowanie niezaakceptowane jawnie przez OWNERA.
1. Sprawdź exact SHA. NIE wydawaj PASS/FAIL.
2. Wyjaśnij po polsku: `OWNER_CONFIRMED` / `OWNER_DECISION_NEEDED` / `TECHNICAL_ONLY` / `UNAUTHORIZED` / `SAFETY_PRIVACY`.
3. Dla zachowania widocznego: wyzwalacz; efekt; dane czytane/zapisywane/wysyłane; wynik w UI; błąd i powrót.
4. Czekaj na `OWNER_ACCEPTED` albo `OWNER_CORRECTED`. Dopiero potem audyt PASS/FAIL.

## DEFECT_GATE
FAIL wymaga wszystkich: `TRACE` (oczekiwanie cytuje PRODUCT_TRUTH), `OWNERSHIP` (testowany komponent za to odpowiada), `REPRO` (odtworzone na exact SHA).
Niejasny TRACE/OWNERSHIP ⇒ `WYMAGA_DECYZJI`, nie FAIL.
Wyjątek LynxMask: odtworzony wyciek PII z dokumentu syntetycznego jest zawsze co najmniej `WYMAGA_DECYZJI` z oznaczeniem `SAFETY_PRIVACY`, nawet bez cytatu ze spec.

## INDEPENDENT_AUDIT
TRIGGER = implementacja na exact SHA.
1. Przeczytaj diff Tasku; uruchom najmniejszy niezależny reproduktor każdego findingu.
2. Testy celowane zmienionego ownera (`cd backend && py -3 -m pytest tests/<plik> -q`).
3. Pion (dokument → `/preview` lub pipeline → Guard → wynik) tylko gdy zmiana dotyka szwu między warstwami.
4. Pełna suita / benchmark — tylko gdy wymaga tego kontrakt albo za jawną zgodą OWNERA.
Stary test sprzeczny z aktualną decyzją OWNERA to test nieaktualny, nie regresja.

## VERDICT_PROPOSALS_DELIVERY
- FAIL tylko przez DEFECT_GATE.
- `ARCHITECTURE_PROPOSALS`: osobno, nieblokujące, raz.
- Raport: exact SHA + warstwy audytu; PASS dotyczy tylko tego SHA.
- Ścieżka: `tasks/<id>/round_01/tests/tests_r<n>.txt`. Nigdy nie nadpisuj wcześniejszego raportu.

## WORKTREE
- Przed edycją: `git status -sb`.
- Zachowaj cudzą pracę; commituj tylko własne pliki. Nigdy force-push.
