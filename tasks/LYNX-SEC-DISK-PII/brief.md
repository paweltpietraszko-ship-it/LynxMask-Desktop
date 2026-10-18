# LYNX-SEC-DISK-PII — dane osobowe na dysku poza szyfrowaniem (F1–F3 przeglądu bezpieczeństwa)

STATUS: brief CC, obieg skrócony (CC → Codex precheck → CC implementacja → Codex audyt exact-SHA → merge na słowo Pawła). Architekt: informacja w BOARD.
Uzasadnienie obiegu: usterki mają zamrożoną wyrocznię (S5 oraz obietnicę resetu w kodzie i UI), wskazanego właściciela kodu i reproduktory Codexa. Nie powstaje nowy kontrakt produktu. Sprawy wymagające decyzji (R1 tytuł PDF, R2 zależności) są poza tym briefem.
POCHODZENIE: przegląd bezpieczeństwa Codexa `6cbd0ab` (gałąź `codex/security-review-20261018`, `tasks/LYNX-SECURITY-REVIEW/round_01/tests/tests_r1.txt`, `run_review_r1.py`, `evidence_r1/dynamic.json`); BOARD `LYNX-SEC-PROFILE-STORAGE`, `LYNX-SEC-LOG-PII`.
PRODUCT_TRUTH: `arch/spec.md` S5 („mapa zapisywana na dysk wyłącznie zaszyfrowana”, „logi tylko konsola, bez FileHandler — PII nie trafia na dysk w logach”), S1. Bez zmian S2/S3/S4.

## Klasa błędu
Dane osobowe trafiają na dysk w postaci jawnej obok zaszyfrowanej mapy albo zostają po obiecanym usunięciu. Wszystkie trzy przypadki należą do jednej klasy i mają jedną miarę: **po zwykłym użyciu i po resecie w plikach programu nie ma wartości z dokumentu ani z profilu, poza świadomymi eksportami użytkownika.**

## F1 — jawny `trie.pkl` z formami encji profilu (P1)
Stan: `AnonymizerMap._rebuild_trie` zapisuje automat Aho-Corasick (token + oryginalne formy) do `trie.pkl` (pickle, jawnie) obok szyfrowanej `mapa.enc`. Repro Codexa: znacznik dodany przez `/profile/add-entity` jest w `trie.pkl`, a w `mapa.enc` go nie ma.
Kontrakt:
1. Automat istnieje **wyłącznie w pamięci** i jest budowany z odszyfrowanej mapy (przy wczytaniu profilu i po każdej zmianie). Nie jest zapisywany na dysk w żadnej postaci. Cache `_trie_cache` już istnieje, plik jest zbędny.
2. **Migracja:** istniejący `trie.pkl` w katalogu profilu jest usuwany przy wczytaniu profilu (u obecnych użytkowników plik już istnieje).
3. Zachowanie maskowania profilem bez zmian (te same dopasowania), także po restarcie.
4. Mechanizm `trie_version`/`version` w mapie służył tylko zgodności z plikiem. Uprościć go albo zostawić jako nieszkodliwy; nie zmieniać formatu `mapa.enc` bez potrzeby. Decyzja CC przy implementacji, z uzasadnieniem w DELIVERY.

## F2 — reset nie usuwa wszystkiego, co obiecuje (P1)
Stan: `POST /profile/reset` (docstring: „Usuwa WSZYSTKIE dane użytkownika”; UI `SecurityScreen`: „Zostanie usunięty słownik biura, całe archiwum dokumentów i logi”) usuwa `mapa.enc`/`mapa.json`, mapy sesji i rekordy archiwum. Zostają:
- `trie.pkl` (F1);
- `guard_allowlist.json` (osobny katalog `PROFILE_DIR`, domyślnie `~/.pseudominizer/profile`);
- **(ustalenie CC, ta sama klasa)** stary obiekt `_app_state.anonymizer` w pamięci. Reset tworzy nową `anon_map`, ale `Anonymizer` z poprzednią mapą zostaje. Warstwa profilu (`trie_layer` czyta `anonymizer.anon_map`) dalej maskuje encjami sprzed resetu aż do restartu, a encje dodane po resecie (`_app_state.anon_map.add_entity`) do niej nie trafiają. Analiza źródła; do odtworzenia testem przy implementacji;
- „logi” z obietnicy UI: plik `pseudominizer.log` (F3) i dziennik audytu w `rejestr.db` (zdarzenia bez wartości; czy reset ma je czyścić — patrz pkt 3).
Kontrakt:
1. Po `reset` (200) w katalogu profilu, katalogu allowlisty i katalogu archiwum nie ma żadnego pliku zawierającego wartości z profilu, allowlisty ani dokumentów. `trie.pkl` (stary) i `guard_allowlist.json` są usunięte.
2. Po resecie maskowanie używa pustego profilu: `_app_state.anonymizer` jest odtworzony razem z `anon_map`. Encja sprzed resetu nie jest już maskowana z profilu, a encja dodana po resecie jest.
3. Tekst UI i zachowanie są zgodne: albo reset usuwa także dziennik audytu i plik logu (jeśli istnieje), albo tekst ekranu mówi dokładnie, co jest usuwane. Rekomendacja CC: reset usuwa zdarzenia audytu, a tekst wymienia „słownik biura, wyjątki „to nie PII”, archiwum dokumentów i dziennik zdarzeń”. Do potwierdzenia przez Codexa w prechecku; bez nowej decyzji produktowej, bo to realizacja istniejącej obietnicy.
4. Nie wymagamy nadpisywania nośnika (SSD) ani kasowania świadomych eksportów użytkownika w Dokumentach.

## F3 — wartości i nazwy plików w logach; log na dysku (P1)
Stan:
- `ocr_engine.extract_text_from_image` loguje nazwę pliku (`[OCR] błąd dla {filename}`);
- `export_pdf.generate_pdf` loguje tytuł z nazwy pliku;
- `guard_allowlist_add` loguje całą frazę (`[GUARD-ALLOWLIST] Dodano: {phrase!r}`);
- `backend/uruchom.vbs` przekierowuje stdout i stderr do `backend/pseudominizer.log` (dopisywanie, bez retencji).
Do tego **przegląd rodziny (ustalenie CC):** wiele wywołań `logger.debug` zawiera wartości encji (`ner_layer.py` [FILTER]/[NER], `spacy_ner.py`, martwy kod `pipeline.py` za `USE_NEW_PIPELINE`). Dziś nie trafiają do logu, bo poziom to INFO. Wystarczy jednak zmiana poziomu, żeby PII poszło na dysk. S5 nie robi wyjątku dla poziomu DEBUG.
Kontrakt:
1. Żadne wywołanie logowania w backendzie (każdy poziom) nie zawiera wartości pochodzących z dokumentu, profilu, allowlisty ani nazwy pliku użytkownika. Dozwolone: kody (PSE, token_id), typy, liczby, długości, nazwy klas wyjątków. Dotyczy wszystkich modułów `backend/` (bez testów i skryptów pomiarowych).
2. `uruchom.vbs` nie zapisuje wyjścia na dysk: konsola tylko w widocznym oknie. Istniejący `pseudominizer.log` jest usuwany przez launcher przy starcie (migracja).
3. Mechaniczny dowód: test uruchamia `/preview` (TXT i prawdziwy PNG z OCR), `/export-pdf`, `/profile/add-entity`, `/profile/guard-allowlist` i reset z syntetycznym znacznikiem w treści, nazwie pliku i wartościach, przy poziomie **DEBUG** na wszystkich loggerach. Znacznik nie pojawia się w żadnym rekordzie logu.

## Szew
- `anonymizer.py`: `_rebuild_trie`, `load_trie`, `_save`, `AnonymizerMap.__init__/_load` — usunięcie zapisu pickle i migracja. Plik legacy 1577 linii ma się zmniejszyć, nie urosnąć.
- `pseudominizer_api.py`: `profile_reset` (odtworzenie `anonymizer`, usunięcie allowlisty i starego `trie.pkl`, audyt); log allowlisty. Wzrost minimalny; większa logika do małego modułu, jeśli potrzebna.
- `ocr_engine.py`, `export_pdf.py`, `ner_layer.py`, `spacy_ner.py`, `pipeline.py` (tylko linie logów; martwego kodu nie przebudowywać).
- `db_store.py` (jeśli reset czyści audyt), `frontend/src/screens/SecurityScreen.tsx` (tekst resetu), `backend/uruchom.vbs`.
- Testy: nowy `backend/tests/test_disk_pii.py`.

TASK_SCOPE:
- backend/anonymizer.py
- backend/pseudominizer_api.py
- backend/ocr_engine.py
- backend/export_pdf.py
- backend/ner_layer.py
- backend/spacy_ner.py
- backend/pipeline.py
- backend/db_store.py
- backend/uruchom.vbs
- frontend/src/screens/SecurityScreen.tsx
- backend/tests/test_disk_pii.py
- backend/anonymizer_crypto.py
- backend/output_guard.py
- backend/verbal_amounts.py

OUT_OF_SCOPE:
- R1 — tytuł i nazwa eksportu PDF (decyzja Pawła, osobno);
- R2 — triage i aktualizacje zależności (osobny Task);
- szyfrowanie allowlisty (Codex: jawny format świadomych wyjątków nie jest defektem);
- `api_token.txt` (granica konta Windows, nieuznana za defekt);
- synchronizacja OneDrive (ryzyko instalacji — dokumentacja dla administratora, osobno);
- LYNX-APP-LAUNCHER;
- Tauri/Rust;
- jakość NER.

## Minimalna falsyfikacja
1. **RED na main:** reproduktory Codexa (`run_review_r1.py`) i nowy test pokazują F1 (znacznik w `trie.pkl`), F2 (znacznik po resecie w `trie.pkl` i allowliście; encja sprzed resetu dalej maskowana) oraz F3 (znacznik w logu z PNG, PDF i allowlisty).
2. **GREEN:**
   - po `add-entity` żaden plik w katalogu profilu poza `mapa.enc` (i keystore) nie zawiera znacznika;
   - po restarcie maskowanie profilem działa jak przed zmianą;
   - po resecie żaden plik w katalogach profilu, allowlisty i archiwum nie zawiera znacznika, encja sprzed resetu nie jest maskowana z profilu, a nowa encja jest;
   - test logów na poziomie DEBUG nie znajduje znacznika;
   - `uruchom.vbs` bez przekierowania do pliku i z usuwaniem starego logu.
3. **Migracja:** profil z istniejącym `trie.pkl` (syntetyczny) → po wczytaniu pliku nie ma, a maskowanie działa.
4. **Regresje:**
   - `tests/` na backendzie gałęzi;
   - `test_failclosed`, `test_startup_check` (próba „profil biura” nadal działa na izolowanym profilu), `test_express_one_engine`;
   - 178 dok. przez `/preview` z profilem Pawła: wynik identyczny z main (0 różnic);
   - pliki profilu Pawła: `trie.pkl` usunięty przy starcie (migracja — **zmiana na jego profilu, zgłoszona z góry**), `mapa.enc` bez zmian.

GATE: 1 nowy plik testu. Pliki legacy (`anonymizer.py` 1577, `pseudominizer_api.py` 1060) — bez wzrostu albo minimalny i uzasadniony. Szacunek CC: produkcja ok. +60/−50, testy ok. +150. TOTAL > 150 → WYMAGA_DECYZJI. **Paweł 2026-10-18 przed kodem: obieg skrócony — „Tak”, rozmiar — „Tak”.**

## ROZSZERZENIE CC (przy implementacji, ta sama klasa F3)
Przegląd wszystkich wywołań logowania w `backend/`, także wieloliniowych, znalazł wartości poza modułami z briefu:
- `anonymizer_crypto.py`: ścieżka keystore z nazwą konta;
- `output_guard.py`: fraza wykrytej injekcji z pytania użytkownika;
- `verbal_amounts.py`: kwota słowna i treść wyjątku;
- w `anonymizer.py` debug `[STDNUM-L4]` z wartością numeru.
Pliki dopisane do TASK_SCOPE. Bez zmiany kontraktu.
