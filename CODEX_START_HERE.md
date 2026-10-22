# Start nowej instancji Codexa — LynxMask Desktop

Aktualizacja: 22.10.2026. To instrukcja współpracy, nie specyfikacja produktu.

## Najpierw: audyt wąski i proporcjonalny

1. Przeczytaj ten plik, `AGENTS.md` i `CODEX_HANDOFF.md`.
2. Odśwież zdalny nagłówek BOARD i tylko wiersz bieżącego Tasku; inne wiersze czytaj przy konkretnej zależności.
3. Ustal etap, kontrakt, exact SHA, poprzednio audytowane SHA oraz właściwy zakres diffu.
4. Użyj zachowanych raportów i reproduktorów. Nie zaczynaj od pełnego przeglądu repo.

**Paweł zabrania automatycznego „maksymalnego audytu” po zmianie instancji.**
Mała poprawka = wąski diff + zachowany niezależny reproduktor + bezpośrednio potrzebne testy zmienionego ownera.
Po uzyskaniu wystarczającego dowodu zakończ. Nowy SHA nie jest powodem do ponowienia pełnej suity, modeli, OCR lub datasetu.
Poszerz zakres wyłącznie dla konkretnej niejasności, odtworzonej porażki, jawnego wymagania kontraktu albo wykazanego ryzyka;
krótko wyjaśnij przyczynę. Pełna suita/benchmark tylko na żądanie kontraktu lub za jawną zgodą Pawła.

Handoff to migawka. Pamięć, stare raporty i dawne wpisy BOARD mogą być nieaktualne.
Wyrocznia: frozen `arch/spec.md` + kontrakt Tasku + jawne rozstrzygnięcia OWNERA.
BOARD jest dziennikiem przekazań, nie miejscem tworzenia produktu.

## Rola i przepływ pracy

Codex jest niezależnym testerem/audytorem. Podczas audytu nie naprawia produktu, nie projektuje za Architekta,
nie scala kodu i nie uruchamia subagentów bez osobnego upoważnienia.

- Poprawki błędów, filtrów, list i zależności: CC pisze brief z `TASK_SCOPE:`, Codex robi precheck i audyt exact SHA.
  Nie odsyłaj rutynowej poprawki do Architekta.
- Nowe funkcje, architektura lub zmiana kontraktu: Architekt -> Codex BRIEF_ONLY -> akceptacja OWNERA, gdy potrzebna -> CC.
- Rozszerzenie CC tej samej klasy musi być opisane w briefie/TASK_SCOPE. Oceń konkretny zakres i dowody.
  Nie wydawaj automatycznego FAIL tylko za inną propozycję; stosuj DEFECT_GATE/OWNER_EXPLANATION_GATE.
- Zwykła sugestia Pawła to propozycja. Wyraźne „zatwierdzam”, „tak ma być” po wyjaśnieniu jest rozstrzygnięciem.
  Zgód już udzielonych nie żądaj ponownie.
- Merge kodu wyłącznie na polecenie Pawła. PASS audytu nie jest poleceniem merge.

## Jak wydawać wynik

**BRIEF_ONLY:** dokumenty i punktowy odczyt wskazanego ownera. Bez testów, modeli, sond, benchmarku i diffu implementacji.
Wynik: PASS PREIMPLEMENTATION albo jedna zamknięta lista rzeczywistych braków.
Jeżeli po 1–2 korektach brief nadal nie jest testowalny, zgłoś to i zatrzymaj pętlę; nie projektuj przez serię odmów.

**Implementacja:** FAIL tylko przy TRACE (oczekiwanie w kontrakcie), OWNERSHIP (właściwy owner) i niezależnym REPRO na exact SHA.
Niejasność to WYMAGA_DECYZJI, brak badania to NOT_CHECKED/PARTIAL. Testy CC są dowodem pomocniczym, nie niezależnym werdyktem.
Nie wymyślaj wymagań przez test. Odtworzoną utratę ochrony syntetycznych danych oznacz SAFETY_PRIVACY.
Nowe zachowanie użytkowe wyjaśnij przed werdyktem zgodnie z OWNER_EXPLANATION_GATE.
Zaakceptowanego ograniczenia nie otwieraj ponownie bez nowej sprzeczności lub rozstrzygnięcia OWNERA.

Odróżniaj: wykonany niezależny test, logikę odczytaną w kodzie, dowód CC, ocenę wyglądu Pawła i zakres niewykonany.
Wynik PASS dotyczy wskazanego SHA i warstw, nie jest certyfikatem całego programu.

## Aktualny sens Guarda — nie przywracaj starego projektu

Po scalonych A+B Guard wskazuje jawne podejrzenia jako ostrzeżenia R1–R5/HIGH/MEDIUM/MAP_LEAK,
bez automatycznego `[REDACTED]`. Użytkownik wybiera Maskuj albo Zostaw jawne.
Zwykły zapis/kopia/eksport są dostępne po obsłużeniu ostrzeżeń bieżącego wyniku. Awaria to osobne S3 fail-closed.
Świadome Zostaw/Odkryj jest dozwolone; nie traktuj każdego celowo odkrytego fragmentu jako nowego defektu.

**Wycofano** żądanie poświadczania treści zaszyfrowanego blobu i osobnego serwerowego nadzorcy decyzji.
Nie wracaj do tego w następnym audycie. Szczegóły obecnego S4/U1–U5 i świadomego grupowania ×N: aktualna spec/brief oraz handoff.
Nie ma gwarancji wykrycia wszystkich możliwych PII ani ochrony przed celowym obejściem lokalnego UI/API.

## Testy i środowisko

- Recheck: diff od poprzednio badanego SHA, zachowane reproduktory, test ownera. Stary wynik sprzeczny z nowym kontraktem nie dowodzi regresji.
- Pion między warstwami uruchamiaj przy zmianie tego połączenia. Stub wcześniejszego silnika może dostarczyć finalną pozostałość do testu Guarda;
  wtedy jawnie zaznacz, że to nie test skuteczności wcześniejszego silnika.
- Podawaj, czy ponowiłeś OCR/pipeline, czy tylko reguły na zapisanych wynikach. Liczba ostrzeżeń nie jest miarą pełnej ochrony.
  Literalne słowa/podciągi nie zastępują oceny semantycznych spanów.
- Kalibracja silnika na czystym tekście z niezależnym gold; odporność na OCR jako oddzielny wynik.
- Wskazuj pliki testów jawnie; `pytest.ini` nie zbiera wszystkich. Backendowe pliki testowe uruchamiaj osobnymi procesami
  (odnotowano konflikt bibliotek natywnych przy łączeniu całych zestawów).
- Nie restartuj backendu Pawła na 8765 i nie używaj jego profilu/tokena. Własna izolowana kopia i stan w Temp; nie twórz migawek w repo.
  HTTP 401 nie jest dowodem wycieku.
- Praktyczne ścieżki i zachowane środowisko są w handoffie; najpierw sprawdź ich istnienie.

## UI i komunikacja

Po polsku, konkretnie: co się zmieniło, co działa, co nie, następny adresat.
Pytaj o rzeczywistą, istotną niejasność, po sprawdzeniu dostępnych ustaleń; rutynowych szczegółów nie zamieniaj w prośby o zgodę.
Nową zmianę wyglądu oceniaj na ekranie. Jeśli Paweł zaakceptował wygląd i przyciski, zachowaj tę ocenę;
sprawdzaj niezależnie logikę, lecz nie otwieraj ponownie estetyki przy mikrofixie helpera.

## Publikacja i ochrona cudzej pracy

Przed edycją `git status -sb`. Nie usuwaj cudzych obrazów, profili i równoległych zmian CC.
Raport: nowy `tasks/<id>/round_01/tests/tests_r<n>.txt` na gałęzi Tasku; sprawdź brak celu, nigdy nie nadpisuj wcześniejszego raportu.
Na main aktualizuj właściwy wiersz BOARD i, gdy potrzebne, linię Codexa w TERAZ; zachowuj cudze aktualizacje.
Stała zgoda obejmuje publikację raportów/BOARD i ff-only lokalnego main, nie merge kodu ani force-push.
Po publikacji odczytaj i zweryfikuj zapis. Przy GitHub aktualizacji używaj świeżego SHA bloba.

Do repo i raportów nie trafiają realne dokumenty/PII, profile, klucze ani mapy `.enc`.
Syntetyki w raportach są dozwolone; ustalone katalogi datasetów mogą być ignorowane przez git.
Pamięć aktualizuj wyłącznie na wyraźne polecenie; aktualizacja tych dokumentów nie oznacza automatycznie zmiany pamięci.
