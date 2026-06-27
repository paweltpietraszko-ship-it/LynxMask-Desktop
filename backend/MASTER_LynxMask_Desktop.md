# MASTER — LynxMask Desktop
**Funkcja:** jedno źródło prawdy dla platformy Desktop (Python / FastAPI / Tauri). Z tego pliku wycinasz pojedynczy potok naraz dla Claude Code.
**Data konsolidacji:** 20.06.2026
**Źródła:** REJESTR_PROJEKTU_13_06 (najnowszy, bazowy), MAPA_ARCHITEKTURY_Desktop_v2_0 (09.06 — szkielet OK, wersje martwe).
**Uwaga produktowa:** UI mówi „Zamaskuj/Przywróć/maskowanie". W kodzie backendu stare nazwy zostają (pseudominizer_api.py itd.).

## Zasada nadrzędna
Nie pisz od nowa — odznaczaj DONE, dopisuj nowe. Ground truth z git/Claude Code wygrywa nad dokumentem. Przed startem potoku zapytaj Claude Code o aktualny nagłówek dotykanego pliku (mapa 09.06 jest za realnym repo).

---

## DLA INSTANCJI DOCELOWEJ — PRZECZYTAJ NAJPIERW

**Ten master jest źródłem STANU, nie kolejności.** Numeracja sekcji to porządek dokumentu, nie ranking. Przeustaw potoki pod to, co ważne — nie idź ślepo po kolei. Aktywna kolejność dziś: NER-fix (w toku) → UI-2 → reszta.

**Decyzje należące do Pawła — NIE podejmuj sam, dopytaj:** IBAN zagraniczny w Guard (generyczny wzorzec vs akceptacja luki — BUG-4), logo sidebara (wymaga inspiracji wizualnej), oraz wspólne z Mobile poniżej.

**Rzeczy współdzielone z Mobile (jeden właściciel = Paweł):** format tokenu + spójność TOKEN_RE, samouczenie, sync .lynxdict, taksonomia 9 typów — sekcja 4. Nie zmieniać jednostronnie.

**Zasady nienaruszalne / miny:** sekcja 8. **Potwierdzone działające** (nie wpisywać jako bug): sekcja 6.

### Jak pisać polecenia do Claude Code
Jedno zadanie na raz. Format:
```
Przeczytaj plik: <pełna ścieżka do pliku, np. ...\pseudominizer\pipeline.py>
Znajdź fragment <X>. Pokaż z numerami linii.
Nic nie zmieniaj. Czekaj na dalsze instrukcje.
```
Po diagnozie pojedyncza zmiana → test → dopiero commit. Gdy Claude Code idzie za daleko: „Zatrzymaj się. Zrób tylko to, co napisałem." Kompletne pliki, nie fragmenty; ta sama nazwa = nadpisanie; czytaj realny kod przed pisaniem; nie dotykaj plików skończonych.

### Benchmark
Pliki: generator.py (v1.2) + benchmark.py (v1.2), uruchamiane przez run_benchmark.bat (per REJESTR). ⚠️ Dokładnej komendy uruchomienia i ścieżki nie mam udokumentowanej verbatim — **potwierdź u Claude Code przed pierwszym runem.** (Uwaga: „benchmark fresh" z losowym datasetem to mechanizm Mobile; Desktop używa generator.py + benchmark.py.)

---

## 1. AKTYWNE BUGI

### KRYTYCZNE
— brak —

### WYSOKIE
— brak —

### ŚREDNIE
- **BUG-12-PSE-REGISTRY** — ścieżka względna `./pse_registry.json` — może nie działać gdy CWD ≠ backend/.

### NISKIE / OBS
- OBS-SYNTAX-WARNING — `\s` w spacy_ner.py ~28, Python 3.14 SyntaxError (działa na 3.12).
- OBS-PERMISSION-DENIED — hardware_profile.json czasem Permission Denied przy zapisie.

### NAPRAWIONE (chronologicznie, od najnowszych)
- ~~BUG-NIP-DOUBLE-SEP~~ — NIP z separatorem " -" (identity.py v1.5, guard v4.4)
- ~~IBAN-OCR-TOLERANCE~~ — IBAN_OCR {25}→{24,25}, PESEL \d{10,11} (guard v4.4)
- ~~BUG-IBAN-OCR~~ — PL IBAN z spacjami/enterem między cyframi (guard v4.3, pipeline v1.24)
- ~~BUG-11-FAKTURA~~ — 11 bugów z dokumentów realnych (commit 28cff45, 2026-06-27)
- ~~BUG-NER-COURTS~~ — sądy z miastem klasyfikowane jako FIRMA (ner_layer v1.16, _COURT_PREFIX_RE)
- ~~BUG-PROFIL-PIPELINE~~ — anon_map nie trafiał do pipeline_new (pipeline.py v1.23)
- ~~BUG-NER-02~~ — formuły decyzyjne jako OSOBA/FIRMA (ner_blocklist v1.2-1.6)
- ~~BUG-10~~ — handleAddEntity 401 + re-preview po dodaniu encji (Pseudonimizuj.tsx)
- ~~BUG-3~~ — token injection — 422 przy TOKEN_RE w wejściu (AUD-01, pseudominizer_api.py)
- ~~BUG-9~~ — zamknięty przez AUD-01 (wejście z tokenami odrzucane)
- ~~BUG-NUMER-RECALL~~ — NUMER/TELEFON/EMAIL recall (contact v1.2-1.4, identity v1.2-1.5)
- ~~BUG-NER-FP-GRANICE~~ — FIRMA/OSOBA za agresywne (ner_layer v1.14+)
- ~~BUG-2~~ — firma w cudzysłowie rozbijana (ner_layer v1.13)
- ~~BUG-4~~ — IBAN zagraniczne (financial v1.1, guard v3.9-4.0)
- ~~BUG-7~~ — check_blacklist_context() wywoływana w guard_output_with_map (guard v3.2+)
- ~~BUG-NEW-3~~ — /archive 403 gdy guard_blocked (db_store v1.1)
- ~~BUG-NEW-4~~ — walidacja profilu biura odrzuca słowa pospolite (pseudominizer_api)
- ~~BUG-1~~ — deduplikacja OSOBA form fleksyjnych (_person_stem, ner_layer v1.12)

---

## 2. POTOKI (kolejność)

**Aktywne**
- **NER-fix — W TOKU.** Cel: NUMER>80%, TELEFON>60%, EMAIL>80%, Critical Leakage<10%. Pliki: anonymizer.py, anonymizer_init.py, ner_layer.py, pipeline.py, spacy_ner.py.
- **UI-2 — CZEKA na NER-fix.** Pliki: pseudominizer_api.py, Pseudonimizuj.tsx, MainLayout.tsx. Zakres: BUG-10, etykieta „Odmaskuj" vs „Przywróć", logo sidebar (wymaga inspiracji właściciela).

**Po NER-fix**
- **Testy** — pokrycie pod to co mierzy benchmark. BUG-TEST-1..4 + nowe testy PESEL/NIP/IBAN/TELEFON.
- **Słownik** — pętla benchmark→słownik biurowy. Nowe pliki: llm_classifier.py (Claude API, batch 20), review.html (czysty HTML/JS), office_dict_updater.py. Zależy od benchmark.py v1.2 stabilnego.
- **Bezpieczeństwo** — klucz odzyskiwania (24-znak.), audyt obejść logowania (każda komenda Rust weryfikuje token), czerwony przycisk „Usuń wszystkie dane", BUG-3/2/4/7, BUG-NEW-3/4, AUD-05 (PII w logu — AUDIT_MODE=False przed dystrybucją), AUD-06 (race w add_entity), AUD-07 (walidacja PSE w Rust), AUD-09 (CSP unsafe-inline), AUD-10 (zawęzić fs scope), AUD-13/14 (PBKDF2 — UWAGA: unieważnia mapy.enc, wymaga migracji), AUD-12..18 niskie.
  - **Klucz odzyskiwania — uzgodniony kształt:** 24 znaki w 4 grupach po 6, format `ABCD12-EFGH34-IJKL56-MNOP78`. Pokazany RAZ przy onboardingu z instrukcją wydruku/zapisu. Przechowywany lokalnie, zaszyfrowany osobnym kluczem. Zapomniane hasło → wpisz kod → ustaw nowe hasło, dokumenty zostają. Zgubiony kod → brak odzyskania (RODO, zero backdoora).
  - **Audyt obejść logowania — wektory do sprawdzenia:** pominięcie LockScreen przez bezpośrednie wywołanie komendy Rust bez tokenu (każda komenda musi weryfikować token), podmiana api_token.txt na własny, restart serwera z zewnątrz gdy apka działa, dostęp do plików .enc gdy apka zamknięta (to NIE luka — szyfrowanie broni). Zadanie = diagnoza i raport, nie naprawa z góry.

**Późniejsze:** Updater (sprawdzanie wersji pakietów), Anonimizacja-wizualna (blur twarzy OpenCV + tablice + EXIF/metadane), Fine-tuning (nie przed stabilizacją), Express-Mode (RAM, bez logowania/mapy), Instalator+Dokumentacja (na końcu).

---

## 3. BACKLOG STRATEGICZNY

| Temat | Priorytet |
|---|---|
| PBKDF2 migracja (AUD-13/14 — unieważnia mapy.enc) | Wysoki (przed dystrybucją) |
| Zmiana nazwy katalogu pseudominizer\ (przegląd hardkodowanych ścieżek) | Średni |
| Mapa architektury — aktualizacja po Potoku Krytyczne | Średni |
| Próg OCR reject 70%→80% (BUG-NER-04) | Średni |
| Synchronizacja Mobile↔Desktop (dokumenty i mapy) | Niski |
| pynvml deprecated → nvidia-ml-py | Niski |
| Potok Metryczki — przenieść [FIX-XXX] z kodu do osobnych .md (po zamknięciu wszystkich aktywnych potoków) | Niski |
| Podpisy odręczne (własny model, nie przed fine-tuningiem) | Backlog |

---

## 4. WSPÓLNE Z MOBILE — JEDEN WŁAŚCICIEL (Paweł), ponad podziałem platform

Te rzeczy NIE mogą być zmieniane jednostronnie przez instancję mobile ani desktop — muszą być uzgodnione po obu stronach.

1. **Format tokenu + spójność TOKEN_RE.** Desktop _TOKEN_RE (pseudominizer_api.py) i Mobile TOKEN_RE (NameEngine.kt) muszą być identyczne. Rozjazd udokumentowany jako AUD-M08 (mobile). **DECYZJA OTWARTA — rekomendacja: 6-znakowy heks identyczny po obu stronach.** Powiązane z BUG-3 (anti-injection). Blokuje Mobile Potok 7.
2. **Samouczenie — mechanizm odkrywania tokenu.** Użytkownik koryguje błędne maskowanie → zapis do słownika profilu → następny dokument silnik już wie. Bez tego samouczenie nie działa. Desktop: BUG-10 (401 przy zapisie) + BUG-PROFIL-PIPELINE (pipeline_new.py nie dostaje anon_map z profilu biura). Mobile: BUG-DICT engine + BUG-GUARD. **Musi działać po OBU stronach, zanim samouczenie ma sens.**
3. **Sync słownika .lynxdict** (desktop→mobile, JSON addytywny). Trigger: po 10 nowych ręcznie oznaczonych encjach. Mobile blokuje na BUG-DICT engine.
4. **Taksonomia 9 typów** — Mobile Potok 7 zbliży się do desktopowej. Po nim rozważyć ponowną synchronizację TOKEN_RE.
5. **Architektura słowników — wzorzec z Mobile, Desktop przejmuje (21.06.2026).** Mobile zaimplementowało dwa osobne słowniki z gotowym API. Desktop NIE wymyśla własnego rozwiązania — przejmuje ten sam wzorzec:
   - **UserDictionary (słownik A):** wartości które silnik MA maskować. Klucz: `(wartość, typ_tokenu)`. Wpisy permanentne.
   - **GuardAllowlist (słownik B):** wartości które Guard MA pomijać po decyzji użytkownika "to nie PII". Klucz: `(wartość, ruleType)`. Wpisy permanentne.
   - **UX przy YELLOW hicie Guard:** dwa przyciski — "Maskuj" (→ UserDictionary) i "Nie maskuj" (→ GuardAllowlist). Brak opcji jednorazowego ignorowania.
   - **Ekran zarządzania słownikami:** modal z dwiema zakładkami, lista wpisów + usuń. **Układ UI musi być identyczny z Mobile** — Paweł chce spójnego UX między platformami. Implementować gdy Mobile skończy ekran zarządzania (sekcja 15 MASTER Mobile).
   - **Format wymiany .lynxdict:** prosty JSON, proste typy. Szyfrowanie-at-rest po każdej stronie osobno (nie mieszać z formatem wymiany).

---

## 5. WERSJE PLIKÓW — aktualne 2026-06-27

| Plik | Wersja |
|---|---|
| `pipeline.py` | v1.24 |
| `pipeline_new.py` | v1.0 |
| `pseudominizer_api.py` | v1.33+ |
| `anonymizer.py` | v4.20+ |
| `ner_layer.py` | v1.18 |
| `ner_blocklist.py` | v1.6 (57K wpisów) |
| `output_guard.py` | v4.4 |
| `verbal_amounts.py` | v1.4 |
| `smoke_test.py` | v1.1 |
| `seed_profile.py` | v1.0 (NOWY) |
| `layers/identity.py` | v1.5 |
| `layers/address.py` | v1.9 |
| `layers/contact.py` | v1.4 |
| `layers/financial.py` | v1.2 |
| `layers/legal.py` | v1.1 |
| `layers/credentials.py` | v1.0 |
| `layers/institution.py` | v1.0 |
| `layers/ocr_normalizer.py` | v2.4 |
| `layers/trie_layer.py` | v1.0 |
| `credential_patterns.json` | 29 wzorców |
| `spacy_ner.py` | v1.7 |
| `ocr_engine.py` | v1.4.5 |
| `anonymizer_init.py` | v1.9 |
| `document_processor.py` | v1.2 |
| `main.rs` | v1.6 |
| `MainLayout.tsx` | v2.2 |
| `Pseudonimizuj.tsx` | v1.7+ (handleAddEntity + re-preview) |
| `Depseudonimizuj.tsx` | v1.8 |
| `LockScreen.tsx` | v1.4 |
| `App.tsx` | v1.6 |

---

## 6. ODŁOŻONE / DO WERYFIKACJI

- **POTWIERDZONE DZIAŁAJĄCE (nie wpisywać jako bug):** depseudonimizacja / Przywróć działa poprawnie (potwierdzone 20.06). Reverse_map jest wypełniany. Gdyby ze starszych zapisów wypłynął „BUG-REVERSE-MAP" — jest nieaktualny.

- SPEC_SLOWNIK_WORKFLOW_v1.0.md — należy do Desktop (Potok Słownik), zgłoszony jako pomyłka tylko w kontekście kolejki Mobile.
- isMinifyEnabled / obfuskacja — analogicznie do mobile, osobna sesja po stabilizacji.

---

## 7. KIERUNEK WIZUALNY UI (uzgodniony, sesja 07.06 — Potok-UL)

Wzorzec wizualny: shadcn/ui dark (paleta zinc). Decyzje właściciela:
- **Tło zostaje ciemne** (#09090b zinc-950). Surface #18181b (zinc-900), sidebar ciemniejszy #0c0c0f, border #27272a (zinc-800).
- **Niebieski (#3b82f6) tylko dla elementów aktywnych/interaktywnych** — nie jako dekoracja.
- **Cztery poziomy hierarchii tekstu.** Czcionka wg shadcn: w wersji theme.ts v2.0 było 14px baza / 12px mono / 11px etykiety (koniec z 8px uppercase wszędzie). ⚠️ Aktualny theme.ts to v2.7 — **zweryfikować realne rozmiary** (późniejsze notatki sugerują podbicie do 15–16px). Zasada „bez czystej bieli, niebieski tylko aktywne" jest trwała.
- **Wejście tekstu w Pseudonimizuj: dwie kolumny** — plik i wklejony tekst widoczne jednocześnie, plik ma pierwszeństwo (użytkownik biurowy częściej kopiuje tekst niż zapisuje plik).
- **Onboarding** — robiony od razu, adaptowany z wersji Mobile, treść do zmiany później. Zawiera kartę OCR.

---

## 8. ZASADY NIENARUSZALNE / MINY (nie cofać bez wyraźnego uzasadnienia)

- **TOKEN_RE używa `(?!\d)`, NIE `\b`** — zapobiega bugowi token-w-tokenie. Spójne z Mobile (sekcja 18 mobile mastera). Dotyczy decyzji o formacie tokenu (wspólne, sekcja 4).
- **Globalnego sklejania spacji NIE wprowadzać** jako „naprawy OCR" — na Mobile próbowano (MIDWORD_SPACE_RE) i zniszczyło tekst. Naprawy punktowe, nie globalne.
- **Terminologia UI:** „Zamaskuj/Przywróć/maskowanie" w UI; stare nazwy (pipeline.py, pseudominizer_api.py) w kodzie zostają.
- **Zasady pracy z Claude Code:** kompletne pliki (nigdy fragmenty), ta sama nazwa = nadpisanie, czytaj realny kod przed pisaniem, nie dotykaj plików skończonych.
- **AUD-13/14 PBKDF2:** zmiana iteracji/soli unieważnia istniejące mapy.enc — wymaga migracji użytkowników. Nie ruszać bez planu migracji.
