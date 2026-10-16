# LynxMask Desktop — zamrożone kontrakty (PRODUCT_TRUTH)

STATUS: FROZEN. OWNER_ACCEPTED 2026-10-16: „To są twoje dokumenty i codexa jeśli chcesz je mrozić to zamrażaj".
Każda zmiana po zamrożeniu: decyzja OWNERA → edycja → ponowne `freeze` w osobnym commicie.

Źródła: `PROJEKT_KONTEKST.md` (sekcje „Zasady nienaruszalne", „Output Guard", „Bezpieczeństwo — stan"),
`C:\Projects\LynxMask\MASTER_LynxMask_Desktop.md`. Spisane 2026-10-16 bez zmiany zachowania — to opis
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

## S5. Brak PII poza mapą

- `AUDIT_MODE = False`; logi tylko konsola, bez FileHandler — PII nie trafia na dysk w logach.
- Rekord audytu nie zawiera pola `original`.
- Mapa zapisywana na dysk wyłącznie zaszyfrowana; parametry KDF (AUD-13/14, PBKDF2) bez zmian bez planu migracji.

## S6. Interfejs

- UI używa słów „Zamaskuj" / „Przywróć"; nazwy w kodzie backendu (`pseudominizer_*`) zostają.
- Backend nasłuchuje lokalnie na porcie 8765; każde wywołanie wymaga tokenu API.
