# LYNX-ADDR-REVERSED — adres z miastem przed kodem pocztowym („Opole, 45-407, ul. …”)

22.10.2026. Brief: CC. **Wykonawca: Qwen 3.8 (próba OWNERA — ten sam proces co CC: brief → kod → `gate.py` → audyt Codexa).**
Poprawka bez Architekta. Repo: `paweltpietraszko-ship-it/LynxMask-Desktop`, gałąź `task/LYNX-ADDR-REVERSED` (od main).
Kontekst projektu: `PROJEKT_KONTEKST.md`, zasady pracy: `CLAUDE.md` (sekcje GIT WORKFLOW i PIPELINE MECHANICS obowiązują także Ciebie).

## Problem (zmierzony na zbiorze LYNX-GOLD-SET, `BOARD.md` wiersz LYNX-GOLD-SET)
Adres zapisany w odwróconej kolejności, z miastem przed kodem pocztowym, zostaje częściowo jawny:
```
wejście:  Punkt odbioru: Opole, 45-407, ul. Rzemieślnicza 433
dziś:     Punkt odbioru: Opole, 45-407, ADRES_002          ← miasto i kod pocztowy jawne (wyciek)
oczekiwane: Punkt odbioru: ADRES_00n, ADRES_002  albo  Punkt odbioru: ADRES_00n   (miasto+kod zakryte)
```
Kolejność „kod miasto” („45-407 Opole”) już działa: `backend/layers/address.py`, Faza 2b (`_POSTAL_ANCHOR_RE` + `_match_city`).

## Zakres
- `backend/layers/address.py`, `apply_address_layer`: dodaj rozpoznanie **„Miasto, NN-NNN”**.
  - Miasto potwierdzone w bazie SIMC: istniejące `_CITY_FORMS` / `_CITY_FORMS_ASCII`, ta sama logika co `_match_city`, 1–2 słowa, także bez polskich znaków.
  - Między miastem a kodem: przecinek i/lub spacje.
  - Hit dodaj do `all_hits` (jeden wspólny `_apply_hits`, jak inne fazy — nie zmieniaj tekstu w trakcie). Typ `"ADRES"`.
  - Jeśli zaraz po kodzie stoi przecinek i ulica, którą łapie już Faza 1, wystarczą dwa tokeny (miasto+kod oraz ulica). Nakładanie się hitów rozwiązuje `_apply_hits` — sprawdź, że nie powstaje token w tokenie.
- Bez zmian zachowania dla:
  - samego miasta bez kodu („Wrocław, 21.10.2026”, „w Opolu”) — **samo miasto nie jest daną** (polityka OWNERA);
  - daty pisma po mieście („Opole, 22.10.2026 r.”);
  - kodu, który nie ma formatu NN-NNN.
- Bez zmian formatu tokenów, `TOKEN_RE`, `.lynxdict`, `arch/spec.md`. Nowa logika krótka, w istniejącej funkcji albo małym helperze w tym samym pliku. Funkcja `apply_address_layer` ma dziś 56 linii i według `gate.py` (ratchet) nie może urosnąć, więc **logikę umieść w nowym helperze**, a w funkcji zostaw jedną linię wywołania w miejsce istniejącej.

### Rozszerzenie — przypadki z diagnozy Qwen 3.8 (22.10, potwierdzone przez CC na main `b053f56`; OWNER: „dopisz jego przypadki”)
Ta sama klasa: element adresu sąsiadujący z rozpoznanym adresem zostaje jawny albo token tnie adres. Wynik dziś (warstwy bez NER):

| wejście | dziś | wymagane |
|---|---|---|
| „Warszawa, ul. Marszałkowska 12/4, 00-001” | `Warszawa, ADRES_001` | miasto przed adresem z ulicą/kodem też zakryte |
| „ul. Polna 5, Radom” | `ADRES_001, Radom` | miasto tuż po ulicy (bez kodu) zakryte |
| „Adam Kowalski, Radom, ul. Polna 5” | `OSOBA_001, Radom, ADRES_001` | miasto tuż przed ulicą zakryte |
| „00-001 Warszawa, Twarda 18” | `ADRES_001, Twarda 18` | ulica bez „ul.” po kodzie i mieście zakryta |
| „Kraków al. Jana Pawła II 15 31-001” | `Kraków ADRES_001-001` (token tnie kod, `-001` jawne i sklejone) | kod pocztowy nigdy cięty w połowie; miasto, ulica i kod zakryte, bez sklejeń |

Zasada (polityka OWNERA: „adres w całości z miastem; samo miasto NIE jest maskowane”):
- miasto (SIMC) jest częścią adresu tylko wtedy, gdy **bezpośrednio** sąsiaduje (przecinek/spacja) z rozpoznaną ulicą z numerem albo z kodem pocztowym;
- samo miasto bez takiego sąsiada zostaje jawne;
- ulica bez prefiksu („Twarda 18”) jest częścią adresu tylko zaraz po „kod + miasto”;
- liczba tokenów jest dowolna (jeden albo kilka ADRES), ale żaden człon nie zostaje jawny i nie ma tokenu sklejonego z resztą liczby (wzorzec `GLUED` z `test_addr_email_leaks.py`).

TASK_SCOPE:
- backend/layers/address.py
- backend/tests/test_addr_reversed.py
- tasks/LYNX-ADDR-REVERSED/brief.md
- tasks/LYNX-ADDR-REVERSED/repo_before.hash
- tasks/LYNX-ADDR-REVERSED/round_01/implementation/DELIVERY.md

## Odbiór (testy w `backend/tests/test_addr_reversed.py`, wzór: `backend/tests/test_addr_email_leaks.py`, funkcja `_run` z `run_pipeline_new` i wyłączonym NER)
Zakryte (miasto i kod nie występują jawnie w wyniku; Przywróć odtwarza tekst 1:1 jak w `_restore`):
- „Punkt odbioru: Opole, 45-407, ul. Rzemieślnicza 433”
- „Siedziba: Wrocław, 50-001”
- „Adres: Jelenia Góra, 58-500, ul. Długa 1”
- „Adres: Zielona Gora 65-001” (bez polskich znaków, bez przecinka)
- rozszerzenie Qwen: „Warszawa, ul. Marszałkowska 12/4, 00-001”, „ul. Polna 5, Radom”, „Adam Kowalski, Radom, ul. Polna 5” (wymagane: „Radom” niejawne; osoba poza zakresem tego Tasku), „00-001 Warszawa, Twarda 18”, „Kraków al. Jana Pawła II 15 31-001” (dodatkowo: brak sklejenia `GLUED`).
Bez zmian (`out == text`, pusta mapa):
- „Wrocław, 21.10.2026”
- „Spotkanie odbyło się w Opolu.”
- „Opole, dnia 22.10.2026 r.”
- „Kraków, 12.05.2026”
- „Mieszkam w Radomiu od lat.”
- „Delegacja: Warszawa, Kraków, Gdańsk.” (wyliczenie samych miast)
Regresja: `test_addr_email_leaks.py` w całości zielony, a pozostałe testy, które dziś przechodzą (`backend/tests/`, uruchamiaj pliki pojedynczo, zob. `CLAUDE.md`), nadal przechodzą.

## Jak pracować
1. Gałąź `task/LYNX-ADDR-REVERSED` już istnieje (brief + `repo_before.hash`). Commituj na niej. **Nie commituj na `main`.**
2. Testy: `cd backend && python -m pytest -q tests/test_addr_reversed.py tests/test_addr_email_leaks.py` (zależności: `backend/requirements.txt`).
3. Bramka: `python gate.py tasks/LYNX-ADDR-REVERSED/brief.md <sha_bazy> <twój_head> tasks/LYNX-ADDR-REVERSED/round_01/gate_r1.txt`. Bazą jest commit, od którego wyszła gałąź (`git merge-base HEAD origin/main`). Wynik w DELIVERY przepisz dosłownie.
4. `tasks/LYNX-ADDR-REVERSED/round_01/implementation/DELIVERY.md` musi zawierać:
   - co zmieniłeś;
   - wynik testów (dosłownie);
   - wynik gate;
   - znane ograniczenia.
5. Push gałęzi. **Nie scalaj.**
6. Nie dotykaj plików spoza TASK_SCOPE. Dane realne nie są w repo i nie są potrzebne.

Po dostawie: pomiar CC na LYNX-GOLD-SET (lokalnie, `tasks/LYNX-GOLD-SET/measure/human_view.py`), potem audyt Codexa na exact SHA.
Ocena próby (OWNER): poprawność, zgodność z zakresem, czy przeszło gate i audyt bez poprawek.

## Środowisko pracy (po pierwszej próbie 22.10)
Pierwsza próba odbyła się na płytkim klonie z 18.10 (`6cbd0ab`), bez dostępu do `origin`. Gałęzi i briefu nie było, kodu nie powstało. **Wymagane:**
- pełny klon (`git clone https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop`, bez `--depth`);
- `git checkout task/LYNX-ADDR-REVERSED`;
- prawo push do tej gałęzi.

Commity z tamtej próby (`29016e6`, `75aac50` na bazie `6cbd0ab`) porzucić — nie są potrzebne, przypadki z ich diagnozy są już w tym briefie.
Rola: **implementacja** według tego briefu (nie Architekt, nie pisz nowego briefu ani wierszy BOARD).

## Korekta odbioru i wykonawca (CC, 22.10, po zakończeniu próby Qwen decyzją OWNERA)
- Wykonawca: **CC**, od main (WIP Qwena nie jest bazą).
- Daty po mieście („Wrocław, 21.10.2026”, „Kraków, 12.05.2026”, „Opole, dnia 22.10.2026 r.”) są już na main zakrywane jako NUMER (polityka dat).
  Odbiór „bez zmian, pusta mapa” był błędem briefu. Właściwe kryterium: **miasto jawne i brak tokenu ADRES**.
