# LYNX-ZUS-BOXED-IDS — PESEL/NIP w kratkach formularzy PDF

STATUS: BRIEF_ONLY → Codex precheck → CC ocena i ewentualna implementacja → Codex audyt exact SHA → merge wyłącznie OWNER.
PRODUCT_TRUTH: arch/spec.md S1–S5; BOARD.md LYNX-LAYOUT-SAMPLES i LYNX-LAYOUT-FINDINGS (2026-10-17); audyt/engine_quality.py --layout; backend/document_processor.py::_extract_text.
OWNER_PROPOSAL: po przeglądzie 70 pól najpierw formularze kratkowe ZUS. OCENA ARCHITEKTA: priorytet uzasadniony; brak zgody na globalne sklejanie cyfr z kolejnych wierszy.

## Potwierdzony problem
Lokalna próbka: 20 formularzy (4 PDF AcroForm ZUS), 70 pól syntetycznych. Finding: 6 PESEL/NIP w kratkach daje po ekstrakcji pojedyncze cyfry w kolejnych liniach; 4/6 bez tokenu na cały identyfikator, 2/6 zamaskowane wraz ze znakami nowej linii. To bezpośredni wyciek S1, ale jeszcze nie dowód jednej przyczyny wszystkich sześciu przypadków.
Na main PDF jest odczytywany przez PyMuPDF page.get_text(), bez jawnego pobrania form fields/widgets. Warstwa identity akceptuje cyfry ze spacją lub tabem, lecz nie z nową linią. Globalny wzorzec 11 cyfr rozdzielonych newline mógłby łączyć różne pola i cofnąć naprawę NEWLINE-CROSSING.

## Krok 0 — obowiązkowa diagnostyka przed kodem
Codex/CC na jednej lokalnej, wyłącznie syntetycznej próbce ZUS mają ustalić:
1. Czy cyfry pochodzą z tekstu page.get_text(), osobnych widgetów AcroForm (field_value, nazwy, grupy, położenia) czy innej reprezentacji PDF; czy da się wskazać JEDNOZNACZNIE cały PESEL/NIP bez łączenia niezależnych wartości.
2. Jak wygląda pion PDF → produkcyjny _extract_text → pipeline → tokeny/mapa/Przywróć. Osobno sprawdzić przypadki 4 dotąd jawne i 2 już rozpoznane, bez publikowania dokumentu ani wartości. W raporcie tylko liczby i typ źródła: TEXT_LAYER / WIDGET_GROUP / AMBIGUOUS.
3. Czy istniejący owner document_processor.py wystarcza. Jeśli potrzebna jest globalna zmiana warstwy identity lub nie ma bezpiecznej informacji o granicach, STOP + OWNER_DECISION_NEEDED, bez kodu i bez automatycznego rozszerzenia TASK_SCOPE.

## Oczekiwany efekt przy potwierdzonym szwie
- Każdy wiarygodnie zgrupowany PESEL (11 cyfr) i NIP (10 cyfr) zostaje osobną kompletną wartością przekazaną istniejącemu silnikowi; Zamaskuj nadaje jeden NUMER_NNN na całość. Żadna cyfra spanu nie pozostaje jawna, a reverse_map ma pełną wartość zastępowaną tokenem.
- Preferowana naprawa, jeśli możliwa: w istniejącej gałęzi PDF funkcji _extract_text użyć lokalnej informacji o grupowaniu pola (np. metadane AcroForm lub jednoznaczny układ), zamiast modyfikować wszystkie regexy lub łączyć dowolne linie tekstu. Nie dodawać drugiego parsera PDF, zależności ani globalnego czyszczenia newline.
- Nie łączyć cyfr z sąsiedniego pola, telefonu, daty i drugiego identyfikatora. Nie przestawiać tekstu niezwiązanego z PESEL/NIP, nie pochłaniać etykiet, nie tworzyć zagnieżdżonych tokenów. Przywróć dla wyniku tekstowego odtwarza dokładny tekst przekazany do maskowania; jeśli extractor wcześniej zmienił reprezentację PDF, wykazać tę różnicę jawnie (F3), nie udawać 1:1 względem wizualnego PDF.
- Guard blocked/force_block nie jest sukcesem maskowania. Dotychczasowe zwykłe PDF/DOCX/TXT/OCR i dwa już poprawne przykłady ZUS bez regresji. S2–S5 bez zmian.

TASK_SCOPE:
- backend/document_processor.py
- backend/tests/test_engine_quality_layout.py

OUT_OF_SCOPE: backend/layers/identity.py, layers/fallback.py, layers/ocr_normalizer.py, pipeline_new.py, output_guard.py, TOKEN_RE, audyt/engine_quality.py, DOCX-TABLES, NEWLINE-CROSSING, eksport dokumentów, UI, nowy parser/zależności, OCR skanów, KRS/KW, prawdziwe PII. Gdy diagnostyka wymaga innego ownera — wrócić z dowodem i korektą briefu, nie rozszerzać samodzielnie.

## Minimalne testy i PASS
1. Przed/po: ten sam lokalny zestaw 6 pól z identycznym digest i SHA wejść. Cztery niezamaskowane powinny zostać zamaskowane w całości, dwa wcześniej poprawne pozostać poprawne. Brak lokalnej próbki = NOT_RUN, nie PASS.
2. Syntetyczny PDF w tmp odwzorowujący rzeczywisty mechanizm pól (w tym widgety AcroForm, jeśli to one są źródłem); PESEL i NIP osobno. Sam PDF tekstowy bez pola nie zastępuje reproduktora ZUS, jeżeli próbka opiera się na widgetach.
3. Kontrpróby: 11 pojedynczych cyfr w różnych polach bez kontekstu, dwa identyfikatory obok siebie, PESEL nad telefonem, oddzielne daty/kwoty, normalne cyfrowe PESEL/NIP, PDF bez formularza. Żadna nieuzasadniona fuzja dwóch encji; pełna mapa, brak jawnych resztek i działające jednoprzejściowe Przywróć.
4. Uruchomić jawnie backend/tests/test_engine_quality_layout.py (poza pytest.ini), standardową suitę i gate exact SHA. Status i liczności bez wartości i fragmentów dokumentów, raport poza repo. Nie zmieniać istniejących M1/M2/M3 ani readera DOCX.

PASS: pełne odtworzenie granic PESEL/NIP z kratkowych PDF i kompletne maskowanie potwierdzone na lokalnej próbce, bez przypadkowego sklejenia niezależnych pól i bez regresji. Gdy tego nie da się bezpiecznie osiągnąć w obecnym ownerze, poprawny wynik prechecku to STOP, a nie udawany PASS.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/document_processor.py --symbol _extract_text
- TARGETS: backend/tests/test_engine_quality_layout.py
- REASON: odróżnić utratę granic na etapie ekstrakcji PDF od braku rozpoznania w silniku.

ZALEŻNOŚCI / AKTUALNY MAIN (2026-10-17): NEWLINE-CROSSING jest MERGED (impl 61ef3a84d54b17eee6bbe89ffb464453a8c46f89); DOCX-TABLES jest MERGED (impl 57e39fbb6e30cccdce87103b9f72f066c4126c2a). Odpadają wcześniejsze blokady. Codex precheck niniejszego briefu na aktualnym main, potem CC wykonuje odrębny wąski Task. Najpierw przypadek jawnego PESEL w kratkach; NIP w tym samym zakresie tylko jeśli potwierdzono identyczne źródło/granice ekstrakcji, w przeciwnym razie oddzielny finding. Zestaw 70 pól jest dawnym baseline, nie dowodem nowego pomiaru po ostatnich merge'ach. Bez merge bez zgody OWNER.
GATE: 0 nowych plików, >150 linii lub ratio >5:1 = WYMAGA_DECYZJI. Codex najpierw BRIEF_ONLY i analiza własności źródła, nie implementacja.