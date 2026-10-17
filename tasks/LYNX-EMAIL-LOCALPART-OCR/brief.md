# Brief — LYNX-EMAIL-LOCALPART-OCR

STATUS: BRIEF_ONLY. Codex precheck → CC review → CC implementation → Codex audit exact SHA → OWNER merge.
PRODUCT_TRUTH: arch/spec.md S1–S5; BOARD.md LYNX-EMAIL-LOCALPART-OCR, LYNX-THREAT-MODEL; tasks/LYNX-T11-TEXT-FIDELITY/round_01/implementation/DELIVERY.md § Zgłoszenia. OWNER proponuje kolejność wycieki → PUBLIC-DATA-TESTS; wybór Architekta: najpierw ten przypadek, bez zgody na merge.

WADA: W pełnym trybie i Express rozbity przez OCR adres «anna. nowak@example.pl» jest wykrywany jedynie od «nowak@», a «anna.» pozostaje jawne. layers/ner_adapter.py naprawia lokalną część dopiero PO warstwie contact. To częściowy wyciek S1, którego zielona suita nie wykrywa.

CEL: cały adres z wewnętrzną spacją OCR w lokalnej części (po kropce) staje się JEDNYM EMAIL_NNN; reverse_map zawiera pełen surowy span potrzebny do Przywróć. Nie może zostać jawny prefiks ani zagnieżdżony token. Reszta wejścia, w tym kropka kończąca zdanie, odstępy i kolejna linia, pozostaje bez zmian.

OWNER / SZEW: istniejący backend/layers/contact.py i jego _EMAIL_OCR_RE / apply_contact_layer. Preferować punktowe dopasowanie kompletnego e-maila w contact. NIE przesuwać globalnie normalizatora lub warstw. Zachować regułę T07 (pełna encja albo brak dopasowania, fallback ostatni) oraz T11 (brak globalnego sklejania zdań).

TESTY MINIMALNE:
1. Reproduktor «Kontakt: anna. nowak@example.pl. Termin płatności.»: po contact i w obu pipeline'ach cały adres pod jednym EMAIL_NNN, pełny oryginalny zapis w reverse_map, «anna.» niejawne, brak tokenów w wartościach mapy. Symulowane Przywróć (audyt/unmask_sim.py) ma odtworzyć wejście znak w znak, o ile wcześniejsza normalizacja nie zmodyfikowała wejścia (osobne wskazanie, nie pozorne PASS).
2. Dodatnie: zwykły e-mail bez spacji, spacja przy @, spacja przy TLD. Ujemne: «Kontakt. jan@example.pl», «Podpisano. Jan@example.pl», «example.pl. Termin», kropka/nowa linia poza e-mailem. Nie pochłaniać sąsiedniego zdania.
3. Test T07: 15 cyfr w lokalnej części poprawnego e-maila pozostaje w EMAIL_NNN, niezależne 15 cyfr jest NUMER_NNN; brak zagnieżdżonej mapy. Testy regresyjne IBAN/NRB, recepty i Guard nadal poprawne.
4. Test warstwy w backend/tests/test_layers.py i pion w backend/tests/test_audyt_2026_10.py. Uruchomić jawnie oba pliki (test_layers.py nie jest zbierany przez domyślne pytest.ini) oraz standardową suitę. test_audyt blisko limitu 600 linii: nie rozbudowywać go bez potrzeby. Raport zawiera dokładne SHA, PASS/XFAIL i dowód przed/po.
5. Pomiar audyt/engine_quality.py tylko na identycznym digest, ale nie traktować braku tej próbki w M1 jako potwierdzenia naprawy. Bez rzeczywistych danych i bez logowania PII.

TASK_SCOPE:
- backend/layers/contact.py
- backend/tests/test_layers.py
- backend/tests/test_audyt_2026_10.py

OUT_OF_SCOPE: ner_adapter, ocr_normalizer, pipeline_new, fallback, financial/IBAN-O2, Guard, TOKEN_RE/S2, UI, nowe parsery, przebudowa kolejności warstw, profile, nowe pliki i dane rzeczywiste. Gdy kontaktowy owner nie wystarcza, Codex ma zgłosić wąski finding; nie poszerzać samowolnie TASK_SCOPE.

PASS: reproduktor pełnego e-maila bez jawnego fragmentu i z prawidłową mapą działa w full/Express; kontrola Przywróć, brak regresji T07/T11 i brak osłabienia S3/S4. Wynik z blokadą nie jest sukcesem maskowania.
WHERE_MAP:
- MODE: REQUIRED
- TARGETS: backend/layers/contact.py --symbol _EMAIL_OCR_RE
- TARGETS: backend/layers/contact.py --symbol apply_contact_layer
- REASON: istniejący właściciel detekcji całych adresów.
GATE: zero nowych plików; >150 zmienionych linii lub ratio >5:1 → WYMAGA_DECYZJI. Precheck Codexa bez implementacji.
