# CC — ocena merytoryczna briefu LYNX-T01-NER-PREFIX (r1)

Brief na `851bc26607bd8615afac7cc94ae6df8e31f8c91d` (precheck Codexa: PASS PREIMPLEMENTATION).
Werdykt CC: **PRZYJĘTY** — z dwoma doprecyzowaniami wykonania w obecnym TASK_SCOPE. Jeśli Architekt
lub Codex się z nimi nie zgadza, proszę o sygnał przed implementacją.

## Doprecyzowania (jak CC wykona brief)

### D1. Główne źródło potwierdzenia osoby = kwalifikator Morfeusza, słowniki jako uzupełnienie

Brief: „istniejące słowniki / kwalifikator Morfeusza". Słowniki Desktop są małe (`names_inflected.json`
199 imion, `surnames_top1000.json` 1000 nazwisk). Wynik prototypu z `FINDING_2026-10_MOBILE_PORT.md`
(OSOBA 85→105/106) jest zawyżony, bo benchmark generuje osoby z tych samych list (raport sam to zaznacza).
Na realnych dokumentach rzadkie nazwisko spoza listy nadal zginęłoby w filtrze. Morfeusz (już zależność,
kwalifikatory `imię`/`nazwisko`, `MOBILE_PORT` §5a) jest ogólny. Kolejność: słownik → Morfeusz → dopiero
wtedy filtr odrzucający.

### D2. Dowód PASS na danych rozłącznych z listami słownika

Oprócz reproduktorów i benchmarku CC dołączy pomiar na zdaniach z nazwiskami **spoza**
`surnames_top1000.json` (np. z `surnames_extended.json` aplikacji Mobile), żeby PASS nie opierał się
na danych, z których zbudowano słownik. Skrypt pomiarowy w `audyt/` (poza produktem; nie zmienia TASK_SCOPE).

### D3. Morfeusz niedostępny (tryb degraded)

Gdy Morfeusz się nie załaduje, potwierdzenie działa tylko na słownikach, a encja OSOBA wykryta przez spaCy,
której nie da się rozstrzygnąć, **nie jest odrzucana przez filtr prefiksu** (wolimy FP niż wyciek — S1/S3).
Istniejący test trybu degraded (`test_anonymizer_adversarial.py:480`) pozostaje zielony.

## Przyjęte bez uwag

Owner (`ner_layer._filter_institutions`, `ner_blocklist.py`), zakres plików, ochrona adresów (warstwa adresu
zajmuje span przed NER — `is_occupied`), instytucji i słów pospolitych, OUT_OF_SCOPE, kryteria PASS.
Kolejność z `PLAN_2026-10.md` (T02 → T03 → T01) — CC się zgadza; T01 może jednak ruszyć, jeśli T02/T03
czekają na korektę.
