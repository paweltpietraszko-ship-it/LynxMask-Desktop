# Brief — LYNX-T03-TOKEN-ALLOC
Status: propozycja kontraktu do prechecku Codexa; bez implementacji.
PRODUCT_TRUTH: `arch/spec.md` S1, S2, S3; `arch/FINDING_2026-10_AUDYT.md` BUG-TOKEN-COLLISION.
OWNER_DECISION: brak nowej; zachowujemy aktualne tokeny `KATEGORIA_NNN` bez zmiany regexu/taksonomii.
Cel: dwie różne encje nie mogą wskazywać tego samego tokenu, a odmiana jednej osoby nie może powodować nieuprawnionej zamiany na inną.
Zachowanie: po Zamaskuj mapa jest jednoznaczna, Przywróć odtwarza właściwy oryginał. Przy wykryciu konfliktu brak przepuszczenia błędnego tekstu (S3). UI poza poprawnością przywracania bez zmian.
Existing owner: `backend/pipeline_core.py::TokenAllocator`; `backend/layers/ner_adapter.py` jest szwem NER→alokator, `backend/ner_layer.py` dziś sam numeruje OSOBA/FIRMA. NER nie może niezależnie zarezerwować `OSOBA_001` zajętego przez trie/profil. Zachować dotychczasowe poprawne łączenie odmian i nie wprowadzać nowego alokatora.
TASK_SCOPE:
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/pipeline_core.py
- backend/tests/test_audyt_2026_10.py
OUT_OF_SCOPE: zmiana TOKEN_RE/S2, migracja profili, seed, nowy format mapy, osobny licznik w NER, usunięcie propagacji odmian, przebudowa całego pipeline, Express/CORS.
Test celowany: `test_dwie_osoby_dwa_tokeny` z `backend/tests/test_audyt_2026_10.py`: XPASS i zdjęcie znacznika xfail. Dodać najmniejszy przypadek dwóch różnych osób oraz dwóch form tej samej osoby przy obecnym tokenie w profilu. Trzy znane faile NER dotyczą filtra, nie alokatora: nie są kryterium PASS T03.
PASS: unikalne token_id dla różnych canonical values tej samej kategorii; powtarzana ta sama encja wykorzystuje token; reverse_map nie traci danych, a odtworzenie nie wstawia cudzej osoby. W razie konfliktu fail-closed.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_core.py --symbol TokenAllocator
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- REASON: zmiana granicy pomiędzy alokatorem centralnym i własną numeracją NER.
Gate: jeśli potrzebne >150 linii lub zmiana publicznej sygnatury NER wykraczająca poza wąski szew, WYMAGA_DECYZJI; nie tworzyć nowego subsystemu.
