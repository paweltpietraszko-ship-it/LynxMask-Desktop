# ODLOZONE.md — rzeczy zauważone, świadomie odłożone

Backlog spraw zauważonych przez CC lub Codexa, które NIE trafiają do BOARD.md ani pamięci CC, żeby nie odżywały same w każdej rozmowie. Czytany tylko wtedy, gdy Paweł chce wrócić do tematu. Jeden wpis = jedna sprawa.

Format wpisu:

```
## [data] Tytuł

Krótki opis (2-4 zdania). Dlaczego odłożone. Gdzie szukać kontekstu.
```

---

## 2026-10-16 Integracja z Elnath Rota (mask/unmask dla pytań koordynatora)

Rota potrzebuje bezstanowego `mask(text, known_people) -> {masked_text, mapping}` i `unmask(text, mapping)` działającego na Linuksie bez Tauri/UI. Odłożone decyzją Pawła: najpierw testy LynxMask na dokumentach. Pełny opis: GitHub `paweltpietraszko-ship-it/LynxMask` (gałąź master), plik `MASTER_LynxMask_Desktop.md` §9; strona Roty: GitHub `paweltpietraszko-ship-it/elnath-rota`, plik `BOARD.md`, wiersz ROTA-SERVICE-ONBOARDING.

## 2026-10-17 Douczanie modelu NER spaCy (fine-tuning)

Pomysł z `MASTER_LynxMask_Desktop.md` („Fine-tuning (nie przed stabilizacją)”); OWNER 2026-10-17: „to ważne”, pamięta
też pomysł poprzednika na „sprytną drogę na skróty” — źródła NIE znaleziono (przeszukane MASTER Desktop/Mobile, TODO, docs,
pamięć sesji Mobile/pseudominizer). Znane skróty, które pasują do opisu (do rozpoznania przez OWNERA):
(a) **EntityRuler** — wzorce/słownik wpięte w potok spaCy jako dodatkowy rozpoznawacz, bez treningu;
(b) **etykiety „za darmo” (weak supervision)** — zdania oznaczone automatycznie przez nasz silnik + słownik + ground truth
generatora, użyte jako dane treningowe (ryzyko: model uczy się generatora i naszych błędów);
(c) **etykietowanie przez LLM** na danych syntetycznych (por. `llm_classifier.py` w MASTER Desktop), potem trening lokalny.
Kolejność wg CC: pomiar M1/M2 (LYNX-DICT-LEAKTEST) → reguły kontekstowe (LYNX-CONTEXT-ANCHORS) → douczenie tylko jeśli M1
pokaże istotną grupę wycieków bez kotwicy. Dane treningowe: syntetyczne, z nazwiskami rozłącznymi ze słownikiem; ocena na
zbiorze rozłącznym; mierzyć „zapominanie” (FIRMA/miejsca) przed/po. Bez realnych dokumentów w zbiorze treningowym (RODO).
**Uzupełnienie 2026-10-17 (propozycja Pawła):** uczyć spaCy na przypadkach, które silnik przepuści na danych z LYNX-PUBLIC-DATA-TESTS
(wzory + dane syntetyczne, odpisy KRS; etykiety z konstrukcji/API lub od innego modelu). Ocena CC — wykonalne, warunki:
(1) najpierw rozbić wycieki: „spaCy nie wykrył” vs „wykrył, a nasz filtr odrzucił” — T01 i GEO-EXACT pokazały, że duża część to
filtr; trening pomaga tylko pierwszej grupie; (2) trening na całych dokumentach, nie tylko na samych pominięciach (inaczej model
zapomina resztę) + pomiar zapominania; (3) twardy podział dokumentów na treningowe i testowe — nigdy nie mierzyć na tym, na czym
uczono; (4) dane jawne rejestrowe dopuszczalne wg tej samej oceny co PUBLIC-DATA-TESTS, prywatne (`dataset_real/`) — nie;
(5) nowy model to plik ~500 MB z wersją i powtarzalnym treningiem — osobny Task po wynikach pomiaru na danych prawdziwych.

**Uzupełnienie 2026-10-18 (pytanie Pawła o większy model):** opcje lokalne wg rozmiaru — SpaCy (dziś), HerBERT base 125 MB (pobrany, kilka s/dok.), HerBERT large ~400 MB (2–3× wolniejszy), mały lokalny model językowy 1–3 GB (np. polski Bielik — licencja do sprawdzenia; minuty na dokument na CPU biurowym, ryzyko przekręcenia nazwy → każde wskazanie weryfikować dosłownie z tekstem). Propozycja CC: dwa poziomy — domyślnie SpaCy+HerBERT+słownik+reguły; opcjonalne „dokładne sprawdzenie” małym modelem tylko na fragmentach ostrzeżonych przez Guard lub na żądanie. Decyzja po pomiarze K1 (HerBERT) na tych samych 17 dokumentach, czasy mierzone z ograniczeniem do maszyny biurowej (np. 4 rdzenie, bez GPU; komputer Pawła i7-14650HX/32 GB jest 2–4× szybszy od typowego biurowego).

## 2026-10-16 Redakcja wizualna obrazu (blur twarzy, prostokąty na pikselach)

Istnieje tylko w Mobile. W `PROJEKT_KONTEKST.md` oznaczone jako „wymaga osobnej sesji". Nie ruszane do czasu ustabilizowania silnika tekstowego.

## 2026-10-16 AUD-13/14 PBKDF2 — zmiana iteracji/soli

Zmiana parametrów KDF unieważnia istniejące `mapy.enc`. Wymaga planu migracji przed dystrybucją; nie ruszać bez osobnego Tasku. Źródło: `PROJEKT_KONTEKST.md` → Bezpieczeństwo.

## 2026-10-17 Teksty nie po polsku (np. ukraiński cyrylicą) — LYNX-FOREIGN-LANG-FP

Z pomiaru DOCX-TABLES (próbka LAYOUT-SAMPLES, dwujęzyczny formularz PL/UA): polski NER na tekście ukraińskim daje ~15 fałszywych OSOBA,
a jeden token przypięty do dwóch form powoduje, że Przywróć dopisuje słowo. Nie wyciek — nadmaskowanie i psucie tekstu.
Uwaga Pawła: produkt jest dla tekstu polskiego; każdy kolejny taki finding ciągnąłby w stronę dwujęzycznego LynxMask — nie rozwijać.
Ocena CC: zgoda na odłożenie (nie dotyczy S1). Nazwiska ukraińskie zapisane łacinką w polskim tekście są obsługiwane jak każde inne.
Jeśli wróci: najtańszy wariant to nie przyjmować OSOBA z NER dla fragmentów pisanych cyrylicą (numery/e-maile i tak maskowane regexami) —
bez wykrywania języka i bez drugiego modelu.


## 2026-10-19 Poligon Arena — odłożony przez OWNERA

OWNER: „Odstawiamy Arenę na boczny tor, nie pokazuje znacznej poprawy jakości”. Decyzja o **priorytecie**: nie uruchamiać kolejnego F0a/LYNX-ARCH-CANDIDATES, R2b/R3/R4 ani przepisywania pipeline na kandydatów i arbitra. Dopracowywać istniejący silnik LynxMask (szczególnie OSOBA/FIRMA, mapę, Przywróć i błędy end-to-end); Arena może służyć jako przyrząd diagnostyczny, ale nie przyszły silnik bez nowego pomiaru. Nie twierdzić, że sekwencja warstw jest formalnie bezbłędna.

Dowody: experiment/lynx-architecture-arena (R1: nadmiar STOP, 16 i 19 prób), experiment/lynx-architecture-arena-v02 (R2: mniej STOP na 35 syntetykach, ale fałszywie szeroka FIRMA pochłania OSOBA+prozę — Codex H1), task/LYNX-ARENA-SIGNALS-PILOT (mechanika zatwierdzona exact 243cc508; r2 Codexa: na trzech NOWYCH syntetykach rzeczywiste kandydatury pozwoliły odróżnić R1 od R2; nie uogólniać „R1=R2”). W żadnym z tych badań nie wykazano dostatecznej przewagi całego nowego silnika nad działającym produktem ani realnego wycieku jednoznacznie spowodowanego sekwencją podmian.

Historia: git log -p BOARD.md dla wierszy LYNX-POLIGON, LYNX-ARENA-SIGNALS-PILOT i dawnych ARCH-ARENA; raporty Codexa w tasks/LYNX-ARCH-ARENA*/round_01/tests/ oraz tasks/LYNX-ARENA-SIGNALS-PILOT/round_01/tests/. Powrót tylko na nowe jawne polecenie OWNERA albo gdy zmierzone powtarzalne błędy produkcji dają **dowód**, że warstwy sekwencyjne są przyczyną, a nie błędne detektory czy mapy. Przed wznowieniem porównanie na tym samym gold, metryki FN/FP, STOP, Przywróć i koszty, nie same testy kontraktowe.

## 2026-10-21 — Aktualizacje składników bez wpływu na jakość maskowania (po LYNX-DEPS-UPDATE)
Odłożone na etap końcowy („jak uznamy, że program jest zbudowany” — Paweł; decyzję zostawił CC). Załatwione w LYNX-DEPS-UPDATE (main
`20d43e9`): wszystkie luki bezpieczeństwa (Pillow 13, cryptography 50, starlette/fastapi, multipart, urllib3, rustls/anyhow), Morfeusz
1.99.15 (SGJP 2026-06-01), własne `.venv` + `backend/requirements.txt`. Czeka (bez znanych luk, bez wpływu na maskowanie): onnxruntime
1.25→1.31 + numpy 2.4→2.5 (czytnik PP — z pomiarem odczytu), spaCy 3.8.13→3.8.16, phonenumbers 9.0.30→9.0.41 (z pomiarem telefonów),
PyMuPDF 1.27→1.28, uvicorn, pydantic, Python 3.14.4→3.14.8 (przebudowa `.venv`), Tauri 2.11→2.12 (npm + crate razem), Tesseract
5.5.0→5.5.3 (tylko zapas); React 18→19 / Vite 5→8 / TypeScript 5→7 — osobny temat. Słownik SGJP 2026-10 (ręczne pobranie) i pełny lock
zależności tranzytywnych → `LYNX-INSTALLER`. Metoda: nowe `.venv`, porównanie `/preview` przed/po (pomocnik), Codex.

## [2026-10-21] Narzędzie porównujące silnik Mobile i Desktop

Silnik Mobile uruchamia się na komputerze Pawła jako test JVM, bez telefonu: JDK z Android Studio (`C:\Program Files\Android\Android Studio\jbr`), `gradlew.bat testDebugUnitTest --offline`, punkt wejścia `PseudonymEngine.pseudonymize` (`PseudonymEngine.kt:116`), słowniki przez `LookupTables.initializeFromClasspath()`; w kopii repo trzeba podmienić przestarzały root `build.gradle.kts`. Dowód pomocnika CC 21.10: 758/761 testów JVM przechodzi, jedno zdanie zamaskowane poprawnie (kopia i logi lokalnie `%TEMP%\lynx_cc_review\mobile_engine\`). Narzędzie: te same pliki .txt przez Mobile i Desktop `/preview`, lista różnic (~1–2 h pracy pomocnika). Odłożone przez Pawła 21.10; wrócić przy ogólnym teście skuteczności maskowania (BOARD → TERAZ pkt 3) albo przy kolejnym pytaniu „jak robi to Mobile”.

## [2026-10-21] OSOBA krok 2 — „udowodnij, że jesteś OSOBA”

Pojedyncze słowo zakrywane tylko z dowodem (imię obok, Pan/Pani, PESEL, nazwisko ze słownika); bez dowodu — lista do decyzji człowieka. Odłożone przez Pawła 21.10: dziś pojedyncze słowo ze spaCy jest zakrywane (bezpieczny kierunek, czasem nadmaskowanie np. „Kawa”), a celem są dokumenty biurowe, gdzie nadmaskowanie jest akceptowane. Wycieki niezłapanych słów rozwiązuje `LYNX-GUARD-RESIDUE` („pokaż resztę”). Wrócić tylko, jeśli nadmaskowanie zacznie przeszkadzać w praktyce. Kontekst: BOARD 21.10, pomiar KPWr (`%TEMP%\lynx_cc_review\kpwr\` lokalnie u CC).
