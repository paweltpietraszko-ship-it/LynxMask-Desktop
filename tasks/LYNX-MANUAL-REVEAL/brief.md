# LYNX-MANUAL-REVEAL — brief v5 (prosty wariant CC, do Codex BRIEF_ONLY)

Data: 2026-10-21. **STATUS: READY_FOR_CODEX — BRIEF_ONLY, NIE WDRAŻAĆ JESZCZE.** Nowy kontrakt po [recenzji CC v4, commit `2b5a60f`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/2b5a60f587c043fe8fe6d85ba62d1f932b1cdad2/tasks/LYNX-MANUAL-REVEAL/cc_review.md). OWNER preferuje prostą wersję podobną do Mobile i **wprost wymaga powrotu v5 do Codexa**. Historyczne PASS Codexa dla v4 (r3 `6e89ce2`) NIE obowiązuje dla v5. Brak zgody na kod/merge/przekroczenie budżetu.

## Zachowanie użytkownika (jedna funkcja)

Po pseudonimizacji i normalnej, pomyślnej kontroli Guarda użytkownik na ekranie **Zamaskuj** może kliknąć konkretne wystąpienie zamaskowanego tokenu i wybrać **„Odkryj tutaj”**. Tekst pomocniczy: „Jeśli LynxMask zakrył coś niepotrzebnie, możesz odkryć wybrane miejsce. Odkryta wartość znajdzie się także w kopiowanym i zapisanym tekście.” Ponowne kliknięcie/„Cofnij odkrycie” przywraca token. Bez alertu przy każdym poprawnym maskowaniu i bez słownika homonimów.

- Odkrywanie **tylko po niezablokowanym `/preview` i zakończonej obsłudze wymaganych ostrzeżeń** na istniejących zasadach. Nie obchodzimy HIGH, S3 ani `guardBlocked`; błędne/zablokowane dokumenty nie otrzymują tej funkcji. Nie dodawać nowych dialogów „obsługi Guarda” ani automatycznego odblokowania przy zwykłym kliknięciu.
- Zgoda użytkownika dotyczy tylko bieżącego dokumentu i **dokładnie jednego wystąpienia**, nie wszystkich wystąpień tego samego identyfikatora. Stan odkryć utrzymuje **wyłącznie React UI**, nie serwer. „Nowy dokument” i ponowne `/preview` (także po „Dodaj i zakryj”) czyszczą odkrycia.
- **Pełny token, pełna wartość:** np. `OSOBA_001 → Anna Malina` może ujawnić całe `Anna Malina`, ale nie można odsłaniać tylko fragmentu większego tokenu. UI powinno jednoznacznie pokazać, że chodzi o **całą wartość**, zanim użytkownik ją odkryje. Brak wartości w mapie → nie odkrywać, wyświetlić krótką instrukcję.
- **Jedna kanoniczna wartość tekstu po korekcie:** wyświetlenie, „Kopiuj tekst” i archiwizacja `anonymized_preview` używają tego samego wyliczonego `finalText`, z zachowaniem nagłówka PSE, spacji, interpunkcji i pozostałych tokenów. Zapis do archiwum nadal używa dotychczasowego szyfrowania po stronie klienta; pierwotna mapa sesji nie jest modyfikowana.
- **Guard pracuje raz przy `/preview`**, przed ręcznym odkryciem. Ręczne „Odkryj” to **świadoma edycja wyniku przez użytkownika**; nie uruchamiać ponownie Guarda, nie dopisywać globalnego wyjątku `MAP_LEAK`, nie przebudowywać/podmieniać wyniku przez pipeline. To **jawny kompromis**: Guard nie ocenia ryzyka wartości, którą człowiek sam postanowił odkryć. Nie przedstawiać skorygowanego tekstu jako niezależnie ponownie zweryfikowanego.
- Nowe `ERROR` i bloki produktu nie są potrzebne. Gdy nie da się wskazać całego tokenu/znaleźć mapy, przycisk jest nieaktywny z prostym wyjaśnieniem; użytkownik nadal może korzystać z poprzedniego wyniku.

## Niezmienny test krytyczny

Przykład syntetyczny:
```
01. OSOBA_033 zakwitła rano na rabacie.
02. Pani OSOBA_033 odebrała dokument.
```
Mapa `OSOBA_033 → Róża`. Po wskazaniu **pierwszego** wystąpienia wynik jest dokładnie:
```
01. Róża zakwitła rano na rabacie.
02. Pani OSOBA_033 odebrała dokument.
```
Odkrycie drugiego wystąpienia to niezależna czynność. Cofnięcie pierwszego nie zmienia drugiego. **Niedozwolone globalne `replaceAll`** i trwałe wyjątki w `GuardAllowlist`, profilu lub `.lynxdict`.

## Techniczny szew i TASK_SCOPE

**Jeden owner:** `frontend/src/screens/Pseudonimizuj.tsx`. Obecny `HighlightedText` rozpoznaje token i jego `m.index` w `anonymized_preview`; zamiast samego numeru tokenu identyfikować **wystąpienie** stabilnym indeksem/pozycją w bazowym tekście. Zachować bazowy tekst jako źródło, stan odkryć jako zbiór pozycji; wyliczyć `finalText` z bazowego tekstu i mapy tokenów, nie robić kolejnych zamian na edytowanym tekście (przesunięcia offsetów). `selectionchange` domaskowania nie może przypadkowo odkrywać tokenów; element tokenu może mieć niezależny click i akcję „Odkryj tutaj”. Akcja „Dodaj i zakryj” działa jak dotąd. Zachować dostępność mysz/klawiatura.

**Tylko:** `frontend/src/screens/Pseudonimizuj.tsx` oraz najmniejsze celowane testy UI / funkcji przeliczenia tekstu. Domyślnie bez nowego modułu produkcyjnego. **OUT_OF_SCOPE:** `backend/pseudominizer_api.py`, `backend/output_guard.py`, `pipeline*`, `ner_layer`, nowe API, stan serwera, ponowne uruchomienie Guarda, projekcje mapy, analiza znaczenia, zmiany formatu mapy/archiwum, globalne słowniki, HerBERT, OSOBA-REDESIGN. S3 i obecne blokady początkowego wyniku nadal obowiązują. Jeśli CC wykryje rzeczywistą zależność wymagającą rozszerzenia zakresu, ma zgłosić ją **przed kodem**, nie dopisywać nowego subsystemu.

TASK_SCOPE:
- frontend/src/screens/Pseudonimizuj.tsx
- frontend/src/screens/revealText.ts
- frontend/tests/revealText.test.mjs

**Uzupełnienie CC przed kodem (zgoda OWNERA 21.10):** `Pseudonimizuj.tsx` ma 929 l. (>600, nie może rosnąć bez zgody) → czysta logika
(wystąpienia tokenów, wyliczenie `finalText`, segmenty podglądu) w nowym `revealText.ts`; w dużym pliku tylko podłączenie. Front nie
ma frameworka testów → test czystych funkcji `node --test` (Node 24, bez nowych zależności).

## S4 na gałęzi zadania — propozycja do oceny Codexa

Poprzedni v4 dodał do zamrożonego S4 rozbudowany mechanizm `MAP_LEAK`/podwójnej walidacji, który **nie jest częścią v5**. Proponowane brzmienie zastępcze: „Po zakończonej, niezablokowanej kontroli OutputGuarda użytkownik może świadomie odkryć jedno wystąpienie tokenu w podglądzie; jest to jego ręczna zmiana wyniku, której Guard nie kontroluje ponownie.” Jest to **zmiana granicy odpowiedzialności**, nie dowód, że ostateczny tekst został sprawdzony przez Guard. S3/S4 HIGH i MEDIUM dla pierwotnego wyniku pozostają bez zmian. Zmiana spec i lock na **gałęzi Tasku** jest do punktowego prechecku, a nie automatycznego przeniesienia na `main`. Proponowane S4: `arch/spec.md` commit `e22866eaaaa6cbc12ddbdb9545c5d0832cd4c1bc`; nowy `arch/FROZEN.lock` osobnym commitem `cc65fe561903004dee437ddc587a8d0cb745c426`, SHA256 spec = `367b9c6e03a01adadab21bd729b742f1d7c03f08ace8cce30ebb19a1528f8a0e`. Codex sprawdza również `guard.py check` na exact SHA gałęzi. Codex ma ocenić, czy nie wprowadza to niezamierzonej regresji/obejścia istniejącej blokady.

## Odbiór, budżet, workflow

Testy celowane CC i niezależnego Codexa (po kodzie): dwie i trzy identyczne wartości, odkrycie wyłącznie klikniętego wystąpienia; cofnięcie jednego; wielowyrazowy token odkrywany w całości (widoczne ostrzeżenie zakresu); brak mapy; reset po nowym dokumencie i po „Dodaj i zakryj”; pierwotny stan `guardBlocked=true` nie pozwala na odkrycie/kopiowanie/zapis; podgląd = skopiowany tekst = odszyfrowany tekst archiwum; późniejsze `Przywróć` bez uszkodzenia tokenów. Brak PII w logach/niezaszyfrowanych plikach; bez rzeczywistych dokumentów w repo.

**Budżet CC:** szacunek ~60–80 linii UI, ale to **nie gwarancja**. Obecny plik przekracza 600 linii; CC ma przed implementacją wskazać minimalną zmianę i potrzebne odstępstwo od limitu (>150 linii, plik >600, funkcja >50, ratio >5:1) do osobnej decyzji OWNERA, jeśli konieczne. Nie utrwalać wyjątków od limitu przez rozbudowę frameworka.

**Kolejność bez skrótów:** (1) Architekt zapisuje v5 i projekt S4 na gałęzi, (2) **Codex BRIEF_ONLY dla v5 na dokładnym SHA, bez testów i implementacji** → nowy raport (r4 albo następny wolny, nie nadpisywać r1–r3), (3) po PASS/rozstrzygnięciu braków **CC recenzuje zakres i budżet**, (4) CC implementuje, (5) Codex audytuje dokładny SHA implementacji, (6) OWNER decyduje o merge. PASS v4 i recenzja CC nie zastępują tego prechecku.

Historia: v4 `5a6f13c` i freeze S4 `4bb9e86` / `eb44b6b` pozostają w historii Git; [CC review `2b5a60f`](https://github.com/paweltpietraszko-ship-it/LynxMask-Desktop/blob/2b5a60f587c043fe8fe6d85ba62d1f932b1cdad2/tasks/LYNX-MANUAL-REVEAL/cc_review.md) uzasadnia redukcję.
