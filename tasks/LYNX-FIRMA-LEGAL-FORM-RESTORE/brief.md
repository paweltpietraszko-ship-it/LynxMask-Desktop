# LYNX-FIRMA-LEGAL-FORM-RESTORE — Przywróć bez utraty formy prawnej

STATUS: BRIEF_ONLY → Codex precheck zakresu → CC ocena i punktowa implementacja → Codex audyt exact SHA → merge wyłącznie OWNER.
PRODUCT_TRUTH: arch/spec.md S1–S5 (w szczególności odwracalne maskowanie); BOARD.md LYNX-FIRMA-HYPHEN-SUFFIX MERGED oraz LYNX-FIRMA-LEGAL-FORM-RESTORE; tasks/LYNX-FIRMA-HYPHEN-SUFFIX/round_01/tests/tests_r2.txt, tests_r3.txt i tests_r2_repro.py.
OWNER_PROPOSAL 2026-10-17: po merge FIRMA-HYPHEN-SUFFIX najpierw bezstratne Przywróć formy prawnej, następnie FIRMA-NO-CANDIDATE. OCENA ARCHITEKTA: TAK, jedna mała korekta w istniejącym ownerze, bez rozszerzania detektora firm. W poprzednim Tasku Owner świadomie zaakceptował ograniczenie na potrzeby merge — ta zgoda nie oznacza, że utrata tekstu jest zachowaniem docelowym.

## Dowód i źródło
Audyt Codexa r2: reproduktor repeat-form-0 na prawdziwym Full NER: ta sama firma pierwszy raz bez formy, drugi raz ze Sp.k. (np. „Mega-Pack Polska” i „Mega-Pack Polska Sp.k.”). Pipeline zamienia samą nazwę na ten sam FIRMA_NNN, a backend/layers/ner_adapter.py::_FIRMA_CLEANUP_RE w końcu apply_ner_layer wykonuje sub zastępujący „FIRMA_NNN Sp.k.” przez „FIRMA_NNN”. Skrót znika z wyjścia, ale nie występuje w reverse_map, więc Przywróć gubi go bez ostrzeżenia. Odwrócona kolejność repeat-form-1 była bezstratna. Repeat-form-2 (S.A.) również ma zaobserwowaną niedokładność, ale jej przyczyna nie została niezależnie rozstrzygnięta. To wada wierności/znaczenia umowy, nie nowy wyciek; nie mylić z FIRMA-NO-CANDIDATE.

## Wymagane zachowanie (decyzja architektoniczna do prechecku)
- **Żaden cleanup nie może usuwać znaków tekstu, których nie przechowuje mapa.** W wariancie, w którym alokator ma tylko nazwę podstawową, zachować postać „FIRMA_001 Sp.k.”, a Przywróć odtwarza oba wystąpienia dokładnie, także kolejność i spacje. W pełnej encji rozpoznanej jako „Nazwa Sp.k.” dopuszczalny jeden FIRMA_NNN z pełną wartością w reverse_map. Różne reprezentacje nie mogą tracić oryginału.
- Zachować dotychczasowy przydział tokenów: nie narzucać wspólnego ani rozdzielnego ID dla „Nazwa” i „Nazwa Sp.k.”; widoczny sufiks przy wspólnym tokenie już odróżnia zapisy. Forma prawna sama („Sp.k.”, „S.A.”, „Sp. z o.o.”) nie wymaga nowego tokenu FIRMA i nie jest samodzielnym identyfikatorem podmiotu.
- Preferowana minimalna naprawa: usunąć lub zastąpić **stratną** końcową operację _FIRMA_CLEANUP_RE.sub(...) w apply_ner_layer oraz nieużywany wzorzec, jeśli już niepotrzebny. Nie przepisywać NER ani adaptera. Jeśli istnieje realny przypadek, w którym to ujawnia wcześniej chronioną część pełnej encji (nie samą formę), STOP z reproduktorem i nowym rozstrzygnięciem, nie deklarować PASS.
- Nie zmieniać zachowania zwykłych firm, NER, Guard, Express, OCR normalizatora, token format ani zabezpieczeń fail-closed. Bez globalnego poprawiania tekstu i bez wyłączania kontroli FP.

TASK_SCOPE:
- backend/layers/ner_adapter.py
- backend/tests/test_layers.py

OUT_OF_SCOPE: backend/ner_layer.py, ner_blocklist.py, spacy_ner.py, pipeline_new.py, output_guard.py, anon_profile, audyt/engine_quality.py, odtworzenie układu PDF/DOCX, nowa reguła AnchorEngine, pełna detekcja firm bez kandydata, COMB, ADRES i FP SPRZECIW. Każdy inny owner wymaga punktowego dowodu i korekty briefu przed implementacją.

## Minimalne testy
1. RED→GREEN na reproduktorze Codexa tasks/LYNX-FIRMA-HYPHEN-SUFFIX/round_01/tests/tests_r2_repro.py repeat-form-0 oraz kontrola repeat-form-1, przy **prawdziwym NER i prawdziwym Full pipeline/Guard**; wejście i Przywróć identyczne znak w znak, bez block, forma prawna występuje dokładnie tyle razy co w źródle. Bez fałszywego sukcesu poprzez zablokowanie całego dokumentu.
2. Przetestować rodzinę Sp.k., S.A. i Sp. z o.o. z nazwą bez i z formą, w obu kolejnościach; sprawdzić treść pod maskowaniem, mapę, brak zagnieżdżonych tokenów i Przywróć 1:1. W szczególności nazwa bez sufiksu nie może potajemnie odziedziczyć formy z innego wystąpienia. Repeat-form-2 z r2 uruchomić i sklasyfikować oddzielnie; jeśli nadal FAIL z inną przyczyną, nie ukrywać ani nie rozszerzać scope bez decyzji.
3. Negatywy: samo „Sp.k.” i „Sp. z o.o.” bez nazwy, inne słowo tuż po tokenie, dwie odrębne firmy, jedno rozpoznane pełne FIRMA z formą w reverse_map, akapit z nagłówkiem ALL-CAPS, zwykły tekst bez firmy. Sufiks za FIRMA w output może być jawny, ale nie może być **usunięty**. Brak nowych częściowo jawnych nazw, Guard nie osłabiony.
4. backend/tests/test_layers.py uruchomić jawnie (poza pytest.ini), standardową suitę i niezależny gate exact SHA; jeśli lokalnie dostępne, firma_sweep.py 160 wariantów na tej samej bazie i input_digest (zero nowych regresji). Zbiór 70 pól dotyczy głównie detekcji firm, nie dowodu tej utraty: NIE żądać jego zmiany jako kryterium PASS. Testy tylko syntetyczne, logi bez PII.
5. test_layers.py na main ma 568 linii; nowe przypadki parametryzować oszczędnie, nie przekroczyć 600 ani nie usuwać dotychczasowych testów dla gate. Jeśli nie mieści się rzetelna regresja, Codex ma wskazać dodatkowy plik testowy w prechecku przed edycją TASK_SCOPE, zamiast zgadywać akceptację.

PASS: w odtworzonym F1 żadna forma prawna nie ginie i Przywróć 1:1; brak nowych naruszeń ochrony danych, FP i NER/Guard; testy i gate dla jednego exact SHA. PASS tego Tasku **nie** potwierdza wykrywania firm bez kandydata SpaCy.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/ner_adapter.py --symbol apply_ner_layer
- TARGETS: backend/layers/ner_adapter.py --symbol _FIRMA_CLEANUP_RE
- REASON: usunąć źródło stratnej operacji, nie zmieniając klasyfikacji firm.
GATE: 0 nowych plików; pliki ≤600 linii (dla starszych bez pogorszenia), funkcje ≤50 linii (dla starszych bez pogorszenia); >150 zmienionych linii albo ratio >5:1 → WYMAGA_DECYZJI. Codex: BRIEF_ONLY, sprawdź minimalność i czy pozostawienie jawnej formy nie narusza zamrożonej polityki ochrony.
Kolejny Task po osobnym MERGED i zgodzie OWNERA: LYNX-FIRMA-NO-CANDIDATE — osobna architektura i próg FN/FP, bez włączania tutaj.