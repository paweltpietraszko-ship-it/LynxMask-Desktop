# Brief — LYNX-T01-NER-PREFIX
Status: propozycja kontraktu do prechecku Codexa; bez implementacji.
PRODUCT_TRUTH: `arch/spec.md` S1, S3, S4; `arch/FINDING_2026-10_AUDYT.md` BUG-NER-PREFIX-FILTER; `arch/FINDING_2026-10_MOBILE_PORT.md` §1 pkt 1 i P01.
OWNER_DECISION: brak nowej decyzji produktowej; naprawa odtworzonego wycieku przy zachowaniu S2–S4.
Cel: encja OSOBA wykryta przez spaCy nie ginie tylko dlatego, że pierwsze 8 liter jest prefiksem nazwy ulicy/miejscowości.
Zachowanie: przy tekście z nazwą osoby w treści dokumentu silnik maskuje encję OSOBA; nazwy ulic, słowa pospolite i sądy nadal nie stają się automatycznie OSOBA. Wynik w UI bez zmian poza usunięciem wycieku; przy wyjątku NER wynik zablokowany według S3.
Existing owner: `backend/ner_layer.py::_filter_institutions` oraz kuratorowana blocklista w `backend/ner_blocklist.py`. Metoda z Mobile: najpierw potwierdzenie imienia/nazwiska przez istniejące słowniki / kwalifikator Morfeusza, dopiero później odrzucenie jednowyrazowego przymiotnika. Nie wprowadzać nowego NER ani drugiego pipeline.
TASK_SCOPE:
- backend/ner_layer.py
- backend/ner_blocklist.py
- backend/tests/test_audyt_2026_10.py
- backend/tests/test_pipeline.py
OUT_OF_SCOPE: TOKEN_RE, taksonomia, Express, TokenAllocator, pełny seed, AnchorEngine, przebudowa słowników profilu, usunięcie blokowania PII.
Test celowany: `test_filtr_ner_nie_odrzuca_osob` i reproduktor BUG-NER-ADJ-FILTER z `backend/tests/test_audyt_2026_10.py` po naprawie XPASS, następnie usunąć odpowiednie znaczniki xfail. Trzy znane faile: oczekiwane zielone `test_prefix_nie_uderza_w_podobne_nazwy` i `test_prywatna_firma_nie_odfiltrowana` wyłącznie gdy wynikają z tego samego filtru; trzeci pozostaje poza zakresem.
PASS: wskazane osoby wykryte przez spaCy nie są odrzucane prefiksem ani bezwarunkowo przymiotnikiem; brak nowych FP w syntetycznych próbkach słów pospolitych, adresów i instytucji; brak pogorszenia Guard/fail-closed. Benchmark porównawczy OSOBA + FP z raportu, bez wymogu identycznych liczb pomiaru prototypu.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/ner_layer.py --symbol _filter_institutions
- REASON: zmiana reguły filtrującej właściciela detekcji OSOBA.
Gate: max 2 nowe pliki, pliki >600 linii / funkcje >50 linii nie pogarszać, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI.
