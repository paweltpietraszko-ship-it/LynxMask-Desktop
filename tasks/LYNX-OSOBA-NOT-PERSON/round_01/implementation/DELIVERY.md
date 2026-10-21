# LYNX-OSOBA-NOT-PERSON — DELIVERY r1 (CC, 2026-10-21)

Brief v3 `42f83a8` (Codex BRIEF_ONLY PASS `d116271`). Baza main `1f60c060e3ecd2beab215e34ad4f817a1aeb8e24`, kod HEAD `389830290bc6e28573da1c17f405960bf0cf0c75`.

## Zmiany
- `backend/osoba_not_person.py` (nowy): `OSOBA_DENYLIST` (pierwsza część dotychczasowej listy z `ner_adapter.py`, = Mobile
  `NameEngine.kt:291–332`), `_CALENDAR_GEO` (druga część dotychczasowej listy), port 1:1 Mobile `WHITE_LIST_DOCUMENTS` (:217) i
  `WHITE_LIST_COMMON_WORDS` (:244); `WHITE_LISTS`, `DICTIONARY_PATH_DENYLIST = OSOBA_DENYLIST | _CALENDAR_GEO`;
  `reject_single_osoba(entity_text, person_forms)`: jednowyrazowa — mała litera albo `OSOBA_DENYLIST` (zawsze, kompromis 2a) albo
  `WHITE_LISTS` i spoza `person_forms`.
- `backend/ner_layer.py`: import + warunek dołączony do istniejącego pierwszego `if` w `_filter_institutions` (przed T01); długość funkcji
  bez zmian (72), plik 598/600.
- `backend/layers/ner_adapter.py`: lista zastąpiona importem `DICTIONARY_PATH_DENYLIST as _OSOBA_DENYLIST` — zbiór identyczny
  (216 = 216, porównanie z `origin/main` przez `ast`), `_apply_dictionary_names` bez zmian zachowania.
- `backend/tests/test_osoba_not_person.py` (nowy, 21 testów).

## Bramka (stdout dosłownie, `gate_r1.txt`)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 389830290bc6e28573da1c17f405960bf0cf0c75
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 128/21 = 6.1:1 (threshold 5:1)
```
RATIO: przewaga dodanych linii to listy (przeniesiona z `ner_adapter.py` + port dwóch list Mobile), nie logika.

## Testy
- `tests/test_osoba_not_person.py`: 21 passed.
- Regresja (`test_audyt_2026_10.py test_layers.py test_firma_context.py test_ner_multiline.py test_pipeline_v2.py`): 4 failed,
  336 passed, 3 xfailed — **te same 4 failują na main `1f60c06` bez zmiany** (worktree z `origin/main`, 4 failed / 239 passed):
  `test_filtr_ner_nadal_odrzuca_nie_osoby[Komornik Sądowy'-FIRMA]`, `test_nazwisko_z_ulicy_w_pipeline[…ul. Kowalskiego 7…]`,
  `TestFirmaBounds::test_osoba_i_fragment_formy`, `test_forma_prawna_nie_ginie_przy_przywroc[…S.A.]`. Nie należą do tego Tasku —
  zgłoszone w BOARD (`LYNX-ENGINE-BACKLOG`).

## Pomiar (pomocnik CC; `/preview` w procesie z `git archive`, pusty profil; lokalnie `%TEMP%\lynx_cc_review\osoba_not_person\`)
Odtworzenie: kopia `tasks/LYNX-FIRMA-FILTER-FIX/measure/measure_run.py` + zbiór `Pliki testowe/*.txt` (czytany bajtowo);
`.venv\Scripts\python.exe measure_run.py <SHA> przed|po .`, potem `cmp.py .`, `lvl3.py .`.

| zbiór | dok. | OSOBA przed | OSOBA po | zniknęły FP | zniknęły prawdziwe | nowe |
|---|---|---|---|---|---|---|
| dataset_clean (gold) | 300 | 528 | 528 | 0 | 0 | 0 |
| testy Mobile | 30 | 167 | 167 | 0 | 0 | 0 |
| obrazy benchmarku | 48 | 100 | 89 | 11 | 0 | 0 |
| sweep FIRMA | 160 | 40 | 40 | 0 | 0 | 0 |
| zdania celowane | 12 | 3 | 3 | 0 | 0 | 0 |
| Pliki testowe | 7 | 32 | 32 | 0 | 0 | 0 |

Zniknięte (wszystkie FP wg ground truth): „Data” ×8, „Wydziatu” ×2 (OCR), „wystawienla” ×1 (OCR, mała litera). Inne typy tokenów
identyczne. Osoby gold dataset_clean: 417 zakrytych przed i po, 0 jawnych. Przypadek kompromisu 2a (samotne słowo z OSOBA_DENYLIST
będące osobą): 0.
`doc_lvl3_faktura_zlecenie.txt`: w procesie „zamieszkaly” jawne już PRZED (nie odtwarza się), 4 osoby zakryte przed i po. Na żywym
silniku 8765 (main) „zamieszkaly” → OSOBA odtwarzane przez CC (plik CRLF; także sama linia LF z wcięciem) — różnica środowiska
nierozpoznana; reguła małej litery odrzuca każdą jednowyrazową OSOBA „zamieszkaly” niezależnie od kontekstu (test celowany).
Kandydat na kolejny FP poza zakresem: „FAKTURAvVAT” (OCR) jako OSOBA przed i po — `LYNX-ENGINE-BACKLOG`.

## r2 — korekta po Codex r3/r4 (`b5b6547`, `bccd204`)
Białe listy odrzucały prawdziwe nazwiska spoza `_PERSON_FORMS` („Czerwiec”, „Styczeń”, „Bill” → jawne). Korekta w
`osoba_not_person.py`: biała lista nie odrzuca słowa, które Morfeusz zna jako imię/nazwisko (`_morfeusz_name`); bez Morfeusza białe
listy nieaktywne (OSOBA_DENYLIST i mała litera działają dalej). Z 247 słów białych list spoza `_PERSON_FORMS` i denylisty zostaje
odrzucanych 194 (m.in. faktura, umowa, zamieszkały, adresem, październik, gdańsk); 53 z kwalifikatorem imię/nazwisko już nie są odrzucane
(m.in. czerwiec, styczeń, bill, wtorek, warszawa). Sprawdzenie 194 odrzucanych ze słownikiem Mobile `surnames_extended.json`
(311 387 form): jedyne trafienie „gdańsku” (forma z listy miast; Mobile też je pomija).
Reproduktory Codexa na kodzie r2: `repro_polish_r4.py` → Czerwiec, Styczeń kept; `repro_bill_r3.py` → Bill kept.
Testy: `tests/test_osoba_not_person.py` 25 passed (nowe: Czerwiec/Styczeń/Bill zostają; bez Morfeusza biała lista nieaktywna, denylista działa).
Pomiar r1 bez zmian co do usuniętych FP (Data — denylista, Wydziatu — denylista, wystawienla — mała litera; żadne nie zależy od białych list).
Rozmiar ponad 150 linii — zgoda Pawła 21.10.

Bramka r2 (stdout dosłownie, `gate_r2.txt`):
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: 62c72a2387d58dc405113e37b3325d82479b9b23
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - RATIO: 152/21 = 7.2:1 (threshold 5:1)
  - TOTAL_LINES: 173 lines changed (threshold 150)
```
