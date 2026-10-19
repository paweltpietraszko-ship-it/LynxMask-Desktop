# LYNX-ARCH-ARENA — CASES_V01: jawny zestaw szkoleniowy i prognozy Architekta

STATUS: FROZEN INPUTS/GOLD dla pierwszego szkolenia. Gold jest zewnętrzną wyrocznią sędziego, NIGDY nie jest podawany programowi obrońcy. Wszystkie napisy fikcyjne; brak danych klienta. Prognozy to hipotezy przed implementacją, NIE wyniki uruchomionego symulatora.

Jak uruchomić: z każdego przypadku podaj do obrońcy wyłącznie pola text, base_candidates i mode="full" (podana struktura JSONL). Spans i prognoza muszą pozostać w testach sędziego, nie w danych obrońcy. Wskaźnik start/end oznacza półotwarty indeks oryginalnego Python str, nie bajty i nie UTF-16. Codex ma sprawdzić wszystkie granice niezależnie. Kod gry nie może czytać tego pliku.

Podział: A01–A05 i A08–A09, A12–A14 to zachowania bezpośrednio oczekiwane; A06, A07, A11, A15, A16 to **celowe przewidywane kontrprzykłady**. Można osiągnąć sukces uczciwie je wykrywając, ale nie wolno oznaczyć ujawnionego PII/FP jako wygraną. A10 to poprawny STOP bezpieczeństwa, lecz nie udane maskowanie. Osobno raportować PASS/FAIL mechaniki, FN/FP, STOP i Guard.

## A01 — Base wykrył czysty e-mail
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma.pl","base_candidates":[{"start":9,"end":21,"kind":"EMAIL","source":"EmailEngine","evidence":["FORMAT"]}],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":21,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED, 1 EMAIL; Anchor nie zmienia już pełnego spanu.

## A02 — OCR zamienił kropkę domeny w przecinek
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma,pl","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":21,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED, Anchor odzyskuje całość od ala po pl bez walidacji RFC.

## A03 — Resztka obok częściowo chronionego e-maila
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma .pl","base_candidates":[{"start":9,"end":18,"kind":"EMAIL","source":"EmailEngine","evidence":["FORMAT"]}],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":22,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED, Anchor rozszerza TEN SAM e-mail zamiast odrzucać overlap.

## A04 — Ulica i uszkodzony numer
INPUT_DO_OBROŃCY: {"text":"Adres: ul. Polna l2/8","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":7,"end":21,"kind":"ADRES"}]

PROGNOZA_ARCHITEKTA: RENDERED, Anchor proponuje pełny ADRES; nie sprawdza poprawności numeru.

## A05 — Nie maskuj cytatu aktu prawnego
INPUT_DO_OBROŃCY: {"text":"Źródło: Dz. U. Nr 223","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: []

PROGNOZA_ARCHITEKTA: RENDERED bez tokenów; Dz. U. nie jest kotwicą ulicy.

## A06 — Kotwica z fałszywym znaczeniem
INPUT_DO_OBROŃCY: {"text":"Profil: @administrator","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: []

PROGNOZA_ARCHITEKTA: Spodziewany FP (Anchor będzie podejrzewać e-mail); test pokazuje koszt zachłanności, NIE zielony sukces.

## A07 — Osierocony kod i miasto po poprawnym adresie
INPUT_DO_OBROŃCY: {"text":"Adres: ul. Polna 12, 65-001 Poznań","base_candidates":[{"start":7,"end":19,"kind":"ADRES","source":"AddressEngine","evidence":["FORMAT"]}],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":7,"end":34,"kind":"ADRES"}]

PROGNOZA_ARCHITEKTA: Spodziewany FN w wersji z twardym stop na przecinku — kontrprzykład do przyszłego rozszerzenia sąsiedztwa.

## A08 — Nie pożeraj następnego zdania po średniku
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma.pl; jutro spotkanie","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":21,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED; średnik i reszta zdania pozostają oryginalne.

## A09 — Nie przechodź przez nową linię
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma.pl\nAdres: ul. Polna l2","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":21,"kind":"EMAIL"},{"start":29,"end":41,"kind":"ADRES"}]

PROGNOZA_ARCHITEKTA: RENDERED z dwoma rozłącznymi tokenami, znak nowej linii pozostaje.

## A10 — Wstępny OSOBA nakłada się na kotwicę EMAIL
INPUT_DO_OBROŃCY: {"text":"Kontakt: ala@firma.pl","base_candidates":[{"start":9,"end":12,"kind":"OSOBA","source":"NER","evidence":["NER_SPACY"]}],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":9,"end":21,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: STOP/AMBIGUOUS; typów OSOBA i EMAIL nie łączymy siłą zasięgu.

## A11 — OCR zniszczył numer PESEL bez @ i ul.
INPUT_DO_OBROŃCY: {"text":"PESEL: 9O05141234O","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":7,"end":18,"kind":"NUMER"}]

PROGNOZA_ARCHITEKTA: Spodziewany FN; ograniczenie v0.1 Anchor, Guard powinien zgłosić podejrzaną resztkę po PESEL.

## A12 — Próba wstrzyknięcia istniejącego tokenu
INPUT_DO_OBROŃCY: {"text":"Oznaczenie: OSOBA_001","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: []

PROGNOZA_ARCHITEKTA: STOP/INVALID (token injection); bez możliwości uznania gotowego tokenu za własny.

## A13 — Unicode i przesunięcie offsetów
INPUT_DO_OBROŃCY: {"text":"😀 Kontakt: żaneta@firma.pl","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":11,"end":26,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED, granice liczone w Python str, nie w JS UTF-16; emoji poza tokenem.

## A14 — Dwa identyczne wystąpienia
INPUT_DO_OBROŃCY: {"text":"Maile: ala@firma.pl; ala@firma.pl","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":7,"end":19,"kind":"EMAIL"},{"start":21,"end":33,"kind":"EMAIL"}]

PROGNOZA_ARCHITEKTA: RENDERED, dwa spany ten sam token EMAIL_001; dokładny roundtrip.

## A15 — Kotwica adresowa w zwykłym zdaniu
INPUT_DO_OBROŃCY: {"text":"Skrót ul. w instrukcji nie oznacza tu adresu.","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: []

PROGNOZA_ARCHITEKTA: Spodziewany FP albo blokada/niepewność; dowód ryzyka Anchor z samą kotwicą.

## A16 — Nie przełykaj drugiego identyfikatora
INPUT_DO_OBROŃCY: {"text":"Adres: ul. Polna l2/8; PESEL 9O05141234O","base_candidates":[],"mode":"full"}

GOLD_SĘDZIEGO: [{"start":7,"end":21,"kind":"ADRES"},{"start":29,"end":40,"kind":"NUMER"}]

PROGNOZA_ARCHITEKTA: Anchor nie może połknąć PESEL; PESEL będzie FN w v0.1, Guard powinien sygnalizować. Nie zaliczać jako WIN.

## Obowiązki falsyfikacyjne sędziego

1. Zamroź exact SHA obrońcy przed napisaniem własnych przypadków; zmieniaj nazwy źródeł, kolejność propozycji i dodawaj nowe frazy spoza tej listy. Nie wrzucaj nowych oracle do inputu runtime.
2. Sprawdź przypadki bez PII (maskowanie wszystkiego to porażka), częściowo zakryte dane (maskowanie częściowe to FN), STOP na czystym tekście (porażka użyteczności) i kolizję typów (STOP poprawną reakcją).
3. Nie przyjmuj predykcji Architekta za prawdę. Jeśli oryginalny gold jest niejednoznaczny, oznacz JUDGE_DISPUTE i przekaż do OWNER zamiast przestawiać etykietę pod wynik silnika.
4. Zakończ raportem: liczba prawdziwie uratowanych FN, nadmaskowań, powtórzonych błędów po zmianach i testów, których wynik może pochodzić z zapamiętanego przykładu. Niezależny test ma wykrywać hardcoding po identyfikatorze lub frazie.

## Ocena sędziego r2 — doprecyzowanie C2 bez zmiany wejść i gold

Poniższa tabela dotyczy WARUNKÓW według briefu r2, a nie odtworzonych wyników kodu. Zamrożone teksty, indeksy, gold_spans i pierwotne prognozy A01–A16 pozostają bez zmian. Mechanika i skuteczność mają ODDZIELNE oceny.

| Case | Prognoza mechaniki r2 | Klasyfikacja ochrony, jeśli wynik zgodny z prognozą |
|---|---|---|
| A01 | RENDERED, EMAIL w całości | PROTECTION_PASS |
| A02 | RENDERED, kotwica ratuje EMAIL mimo przecinka | PROTECTION_PASS |
| A03 | RENDERED, rozszerzenie tego samego EMAIL o ogon .pl | PROTECTION_PASS |
| A04 | RENDERED, ul. + Polna + l2/8 | PROTECTION_PASS |
| A05 | RENDERED, bez tokenów | PROTECTION_PASS (brak gold) |
| A06 | RENDERED, @administrator jako EMAIL | PROTECTION_FAIL / FP mimo trafnej prognozy |
| A07 | RENDERED, ADRES tylko do przecinka | PROTECTION_FAIL / FN_PARTIAL, Guard może nie ostrzec |
| A08 | RENDERED, EMAIL nie pochłania reszty zdania | PROTECTION_PASS |
| A09 | RENDERED, dwa rozłączne tokeny i zachowany newline | PROTECTION_PASS |
| A10 | STOP / AMBIGUOUS, konflikt OSOBA i EMAIL | SAFE_REFUSAL; NIE PROTECTION_PASS za maskowanie |
| A11 | RENDERED, brak tokenów, ID_LABEL_REMAINS | PROTECTION_FAIL / FN_FULL, Guard ostrzegł, nie uratował |
| A12 | STOP / TOKEN_INJECTION | SAFE_REFUSAL; NIE PROTECTION_PASS za maskowanie |
| A13 | RENDERED, EMAIL po emoji i polskich literach | PROTECTION_PASS |
| A14 | RENDERED, dwa wystąpienia pod EMAIL_001 | PROTECTION_PASS z roundtrip 1:1 |
| A15 | RENDERED, ul. w instrukcji nie jako ADRES | PROTECTION_FAIL / FP mimo trafnej prognozy |
| A16 | RENDERED, ADRES do średnika; ID_LABEL_REMAINS | PROTECTION_FAIL / FN_FULL na PESEL, Guard nie kompensuje |

Sędzia nie może przydzielić PROTECTION_PASS tylko dlatego, że wynik odpowiada tej tabeli. Jeśli nowy kod zachowa się inaczej, oceniać rzeczywisty output przez reguły briefu r2 i gold, z osobnym wykazaniem odchylenia od prognozy. Dla A10 i A12 poprawny STOP nie daje „punktów za zamaskowanie”. STOP przy A01–A09/A11/A13–A16 bez formalnej przyczyny = UNEXPECTED_STOP. Zmiana gold lub tych reguł wymaga nowej wersji eksperymentu, nie cichej korekty po wyniku.
