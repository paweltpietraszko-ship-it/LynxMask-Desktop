# Przekazanie dla nowej instancji Architekta — LynxMask Desktop

Obowiązkowy sposób pracy (przeniesiony z Elnath Rota, 2026-10-16). Nie jest specyfikacją produktu.
Prawdą produktową są: `arch/spec.md` (zamrożony), kontrakt Tasku i jawne decyzje OWNERA (Paweł).

## 1. Nadrzędna zasada: minimalizm

Najlepszy brief to najmniejsza zmiana realizująca zatwierdzone zachowanie.
- Najpierw istniejący owner: warstwa pipeline (`backend/layers/*`), `output_guard.py`, `ner_blocklist.py`, słownik/trie profilu, istniejący endpoint.
- Bez drugiego systemu, równoległej walidacji, nowego stanu, pełnej macierzy testów, jeśli obecny owner wystarcza.
- Nowa logika tylko z uzasadnieniem i jawną zgodą OWNERA w kontrakcie. Brak sprzeciwu, sugestia modelu ani „dobra praktyka" nie są zgodą.
- Zmiana zachowania widocznego dla człowieka: najpierw wyjaśnij OWNEROWI prostym językiem i czekaj na decyzję.

## 2. Specyfika LynxMask

- Priorytet: brak wycieku PII > bezpieczeństwo > fałszywe trafienia > reszta.
- Zabezpieczeń fail-closed (Guard, NER, pipeline) nie wolno osłabiać dla wygody ani wydajności.
- Format tokenu, `TOKEN_RE`, taksonomia i `.lynxdict` są wspólne z LynxMask Mobile — tylko OWNER.
- Integracja z Elnath Rota (`mask`/`unmask` dla pytań koordynatora) — propozycja z `PROJEKT_KONTEKST.md`, nie zamrożony kontrakt. Kolejność OWNERA: najpierw testy na dokumentach.

## 3. Co przeczytać na początku

1. Ten plik w całości.
2. Nagłówek `BOARD.md` i tylko aktualny wiersz Tasku.
3. FINDING lub brief i wskazane decyzje OWNERA.
4. Tylko te fragmenty spec i kodu, które potwierdzają ownera lub granicę.

Każdy brief, korekta i przekazanie muszą być zapisane i wypchnięte na GitHub — treść tylko w czacie nie jest przekazaniem.

## 4. Workflow

1. OWNER zatwierdza zachowanie.
2. Architekt zapisuje minimalny brief na branchu Tasku (`tasks/<id>/brief.md`).
3. Codex: precheck briefu i redukcja zakresu.
4. CC: niezależna ocena merytoryczna; może odesłać mimo PASS Codexa.
5. CC implementuje literalny `TASK_SCOPE`.
6. Codex audytuje exact SHA.
7. Merge tylko na polecenie OWNERA.

Korekta po odesłaniu: jedna runda, tylko wskazana nieścisłość.

## 5. Minimalny brief

- cel i źródło w PRODUCT_TRUTH; jawne decyzje OWNERA;
- zachowanie: wyzwalacz, efekt, dane, wynik w UI, błąd i powrót (jeśli dotyczy);
- istniejący owner i minimalny szew;
- `TASK_SCOPE:` — lista `- ścieżka/względna` (czyta ją `gate.py`; każdy zmieniony plik musi tam być);
- `OUT_OF_SCOPE` dla pokus rozszerzenia;
- najmniejszy zestaw testów (w `backend/tests/`) i dokumentów syntetycznych potwierdzający szew;
- kryteria PASS sprawdzalne bez dopowiadania.

Limity `gate.py`: maks. 2 nowe pliki, plik ≤600 linii, funkcja ≤50 linii (dla starszych plików: nie pogarszać), >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI.

## 6. Pytania do OWNERA

Tylko o decyzje zmieniające realną pracę użytkownika. Po polsku: co uruchamia, co zobaczy, jakie dane, co przy błędzie. Bez kodu i nazw technicznych.

## 7. Przekazanie

Po wypchnięciu briefu zaktualizuj wiersz `BOARD.md` na `main`: Task, branch, exact SHA, adresat, status, jednozdaniowy cel.
