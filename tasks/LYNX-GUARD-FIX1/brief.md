# LYNX-GUARD-FIX1 — fałszywe ostrzeżenia Guarda: dwie kolumny, etykieta, nazwa instytucji

22.10.2026, CC. Poprawka bez Architekta (błąd reguł R1/R5 z `LYNX-GUARD-A`, main `9465f96`). Zgłoszenie: ogląd OWNERA 22.10, plik
`Pliki testowe/doc_stresstest_silnik_guard_lvl0_3.txt` l. 112–113 (syntetyczny, układ w dwóch kolumnach, końce linii CRLF):
```
Sprzedawca:                              Nabywca:
MEDITECH SOLUTIONS SP Z O.O              Przychodnia Rejonowa „Zdrowie”
```
Na main Guard pokazuje „Nabywca:\r” jako „Możliwa firma” (R5) i „Przychodnia” jako „Możliwe nazwisko” (R1). Dla człowieka oba to śmieci.

## Zmiany (`backend/guard_residue.py`)
1. R5 z roli:
   - wartość bez `\r`;
   - przy odstępie ≥3 spacji/tabulatorów bierzemy tylko kolumnę zaraz po etykiecie;
   - pomijamy, gdy po etykiecie stoi kolejna etykieta pola („Nabywca:”).
2. R1: słowo, które samo jest słowem nazwy instytucji (`_INSTITUTION_RE`: Przychodnia, Szpital, Urząd…), nie jest pytane jako nazwisko.
   Wcześniej sprawdzane były tylko słowa przed nim.

TASK_SCOPE:
- backend/guard_residue.py
- backend/tests/test_guard_residue.py
- tasks/LYNX-GUARD-FIX1/brief.md
- tasks/LYNX-GUARD-FIX1/repo_before.hash

## Odbiór
- `backend/tests/test_guard_residue.py`:
  - bez alarmu: dwie kolumny „Sprzedawca: … Nabywca:” z CRLF, „Odbiorca:\r\nPrzychodnia Rejonowa …”;
  - R5 tylko lewej kolumny: „Biuro Rachunkowe RACHMISTRZ”.
- Pomiar zalewu `%TEMP%\lynx_cc_review\guard_a\rerun_cc.py <wt>\backend`: bez zmian (25 / 150 dok.).
- Dokument OWNERA: na main 5 ostrzeżeń (w tym „Nabywca:\r”, „Przychodnia”), po poprawce 3: „7” przy NIP, „ING Bank Slaski S.A.”, „32-5 00 Chrzanow”.
