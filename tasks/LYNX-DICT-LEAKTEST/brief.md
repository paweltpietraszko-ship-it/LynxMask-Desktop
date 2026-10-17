# Brief — LYNX-DICT-LEAKTEST / etap 1: M1–M3, pomiar BEZ zmian silnika

STATUS: BRIEF_ONLY — wyłącznie diagnostyka; precheck Codexa, niezależna ocena CC, dopiero potem implementacja.
PRODUCT_TRUTH: `arch/spec.md` S1 (maska/Przywróć), S2 (format tokenów), S3 (fail-closed), S5 (bez zapisu PII). Źródła: `BOARD.md` wiersz `LYNX-DICT-LEAKTEST`; `arch/PROPOSAL_2026-10-16_SLOWNIK_SZCZELNOSCI.md` §4 i §6; `arch/PLAN_2026-10.md` pkt 9. `LYNX-T01`, `LYNX-T03` i `LYNX-NER-GEO-EXACT` już scalone.
OWNER_PROPOSAL: automatycznie testować silnik i z pominiętych form budować osobny słownik „zawsze maskuj”. OWNER wybrał kierunek pomiar + kuratorowana lista kontekstowa, ale NIE zamroził automatycznego maskowania każdej znalezionej formy. `T04-SEED` pozostaje nierozstrzygnięty. Dlatego **ten Task obejmuje tylko bazowy pomiar M1–M3; słownik programowy i wpinanie go do silnika będą osobnym zadaniem po T04 i ocenie FP**.
CEL: dać OWNEROWI powtarzalny, lokalny raport pokazujący *które klasy przypadków* silnik przepuszcza, co maskuje niepotrzebnie i czy Zamaskuj→Przywróć zmienia tekst. Nie obiecywać szczelności na podstawie wyniku benchmarku OCR.

## Istniejący owner i minimalne użycie
- Nowy **jeden** skrypt diagnostyczny `audyt/engine_quality.py` jako runner; nie modyfikować `pipeline.py`, `pipeline_new.py`, NER, Guard, profilu ani UI.
- Reuse produkcyjnego `pipeline.pseudonymize_document` na `pipeline.AppState` z rzeczywistym NER (jak `audyt/repro_pipeline.py`), z osobnym `TemporaryDirectory` dla profilu, hasła i ewentualnych plików. NIE używać HTTP ani produkcyjnego profilu; NIE stosować monkeypatchy zmieniających reguły silnika (`bench_offline.py` ma warianty patchowane).
- Reuse `audyt/unmask_sim.py::unmask` do **symulacji** algorytmu przywracania z `frontend/src/screens/Depseudonimizuj.tsx::restoreText`. Wynik M3 nazwać „symulowany round-trip”, nie pełnym UI E2E; osobno oznaczyć rozbieżność, jeśli symulator i aktualne `replaceAll` różnią się.
- Referencje do istniejących próbek: `tasks/LYNX-T01-NER-PREFIX/round_01/implementation/holdout_measure.py` (sposób separacji nazwisk), `audyt/rota_leak_test.py` (odmiany) i `audyt/roundtrip.py` (diff). Nie edytować historycznych raportów, nie kopiować całych narzędzi.
- Jedyny plik testowy: obecny `backend/tests/test_audyt_2026_10.py`, z małymi testami deterministyki, etykietowania wyników, nieodczytywania profilu i round-tripu. Kod produkcyjny bez zmian.

## Kontrakt wykonania — etap bazowy
Jedno polecenie z korzenia repo, np. `python audyt/engine_quality.py --seed 2026 --out <ścieżka-poza-repo>/quality.json`. Działa offline na Windows i Linux, po zainstalowaniu istniejących zależności; jeżeli zabraknie spaCy/Morfeusza, raportuj `NOT_RUN` lub zakończ błędem — nie zastępuj rzeczywistego NER atrapą i nie nazywaj pustego wyniku sukcesem. Raport ma `git_SHA`, datę, seed, identyfikator/skrót wejścia, wersję/tryb pipeline, liczności, liczbę prób niespełniających założeń i status.
- **M1 — wycieki na czystym tekście, bez OCR.** Mały, jawnie opisany zestaw syntetycznych szablonów pism: urzędowe, umowa, faktura, korespondencja. Kategorie: OSOBA (pełne imię/nazwisko i odmiana, tytuł, CAPS, inicjał), FIRMA, ADRES, NIP/PESEL/IBAN, telefon, e-mail — na tyle, na ile istniejące fixture mają oczekiwane trafienia. Każdy przypadek ma jawny oczekiwany span i kategorię, nie tylko porównanie podsłowa z całym wyjściem. Oddziel wyniki: maskowanie poprawne, forma jawna w **udostępnialnym** wyniku, `guard_blocked/force_block`, błąd, niewłaściwa kategoria i brak mapowania. Zablokowanego wyniku nie wolno liczyć jako „zamaskowany poprawnie”.
- **M1 HOLDOUT.** Jednoznacznie oddziel `in_dictionary` i `holdout`. Opcjonalna wskazana ścieżka do syntetycznego zbioru rozłącznych nazwisk (np. Mobile `surnames_extended.json`), a filtr usuwa formy (także odmiany) występujące już w `surnames_top1000.json` / `names_inflected.json` i w danych testowo-treningowych użytych do generacji. Jeżeli holdout nie jest dostępny lub rozłączność nie została potwierdzona, pole `holdout` to `NOT_MEASURED` — bez fikcyjnego zera czy „100%”.
- **M2 — czysty tekst bez encji przeznaczonych do maskowania.** Kontrolowane pułapki: „w piątek”, „zapłata”, „pracuje w Radomiu”, nazwy instytucji, nagłówki CAPS, akronimy, patronimiczna ulica w *negatywnym dla OSOBA* kontekście. FP = token bez przypisanej encji wymagającej maskowania; jeżeli kwota, numer lub adres **zgodnie z istniejącym kontraktem** ma zostać zamaskowany, to nie może być FP tylko dlatego, że zdanie nie zawiera osoby — takie przypadki klasyfikować osobno. Nie używać tych samych przykładów do wyboru przyszłego słownika i do ostatecznej oceny słownika.
- **M3 — wierność symulowanego Przywróć.** Dla każdego odblokowanego M1/M2 użyj zwróconej `reverse_map` i obecnego symulatora Przywróć. Porównaj pełny oryginalny tekst znak po znaku (również spacje, diakrytyki i interpunkcję); podaj liczbę dokumentów identycznych i różnice **poza oryginalnymi spanami encji**. Nie przypisuj błędu przywracania samemu modelowi AI (w teście brak AI). Brak mapy, konflikt tokenów lub różnica bez prawidłowego przywrócenia muszą mieć jawny status błędu; `blocked` nie przechodzi round-tripu.
- **Raport:** jeden JSON z osobnymi M1, M2, M3, liczbami per kategoria/wariant i ID przypadków; stdout krótkie sumy. Bez surowych dokumentów, pełnych nazwisk, sekretów ani PII z prawdziwych plików. Zakaz domyślnego zapisu raportów w repo i zakaz odczytu `dataset_real/`, `preview_real_results/`, prawdziwego archiwum i profilu. Raporty syntetyczne mogą służyć do porównania dwóch exact SHA przy IDENTYCZNYCH wejściach/seedzie, bez sztucznego „po” z inną próbką.

TASK_SCOPE:
- audyt/engine_quality.py
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: implementacja „zawsze maskuj”, modyfikacja `dict_auto_builder.py --apply`, seed/T04, trie/profil użytkownika, dodawanie list słów do `ner_blocklist.py`, jakakolwiek poprawka maskowania, AnchorEngine, zmiana Output Guard/S2/S3, OCR, UI, format tokenów, kosztowny benchmark na obrazach i testowanie realnych dokumentów.

## Minimalny dowód / PASS
1. W prechecku Codex ocenia tylko testowalność M1–M3, możliwość wykorzystania istniejących ownerów, separację danych i minimalizm. Jeśli jeden skrypt jest zbyt szeroki, zgłoś WYMAGA_DECYZJI przed implementacją — nie dodawaj subsystemów.
2. Runner uruchamia się dwa razy z tym samym seedem i wejściem: identyczne miary/liczności/ID i digest wejścia (poza datą/czasem); rozłączna próbka ma potwierdzoną separację. Brak danych holdout nie psuje pomiaru bazowego, ale jawnie oznacza brak holdout.
3. Jedna sztucznie wstrzyknięta porażka/błąd i przypadek `blocked` nie mogą dać fałszywego „brak wycieku” ani „100%”; M2 wykazuje FP na kontrolowanej atrapowej funkcji liczenia, M3 wykrywa zmienioną spację i błąd mapowania.
4. Potwierdzenie, że stan/profil tworzony jest tylko pod TEMP i sprzątany także przy błędzie; żaden dokument użytkownika ani token API nie jest odczytywany, backend HTTP nie startuje.
5. Brak jakościowego PASS typu „silnik szczelny”: Task ma PASS za **wiarygodny pomiar**, nie za dobre wyniki maskowania. Błędy wykryte przez runner → osobne findingi. Znany `IBAN-RECEPTA` jest mierzoną wadą silnika, nie pretekstem do jej naprawy w tym Tasku.
6. Audyt na exact SHA; wyniki testów celowanych + syntetyczny krótki przebieg runnera; bez pełnego benchmarku OCR.

WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: backend/pipeline.py --symbol pseudonymize_document
- TARGETS: audyt/unmask_sim.py --symbol unmask
- REASON: wykorzystanie istniejących publicznych szwów bez zmiany ownera.
GATE: maks. 2 nowe pliki (cel 1), pliki/funkcje nowe ≤600/50 linii, >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI. Nie osłabiać kryteriów M1–M3 tylko dla przejścia gate; jeśli implementacja wymaga szerszego narzędzia, wrócić do Architekta przed kodowaniem.
