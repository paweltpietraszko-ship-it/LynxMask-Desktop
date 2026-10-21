# LYNX-FIRMA-FILTER-FIX — zakres (CC, 2026-10-21; poprawka bez Architekta — zasada Pawła 21.10)

Paweł 21.10: „wszystkie poprawki idą bez architekta, on projektuje zmiany programu”. Propozycja i dowody: `cc_proposal.md`.
Diagnoza (pomocnik CC, kod main, syntetyki; lokalnie `%TEMP%\lynx_cc_review\firma_diag\` — `trace*.py`, `b_audit.py`, `b_biz.py`,
`raport.md`). **Korekta propozycji:** przykład „Piękna Dekoracja” był błędny — prefiks to `name_lower[:8]` całej encji, więc reguła
trafia w encje jednowyrazowe i te, których pierwsze słowo ma ≥8 znaków; „Piekarnię” blokuje ul. Piekarnicza, nie wieś.

## Ustalenia diagnozy
- **Samotne „z o.o”:** `spacy_ner.detect_entities` zwraca span ORG→FIRMA „z o.o.”; „ALFA Sp.” nie jest encją. `ner_layer._firma_bounds`
  (:219) rozszerza tylko w prawo i o człon przed łącznikiem, nie o słowa oddzielone spacją → `_process_ner` daje `FIRMA_001 → "z o.o"`,
  w tekście „ALFA Sp. FIRMA_001.”. Gorzej „ALFA S.A.” w osobnym wierszu: spaCy daje `OSOBA "A."`, `ner_layer.py:515` (len ≤ 2) usuwa →
  **zero tokenów, pełny wyciek firmy**. „Kowalski i Wspólnicy Sp. k.” → `OSOBA "Kowalski"` + `FIRMA "Wspólnicy Sp. k"`.
- **Lista prefiksów:** 34 141 prefiksów (city 26 894 z GUS, street 8 536 — przymiotniki ulic, med 88, ręczne 120; 1 507 śmieci
  z łącznikiem). 26,7% prefiksów pochodzi od słów, które Morfeusz zna jako pospolite. Absurdy: Przedsiębiorstwo ← ul. Przedsiębiorców,
  Piekarnia ← ul. Piekarnicza, Spółdzielnia ← ul. Spółdzielców, Transport ← ul. Transportowa, Pracownia ← „pracownik” (lista ręczna).
  Odrzucane prawdziwe dane: firmy 4/30 („Przedsiębiorstwo Budowlane MARBUD S.A.”, „Warszawa Kowalski Sp. z o.o.”…), samotne
  imię/nazwisko 14/89 (Katarzyna, Kowalska, Grzegorz…); pełne osoby 0/349.

## Zakres
1. **Forma prawna nigdy sama** (nowy moduł `backend/firma_context.py`, wywołanie w `ner_layer._firma_entities`): kandydat dowolnej
   etykiety, którego tekst to wyłącznie forma prawna (`_LEGAL_FRAGMENT_RE`: „z o.o.”, „A.”, „S.K.A.”, „k.”…), rozszerzany w lewo w tej
   samej linii o „Sp.”/„S.” i nazwę: słowa z wielkiej litery / WIELKIE / z cyfrą oraz „i”, „&”, łącznik; stop na początku linii,
   dwukropku, słowie z małej litery. Etykieta → FIRMA, encje zawarte w rozszerzonym zakresie (np. `OSOBA "Kowalski"`) odrzucane. Brak
   nazwy → kandydat usuwany (bez samotnego tokenu). Jedna wartość mapy („ALFA Sp. z o.o.”), Przywróć 1:1.
   **Dowód formy prawnej (korekta C1 Codexa r1 `2d0b13d`):** kandydat jest formą prawną tylko, gdy w tekście tworzy pełną formę:
   wieloliterowe „z o.o.”, „S.K.A.”, „P.S.A.”, „s.c.” same w sobie, albo **jednoliterowy fragment („A.”, „k.”, „j.”, „p.”) tylko wtedy,
   gdy bezpośrednio przed nim w tekście stoi „S.” / „Sp.”** (czyli „S.A.”, „Sp. k.”, „Sp. j.”, „Sp. p.”). Pojedyncza litera z kropką
   bez takiego poprzednika to inicjał (np. „Jan A.”, „Anna K.”) — encja zostaje bez zmian (etykieta, granice, dotychczasowe filtry),
   bez zamiany na FIRMA i bez usuwania. Macierz testów: „ALFA S.A.” (sama w linii i inline) → FIRMA „ALFA S.A.”; „Jan A.” → bez zmian;
   samo „A.” bez poprzednika → bez zmian; „Kowalski i Wspólnicy Sp. k.” → jedna FIRMA; „Anna K. i Wspólnicy” → bez zmian.
2. **Prefiks z kontekstem:** `_prefix_rejects` nie stosuje się do encji zawierającej formę prawną (`_LEGAL_SUFFIX_RE`) — zasada Pawła
   „jeśli w okolicy jest forma prawna, wykluczenie nie powinno być stosowane”.
3. **Zawężenie źródła prefiksów** (`ner_blocklist.py`): prefiksy tylko ze słów, które Morfeusz zna **wyłącznie** jako nazwę własną
   (geograficzną), bez interpretacji pospolitej; bez wpisów z łącznikiem. Pozostałe wpisy (w tym ręczne) działają tylko jako dokładne
   dopasowanie (`_NER_BLOCKLIST` bez zmian). Wynik obliczany raz (cache), czas startu mierzony.

TASK_SCOPE:
- backend/firma_context.py
- backend/ner_layer.py
- backend/ner_blocklist.py
- backend/tests/test_firma_context.py

Bez zmian: spaCy, HerBERT (`LYNX-HERBERT-NET` osobno), instytucje publiczne (osobne reguły sądów/urzędów), Guard, API, format tokenów.
`ner_layer.py` ma 594/600 l. — w nim tylko wywołania (plik nie może przekroczyć 600).

## Odbiór (pomiar: pomocnik CC; Codex odtwarza)
Testy celowane: „ALFA Sp. z o.o.” (inline i w linii pod „SPRZEDAWCA:”), „ALFA S.A.” sama w linii, „Doradztwo Biznesowe EXPERT S.A.”,
„Kowalski i Wspólnicy Sp. k.”, „Umowa z firmą ALFA Sp. z o.o.” (stop na „firmą”), samotne „z o.o.” bez nazwy (brak tokenu),
„Piekarnia Smaczek Sp. z o.o.” i „Przedsiębiorstwo Budowlane MARBUD S.A.” zakryte, „Sąd Rejonowy”/„Urząd Skarbowy” nadal jawne,
Przywróć 1:1. Pomiar przed/po na `dataset_clean` 300 (gold osób + gold firm z tekstu), `firma_sweep` 160, testy Mobile, benchmark 50
obrazów: firmy jawne/częściowe/zakryte, FP per klasa, **OSOBA: 0 nowych wycieków** i FP przed/po, strażnik `benchmark.py`, czas startu.
Szacunek: ~130 l. z testami.
