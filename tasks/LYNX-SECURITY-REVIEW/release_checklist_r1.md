# Powtarzalna kontrola bezpieczeństwa wydania

Zapisz datę, commit źródeł, wersję Pythona i zależności oraz identyfikator/hash
instalatora, jeżeli testujesz wydanie binarne. Nie przedstawiaj testów źródeł
jako potwierdzenia innego zainstalowanego programu.

1. Utwórz nowy worktree i izolowane katalogi `ANONYMIZER_PROFILE_DIR`,
   `PROFILE_DIR`, `HARDWARE_PROFILE`, `ARCHIVE_DIR`, `PSE_REGISTRY`.
   TestClient bez lifespanu nie dotyka pliku tokenu; serwer uruchamiany osobno
   zapisuje go przy backendzie. Nie używaj profilu/dokumentów użytkownika.
2. Uruchom `round_01/tests/run_review_r1.py`, zachowaj nowy wynik JSON.
   Sprawdź jawne znaczniki w cache, logach, metadanych PDF i po resecie.
   Wyniki typu `*_has_marker: true` są obserwacją wymagającą oceny, nie PASS.
   OCR wymaga Tesseract; jego brak ma dać jawne NOT_CHECKED.
3. Potwierdź istniejące S3/start: `pytest tests/test_failclosed.py
   tests/test_startup_check.py -q`. Przy mikrofixie powtórz tylko odpowiednie
   reproduktory; pełna regresja wymaga kontraktu lub uzasadnienia.
4. Sprawdź ścieżki zapisu i uprawnienia plików na docelowej instalacji;
   ustal, czy system synchronizuje te katalogi. Nazwa katalogu „OneDrive”
   sama nie jest dowodem faktycznej synchronizacji.
5. Skan zależności, bez automatycznych napraw:
   - npm audit z lockfile, następnie `--omit=dev` do klasyfikacji;
   - lokalny inwentarz `scan_dependencies_r1.py --out <nowy plik>`;
   - po zgodzie na wysłanie nazw/wersji `--online` dodaje zapytanie OSV;
   - dla Rust rozdziel inne platformy: cargo tree --locked --offline
     --target x86_64-pc-windows-msvc --edges normal,build.
   Sprawdź osiągalność i rodzaj advisory; unmaintained != wykazany exploit.
6. W gotowej aplikacji sprawdź zwykły dokument, blokadę Guarda, eksport,
   zamknięcie/ponowienie i treść informacji o ograniczeniach. Obserwuj ruch
   całego procesu przy starcie/OCR/eksportach; obserwacja gniazd Pythona
   nie zastępuje monitorowania całego wydania natywnego.
7. Zachowaj raport z TRACE/OWNERSHIP/REPRO, testami i NOT_CHECKED. Każdy
   nowy wynik w nowym pliku, bez nadpisywania poprzedniego raportu.

Nie włączaj automatycznie: forensyki RAM/swap/SSD, pełnego pentestu,
testów statystycznej entropii ani ponownego benchmarku NER.
Dokumentacja dla klienta (ścieżki, usuwanie, ograniczenia, rola użytkownika)
i udostępnienie podsumowania z aplikacji są kolejnym krokiem, nie certyfikatem.
