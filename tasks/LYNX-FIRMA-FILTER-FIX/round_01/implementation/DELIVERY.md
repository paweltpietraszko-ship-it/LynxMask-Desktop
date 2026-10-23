# LYNX-FIRMA-FILTER-FIX — DELIVERY r1 (CC, 2026-10-21)

Brief CC `3e2154f` (Codex precheck PASS `36ed749` = BEFORE). HEAD `2e9d128b9e19aaf19cb3982d8dcdf42c049b2ebd`.
Rozmiar: zgoda Pawła 21.10 na przekroczenie 150 l. („Zgadzam się na przekroczenie”, przy 167 l.); końcowo 178 l. (+11 po naprawie 3 regresji).

## Gate (dosłownie)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 2e9d128b9e19aaf19cb3982d8dcdf42c049b2ebd
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 173/5 = 34.6:1 (threshold 5:1)
  - TOTAL_LINES: 178 lines changed (threshold 150)
```

## Zmiany
- `backend/firma_context.py` (76 l.): kandydat będący wyłącznie formą prawną (wieloliterowa sama; jednoliterowa tylko z „S.”/„Sp.” przed nią —
  C1 Codexa) → FIRMA z nazwą w lewo w tej samej linii (stop: początek linii, `:`, `,`, `;`, słowo z małej litery; „Spółka” pomijana);
  brak nazwy → kandydat usunięty. FIRMA z formą prawną dołącza nazwę przed spójnikiem („Kowalski i Wspólnicy Sp. k.”). Usuwane są tylko
  fragmenty firm zawarte w nowej FIRMA; **OSOBA zostaje** (inny zapis firmy, np. „Sp.z”, nie trafia w wartość mapy → nazwisko musi mieć własny token).
- `backend/ner_layer.py` (595/600): wywołanie w `_firma_entities`; `_prefix_rejects` nie działa na encje z formą prawną; `_INSTITUTION_IN_FIRMA_RE`
  + Urząd/Starostwo/Prokuratura/Ministerstwo/Inspektorat/Kuratorium/Izba Skarbowa (urzędy nigdy FIRMA — wcześniej przypadkiem odrzucał je prefiks).
- `backend/ner_blocklist.py`: prefiksy tylko ze słów, które Morfeusz zna i to wyłącznie jako nazwę własną; bez wpisów z łącznikiem → 34 141 → 16 624.
- Testy `tests/test_firma_context.py`: 14 passed (macierz C1: ALFA S.A., Jan A., samo A., Kowalski i Wspólnicy, Anna K. i Wspólnicy; regresje).

## Pomiar przed/po (pomocnik CC; `tasks/LYNX-FIRMA-FILTER-FIX/measure/measure_run.py <SHA> <etykieta> <katalog>` + `measure_cmp.py <katalog>`;
PRZED = main `dcaa3e1`, PO = `2e9d128`; prawdziwy `/preview` w procesie, pusty profil; wyniki lokalnie `%TEMP%\lynx_cc_review\firma_fix3\`)
| zbiór | firmy zakryte / częściowo / jawne PRZED → PO | dok. z wyciekiem | FP FIRMA instytucje |
|---|---|---|---|
| dataset_clean 300 | 12/5/26 → **29/5/9** | 31 → 14 | 78 → 38 |
| obrazy 48 | 1/0/2 → 2/0/1 | 2 → 1 | 21 → 6 |
| testy Mobile 30 | 2/3/5 → 3/4/3 | 3 → 3 | 2 → 1 |
| firma_sweep 160 | 96/0/64 → **138/0/22** | 64 → 22 | 0 → 0 |
- Gold osób 477/477 zakryte przed i po; FP OSOBA bez zmian; miasta jako OSOBA 0 (test „Zakopanem” czysty). Nowych wycieków: 0.
- Przywróć: PRZED = PO w 547/550; różnice tylko zamierzone (`test_sklejanie`: jedna FIRMA „Zakład Usługowy Baranowski Sp. z o.o.” zamiast sklejki;
  `test_anchor_full`: samotne „z o.o.” bez tokenu, „Kowalski” = własny `OSOBA_007` jak przed; `doc_00024`: Urząd Marszałkowski nie jest już FIRMA).
  Kolizje 0. Kody/blokady identyczne w 561 dok. Import +0,5 s (Morfeusz przy liście), mediana /preview bez zmian.
- Regresje z pierwszego pomiaru (`98b2eba`) naprawione: nazwa przechodziła przez przecinek (data w FIRMA → wyciek), „Powiatowy Urząd Pracy
  w Poznaniu” jako FIRMA, alias innej osoby w „Kowalski i Partnerzy Sp.z o.o.”.
- Zostaje (poza zakresem): „Sp.k.” bez spacji w firma_sweep (22), „Biuro Rachunkowe RACHMISTRZ” bez formy prawnej, „Partnerzy Sp.z o.o.” jawne.
- NOT_CHECKED: `benchmark.py` (port 8765 = silnik Pawła), Guard nie zwraca danych w /preview (kody/blokady porównane).

## Poprawka F1 (Codex r3 `194a636`) — HEAD `3927a86bf8a25f0a03056a12ea2c4b0d9b8fed9a`
Cała forma prawna jako kandydat („Sp. z o.o.”, „S.A.”, „Sp. k./j./p.”, „S.K.A.”, „P.S.A.”) — nowy `_FULL_FORM_RE` w `_form_start`: łączy się
z nazwą w linii albo znika (np. „Forma prawna: Sp. z o.o.” → brak tokenu). Reproduktor Codexa `repro_f1_r3.py <backend>`: 7 passed (4 RED → zielone,
3 kontrole inicjałów bez zmian). `tests/test_firma_context.py` 14 passed. Gate: `STATUS: WYMAGA_DECYZJI` — RATIO 176/5, TOTAL_LINES 181 (+3).
Recheck Codexa: zachowany repro + wąski pion `/preview` dla pełnych form.
