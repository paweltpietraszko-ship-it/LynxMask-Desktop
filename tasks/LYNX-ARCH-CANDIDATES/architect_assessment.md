# LYNX-ARCH-CANDIDATES — ocena Architekta 2026-10-18

STATUS: ARCHITECT_ASSESSMENT, nie zezwolenie na zmianę produkcyjnego pipeline. Źródła: cc_proposal.md, BOARD.md, arch/spec.md, pipeline_core.py, pipeline_new.py, ocr_normalizer.py, Depseudonimizuj.tsx. Hipoteza kandydaci → arbiter → podmiana ma sens. Odrzucam jednak przyjęcie F0–F4 jako jednego kontraktu bez bramek.

## Warunki, bez których architektura byłaby ryzykowna

1. Candidate wskazuje wyłącznie półotwarty span [start,end) w oryginalnym Python str, zawsze: 0 ≤ start < end ≤ długość tekstu i value = dosłowny wycinek źródła. N1 dotyczy WYEKSTRAHOWANEGO TEKSTU, nie bajtów pliku PDF/DOCX. Test CRLF, polskie znaki, emoji, wielokrotne te same fragmenty.
2. Evidence nie jest samą deklaracją detektora. CHECKSUM ma być rzeczywiście sprawdzony, PROFILE rzeczywiście dopasowany do zweryfikowanego wpisu. Dwa regexy z jednym założeniem nie są dwoma niezależnymi dowodami. W F0a dowody przechowywać jako dane/pochodzenie, bez punktacji produktowej.
3. NIE stosować „najdłuższy wygrywa przy remisie” jako ogólnej reguły. Dłuższy span może łączyć dwie osoby, datę i firmę lub zwykłe słowa. Nie zatwierdzać arbitra z arbitralną wagą CHECKSUM/NER/PROFILE. Nierozstrzygnięty konflikt daje AMBIGUOUS/STOP, nie cichy brak maskowania.
4. OCR widok nie jest oryginałem. SequenceMatcher po normalizacji nie daje dowodu poprawnych granic przy powtarzających się cyfrach i usuwaniu separatorów. Preferować monotoniczną mapę pochodzenia tworzoną razem z edycjami. Gdy oryginalnego spanu nie da się jednoznacznie ustalić, w produkcji fail-closed zamiast wypuszczenia półmaski. Samo „maskuj szerzej” może pożreć cudzą encję.
5. Q1: OWNER zgodził się koncepcyjnie na jeden token dla jednej osoby w odpowiedzi AI (kanoniczna forma) oraz dokładne zachowanie źródła. Wymaga to dwóch różnych informacji: token → forma do podstawienia w tekście AI oraz lista oryginalnych wystąpień [span, dosłowny zapis] dla źródła. Dzisiejsze mapy token → original i ekran Depseudonimizuj.tsx z replaceAll nie potrafią odtworzyć różnych form źródłowych jednym tokenem. Jeśli AI przestawi kolejność tokenów, lista wystąpień nie wskaże prawidłowej odmiany — do odpowiedzi AI używamy formy kanonicznej. Miejsce metadanych w szyfrowanym archiwum, migracja starych map i kompatybilność .lynxdict/Mobile wymagają formalnej decyzji OWNER przed F2. F0a nie modyfikuje mapy.
6. Nie podłączać F0 bez silników do /preview, nawet pod flagą ENGINE. Wypuszczałby surowy tekst, a test A/B 178 dokumentów byłby bezwartościowy. F0a to wyłącznie offline mechanika na syntetykach, bez API, kopiowania, UI i archiwum.
7. Jeden APPLY oznacza jeden APPLY. Propozycja CC opisuje też drugi przebieg dla resztek, co przeczy tej zasadzie. Rekomendacja: fallback/Anchor tylko zgłaszają kandydatów na oryginalnych offsetach, a końcowy arbiter i renderer działają po zebraniu wszystkich.
8. „Mechaniczne finditer → Candidate” jest hipotezą dla regexów; trie/profil, propagacja i OCR mają własne stany i offsety. Każdą adaptację trzeba udowodnić osobno. Nie poprawiać przy okazji semantyki istniejących reguł.
9. Profil jako silny dowód nie może nadpisywać w ciemno identyfikatorów innych osób ani pojedynczych słów w innym kontekście. INSTITUTION_LIST jest wetem wyłącznie przy weryfikacji konkretnego spanu, nie dowolnego podciągu.
10. Bezpieczna odpowiedź błędu nie zawiera źródłowych wartości w preview, tokenach, mapie, uzasadnieniach i logach. W produkcji AMBIGUOUS/OCR_MAP_ERROR nie może zostać potraktowane jako „0 kandydatów = PASS”.

## Etapy z bramkami

F0a: niezmienny Candidate/Evidence, walidacja surowych spanów, deterministyczne konflikty bez punktacji, pojedyncza podmiana przez istniejący TokenAllocator, syntetyczne N1/N2/roundtrip i jawne odmowy. Maksimum 2 nowe pliki GATE. Bez integracji i A/B.
F0b: widok OCR z wiarygodną mapą przesunięć i testami niejednoznaczności; osobny brief i gate.
F0c: ewentualne read-only shadow zbieranie kandydatów, bez wpływu na odpowiedź użytkową i bez logowania PII. Dopiero tu powstaje narzędzie do pomiaru mechaniki na rzeczywistych danych.
F1: strukturalne PESEL/NIP/IBAN/telefony, następnie adres i instytucja. A/B przy porównywalnym pokryciu, prawdziwych gold spans i tej samej ekstrakcji/Guard. Kandydatów nie wolno włączyć jako domyślnej ścieżki przy niepełnym pokryciu.
F2: osoby/firmy/linkowanie encji, dwa niezależne schematy Przywróć i HerBERT dopiero po decyzji Q1 i pomiarze CPU/FP.
F3: fallback/Anchor jako detektory resztek bez drugiej podmiany.
F4: niezależny audyt regresji, dane kontrolne (holdout), decyzja OWNER; nie usuwać starego silnika tylko dlatego, że nowy już powstał.

F0a PASS NIE oznacza lepszej jakości maskowania. A/B jakościowe na 178 dokumentach dopiero gdy w F1 istnieje zbliżony zakres reguł, a brak nowych wycieków jest potwierdzony według wystąpień, nie przez substring diff.

Otwarte: formalny schemat K2/Q1 przed F2, progi arbitra ustalane przed pomiarami, włączenie HerBERT i miejsce nowych formatów w Mobile. Nie zmieniać S1–S6 bez odrębnego OWNER_DECISION.
