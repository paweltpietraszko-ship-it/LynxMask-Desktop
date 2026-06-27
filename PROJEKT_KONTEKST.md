# LynxMask Desktop — Kontekst projektu dla Claude

## Czym jest projekt

Pseudonimizacja dokumentów OCR (LynxMask Desktop).
Backend: Python FastAPI (`backend/`), Frontend: Tauri + React (`frontend/`).
Port 8765. Repo: paweltpietraszko-ship-it/LynxMask-Desktop (prywatne).

---

## Stan aktualny — 2026-06-27

### Wyniki benchmarku (ostatni stabilny run 2026-06-26)
- CLR ≤ 4.3%, Recall 89.7%, F1 78.9%
- Pipeline: `pipeline_new.py` aktywny (`USE_NEW_PIPELINE=True` w `pipeline.py`)

### Testy
- Środowisko zdalne (brak cffi/pyo3): `85 passed, 56 skipped, 1 xfailed`
- Lokalnie (pełne): `157 passed, 2 skipped, 1 xfailed, 0 failed`

---

## Wersje kluczowych plików (stan 2026-06-27)

| Plik | Wersja |
|---|---|
| `pipeline.py` | v1.24 |
| `pipeline_new.py` | v1.0 |
| `pseudominizer_api.py` | v1.33+ (seed_profile podpięty) |
| `anonymizer.py` | v4.20+ |
| `ner_layer.py` | v1.18 |
| `ner_blocklist.py` | v1.7 (57K wpisów + "guard/guardu/guardzie") |
| `output_guard.py` | v4.5 |
| `layers/identity.py` | v1.5 |
| `layers/address.py` | v1.9 |
| `layers/contact.py` | v1.4 |
| `layers/financial.py` | v1.3 |
| `layers/legal.py` | v1.1 |
| `layers/credentials.py` | v1.0 |
| `layers/institution.py` | v1.0 |
| `layers/ocr_normalizer.py` | v2.4 |
| `layers/trie_layer.py` | v1.0 |
| `layers/ner_adapter.py` | v1.7 |
| `anonymizer_init.py` | v2.0 |
| `verbal_amounts.py` | v1.4 |
| `smoke_test.py` | v1.1 |
| `seed_profile.py` | v1.0 (NOWY) |
| `credential_patterns.json` | 29 wzorców |
| `medical_facilities.json` | NOWY (~120 form) |

---

## Architektura pipeline (14 warstw, pipeline_new.py)

```
L0b: trie_layer      ← słownik biura (imiona/nazwiska z seed)
L1:  ocr_normalizer  ← normalizacja OCR
L2:  identity        ← PESEL, NIP, REGON, dowód, paszport
L3:  credentials     ← PWZ, licencje, sygnatury, KRS, tablice, KW
L4:  legal           ← sygnatury sądowe, komornicze
L5:  financial       ← IBAN PL + zagraniczne
L6:  contact         ← email, telefon
L7:  address         ← ulice, kody pocztowe, miasta
L8:  amount          ← kwoty PLN
L9:  verbal_amount   ← kwoty słowne
L10: institution     ← ZUS, sądy, urzędy
L11: numeric         ← numery klienta/faktury/umowy
L12: NER (SpaCy)     ← osoby, firmy
L13: fallback        ← 8+ cyfr które przeżyły
L14: validation      ← spójność
```

Następnie: `_apply_guard()` → Output Guard v4.5

---

## Pliki danych (w pakiecie, nie w trie)

| Plik | Zawartość | Użycie |
|---|---|---|
| `names_inflected.json` | 199 imion + odmiany | seed_profile → trie OSOBA |
| `surnames_top1000.json` | 1000 nazwisk + odmiany | seed_profile → trie OSOBA |
| `cities.json` | 31K miejscowości | ner_blocklist (FP ochrona) |
| `cities_forms.json` | 179K form odmian | address layer SIMC |
| `street_names.json` | 11K ulic + odmiany | ner_blocklist (FP ochrona) |
| `medical_facilities.json` | ~120 form placówek med. | ner_blocklist (FP ochrona) |

---

## Output Guard v4.5

**HIGH** (1 hit = blokada całości):
- PESEL `\b\d{10,11}\b` — tolerancja ±1 cyfra OCR
- NIP — 3 formaty + bez separatora
- IBAN — broad (CC+DD+11+ znaków), agnostyczny wobec formatu
- IBAN_OCR — PL + 25-26 cyfr z dowolnymi białymi znakami
- DOWÓD — 3 litery + 6 cyfr (± spacja OCR)
- PASZPORT — 2 litery + 7 cyfr (± spacja OCR)
- EMAIL

**MEDIUM** (suma wag ≥ 3 = blokada):
- REGON waga 1
- TELEFON waga 1

**Zasada GUARD-BROAD:** Guard jest szerszy niż pipeline (prostszy wzorzec, wyższy recall, akceptuje FP).

---

## Bezpieczeństwo — stan

| Element | Status |
|---|---|
| `AUDIT_MODE` | `False` — zero zapisu PII w logach |
| Logi konsola | tylko INFO, bez FileHandler — PII nie trafia na dysk |
| `audit_log.py` | pole "original" usunięte z rekordów (CRIT-2) |
| Guard fail-closed | błąd guarda = blokada, nie przepuszczenie |
| NER fail-closed | crash NER = `force_block=True` |
| Pipeline fail-closed | wyjątek = `(text, {}, True)` |
| `/archive` blob | 403 gdy `guard_blocked=True` |
| Token injection | 422 przy `TOKEN_RE` w wejściu (AUD-01) |

---

## Otwarte — do zrobienia

### Funkcjonalne
- **GuardAllowlist (słownik B)** — gdy Guard ostrzega, użytkownik może powiedzieć "to nie PII, nie alarmuj". Mobile ma UX z "Maskuj"/"Nie maskuj". Desktop nie ma.
- **Ekran zarządzania słownikiem** — lista dodanych encji + usuń. Brak UI.
- **Eksport .lynxdict** — sync Mobile↔Desktop. Nie zrobiony.
- **Import .lynxdict** — Desktop nie ma, Mobile ma.
- **Klucz odzyskiwania** — 24 znaki w 4 grupach (`ABCD12-EFGH34-IJKL56-MNOP78`). Nie zaimplementowany.
- **Zmiana hasła bez usuwania biblioteki encji** — Mobile to ma, Desktop nie.
- **Usunięcie wszystkich danych (reset profilu)** — w karcie Zabezpieczenia. Brak.
- **Redakcja wizualna obrazu** — blur twarzy, prostokąty na pikselach. Tylko Mobile. Wymaga osobnej sesji.

### Znane FN (silnik)
- **"Przychodnia Rejonowa Zdrowie" niezamaskowana** — SpaCy rozbija wielowyrazową encję firmy.
- **"STOCZNIA GDAŃSKA SERWIS Sp." niezamaskowana** — j.w.

### Bezpieczeństwo (przed dystrybucją)
- **AUD-13/14 PBKDF2** — zmiana iteracji/soli unieważnia mapy.enc, wymaga planu migracji.
- **Audyt obejść logowania** — weryfikacja że każda komenda Rust weryfikuje token.
- **CSP unsafe-inline** (AUD-09) — zawęzić.
- **fs scope Tauri** (AUD-10) — zawęzić.

### Techniczne
- Logi wyłączyć całkowicie (`logging.disable`) w wersji Release build.
- `pynvml` deprecated → `nvidia-ml-py`.

---

## Dokumenty testowe

```
backend/test_docs/
  doc_lvl2_pismo_komornicze.txt              ← test real-world (11 bugów naprawionych)
  doc_lvl3_faktura_zlecenie.txt              ← test real-world
  doc_test_nowe_encje.txt                    ← test nowych wzorców (sygnatury, KRS, tablice, KW)
  doc_test_guard.txt                         ← test Output Guard (wszystkie HIGH + MEDIUM + pułapki)
  doc_stresstest_silnik_guard_lvl0_3.txt     ← stress test LVL0-3 (OCR od idealnego do telefonu), 80 encji (PSE-2026-1145)
```

---

## Uwagi praktyczne

- `backend/api_token.txt` — generowany przy starcie, nie w repo
- `backend/anon_profiles/` — dane użytkownika, nie w repo
- `backend/anon_profiles/pseudominizer/__seed_version__` — klucz seedowania w profilu
- Seed działa raz (sprawdza wersję), kolejne starty pomijają
- Start backendu: `cd backend && python pseudominizer_api.py`
- Testy: `cd backend && python -m pytest tests/ -q`
- Zatrzymanie: `backend/zatrzymaj.vbs`

---

## Zasady nienaruszalne (z MASTER)

- `TOKEN_RE` używa `(?!\d)`, NIE `\b` — zapobiega token-w-tokenie
- Globalnego sklejania spacji NIE wprowadzać (zniszczyło Mobile)
- UI mówi "Zamaskuj/Przywróć" — kod backend zostaje z pseudominizer_*
- AUD-13/14 PBKDF2 — nie ruszać bez planu migracji
- Rzeczy wspólne z Mobile (format tokenu, sync, taksonomia) — decyduje Paweł
