# LYNX-HERBERT-NET — brief Architekta v1, do Codex BRIEF_ONLY

2026-10-21. **STATUS: READY_FOR_CODEX.** Kierunek zaakceptowany przez OWNERA: **wkładamy HerBERT-a teraz**, eksperyment kolorów OSOBA odkładamy. Źródło: [propozycja CC `91e096b`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/91e096ba3b886272af0ef8d383bd0b1b9f93b732/tasks/LYNX-HERBERT-NET/cc_proposal.md). Zastępuje K1a z LYNX-K1-PERSONS-FIRMS. **Nie kodować przed precheckiem Codexa.**

## Kontrakt (mały, bez nowej architektury OSOBA)

**HerBERT = ostatnia dodatkowa siatka na nadal jawne osoby**, po istniejącym maskowaniu (spaCy, słowniki, struktury, fallback), **bezpośrednio przed jednym dotychczasowym wywołaniem OutputGuarda**. Miejsce proponowane przez CC: `backend/pipeline.py::_apply_guard` dla aktywnej ścieżki `USE_NEW_PIPELINE=True`. Nie wstawiać HerBERT-a jako konkurenta spaCy, nie modyfikować NER/OSOBA, S1–S6, sposobu działania Guarda ani wyników wcześniejszych warstw.

- Uruchamiamy lokalny `lexedit/herbert-polish-legal-ner`, kwantyzowane ONNX, tokenizację offline; **pierwszy etap maskuje tylko `PER → OSOBA`**. ORG/LOC/ID nie dokładają tokenów, żadnego równoległego FIRMA-REDESIGN. Źródło modelu i dokładną rewizję, nazwy wymaganych plików, checksumy SHA256 wag/tokenizera/configu CC ustala i zapisuje przed testem. Model i jego pliki w `backend/models/herbert/` lub istniejącym uzgodnionym lokalnym katalogu modeli; nie commitować wag ani pobierać ich w czasie pracy produktu.
- Model może użyć już zamaskowanego tekstu jako **kontekstu**, ale **nowa podmiana dotyczy tylko kompletnego, jawnego fragmentu źródłowego**: żaden span nowego PER nie może nachodzić na istniejący `KATEGORIA_NNN` ani przekraczać jego granic. Nie modyfikować ani odkrywać starych tokenów, nie maskować ich fragmentów, nie mieszać zakresów wejścia po przesunięciu offsetów.
- Zanim `PER` dostanie token, sprawdzić istniejące, nieinwazyjne filtry na oczywiste FP (słowa techniczne i kategorie tokenów, nagłówki, instytucje oraz jednowyrazowe osoby, wymagające potwierdzenia). Nie tworzyć nowego silnika kontekstowego ani kolejnych list wyjątków. Granice słów, offsety tokenizera, BIO, nakładanie spanów i długie teksty z oknami oraz zakładką muszą być obsłużone deterministycznie; **brak cichego ucięcia** za limitem modelu.
- Dołożone tokeny otrzymują unikalne identyfikatory bez kolizji z mapą profilu i sesji, zachowując regułę tej samej wartości→ten sam token i `Przywróć` 1:1. Istniejąca mapa nie może zostać nadpisana ani zmienić znaczenia. **Po siatce zwykły OutputGuard sprawdza ostateczny tekst raz**, nie drugi odrębny Guard.
- `LYNX_HERBERT=off` **obowiązkowo daje bajtowo identyczny wynik** jak dotychczas, bez ładowania wag, czasu inferencji i zmian startu. **Pilot początkowo OFF domyślnie, ON jawnie na maszynie testowej**; po pomiarze OWNER osobno zdecyduje o domyślnym ON. Gdy ON, model musi być lokalny i gotowy: brak pliku/niewłaściwy hash/błąd inicjalizacji lub inferencji → **S3 fail-closed, nigdy ciche pominięcie**. Komunikat użytkownika: „Dodatkowa kontrola HerBERT nie działa. Spróbuj ponownie lub użyj wersji bez tej dodatkowej kontroli.” Wyłączenie tylko świadomym przełącznikiem, bez automatycznego downgrade po błędzie.
- Tryb offline S1: żadnego połączenia do zewnętrznych hostów, telemetryka ONNX wyłączona. `tokenizers` przypięty wersją zgodnie z `backend/requirements.txt`, sprawdzona zgodność Python 3.14. Atrybucja modelu lexedit oraz bazy Allegro, licencja CC BY 4.0, w istniejących informacjach o licencjach/README (bez przebudowy interfejsu).

## TASK_SCOPE

Minimalni właściciele: **nowy `backend/herbert_net.py`**, punkt wywołania w **`backend/pipeline.py`**, mała próba w **`backend/startup_check.py`** działająca tylko przy `ON`, **`backend/requirements.txt`**, celowane testy oraz krótka informacja licencyjna. Zero zmian `ner_layer.py`, `layers/ner_adapter.py`, `output_guard.py`, API, UI, archiwum, `arch/spec.md` lub FROZEN.lock. Nie dodawać nowego ogólnego frameworka NER. Gdy CC znajdzie konieczność rozszerzenia — **STOP → Architekt/OWNER**.

**Budżet:** CC szacuje ~290 linii. To tylko szacunek, nie automatyczna zgoda na ponadlimitową zmianę. Zgoda OWNERA 19.10 na rozmiar K1a była na ówczesny zakres; **przed kodem CC ma potwierdzić, czy obejmuje TEN brief; przy niejasności pyta OWNERA o jeden konkretny limit**. Pliki/funkcje zgodnie z gate.py; kod ma być mały.

## Pomiar i kryterium decyzji — falsyfikacja zamiast deklaracji „bez regresji”

Na **tym samym tekście wejściowym, profilu i exact SHA** zmierzyć OFF vs ON. Minimum: zestaw syntetycznych przypadków z nazwiskami/kolizjami, istniejące dane clean z gold oraz aktualna miarka benchmarkowa; holdout niezależny i nieużyty do wyboru progu. Dokumenty OWNERA tylko lokalnie, do repo wyłącznie liczby i zanonimizowane przykłady.

Raport CC przedstawia łącznie:
1. **Nowe prawidłowe maski:** ile wystąpień osoby było wcześniej jawnych, a teraz zakrytych (potwierdzenie gold/okiem, nie sam licznik tokenów).
2. **Nowe błędy:** wszystkie dodatkowo zakryte zwykłe słowa/nagłówki/instytucje (osobno), blokady Guarda przed/po, wierność `Przywróć` 1:1 i niezmienność starych tokenów.
3. **Koszt:** mediana/p95 czasu OFF/ON, RAM i przypadek długiego dokumentu (ok. 60 tys. znaków). Progów PER i budżetu czasu **nie dostrajać na holdoucie**. Jeśli próg nie ma wiarygodnej kalibracji, utrzymać fazę jako eksperyment, nie domyślną ochronę.
4. **Porównanie pomocnicze** HerBERT sam vs spaCy sam na wspólnym gold, o ile da się je wykonać bez zmiany produkcyjnego silnika; **nie warunkuje włączenia siatki** i nie uprawnia do zamiany kolejności.

Decyzja OWNERA po raporcie: **utrzymujemy ON / poprawiamy w wąskim zakresie / wyłączamy i ewentualnie usuwamy**. Samo jedno nowe trafienie nie uzasadnia wdrożenia, jeśli kosztem jest duża liczba FP lub nieakceptowalna zwłoka. Żadnych niezweryfikowanych procentów; przede wszystkim lista przypadków do oceny OWNERA.

**Testy brzegowe:** `OSOBA_001` / `OSOBA_099` nietknięte i bez kolizji, dwa identyczne nazwiska w kilku miejscach, wybrany PER obok tokenu lub przez granicę jego spanu, NER na wielowierszowym polskim tekście, długie słowo/okna BIO, dwa PER nakładające się, złe offsety, niepoprawny hash, brak modelu przy ON, bez zmian przy OFF, błąd inferencji → blokada, wymagany komunikat z alternatywą, izolacja bez sieci i brak PII w logach/raportach.

## Przekazanie — zwykła droga

**Codex teraz BRIEF_ONLY**, na **dokładnym SHA** gałęzi zadania, bez uruchamiania modelu, testów, kodu, bez obchodzenia budżetu: oceń minimalny szew przed Guardem, ochronę starych tokenów/unikalność mapy, S1/S3 przy ON i OFF, walidację spanów i odwrotność, zdolność pomiaru bez nieuczciwych metryk, jednoznaczność wyboru domyślnego OFF. Zwróć PASS lub małą, konkretną listę uwag. Po PASS: **CC review zakresu/budżetu → CC implementacja → Codex audyt exact SHA → OWNER ocena pomiaru i decyzja merge/aktywacji**. PASS ≠ zgoda OWNERA.
