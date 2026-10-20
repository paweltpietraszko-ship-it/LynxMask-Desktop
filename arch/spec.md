# LynxMask Desktop — zamrożone kontrakty (PRODUCT_TRUTH)

STATUS: FROZEN przez CC 2026-10-16 za zgodą OWNERA („To są twoje dokumenty i codexa jeśli chcesz je mrozić to zamrażaj").
Zawartość to opis zasad istniejących w projekcie przed 2026-10-16, nie nowe decyzje produktowe.
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

- Guard jest szerszy niż pipeline (GUARD-BROAD): prostszy wzorzec, wyższy recall, akceptuje fałszywe alarmy.
- HIGH (1 trafienie blokuje): PESEL, NIP, IBAN, DOWÓD, PASZPORT, EMAIL.
- MEDIUM (suma wag ≥ 3 blokuje): REGON (1), TELEFON (1).
- GuardAllowlist: użytkownik może oznaczyć konkretną wartość jako „to nie PII".

- Ręczna korekta nadmaskowania (OWNER zatwierdził 2026-10-20, LYNX-MANUAL-REVEAL): dopiero po zwykłym przejściu OutputGuarda i obsłużeniu obowiązujących alertów użytkownik może świadomie odkryć **jedno dokładne wystąpienie** zamaskowanego tokenu w bieżącym dokumencie. Zgoda jest lokalna dla konkretnego wystąpienia/sesji i może zostać cofnięta; nie tworzy globalnej allowlisty ani wyjątku dla innych miejsc, nazwisk czy dokumentów.
- Po takim odkryciu kontrola końcowego tekstu **nie zgłasza ponownie MAP_LEAK wyłącznie z powodu tej jednej potwierdzonej pozycji**. Pozostałe wystąpienia i niezależne naruszenia podlegają normalnej kontroli mapowej. Pełny rzeczywiście udostępniany tekst pozostaje objęty regułami HIGH/MEDIUM, bez wyjątków. Błąd Guarda, brak wiarygodnego kontekstu, niedozwolona edycja lub nieobsłużony alarm nadal oznacza blokadę (S3). Zgoda na odkrycie nie unieważnia żadnego wcześniejszego HIGH ani blokady.
- Walidacja zgody musi opierać się na wiarygodnym kontekście sesji i konkretnym wystąpieniu, nie na samej nazwie tokenu, globalnej wartości, decyzji klienta ani wartości w allowliście. Odkrycie/cofnięcie i każda zmiana wersji wyniku unieważnia poprzednią zgodę na **udostępnienie całego tekstu**; ponowna kontrola musi dotyczyć dokładnie tekstu kopiowanego/zapisywanego/eksportowanego. Nie wolno odkrywać wszystkich identycznych tokenów przez globalną zamianę.

## S5. Brak PII poza mapą

- `AUDIT_MODE = False`; logi tylko konsola, bez FileHandler — PII nie trafia na dysk w logach.
- Rekord audytu nie zawiera pola `original`.
- Mapa zapisywana na dysk wyłącznie zaszyfrowana; parametry KDF (AUD-13/14, PBKDF2) bez zmian bez planu migracji.

## S6. Interfejs

- UI używa słów „Zamaskuj" / „Przywróć"; nazwy w kodzie backendu (`pseudominizer_*`) zostają.
- Backend nasłuchuje lokalnie na porcie 8765; każde wywołanie wymaga tokenu API.
