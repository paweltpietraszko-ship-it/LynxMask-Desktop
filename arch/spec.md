# LynxMask Desktop — zamrożone kontrakty (PRODUCT_TRUTH)

STATUS: FROZEN przez CC 2026-10-16 za zgodą OWNERA („To są twoje dokumenty i codexa jeśli chcesz je mrozić to zamrażaj").
S1–S3 i S5–S6 opisują zasady istniejące przed 2026-10-16. S4 zaktualizowano 2026-10-22 po akceptacji OWNERA i PASS PREIMPLEMENTATION Codexa r4 (`LYNX-GUARD-RESIDUE`).
Każda zmiana: uzasadniona propozycja (CC/Codex/Architekt) + zgoda OWNERA → edycja → `py -3 guard.py freeze --recompute arch/spec.md` w osobnym commicie.

Źródła: `PROJEKT_KONTEKST.md` (sekcje „Zasady nienaruszalne", „Output Guard", „Bezpieczeństwo — stan"),
GitHub `paweltpietraszko-ship-it/LynxMask` (master), plik `MASTER_LynxMask_Desktop.md`. Spisane 2026-10-16 bez zmiany zachowania — to opis
istniejących zasad, nie nowe wymagania.

## S1. Cel produktu

Lokalna pseudonimizacja dokumentów (tekst i OCR): dane osobowe i identyfikatory zastępowane tokenami,
mapa token→oryginał przechowywana wyłącznie lokalnie i szyfrowana, przywracanie oryginału w tekście
zwróconym przez zewnętrzne AI. Żadne dane dokumentu nie opuszczają komputera użytkownika.

## S2. Kontrakty wspólne z LynxMask Mobile (zmienia wyłącznie OWNER)

- Format tokenu: `KATEGORIA_NNN` (np. `OSOBA_001`, `NUMER_003`).
- `TOKEN_RE` używa `(?!\d)`, NIE `\b` — zapobiega rozpoznaniu tokenu wewnątrz tokenu.
- Taksonomia kategorii (OSOBA, FIRMA, ADRES, EMAIL, NUMER, KWOTA, INSTYTUCJA, …).
- Format wymiany słownika `.lynxdict`.
- Zakaz globalnego sklejania spacji w normalizacji tekstu.

## S3. Fail-closed

- Błąd Output Guarda = blokada wyniku, nie przepuszczenie.
- Wyjątek w NER = `force_block=True`.
- Wyjątek w pipeline = `(text, {}, True)` — zablokowany wynik.
- `/archive` zwraca 403 dla wyniku z `guard_blocked=True`.
- Wejście zawierające ciąg pasujący do `TOKEN_RE` = 422 (AUD-01, token injection).

## S4. Output Guard

- Guard jest ostatnią kontrolą finalnego tekstu po pseudonimizacji. Wskazuje **konkretne, nadal jawne** fragmenty podejrzane o dane wymagające ochrony; nie jest drugim silnikiem NER i nie zastępuje ich automatycznie `[REDACTED]`. Korzysta z istniejących sygnałów i pięciu grup pozostałości R1–R5 (osoby i pseudonimy, inicjały, resztki przy tokenach/OCR, identyfikatory w kontekście, nazwy firm), z uwzględnieniem wyłączeń opisanych w zatwierdzonym briefie `LYNX-GUARD-RESIDUE`. Dotychczasowe wykrycia HIGH/MEDIUM/MAP_LEAK nie znikają: w normalnej pracy są ostrzeżeniami do oceny.
- Guard może zgłaszać fałszywe alarmy, lecz ma wskazywać wiarygodne podejrzenia, nie przypadkowe wyrazy. LynxMask Mobile jest wzorem **obsługi ostrzeżeń**, nie źródłem kodu ani agresywnych reguł. Nie ma gwarancji wykrycia każdego możliwego PII.
- Każde ostrzeżenie RED/YELLOW wskazuje jedno wystąpienie, jego lokalizację i powód. Użytkownik rozstrzyga je indywidualnie: **Zakryj** (istniejące maskowanie, aktualizacja tokenu/mapy i kontrola wyniku) albo **Zostaw** (świadoma akceptacja konkretnego fragmentu). Nie ma zbiorowego `Zostaw wszystkie` ani `Zapisz mimo to`. Ta sama lokalizacja wykryta z kilku przyczyn nie tworzy kilku niezależnych pytań.
- Dopóki istnieje nierozstrzygnięte ostrzeżenie, aplikacja wstrzymuje **zapis do biblioteki, kopiowanie wyniku i eksport/udostępnianie**. Podgląd i korekta pozostają dostępne. Po obsłużeniu wszystkich ostrzeżeń bieżącego wyniku normalne operacje są dostępne, również jeśli część pozycji świadomie pozostawiono.
- Po zmianie wyniku mogącej odsłonić dane Guard ponownie ocenia aktualny tekst. Świadomie wykonane `Odkryj` konkretnego wystąpienia jest decyzją dotyczącą tego miejsca, a nie nowym wyciekiem MAP_LEAK; kontrola nadal obejmuje pozostały tekst. Decyzja `Zostaw` może pozostać ważna w tej samej sesji po ponownym przeliczeniu tylko dla tego samego rozpoznawalnego wystąpienia i kontekstu; nie przechodzi automatycznie na podobne fragmenty.
- Błąd silnika/NER/pipeline/Guarda jest osobnym **S3 fail-closed** i nie może zostać zaakceptowany przez `Zostaw`. Nie dodaje się oddzielnego serwerowego nadzorcy decyzji, poświadczania zaszyfrowanego archiwum ani ochrony przed celowym obejściem lokalnego UI/API; blokada dotyczy zwykłych operacji aplikacji, nie działania innych programów.
- `Zostaw` w bieżącym dokumencie nie zapisuje automatycznie trwałego wyjątku. Przyszłe trwałe zapamiętywanie jest wyraźnym wyborem użytkownika i wymaga ochrony zgodnej z S5; nie poszerzać jawnego `guard_allowlist.json`. Trwały dziennik decyzji pozostaje odrębnym końcowym zadaniem `LYNX-GUARD-DECISION-LOG`.
- Maskowanie i przywracanie zachowują formaty S2: jedna wiarygodnie ustalona osoba = jeden token także przy odmianach; w przywracaniu dopuszczalny mianownik, ale nie wolno scalać różnych osób.

## S5. Brak PII poza mapą

- `AUDIT_MODE = False`; logi tylko konsola, bez FileHandler — PII nie trafia na dysk w logach.
- Rekord audytu nie zawiera pola `original`.
- Mapa zapisywana na dysk wyłącznie zaszyfrowana; parametry KDF (AUD-13/14, PBKDF2) bez zmian bez planu migracji.

## S6. Interfejs

- UI używa słów „Zamaskuj" / „Przywróć"; nazwy w kodzie backendu (`pseudominizer_*`) zostają.
- Backend nasłuchuje lokalnie na porcie 8765; każde wywołanie wymaga tokenu API.
