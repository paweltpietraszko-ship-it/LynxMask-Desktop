# LYNX-NEWLINE-CROSSING — niezależne dane w kolejnych wierszach bez wzajemnego przecinania

STATUS: BRIEF_ONLY → Codex precheck → CC ocena i implementacja → Codex audyt exact SHA → merge wyłącznie na polecenie OWNERA.
PRODUCT_TRUTH: arch/spec.md S1 (brak jawnych danych), S2 (wierność tekstu, bez globalnego sklejania), S3/S4 (fail-closed/Guard), S5. Źródło: BOARD.md LYNX-DOCX-TABLES i LYNX-NEWLINE-CROSSING, tasks/LYNX-DOCX-TABLES/round_01/implementation/DELIVERY.md (WIP 83c94b4c5d28c91c5b0fa20d78e15886b1ba5a9e). 56 syntetycznych par kolejnych wierszy, 4 niepoprawne wyniki. CC sprawdził tę klasę także na kodzie bazowym przed WIP, więc nie jest nową regresją ekstraktora.
OWNER_INPUT 2026-10-17: prośba o rozstrzygnięcie „najpierw NEWLINE-CROSSING czy rozszerzenie DOCX-TABLES”. REKOMENDACJA ARCHITEKTA: osobny Task FIRST; DOCX-TABLES pozostaje STOP i zachowuje WIP, bez poszerzania jego TASK_SCOPE i bez autoryzacji merge.

## Defekt i granica
- Dwa pełne e-maile w kolejnych liniach, np. "a@example.pl\nb@example.pl": ocr_normalizer._EMAIL_SPACE_BEFORE_AT_DOT dopuszcza \s+; potrafi połączyć domenę pierwszego z lokalną częścią drugiego. Efekt z raportu CC: częściowo jawny e-mail, niewłaściwa reverse_map.
- Pełny NIP/PESEL w wierszu poprzedzającym telefon, np. "526-000-12-46\n512 987 654" lub "44051401359\n512 987 654": wzorce numerów/telefonów przekraczają koniec wartości, pozostawiają jawny prefiks lub tworzą NUMER_NUMER_002; Przywróć/mapa przestają odzwierciedlać dwa niezależne identyfikatory.
- **Reguła:** jeśli po obu stronach granicy wiersza istnieją dwie kompletne niezależne encje, żadna warstwa nie może ich połączyć, przeciąć pierwszej ani tworzyć tokenu w tokenie. Obejmuje tekst zwykły (TXT), a nie tylko DOCX. Cały rozpoznany identyfikator pod jednym tokenem albo brak dopasowania i dalsza ochrona (T07).
- **Istniejący OCR wewnątrz JEDNEJ encji zachować.** Przykładowo "jan@\nexample.pl" i "jan\n@example.pl" nadal powinny być wykrywane jako jeden e-mail; nie zastępować mechanicznie każdego \s przez [ \t] w całym silniku. Znane, osobne różnice w Przywróć po wcześniejszej kanonizacji OCR (F3) nie są naprawiane tu. Wzorce poprawnego IBAN/telefonu rozbitego przez OCR nie mogą stracić istniejącej ochrony bez osobnego findingu.

## Minimalny szew
Najpierw dokładnie wskazać pierwszy etap, który zmienia tekst lub przechwytuje podciąg na odtwarzanych wejściach. Kandydaci już potwierdzeni w kodzie main: backend/layers/ocr_normalizer.py (wywołania _EMAIL_SPACE_BEFORE_AT_DOT, pokrewne _EMAIL_SPACE_BEFORE_AT_DIGITS i _PHONE_AFTER_KW_RE) oraz backend/layers/contact.py (_PHONE_322_RE, _PHONE_CONTEXT_RE). Naprawić punktowo rozpoznanie granicy kompletnego identyfikatora, nie globalne działanie regexów, nie zmieniać kolejności pipeline ani zachowania fallbacku. Nienaruszony raw newline pomiędzy dwiema encjami musi pozostać w wyniku i po jednoprzejściowym Przywróć. NIE przesuwać tokenizacji wcześniej w pipeline.

TASK_SCOPE:
- backend/layers/ocr_normalizer.py
- backend/layers/contact.py
- backend/tests/test_layers.py
- backend/layers/identity.py

OUT_OF_SCOPE: backend/document_processor.py, backend/tests/test_engine_quality_layout.py, audyt/engine_quality.py, pozostałe warstwy (financial/validation; identity — tylko ROZSZERZENIE CC E1 niżej), anonymizer_init.py, pipeline_new.py, Output Guard i TOKEN_RE, UI, eksport DOCX, nowe parsery, KRS/KW, realne dokumenty i dane osobowe. Jeśli precheck dowiedzie, że źródło jednego z reproduktorów jest w innym ownerze, **STOP i punktowy finding/nowy TASK_SCOPE przed implementacją**; nie obchodzić błędu zmianą testu ani szerokim przeorganizowaniem warstw.

## Minimalny test falsyfikujący (w istniejącym test_layers.py, uruchamianym jawnie)
1. Dwa niezależne syntetyczne e-maile z \n między nimi, oba tryby run_pipeline_new (z kontrolowanym NER) i run_pipeline_express: dwa pełne poprawne spany w reverse_map (nie połączone), żadna jawna lokalna część/domena, nienaruszona granica wiersza, brak osieroconych lub zagnieżdżonych tokenów; Przywróć = oryginał.
2. Kompletny NIP lub PESEL w wierszu nad telefonem: oba pełne NUMER_NNN, mapa odpowiada dwóm rzeczywistym wartościom bez prefiksów/ogonów i bez NUMER_NUMER; brak jawnych cyfrowych resztek; Przywróć dokładne. Wariant z i bez etykiety ("NIP:", "tel:") oraz zamiana kolejności wierszy. Nie liczyć force_block ani guard_blocked jako prawidłowego maskowania.
3. Regresje pozytywne OCR: jeden e-mail rozcięty bezpośrednio przy @ przez newline (oba kierunki) nadal jeden EMAIL_NNN; istniejące przypadki OCR telefon/IBAN/PESEL zachowują maskowanie, a różnice już znane jako F3 nie są przedstawiane jako nowy PASS wierności. Dwa normalne e-maile oddzielone spacją/zdaniem i istniejące przypadki EMAIL-LOCALPART-OCR oraz T07 nie gorsze.
4. Przegląd 56 par z DELIVERY (ten sam wejściowy digest lub zestaw identycznych syntetycznych wejść) przed/po na main oraz exact SHA dostawy. Co najmniej 4 zgłoszone kolizje przechodzą z FAIL do PASS, bez nowych wycieków; dodać małe kontrpróby na granicy tokenu. Pełna standardowa suita i testy celowane osobno; ewentualnie pomiar --layout na tej samej lokalnej próbce, jeśli dostępna, lecz **nie** uruchamiać/nie modyfikować WIP DOCX-TABLES w tym Tasku.
5. Wynik = tekst, rzeczywiście występujące tokeny, pełne wartości w reverse_map i wynik symulacji Przywróć; nie opierać PASS tylko na braku dosłownego podciągu. Raporty nie zawierają realnych danych ani dokumentów. S3/S4/S5 bez zmian.

PASS: brak nieuprawnionych przecięć między dwoma kompletnymi identyfikatorami w kolejnych wierszach, zachowane wcześniej obsługiwane OCR-newline *wewnątrz* jednej encji, brak regresji Guarda/tokenów, dokładny audyt exact SHA. To nie jest certyfikat wszystkich regexów ani jeszcze PASS DOCX-TABLES.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/ocr_normalizer.py --symbol normalize_ocr
- TARGETS: backend/layers/contact.py --symbol apply_contact_layer
- REASON: zidentyfikować właściciela błędnego \s+ / wzorca telefonu na dwóch minimalnych reproduktorach; uniknąć szerokiej przebudowy.
GATE: zero nowych plików, stare pliki powyżej limitu ≤600 nie mogą rosnąć; >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI. Codex: BRIEF_ONLY precheck wykonalności i zakresu, bez implementacji.

Po merge (osobna decyzja OWNERA): dopiero CC aktualizuje WIP DOCX-TABLES na nowym main, ponawia czerwone testy integracyjne tabel i oddaje je Codexowi do audytu osobnego exact SHA.
## ROZSZERZENIE CC (2026-10-17, przed kodem) — wynik ustalenia pierwszego etapu
Trace warstwa po warstwie (NER wyłączony):
- „a@example.pl\nb@example.pl” → PIERWSZY: `ocr_normalizer` (`_EMAIL_SPACE_BEFORE_AT_DOT`, `\s+` z `\n`, grupa 1 bez lewej granicy łapie domenę poprzedniego adresu) → „a@example.plb@example.pl”. Pokrewna `_EMAIL_SPACE_BEFORE_AT_DIGITS` ma ten sam `\s+`.
- „526-000-12-46\n512 987 654” → PIERWSZY: **`identity`** — wzorzec NIP 3-2-2-3 z `anonymizer_init.STRUCTURAL_PATTERNS` (`[-\s]?`, lewa granica tylko `(?<!\d)`) dopasowuje „000-12-46\n512” (start po „526-”, przez `\n`); potem `contact` (wzorzec telefonu z tych samych STRUCTURAL) łapie „001 987 654” startując w cyfrach tokenu NUMER_001 → „NUMER_NUMER_002”.
- „44051401359\n512 987 654” → PIERWSZY: `contact` — telefon „001\n512 987” startuje w cyfrach tokenu i przechodzi przez `\n`.
- Nowy, ta sama klasa: „PESEL 44051401359\nTel. …” → `ocr_normalizer._PESEL_SPLIT_RE` (wnętrze numeru `[...\s]` z `\n`) zjada „T” z następnej linii → „7el.”.
**E1** `backend/layers/identity.py` — dopisany do TASK_SCOPE (pierwszy błędny etap dla reproduktora NIP; brief dopuszcza nowy TASK_SCOPE przed implementacją). Bez zmiany `anonymizer_init` (wzorce bez zmian).
Poprawka (punktowa, bez globalnej zamiany `\s`): (1) w `identity` i `contact` wzorce **liczbowe** (NUMER; nie e-mail) dopasowywane w obrębie jednej linii i odrzucane, gdy start leży w cyfrach tokenu (`…_\d*`) albo bezpośrednio po „cyfra-” (fragment dłuższego numeru) — jedna funkcja pomocnicza w `contact.py`, użyta w obu warstwach; (2) `ocr_normalizer`: `_EMAIL_SPACE_BEFORE_AT_DOT/_DIGITS` — odstęp bez `\n` i lewa granica grupy 1; `_PESEL_SPLIT_RE` — wnętrze numeru bez `\n` (separator po etykiecie może nadal przechodzić przez `\n`: „PESEL:\n4405…” to jedna encja); `_PHONE_AFTER_KW_RE` — wnętrze numeru bez `\n`. OCR-newline przy `@` w e-mailu (`contact._EMAIL_OCR_RE`) bez zmian.
