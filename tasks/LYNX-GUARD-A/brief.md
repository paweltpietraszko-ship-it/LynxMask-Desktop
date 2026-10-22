# LYNX-GUARD-A — etap A Guarda: silnik zwraca listę ostrzeżeń zamiast [REDACTED]

22.10.2026, CC. Realizacja etapu A zatwierdzonego kontraktu `LYNX-GUARD-RESIDUE` brief v2 (`52d8358`, Codex PASS PREIMPLEMENTATION r4 `93c656c`, zgoda OWNERA 22.10) i S4 zamrożonego w `94a7954` (`task/LYNX-SPEC-S4-GUARD-WARN`; ta gałąź stoi na nim). Uwagi CC U1–U5 i szacunek: BOARD, wiersz LYNX-GUARD-RESIDUE (OWNER zgodził się na koszt i podział A/B).

## Zakres A (silnik)
1. Nowy moduł `backend/guard_residue.py`: `collect_warnings(text, map_values, allowlist)` → lista pozycji `{id, start, end, fragment, rule, rules, level, reasons}`.
   Źródła: dotychczasowe wzorce `output_guard` HIGH/MEDIUM i wartości MAP_LEAK (nie znikają — S4) + R1–R5 z briefu v2:
   R1 słowo z wielkiej litery w środku zdania: tytuł („Pan”, „p.”, „dr”) przed nim albo Morfeusz zna je jako imię/nazwisko albo nie zna wcale;
   bez alarmu: początek zdania/linii, białe listy Mobile (`osoba_not_person.py`), „Strony”, słowa znane wyłącznie jako zwykłe lub geograficzne,
   miejscowość po przyimku (U3); R2 imię lub token OSOBA + inicjał; R3 cyfry obok NUMER/ADRES, kod pocztowy po ADRES, litery doklejone do tokenu;
   R4 słowo-klucz (nr, działka, ur., tel., PESEL…) + wartość z ≥2 cyframi, bez Dz.U./art./poz.; R5 rola kontrahenta + nazwa oraz nazwa z formą
   prawną, bez urzędów/sądów/gmin. Nachodzące fragmenty → jedna pozycja; nic wewnątrz tokenów; istniejąca allowlista tylko odczyt (wycisza).
   Poziom RED: HIGH i MAP_LEAK; reszta YELLOW.
2. `backend/pipeline.py` `_apply_output_guard`: bez zamiany tekstu na `redacted_text` i bez `guard_blocked` z Guarda; `guard_warnings` w `PipelineResult`.
   Awaria Guarda/etapów nadal S3 fail-closed (bez zmian). Odczyt allowlisty przeniesiony do `guard_residue.load_allowlist`.
3. `backend/pseudominizer_api.py` `/preview`: pole `guard_warnings` z pozycjami względem `anonymized_preview` (przesunięcie o nagłówek PSE).
   Plik bez wzrostu (ratchet).
4. Zgodność do etapu B (`frontend/src/screens/Pseudonimizuj.tsx`, bez wzrostu): ostrzeżenia blokują zapis i kopię jak dotychczasowa blokada,
   panel pokazuje fragmenty ostrzeżeń. Panel decyzji Zakryj/Zostaw, usunięcie „To nie PII — zapisz mimo to” i przewijanie (U5) — etap B.
   **Etapu A nie scalać bez B** (A sam zostawia stary zbiorczy bypass) — chyba że OWNER zdecyduje inaczej.

Poza zakresem: UI decyzji (B), szyfrowanie allowlisty (S5, osobno), rejestr decyzji, zmiany OSOBA/FIRMA/NER.

TASK_SCOPE:
- backend/guard_residue.py
- backend/pipeline.py
- backend/pseudominizer_api.py
- frontend/src/screens/Pseudonimizuj.tsx
- backend/tests/test_guard_residue.py
- backend/tests/test_failclosed.py
- tasks/LYNX-GUARD-A/brief.md
- tasks/LYNX-GUARD-A/repo_before.hash

Wzrost powyżej 150 linii: zgoda OWNERA na koszt etapu A (~250–300 l. + testy) udzielona 22.10 (BOARD).

## Odbiór
`backend/tests/test_guard_residue.py`: przypadki dodatnie i ujemne z briefu v2 (Śludkowskiego, „Marcin S.”, „OSOBA_001 S.”, „NIP: 7 NUMER_021”,
„ADRES_003, 32-5 00 Chrzanow”, „Nr działki 128/7”, „Biuro Rachunkowe RACHMISTRZ”, „ALFA sp. z o.o.”; brak alarmu: Sąd Rejonowy, tokeny, „Warszawa,
dnia…”, terminy umowy „Zamawiający/Wykonawca/Strony/Umowa”, miasto po przyimku, Dz.U./art., Gmina, sygnatura). `test_failclosed.py`: MAP_LEAK w
ścieżce pipeline → tekst bez zmian, bez blokady, ostrzeżenia RED dla wartości z mapy i PESEL. Pomiar zalewu ostrzeżeń (pomocnik CC) na
`dataset_20261016_fresh` i `dataset_20260627_095419`: liczba ostrzeżeń na dokument i trafność wg reguły — w DELIVERY.
