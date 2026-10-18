# LYNX-SECURITY-REVIEW — zakres i model zagrożeń r1

Badana wersja źródeł: `978522ae6d28d85874f654b9598a386510c935b9` (main po merge Express).
Data: 2026-10-18. Zlecenie Pawła: rozpocząć przegląd; konsultacja zakresu CC w BOARD.
Audyt techniczny, bez napraw produktu i bez orzeczenia prawnej zgodności z RODO.
Oracle: zamrożone `arch/spec.md`, istniejące kontrakty; propozycje i ograniczenia osobno.

## Aktywa i granice

Chronimy dokument wejściowy, tekst wyjściowy, mapy i profil, klucze, archiwum,
metadane i logi. Łańcuch: plik → ekstrakcja/OCR → /preview → pipeline → Guard →
UI/kopiowanie/eksport; osobno profil i lokalne zaszyfrowane archiwum.

| Sytuacja | Proporcjonalna kontrola |
|---|---|
| Obca strona WWW próbuje użyć localhost | Host, CORS/preflight, token, prosta przeglądarkowa wysyłka; bez pełnego pentestu |
| Inny lokalny proces/konto czyta pliki | token/ACL, klucze DPAPI, jawne ślady w profilu/archiwum/logach; zaznaczyć granicę tego samego konta Windows |
| Dokument lub zwykła awaria pozostawia PII | syntetyczne znaczniki przez istniejące endpointy, błędy ekstrakcji/OCR i eksport, logi oraz pliki |
| Katalog programu jest synchronizowany | inwentarz zapisu i mechanizm ścieżek; nie czytać kont ani ustawień chmury użytkownika |
| Dostawca AI otrzymuje niedostatecznie zamaskowany tekst | potwierdzić Guard/Express, opisać znane ryzyko z istniejących raportów bez nowego benchmarku jakości |
| Podatna biblioteka lub niejawne połączenie | znane advisory dla zależności i obserwacja sieci w testowanych przepływach, bez audytu bibliotek |

## Skończona lista prac

1. Inwentarz zapisów, retencji i świadomych eksportów; profil i archiwum syntetyczne.
2. Niezależne sprawdzenie dostępu HTTP i ekspozycji tokenu; przegląd szwu Tauri.
3. Kryptografia: źródło losowości i kluczy, roundtrip, zły klucz, modyfikacja,
   profile/cache i usuwanie; bez statystycznego badania entropii i forensyki.
4. Znaczniki w logach/metadanych/dysku w normalnym przepływie i typowym błędzie.
5. Skan znanych podatności zależności; odróżnić manifest, lock i faktyczny runtime.
6. Aktualne potwierdzenie S3/startu + istniejące pomiary ryzyka resztkowego;
   zachowana powtarzalna checklista/reproduktor i jawne NOT_CHECKED.

Poza zakresem: atak administratora/malware tego samego konta jako obietnica
ochrony systemu, RAM/swap/hibernacja, bezpieczne nadpisywanie SSD, pełny pentest,
nowe GUI/launcher, ocena podstaw prawnych klientów, pełne DPIA, nowy benchmark.
Ocena lokalnego odczytu ma dokumentować rzeczywiste uprawnienia, nie obiecywać
izolacji od dowolnego procesu działającego jako zalogowany użytkownik.

Każdy defekt wymaga TRACE + OWNERSHIP + REPRO na SHA powyżej; znaleziony
wyciek PII oznaczamy SAFETY_PRIVACY. Nie przedstawiamy braku testu jako FAIL.
Przerywamy rozszerzanie scenariuszy po wystarczającym dowodzie tej samej klasy.
Raport: `round_01/tests/tests_r1.txt`; nowe pliki nie nadpisują starszych raportów.
