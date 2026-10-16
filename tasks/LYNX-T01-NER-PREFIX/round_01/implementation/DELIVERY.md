# DELIVERY — LYNX-T01-NER-PREFIX (CC, runda 1)

Brief: `tasks/LYNX-T01-NER-PREFIX/brief.md` (`851bc26`); ocena CC: `round_01/cc_review_r1.md` (`069df2f`, BEFORE_SHA).
CC nie wystawia werdyktu własnej implementacji — PASS/FAIL należy do `gate.py` i Codexa.

## Zmiana (TASK_SCOPE: `backend/ner_layer.py`, `backend/ner_blocklist.py`, `backend/tests/test_audyt_2026_10.py`)

- `ner_blocklist.py`: `_PERSON_FORMS` — wszystkie formy z `names_inflected.json` i `surnames_top1000.json`.
- `ner_layer.py`:
  - `_is_person_word(word)` — słowo z wielkiej litery, NIE dokładna nazwa geo (`_GEO_WORDS`), oraz: forma ze słownika
    ALBO Morfeusz daje `imię`/`nazwisko` (także `nazwisko_(odmężowskie)`) i NIE daje `nazwa_pospolita`/`nazwa_geograficzna`
    (doprecyzowanie D1 — „Krakowie” ma u Morfeusza `imię`+`nazwisko`, więc sam kwalifikator nie wystarcza).
  - `_prefix_rejects(...)` — filtr prefiksów geo tylko dla encji JEDNOWYRAZOWYCH (wielowyrazowe: „Katarzyna W.”,
    „Kowalski i Partnerzy Sp. z o.o.” nie są już cięte po 8 literach); bez Morfeusza nie odrzuca jednowyrazowej OSOBA (D3).
  - `_filter_institutions`: kolejność token → kod → exact blocklist → adres → sąd → **potwierdzona osoba (keep)** →
    prefiks → reszta bez zmian. Długość funkcji bez zmian (72 linie; skrócone 2 komentarze). Usunięty log `pominięto (prefix)`
    z wartością encji (mniej PII w logach — S5).
- Testy: zdjęte `xfail` z `test_filtr_ner_nie_odrzuca_osob` (4) i `test_filtr_ner_nie_odrzuca_odmienionych_imion` (3);
  dodane `test_filtr_ner_nadal_odrzuca_nie_osoby` (7 przypadków FP) i `test_filtr_ner_bez_morfeusza_nie_odrzuca_osoby_prefiksem`.

## Dowody (Windows, Python 3.14, `py -3`)

| Pomiar | Przed | Po |
|---|---|---|
| `pytest tests/` bez backendu | 3 failed, 122 passed | **1 failed**, 124 passed (zostaje `test_iban_reverse_map_entry` — BUG-IBAN-RECEPTA, poza T01) |
| `pytest tests/` z backendem (profil/archiwum tymczasowe, env `ANONYMIZER_PROFILE_DIR`/`ARCHIVE_DIR`/`PROFILE_DIR`) | 3 failed, 160 passed | **1 failed**, 162 passed |
| `TestFilterFunction` (2 znane faile FIRMA) | 2 failed | 4/4 passed |
| `test_audyt_2026_10.py` | 26 xfailed | 15 passed, 19 xfailed |
| Pomiar holdout: 120 nazwisk z Mobile `surnames_extended.json` SPOZA `surnames_top1000`, 5 zdań/nazwisko (`holdout_measure.py`) | **156/600 form jawnie (26%)**, pełne imię+nazwisko 21/120 | **50/600 (8,3%)**, pełne imię+nazwisko **0/120** |

Próbka FP filtra (te same słowa, stary vs nowy kod): zmiany wyłącznie w kierunku „osoba/firma zostaje”
(Kowalskiemu, Katarzyna W., Nowakowej, Kowalski, Bartłomiej, Kowalski i Partnerzy, Sadowski i Wspólnicy).
Słowa już wcześniej przepuszczane (Osoba, Kont0, Mazur, Zapłata — BUG-NER-FP) bez zmian; odrzucane nadal odrzucane
(Warszawie, KONTROLNA, Piątek, Encje, ZUS, Sąd…).

## Pozostałe 50 wycieków holdout — przyczyny (`diag`)

- 30: spaCy w ogóle nie wykrywa jednowyrazowego nazwiska → poza filtrem; temat LYNX-DICT-LEAKTEST.
- 20: nazwisko = dokładna nazwa miejscowości/ulicy albo słowo pospolite (kierunek D1/D2: rozstrzyga kontekst).

## Zgłoszenia poza zakresem (nie naprawiane)

1. **BUG-NER-GEO-EXACT (nowy, WYS):** `_NER_BLOCKLIST` zawiera `_GEO_WORDS` z nazw ULIC; ulice patronimiczne to nazwiska
   w dopełniaczu. 1008 z 10 080 form `surnames_top1000` (10%) to dokładne słowa geo, np. „Kowalskiego”, „Nowaka”,
   „Adamczyka” — jednowyrazowa OSOBA w tej formie jest odrzucana filtrem exact (przed i po T01). Propozycja: formy ze
   słownika osób nie są odrzucane za samo dopasowanie do nazwy ULICY (miasta — nadal tak).
2. **T20 w `tests/test_pipeline.py` nadal FAIL, inna przyczyna:** „„Wiśniewski Consulting" Sp. z o.o.” — przed T01
   nazwisko jawne; po T01 nazwisko zamaskowane (OSOBA_001), ale spaCy tnie firmę na cudzysłowie typograficznym, więc
   „Consulting” zostaje jawne, a `FIRMA_001=' Sp. z o.o'`. Granice encji przy „…" (FIX-QUOTES), nie filtr. Testu nie zmieniano.
