# Brief — LYNX-T03-TOKEN-ALLOC
Status: propozycja kontraktu do prechecku Codexa; bez implementacji.
PRODUCT_TRUTH: `arch/spec.md` S1, S2, S3; `arch/FINDING_2026-10_AUDYT.md` BUG-TOKEN-COLLISION.
OWNER_DECISION: brak nowej; zachowujemy aktualne tokeny `KATEGORIA_NNN` bez zmiany regexu/taksonomii.
Cel: dwie różne encje nie mogą wskazywać tego samego tokenu, a odmiana jednej osoby nie może powodować nieuprawnionej zamiany na inną.
Zachowanie: po Zamaskuj mapa jest jednoznaczna, Przywróć odtwarza właściwy oryginał. Przy wykryciu konfliktu brak przepuszczenia błędnego tekstu (S3). UI poza poprawnością przywracania bez zmian.
Existing owner: `backend/pipeline_core.py::TokenAllocator`; `backend/layers/ner_adapter.py` jest szwem NER→alokator, `backend/ner_layer.py` dziś sam numeruje OSOBA/FIRMA; `backend/layers/trie_layer.py::apply_trie_layer` ma istniejący dostęp do `anonymizer.anon_map` i jest minimalnym szwem do zarezerwowania liczników dla **wszystkich** identyfikatorów profilu przed NER, niezależnie od dopasowań trie. Jeśli profil nie istnieje, zachowanie bez zmian. Bez nowego ownera czy drugiego alokatora. NER nie może przydzielić `OSOBA_001` innej osobie, jeżeli ten identyfikator istnieje **gdziekolwiek w aktywnym profilu użytkownika**, nawet gdy przypisana mu osoba nie występuje w bieżącym dokumencie. Tokeny profilu zachowują stabilną tożsamość między dokumentami. Rezerwacja dotyczy przestrzeni numerów każdego typu w całym profilu, nie tylko tokenów aktualnie znalezionych przez trie. Nie dodawać do `reverse_map` dokumentu encji z profilu, które w tym dokumencie nie wystąpiły; samo podniesienie liczników alokatora nie oznacza mapowania oryginału ani zajęcia spanu. Zachować dotychczasowe poprawne łączenie odmian i nie wprowadzać nowego alokatora.
TASK_SCOPE:
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/pipeline_core.py
- backend/layers/trie_layer.py
- backend/tests/test_audyt_2026_10.py
OUT_OF_SCOPE: zmiana TOKEN_RE/S2, migracja profili, seed, nowy format mapy, osobny licznik w NER, usunięcie propagacji odmian, przebudowa całego pipeline, Express/CORS.
Test celowany: `test_dwie_osoby_dwa_tokeny` z `backend/tests/test_audyt_2026_10.py`: XPASS i zdjęcie znacznika xfail. Dodać najmniejszy przypadek dwóch różnych osób oraz dwóch form tej samej osoby przy obecnym tokenie w profilu. Osobny reproduktor obowiązkowy: profil ma `OSOBA_001 = Jan K.`, a nowy dokument NIE zawiera żadnej formy Jana; NER wykrywa inną osobę i musi przydzielić jej inny token (np. `OSOBA_002`), przy czym `OSOBA_001` nie pojawia się w reverse_map tego dokumentu. Drugi dokument zawierający Jana ma nadal otrzymać `OSOBA_001` dla niego. Trzy znane faile NER dotyczą filtra, nie alokatora: nie są kryterium PASS T03.
PASS: unikalne token_id dla różnych canonical values tej samej kategorii, także w kolejnych dokumentach tego samego profilu; rezerwacja wszystkich numerów profilu bez ujawniania niewystępujących encji w mapie dokumentu; powtarzana ta sama encja wykorzystuje token; reverse_map nie traci danych, a odtworzenie nie wstawia cudzej osoby. W razie konfliktu fail-closed.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_core.py --symbol TokenAllocator
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- TARGETS: backend/layers/trie_layer.py --symbol apply_trie_layer
- REASON: zmiana granicy pomiędzy alokatorem centralnym i własną numeracją NER.
KOREKTA CC r1: rozstrzygnięto jedno B1 z `round_01/cc_review_r1.md` na korzyść całego profilu; jedyny nowy plik w `TASK_SCOPE` to istniejący `layers/trie_layer.py`; ponowny precheck wyłącznie tej granicy i testu.
Gate: jeśli potrzebne >150 linii lub zmiana publicznej sygnatury NER wykraczająca poza wąski szew, WYMAGA_DECYZJI; nie tworzyć nowego subsystemu.
