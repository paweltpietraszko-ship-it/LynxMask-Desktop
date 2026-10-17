# Architekt — rozstrzygnięcie B1/B2 audytu T12

Data: 2026-10-17. Dotyczy implementacji **exact SHA `c96199b00028f7ce7b06ba1c77d51834a3242fec`** i raportu Codexa `round_01/tests/tests_r2.txt`. Nie zmienia `PRODUCT_TRUTH`, testów ani kodu aplikacji; nie jest merge ani PASS implementacji wydanym przez Architekta.

## B1 — AKCEPTUJĘ techniczne doprecyzowanie granicy cleanupu
Dopuszczam wyłącznie pomocniczą bazę `_IMPORT_TMP` inicjalizowaną przed pierwszym importem `pseudominizer_api`, pozostającą w systemowym TEMP do **zakończenia procesu testowego**, kiedy usuwa ją finalizer. To zabezpiecza przed przywróceniem globali API do ścieżki już usuniętej. Właściwy katalog fixture `_tmp` (SQLite i `.enc`) musi być sprzątany po module i po błędzie. Żadna część testu nie może odczytywać, zmieniać ani usuwać realnego archiwum.

Dowód z niezależnego r2: 2×19 w obu kolejnościach importu, sprawdzony cleanup przy błędzie, sentinel i sygnatury archiwum bez zmian, `_IMPORT_TMP` usuwany po zakończeniu podprocesu. Stwierdzenie z pierwotnego briefu „po zakończeniu nie zostaje plik testowy” rozumiem odpowiednio: po zakończeniu modułu nie zostają pliki jego fixture; po zakończeniu procesu nie zostaje także bootstrap pierwszego importu. Nie wolno rozciągać odstępstwa na inne katalogi ani produkty.

## B2 — AKCEPTUJĘ jednorazowe uzasadnione przekroczenie ratio
`gate.py`: **RATIO = 81/12 = 6,8:1**, więc mechaniczny status pozostaje **WYMAGA_DECYZJI**; to nie błąd narzędzia i nie należy fałszować jego wyjścia. Niniejszy zapis rozstrzyga odstępstwo dla tego dokładnego diffu: jedna fixture ze sprzątaniem i przywróceniem globali oraz dwa testy odmowy 401/400, bez nowych plików produktu. Pozostałe checki gate i niezależne testy Codexa były bez uwag. Nie wycinać testów bezpieczeństwa ani cleanupu tylko dla uzyskania ratio poniżej 5:1.

## Dalszy etap
Codex: wąsko potwierdź, że B1 i B2 są rozstrzygnięte dla **tego samego SHA implementacji**, bez ponownego uruchamiania 19 testów lub pełnej suity, jeśli kod się nie zmienił. W raporcie końcowym odnotuj odstępstwo gate; nie zmieniaj `gate.py`. Po zamknięciu przekaż do OWNERA — **merge wyłącznie na jawne polecenie OWNERA**.

Odrębne ryzyko spoza T12: inne moduły przy kolekcji importują API i mogą inicjalizować `./archive/rejestr.db`. Nie maskuje go PASS T12; wymaga osobnego zadania izolacji całej suity, bez rozszerzania obecnego TASK_SCOPE.
