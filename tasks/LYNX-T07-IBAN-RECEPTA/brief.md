# LYNX-T07-IBAN-RECEPTA — nie dzielić numerów; fallback jako ostatnia warstwa

STATUS: BRIEF_ONLY, precheck Codexa. Bez zmian kodu ani merge.
PRODUCT_TRUTH: `arch/spec.md` S1–S5; `arch/FINDING_2026-10_MOBILE_PORT.md` (BUG-IBAN-RECEPTA), `backend/tests/test_audyt_2026_10.py::test_iban_pl_bez_jawnej_resztki`, `tasks/LYNX-T07-IBAN-RECEPTA/round_01/tests/tests_r1.txt` (K1). Weryfikacja kierunku na `main`: `pipeline_new.py`, `layers/fallback.py`, `layers/validation.py`, `credential_patterns.json`.

OWNER_DECISION 2026-10-17, doprecyzowana w rozmowie: **szczelność ważniejsza od dokładnej kategorii numeru; pozostałe nierozpoznane długie ciągi cyfr maskować jako istniejący `NUMER_NNN`, bez `INNY`. Fallback ma być na samym końcu, po WSZYSTKICH rozpoznających warstwach. Żadna warstwa specjalistyczna nie powinna maskować fragmentu dłuższego numeru: albo rozpoznaje całą wartość, albo pozostawia ją do końcowej ochrony.** Próg nowej ochrony: co najmniej 15 cyfr łącznie, również z wewnętrznymi spacjami/tabami lub myślnikami. Nie zmieniać S2/S3/S4 ani nie uruchamiać automatycznego merge.

## Dlaczego brief zmieniono po prechecku K1
Poprzednia wersja wymuszała wczesny fallback przed `credentials` i przesuwanie `contact`/ `financial` dla uniknięcia kolizji. Codex słusznie wykazał ryzyko `NUMER_001` wewnątrz e-maila, ale OWNER wskazał prostszą regułę: **najpierw wszystkie rozpoznania specjalistyczne, potem fallback**. To nowe rozstrzygnięcie zastępuje wczesny fallback i warunkowe przestawianie wielu warstw; poprawka K1 wynika teraz z finalnego umiejscowienia fallbacku. Wymaga prechecku zmienionego rozwiązania, nie tylko dawnego K1.

## Minimalny szew — wymagane zachowanie
1. **Nie maskować podciągu numeru.** Aktualny wzorzec „Numer recepty” w `backend/credential_patterns.json` ma opcjonalną etykietę i dopasowuje dowolne 22 cyfry, także końcówkę dłuższego NRB/IBAN. W tym Tasku zawęzić TEN wzorzec do pełnego 22-cyfrowego numeru recepty w jawnym kontekście recepty (`recepta`, `nr recepty`, `numer recepty`); dopasowanie wymaga granic całej wartości, nie samego suffixu. **Bez etykiety nie zgadywać, że 22 cyfry to recepta** — zostawić dla finalnego fallbacku. Nie zmieniać innych JSON-owych wzorców i nie dokładać nowego parsera.
2. **Na końcu pipeline:** istniejący `backend/layers/fallback.py` jest ownerem ochrony resztek. Po **wszystkich** innych warstwach mogących tworzyć tokeny, w tym `validation` (w pełnym trybie), maskuje wszystkie samodzielne pozostałe sekwencje >=15 cyfr łącznie z wewnętrznymi spacjami/tabami/myślnikami jako jeden `NUMER_NNN`; zachowuje dokładny pozostały span w `reverse_map`. Nie przechodzi przez newline, interpunkcję kończącą frazę, sąsiedni wyraz ani istniejący token. Nie maskuje części resztki i nie tworzy tokenu wewnątrz innego tokenu.
3. **Full vs Express:** w `run_pipeline_new` fallback wywołać po `apply_validation_layer`, jeśli występuje; zachować istniejącą ochronę **8+ kolejnych cyfr** w pełnym trybie, obok nowego wariantu 15+ z separatorami. W `run_pipeline_express` dodać na końcu jedynie wariant **15+**, bez poszerzania Express o dotychczasowy full-fallback 8–14 cyfr. Ten sam moduł fallback, bez nowego stanu, klas tokenu lub procesu. Nie narzucać zmiany dotychczasowej kolejności innych specjalistycznych warstw — jeśli realny test potwierdzi, że któraś przechwytuje fragment większego numeru, zgłosić ją jako osobny, punktowy finding lub zaproponować rozszerzenie zgodnie z regułą ROZSZERZENIE CC.
4. **Wierność i bezpieczeństwo:** żadna warstwa nie ma tworzyć mapy zagnieżdżonej `NUMER_*`→`EMAIL_*`, na wynikowej mapie brak części liczby zamiast całości. Rozpoznany pełny e-mail (także `123456789012345@example.pl`) ma jeden `EMAIL_NNN`; IBAN/NRB albo pełny token z detektora, albo pełny `NUMER_NNN` z fallbacku. Fail-closed i Output Guard pozostają niezależną końcową kontrolą; wynik z blokadą nie zalicza testu poprawnego maskowania. Normalizacja tekstu *przed* tokenizacją i F3 Przywróć są osobnymi zagadnieniami.

Wyjście w UI: zwykły wynik „Zamaskuj” z obecnym formatem `NUMER_NNN` i działającym „Przywróć”. Nadmaskowanie nieszkodliwych długich liczb zostało zaakceptowane przez OWNERA, ale nie wolno gubić znaków, rozciągać tokenu na zdanie ani zmieniać Guarda.

TASK_SCOPE:
- backend/credential_patterns.json
- backend/layers/fallback.py
- backend/pipeline_new.py
- backend/tests/test_audyt_2026_10.py
- backend/tests/test_pipeline_v2.py
- backend/layers/contact.py
- backend/layers/credentials.py
- backend/layers/financial.py

OUT_OF_SCOPE: globalna przebudowa detektorów/centralnego resolvera, przepisywanie `financial.py` / `credentials.py` / `contact.py` (poza ROZSZERZENIEM CC E1–E3 niżej), `validation.py`, `ocr_normalizer.py`, zmiany ich kolejności bez reproduktora, `output_guard.py`, UI, tokeny/S2, T11/F3, EMAIL-LOCALPART-OCR (OCR-spacja w imieniu localpart), nowe zależności, nowe pliki, rzeczywiste dokumenty i profil.

## Minimalne testy / kryteria PASS
1. Istniejący `test_iban_pl_bez_jawnej_resztki` (dwa warianty: PL z odstępami, 26 cyfr NRB bez PL): zdjąć `xfail(strict=True)` dopiero gdy test potwierdza **jeden** token `NUMER_NNN` za CAŁY pierwotnie wykrywalny span, brak `PL61`/jawnych końcówek, pełną wartość spanu w `reverse_map`, `force_block=False`. Nie wystarczy „brak substringu 6110”.
2. Syntetyczny `numer recepty: 1234567890123456789012` maskowany w całości; ciąg tych samych 22 cyfr bez etykiety pozostaje nierozpoznany przez `credentials`, ale przejęty przez końcowy fallback. Dłuższy 26-cyfrowy ciąg NIE może być pocięty przez `credentials` na 22 cyfry i jawny prefiks (także gdy stoi po słowie `Konto`). Sprawdzić szew `credentials` samodzielnie i oba pipeline'y.
3. Nowy fallback: 15 cyfr jednolicie, 15 cyfr rozdzielonych spacjami i myślnikami, 26 cyfr NRB bez etykiety, w **full i Express** jako jeden `NUMER_NNN`. W full zachowane 8–14 kolejnych cyfr; w Express 8–14 nie przechodzi wyłącznie z powodu nowej reguły. Osobne zdania/wiersze i zewnętrzna interpunkcja bez zmian.
4. **K1 Codexa, pełny e-mail:** dla `Kontakt: 123456789012345@example.pl. Numer: 123456789012345.` oba tryby tworzą jeden `EMAIL_NNN` za cały e-mail i jeden `NUMER_NNN` za samodzielną liczbę, bez tokenów wewnątrz wartości `reverse_map`. Jednoprzejściowe symulowane „Przywróć” zwraca wejście znak w znak (o ile nie modyfikuje go już znany niezależny normalizator — wtedy wskazać osobno konkretną różnicę).
5. Nie pogorszyć istniejących `TestIbanWithSpace`, obcych IBAN, PESEL/NIP, phone/email; zmiana wzorca recepty nie może spowodować nowego jawnego numeru bezpośredniego. Nie dopuszczać do „PASS dzięki Guard blocked”. Raportować liczbę przypadków `leak`/`partial_mask`, `M2 FP` i `M3` z istniejącego `audyt/engine_quality.py --seed 2026` na identycznym `input_digest` przed/po, poza repo. Nadmaskowanie długiego numeru nie jest blokującym FP, jeśli mapowanie poprawne; nie obiecywać 100% szczelności.
6. Testy celowane: `cd backend && py -3 -m pytest tests/test_audyt_2026_10.py tests/test_pipeline_v2.py -q -o log_file=NUL` (Windows); inne istniejące xfail bez zmiany. Dostawa: exact SHA, testy, gate, minimalny diff i dowody wyłącznie syntetyczne.

PASS: potwierdzona integralność **całych** testowanych numerów, fallback na końcu obu pipeline'ów, pełny e-mail z numerami nienaruszony do rozpoznania, brak zagnieżdżenia map, zachowana recepta, istniejące pełne 8+ i Express 15+, S2/S3/S4/S5 bez zmian. Reguła „pełna wartość albo pozostaw bez zmian” jest inwariantem projektowym dla warstw numerów; **ten Task wymusza ją i naprawia w potwierdzonym `credentials`, nie audytuje całego niepowiązanego silnika**.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_new
- TARGETS: backend/pipeline_new.py --symbol run_pipeline_express
- TARGETS: backend/layers/fallback.py --symbol apply_fallback_layer
- TARGETS: backend/layers/credentials.py --symbol _load_patterns (tylko walidacja konsumenta zmienionego JSON)
- REASON: pełny numer lub brak dopasowania; fallback po validation/contact/financial/credentials, bez globalnej reorganizacji.
KOREKTY: r1 Codex K1 wskazał rozcinanie 15-cyfrowego localpart e-maila przez **wczesny** fallback. Nowa decyzja OWNERA przenosi fallback NA KONIEC i wymaga niepartialnego dopasowania w receptach. Weryfikować zmianę architektury względem r1, nie przypisywać Codexowi aprobaty tej nowej wersji bez prechecku.
GATE: 0 nowych plików, >150 zmienionych linii lub ratio >5:1 = WYMAGA_DECYZJI, nie osłabiać testów ani Guarda. Codex: BRIEF_ONLY precheck bez implementacji; CC po nim ocenia niezależnie.

## ROZSZERZENIE CC (2026-10-17, przed kodem rozszerzenia)
Ta sama klasa co BUG-IBAN-RECEPTA — warstwa specjalistyczna maskuje FRAGMENT dłuższego numeru (pkt 3 briefu dopuszcza rozszerzenie po realnym reproduktorze). Plik dopisany do TASK_SCOPE.
- **E1** `backend/layers/contact.py::apply_contact_layer`: wzorce telefonu (9 cyfr w grupach) łapią początek dłuższej liczby. Reproduktor (NER wyłączony, także na `main` przed T07): `run_pipeline_new("Nr 123 456 789 012 345 oraz 123-456-789-012-345.")` → `"Nr NUMER_001 012 345 oraz NUMER_001-012-345."`, mapa `{NUMER_001: "123-456-789"}` — sześć cyfr jawnych w obu zapisach; fallback 15+ nie może już przejąć całości.
- Poprawka: w `apply_contact_layer` odrzucić trafienie telefonu, którego span bezpośrednio sąsiaduje z kolejną cyfrą (po pojedynczym separatorze spacja/tab/myślnik albo bez) — „pełna wartość albo zostaw”; całość przejmuje końcowy fallback. Bez zmiany wzorców e-mail ani kolejności warstw.
- Testy: obie postacie 15 cyfr (spacje, myślniki) w full i Express jako jeden `NUMER_NNN`; zwykły telefon „tel. 512 987 654.” nadal maskowany przez warstwę kontaktów.
- **E2** (dopisane po przeglądzie rodziny numerów `implementation/number_sweep.py`, przed kodem E2) `backend/layers/credentials.py::apply_credentials_layer`: wzorzec „Tablica rejestracyjna pojazdu” łapie „PL6110” z „PL6110 9010 1400 000” → reszta (11 cyfr) jawna, w obu trybach, także przed T07. Bez zmiany wzorców JSON (zakaz briefu): jedna wspólna reguła w `fallback.py` (`long_number_runs` / `cuts_long_number`) — trafienie warstwy, które przecina ciąg ≥15 cyfr, ale go w całości nie obejmuje, jest pomijane; całość przejmuje końcowy fallback. Ta sama reguła zastępuje filtr E1 w `contact.py`. Recepta z etykietą obejmuje cały ciąg — nadal rozpoznawana. Plik dopisany do TASK_SCOPE.
- **E3** (po audycie r3, obserwacja O1 Codexa, przed kodem E3) `backend/layers/financial.py::apply_financial_layer`: 30-cyfrowy ciąg (2 cyfry + siedem grup po 4) — `financial` bierze 26-cyfrowy prefiks, 4 cyfry jawne, oba tryby, także przed T07. Ta sama klasa; ta sama wspólna reguła `cuts_long_number` (bez zmiany wzorców IBAN/NRB) — całość przejmuje fallback. Plik dopisany do TASK_SCOPE. Poprawki F1/F2 z r3 dotyczą `fallback.py` (już w zakresie).
