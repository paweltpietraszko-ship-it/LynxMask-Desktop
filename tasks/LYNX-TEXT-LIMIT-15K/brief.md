# LYNX-TEXT-LIMIT-15K — żadnego cichego obcinania dokumentów

STATUS: BRIEF_ONLY / ARCHITECT_APPROVED_FOR_CODEX_PRECHECK → Codex → CC ocena i implementacja → Codex audyt exact SHA → merge wyłącznie OWNER.
ŹRÓDŁO: CC, tasks/LYNX-TEXT-LIMIT-15K/cc_proposal.md; zaakceptowana diagnoza arch/DIAGNOZA_2026-10-18.md r2 (A7). Architekt usunął sprzeczność Express/NER, wskazał jeden istniejący limit bajtów, zredukował TASK_SCOPE/testy i oddzielił archiwum/Guard. PRODUCT_TRUTH: arch/spec.md S1–S5 (S4 bez zmian).
OWNER_INPUT 18.10: „Limit musi być zdjęty, od ciebie zależy kiedy”; ocena Architekta: teraz, w K0, bo utrata końcówki dokumentu jest cicha i zafałszowuje dalszy pomiar. Nie upoważnia to do zdjęcia limitów bezpieczeństwa ani do merge.

## Wada i zakres
backend/pseudominizer_api.py: MAX_TEXT_CHARS=15_000 i wycinki [:MAX_TEXT_CHARS] w /preview i /preview-express. Dokument dłuższy niż 15 tys. znaków jest przycinany bez ostrzeżenia; original_text także zawiera tylko początek. Pomiar CC: 54/178 lokalnych dokumentów >15 tys., największe do 186 tys. znaków (na CPU 11,2 s przy 162 tokenach). Dane/historyczne czasy to wskazówki, nie nowe gwarancje wydajności.

Dla wszystkich dopuszczalnych dokumentów oba endpointy mają przetwarzać cały tekst, jaki zwrócił istniejący extractor (bez cichego ucinania). Obecne text.strip() pozostaje bez zmian w tym Tasku — usuwanie skrajnego whitespace należy do osobnego findingu wierności. Nie zmieniać przetwarzania PDF/DOCX, NER, Guarda ani sposobu odpowiedzi z tokenami.

## Jedna jawna granica zamiast cichej
- W obu endpointach usuwa się limit 15 000 *znaków* i slice, ale pozostawia MAX_FILE_BYTES=5MB dla uploadu, MAX_TOKENS_PER_REQUEST=500 i MAX_BLOB_BYTES=512KB dla archiwum.
- Górna granica przetwarzanego tekstu: **500 000 bajtów UTF-8**, to samo co istniejące anonymizer_init.INPUT_LIMIT_BYTES. Nie używać „500 000 znaków” ani przelicznika zależnego od polskich liter; precheck Codexa ma sprawdzić import bez cyklu i jedno źródło prawdy. Jeśli ten stały limit nie obowiązuje w obu ścieżkach albo import powoduje cykl: STOP z dowodem, nie wymyślać drugiej wartości.
- Sprawdzenie po ekstrakcji i dotychczasowym strip, ale PRZED pipeline, w obu endpointach. Jeśli len(text.encode("utf-8")) > INPUT_LIMIT_BYTES: odpowiedź HTTP 413 z krótkim polskim komunikatem, blocked=True, bez wyniku, mapy, tokenów lub original_text. Log tylko kategoria, długość/limit — bez PII. Granica równa limitowi przechodzi do pipeline (podlega pozostałym regułom). Odmowa przy >5 MB upload dalej jak dotąd.
- Przekroczenie istniejącego limitu 500 tokenów, blokada Guarda i błędy NER zachowują dotychczasowe S3/S4. Nie otwierać zablokowanego wyniku, żeby „zaliczyć” przetwarzanie długiego dokumentu. Gdy te limity przerwą przetwarzanie, wykazać jawnie liczbę i przyczynę; jeśli obecne API/Express chowa sygnał force_block, osobny finding, nie obchodzić tego zmienianiem spec.
- /archive ma własny jawny błąd dla zaszyfrowanego blobu >512KB; sprawdzić, że nie jest to cichy sukces, ale NIE zmieniać rozmiaru blobu/archiwum w tym Tasku.
- **EXPRESS NIE MA NER.** Oba tryby mają zachować pełną długość i zamaskować PESEL/e-mail w końcówce, lecz nie wymagać maskowania nieznanych imion/nazwisk w Express; to był błąd w propozycji CC. Nie dodawać NER do Express.

TASK_SCOPE:
- backend/pseudominizer_api.py
- backend/tests/test_text_limit_15k.py

OUT_OF_SCOPE: backend/tests/test_audyt_2026_10.py (601 linii), backend/tests/test_pseudominizer.py (istniejący komentarz o 15k w teście — odnotować jako nieaktualny, nie osłabiać asercji), pipeline.py/pipeline_new.py, anonymizer_init.py, output_guard.py, frontend, extractor, archiwum/limity tokenów, NER-MULTILINE, spec S4. Jeden nowy mały plik testowy, bez powiększania 601-liniowego testu. Jeśli backend UI nie pokazuje komunikatu 413, udokumentować finding UI, nie dopisywać frontendu do tego Tasku.

## Minimalne testy
1. RED→GREEN przez prawdziwy lokalny TestClient obu endpointów, bez lifespanu/profile (jak obecne testy T02): syntetyczny TXT o długości 15 001–20 000 znaków, unikalny syntetyczny PESEL i e-mail dopiero w końcówce; oba endpointy: original_text dokładnie pełne text.strip(), no raw PESEL/e-mail w anonymized_preview (po odcięciu wyłącznie nagłówka PSE do porównania), oba mają właściwe tokeny/mapę do symulacji Przywróć. Full ma dodatkową niezależną kontrolę osoby z prawdziwym NER tylko jeśli model dostępny; dla Express NIE żądać OSOBA/FIRMA.
2. Kontrola granicy UTF-8: tekst zawierający polskie litery o długości B=500000 bajtów i B+1 (bez zakładania 1 znak = 1 bajt); przy B nie może być odmowy z powodu nowego limitu, przy B+1 dokładnie HTTP 413/blocked i brak fragmentu wyniku/mapy. Ponieważ długi tekst może trafić w ograniczenie tokenów lub OCR, odróżnić je od decyzji o długości, nie udawać sukcesu pipeline na samym stwierdzeniu granicy; kontrolę limitu można wyizolować, test pełnego przebiegu osobno.
3. Regresje: pusty tekst, plik >5MB, token-injection, zwykły krótki TXT, Express auth, polskie znaki, pełny tekst z końcem zawierającym PII. Ścieżka API nie może zmieniać Guard/NER; przy ograniczeniach tokenów/Guarda status musi być raportowany zgodnie z istniejącym S3/S4.
4. Lokalnie przed/po na tych samych SHA 54 dokumentów dłuższych niż 15k: rzeczywista długość wyekstrahowana/przekazana, mediana/max czasu, liczba blokad Guarda, jawnych błędów, limitów i zbyt dużych zaszyfrowanych map; brak lokalnej próbki=NOT_RUN. Nie zamieniać historycznego „54/178” na nowe pomiary; rozróżnić blokadę Guarda od obcięcia. UI na jednym długim pliku w działającym backendzie, bez publikowania jego treści.
5. Jawnie uruchomić nowy test (poza domyślnym pytest.ini) oraz standardową suitę, testy API i gate exact SHA. PASS: całe wejście mieszczące się w limitach bez ukrytej utraty, końcowy PESEL/e-mail maskowany w obu trybach, ponad limitem czytelna odmowa bez częściowego wyniku, bez osłabienia istniejących zabezpieczeń.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/pseudominizer_api.py --symbol preview
- TARGETS: backend/pseudominizer_api.py --symbol preview_express
- TARGETS: backend/pseudominizer_api.py --symbol MAX_TEXT_CHARS
- REASON: dwa identyczne miejsca ucięcia, jedna granica istniejącego INPUT_LIMIT_BYTES.
GATE: API jest plikiem legacy ponad 600 linii — nie powiększać bez odnotowanej decyzji gate/ownera; >150 linii lub ratio >5:1 WYMAGA_DECYZJI. Codex przed implementacją ma zweryfikować minimalny szew, brak cyklu importu i semantykę błędów; żadnego kodu przed precheckiem.
