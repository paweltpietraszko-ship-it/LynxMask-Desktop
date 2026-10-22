# LYNX-GUARD-RESIDUE — brief v2, do oceny Codexa (BRIEF_ONLY)

22.10.2026. Zastępuje sporny brief v1.2. Jest propozycją kontraktu, nie zgodą na implementację ani zmianą zamrożonego S4. s4_change_proposal.md pozostaje propozycją; S3 fail-closed bez zmian.

## Cel i wzorzec

Guard sprawdza finalny tekst po pracy silnika i wskazuje JAWNE fragmenty, które mogą wymagać ochrony. Nie jest drugim silnikiem pseudonimizacji ani automatycznie nie zamienia podejrzeń na [REDACTED]. Wzór obsługi użytkownika: LynxMask Mobile.

Każde ostrzeżenie RED/YELLOW jest osobną pozycją, pokazuje fragment i powód. Użytkownik przy każdej pozycji wybiera ZAKRYJ lub ZOSTAW. ZAKRYJ używa istniejącej ścieżki maskowania, aktualizuje token/mapę i wynik; ZOSTAW akceptuje tylko wskazane wystąpienie w bieżącym dokumencie. Nie ma zbiorowego „zostaw wszystko” ani „zapisz mimo ostrzeżeń”.

Dopóki pozostaje choć jedno nierozstrzygnięte ostrzeżenie, niedostępne są Zapisz do biblioteki, Kopiuj wynik oraz Eksport/udostępnianie z aplikacji. Podgląd i indywidualne rozstrzyganie pozostają dostępne. Po zmianie wyniku mogącej odsłonić dane (również ręczne Odkryj) Guard kontroluje aktualny wynik ponownie; stare decyzje nie dopuszczają nowej, nieocenionej treści. Awaria pipeline/NER/Guarda nadal twardo blokuje wynik zgodnie z S3 i nie podlega ZOSTAW.

W UI komunikat: „Pozostało N ostrzeżeń. Przy każdym wybierz Zakryj albo Zostaw, aby zapisać, skopiować lub wyeksportować dokument”. Przy awarii: „Nie udało się sprawdzić dokumentu. Spróbuj ponownie; jeśli problem się powtarza, zgłoś błąd”.

## Co Guard ma próbować wskazywać

Źródłem pierwszych czterech grup jest diagnoza CC z 19–21.10 w BOARD.md, LYNX-GUARD-RESIDUE. R5 jest uzupełnieniem OWNERA z 22.10. To zakres ostrzegania, nie obietnica wykrycia każdego przypadku.

R1. Nierozpoznane prawdopodobne imiona, nazwiska i pseudonimy (także odmiany i homonimy), jeśli pozostały jawne.
R2. Inicjały przy imionach lub obok tokenu osoby, np. „Marcin S.” albo „OSOBA_001 S.”.
R3. Resztki danych obok istniejących tokenów, także po OCR, np. „NIP: 7 NUMER_021”.
R4. Jawne identyfikatory w czytelnym kontekście dokumentu, np. nr działki, numer klienta, data urodzenia, telefon.
R5. Prawdopodobne nazwy firm, których silnik nie zakrył: nazwy w kontekście kontrahenta, sprzedawcy, nabywcy lub usługodawcy; pełne nazwy z formą prawną; jawne powtórzenie nazwy firmy już rozpoznanej w tym dokumencie, o ile powiązanie jest wiarygodne. Korzystać z istniejących rozpoznań i sygnałów warstwy FIRMA, nie dodawać drugiego NER ani słownika wszystkich firm.

Sygnały starego Guarda HIGH/MEDIUM/MAP_LEAK nie mogą zniknąć: zamiast automatycznego REDACT normalnie trafiają na listę ostrzeżeń. Nie zgłaszać fragmentów wewnątrz istniejących tokenów. To samo wystąpienie wskazane z kilku powodów daje jedną pozycję.

Wyłączenia zgodne z pomiarami CC: samotne miasto, instytucje publiczne, techniczne skróty, daty pisma i sygnatury sądowe bez przesłanek danych osobowych, przypadki świadomie zaakceptowane dla aktualnego wyniku. Samo wystąpienie słowa w słowniku pospolitym nie wystarcza do odrzucenia podejrzenia nazwiska. Nie klasyfikować każdej frazy z wielkiej litery jako firmy; cel to wskazać wiarygodne podejrzenia, nie zalewać człowieka alarmami.

## Kilka przypadków odbioru (tekst po silniku, syntetyczny)

- „Świadek Śludkowskiego nie stawił się” → ostrzeżenie na „Śludkowskiego” (R1).
- „Marcin S. podpisał protokół” → ostrzeżenie na jawne „S.” lub całe jawne „Marcin S.” (R2).
- „NIP: 7 NUMER_021” → ostrzeżenie na „7”, bez obejmowania tokenu (R3).
- „Nr działki 128/7” → ostrzeżenie na „128/7” (R4).
- „Sprzedawca: Biuro Rachunkowe RACHMISTRZ” → ostrzeżenie na „Biuro Rachunkowe RACHMISTRZ” (R5).
- „Nabywca: ALFA sp. z o.o.” → ostrzeżenie na „ALFA sp. z o.o.”, jeśli pozostało jawne (R5).
- „Sąd Rejonowy w Poznaniu” → brak ostrzeżenia FIRMA; instytucja publiczna, nie przedsiębiorstwo.
- „FIRMA_001, NUMER_021” → brak nowego ostrzeżenia na zakrytych tokenach.
- „Warszawa, dnia 21.10.2026” → brak ostrzeżenia z samego miasta i daty pisma.

Wykrycie firmy pozostawionej jawnie nie wymaga stuprocentowej trafności. Rozstrzygnięcie należy do użytkownika. Jeżeli rzetelne wykrywanie danego wariantu R5 wymaga nowego silnika lub dużej przebudowy, Codex ma zgłosić ograniczenie, nie projektować rozbudowy w prechecku.

## Granice techniczne

Wykorzystać istniejące szwy: backend/output_guard.py, backend/pipeline.py, istniejącą obsługę tokenów/mapy, frontend/src/screens/Pseudonimizuj.tsx oraz tylko konieczne dostosowania bieżącego API. Usunąć zbiorowy bypass „To nie PII — zapisz mimo to”. Guard ma zarządzać listą decyzji i blokadą normalnych operacji aplikacji. Nie budować osobnej serwerowej warstwy nadzorującej Guarda, protokołu poświadczania zaszyfrowanego blobu, nowej infrastruktury PSE/rewizji ani ochrony przed celowym obchodzeniem lokalnego UI/API. Nie twierdzić, że aplikacja potrafi zablokować użytkownikowi ręczne wysłanie oryginału w innym programie.

ZAKRYJ ma zachować spójną mapę i Przywróć. Jedna osoba może mieć jeden token niezależnie od odmiany, jeśli jest to wiarygodnie ta sama osoba; kanoniczna forma po przywróceniu jest akceptowana. Nie łączyć różnych osób. Nie przebudowywać rozpoznawania OSOBA/FIRMA w tym zadaniu.

ZOSTAW w bieżącym dokumencie nie oznacza automatycznego dopisania do trwałej allowlisty. Istniejący guard_allowlist.json utrwala jawne frazy; nie rozszerzać takiego zapisu. Trwałe „zapamiętaj” dopiero po zapewnieniu ochrony S5 (osobna decyzja/małe zadanie). Historia decyzji LYNX-GUARD-DECISION-LOG pozostaje na koniec projektu.

## Odbiór po implementacji — NIE w prechecku

Na dokumencie z kilkoma ostrzeżeniami: przed decyzjami i po rozstrzygnięciu tylko części brak kopiowania, eksportu i zapisu; po obsłużeniu wszystkich operacje są dostępne. ZAKRYJ daje prawidłowy token i Przywróć; ZOSTAW zachowuje tylko świadomie wskazane wystąpienie. Po ręcznym odsłonięciu danych nowy wynik podlega ocenie. Awaria S3 pozostaje bez obejścia. Pokazać przypadek jawnej nazwy firmy z R5 i brak alarmu na instytucji publicznej. Bez ponawiania badań diagnostycznych CC w prechecku.

## TASK_SCOPE i droga

Dotyczy istniejących właścicieli: backend/output_guard.py, backend/pipeline.py, frontend/src/screens/Pseudonimizuj.tsx oraz tylko wymaganych punktów istniejącego API, tokenizacji/mapy i testów celowanych. Poza zakresem: nowy NER, przebudowa FIRMA/OSOBA, naprawa OCR, nowa warstwa zabezpieczeń, installer, trwałe logi decyzji. Formalna zmiana frozen S4 wymaga osobnej zgody OWNERA, commitu i przeliczenia locka.

DO CODEXA — BRIEF_ONLY, bez kodowania, uruchamiania testów i benchmarków. Oceń: (1) jednoznaczność i małość zakresu R1–R5, w szczególności realność R5 na istniejących sygnałach; (2) czy ścieżka ostrzeżenie → indywidualna decyzja → blokada normalnych operacji da się wdrożyć w istniejącym Guardzie/UI bez dodatkowego nadzorcy; (3) czy pozostają sprzeczności z proponowaną zmianą S4 i zachowanym S3/S5. C1 z audytu r1 (kryptograficzne poświadczenie blobu) został wycofany w r2 i nie jest wymaganiem. Zwróć PASS PREIMPLEMENTATION albo krótką zamkniętą listę rzeczywistych braków. PASS nie upoważnia do implementacji ani zmiany zamrożonego S4 bez zgody OWNERA.
