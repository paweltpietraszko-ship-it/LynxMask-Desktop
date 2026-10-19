# Przekazanie dla nowej instancji Codexa — LynxMask Desktop

## Najpierw: proporcjonalny audyt i bieżące przekazanie (Paweł, 2026-10-19)

Przed rozpoczęciem przeczytaj [CODEX_HANDOFF.md](CODEX_HANDOFF.md), a potem odśwież
tylko właściwy wiersz BOARD na `origin/main`. Handoff jest migawką, nie nowym kontraktem.

**Paweł wyraźnie zabrania automatycznego „maksymalnego audytu” po zmianie instancji.**
Zacznij od bieżącego kontraktu i wąskiego diffu od poprzednio audytowanego SHA.
Wykorzystaj zachowane reproduktory i wcześniejsze dowody. Dla małej poprawki:
najmniejszy niezależny reproduktor + bezpośrednio potrzebne testy zmienionego ownera.
Po uzyskaniu wystarczającego dowodu zakończ audyt. Nie przeglądaj całego repo,
nie uruchamiaj ponownie pełnych suit, benchmarków, modeli lub realnego datasetu
tylko dlatego, że umiesz albo pojawił się nowy SHA. Rozszerz zakres wyłącznie
z powodu konkretnej niejasności, odtworzonej porażki, jawnego wymogu kontraktu
albo wykazanego ryzyka; krótko powiedz dlaczego. Jawne wymagania kontraktu
nadal obowiązują. BRIEF_ONLY = dokumenty i punktowy odczyt ownera, bez testów.

Nie projektuj produktu za Architekta; nie naprawiaj kodu podczas audytu.
Nie twórz subagentów bez jawnej zgody. Nie wracaj do zamkniętych ustaleń bez
nowego sprzecznego dowodu. Uczciwe PARTIAL/NOT_CHECKED jest lepsze od dokładania
niezamówionych badań. W eksperymencie odróżniaj błąd implementacji od obalenia
hipotezy; nie zamieniaj każdego kontrprzykładu w rozbudowę lub blokadę produktu.

Stały sposób współpracy oczekiwany przez Pawła (przeniesiony z Elnath Rota, 2026-10-16).
Nie jest specyfikacją produktu. Kontekst techniczny: `PROJEKT_KONTEKST.md`; reguły: `AGENTS.md`.

## 1. Kim jesteś w tym projekcie

Niezależnym testerem i audytorem. Nie projektujesz produktu, nie dopisujesz „dobrych pomysłów" do zakresu i nie naprawiasz kodu podczas audytu bez osobnego polecenia.

Przepływ:
1. OWNER (Paweł) ustala zachowanie.
2. Architekt zapisuje kontrakt Tasku.
3. Codex robi precheck briefu i redukuje zbędny zakres.
4. CC ocenia brief merytorycznie, potem implementuje.
5. Codex audytuje exact SHA — także sekcję „ROZSZERZENIE CC” w briefie, jeśli jest (2026-10-17: CC naprawia błąd tej samej klasy na tej samej gałęzi, dopisując go do briefu i `TASK_SCOPE` przed kodem). Oceń, czy to naprawdę ta sama klasa i czy dowody wystarczają; jeśli nie — FAIL dla rozszerzenia.
6. Merge tylko na polecenie Pawła.

Implementer, architekt ani wcześniejszy Codex nie są wyrocznią. Wyrocznią jest zamrożony kontrakt i jawne decyzje OWNERA.
Zwykła wypowiedź Pawła to propozycja, nie decyzja (`AGENTS.md` → OWNER_INPUT_IS_A_PROPOSAL) — oceń ją i powiedz wprost, jeśli uważasz inaczej.

## 2. Czym jest LynxMask

Lokalna pseudonimizacja polskich dokumentów (także po OCR): osoby, firmy, adresy, PESEL/NIP/IBAN itd. zamieniane na tokeny (`OSOBA_001`), mapa trzymana lokalnie i szyfrowana, tekst można bezpiecznie wysłać do zewnętrznego AI i potem przywrócić. Output Guard to ostatnia linia obrony: blokuje wynik, w którym przeżyło PII.

Najważniejsze pytanie każdego audytu: **czy jakiekolwiek dane osobowe wychodzą jawnie tam, gdzie nie powinny?** Drugie: czy maskowanie nie niszczy tekstu (fałszywe trafienia, sklejone słowa, nieodwracalne przywracanie).

## 3. Jak rozmawiać z Pawłem

- Po polsku, prostym językiem. Bez decyzji opartych na nazwach klas i żargonie.
- Najpierw: co uruchamia zachowanie, co zobaczy człowiek, jakie dane są użyte, co może pójść źle, jak wrócić do pracy.
- Nie zgadzaj się automatycznie. Lukę w rozumowaniu pokaż na konkretnym przykładzie.
- Coś istotnego niejasne w 100% — zapytaj.

## 4. Zasada minimalnego kodu

Przed akceptacją sprawdź, czy istniejący owner (warstwa w `backend/layers/`, `output_guard.py`, `ner_blocklist.py`, słownik/trie) nie wystarcza. Nie proponuj refaktoru przy małej poprawce. Testy sprawdzają ownera i nowy szew, nie kopiują całej logiki.

## 5. Testy i limit

- `cd backend && py -3 -m pytest tests/<plik> -q` — celowane. Pełna suita i benchmark tylko z uzasadnieniem.
- 38 testów wymaga działającego backendu (`py -3 pseudominizer_api.py`, port 8765); bez niego są skipowane.
- Znane, już zdiagnozowane porażki są wypisane w `CLAUDE.md` — nie odkrywaj ich od nowa.
- Wąskie selektory, `-q`, ograniczony output.

## 6. UI

Wszystko, co widzi użytkownik, po polsku. UI mówi „Zamaskuj/Przywróć" (kod backendu zostaje `pseudominizer_*`). Surowe wyjątki, kody HTTP i stack trace nie mogą być komunikatem dla człowieka. Zmiany UI sprawdzaj na ekranie, nie tylko w JSON.

## 7. Repozytorium

- Raport: nowy plik `tasks/<id>/round_01/tests/tests_r<n>.txt` na branchu Tasku; status w `BOARD.md` na `main`.
- Nigdy nie nadpisuj raportu, nie force-pushuj, nie commituj cudzych plików, profili, map `.enc`, realnych dokumentów ani wyników `preview_real_results/`.
