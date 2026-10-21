# LYNX-SPEC-S4-GUARD-WARN — PROPOZYCJA zmiany PRODUCT_TRUTH, NIE obowiązująca specyfikacja

2026-10-21 · powiązana z `LYNX-GUARD-RESIDUE`. `arch/spec.md` i `arch/FROZEN.lock` **nietknięte**. OWNER po ocenie kontraktu ma zatwierdzić formalną aktualizację S4 przed kodem (osobny commit, `guard.py freeze --recompute`, audyt Codexa). Ten plik **nie oznacza jeszcze odmrożenia S4**.

## Proponowana zasada zastępująca obecne „HIGH blokuje bez decyzji / Guard REDACT”

1. **Guard nie jest warstwą maskowania.** Po silniku wykrywa *pozostałe jawne fragmenty* podejrzane o PII i przedstawia ostrzeżenia z lokalizacją i czytelnym powodem. `RED` i `YELLOW` mogą oznaczać wagę, **ale każde nierozstrzygnięte ostrzeżenie blokuje operacje udostępniania z LynxMask**.
2. Użytkownik dla każdego ostrzeżenia wybiera `Zakryj` (istniejące maskowanie + ponowna kontrola aktualnego tekstu) albo `Zostaw` (świadome zaakceptowanie danego przypadku). **Nie ma zbiorowego „Zostaw wszystkie” ani przycisku „Zapisz mimo to”.** Lista „Zostaw” na przyszłość to osobny, jawnie wybrany i chroniony pamięcią lokalną wariant, nie bezwarunkowe prawo do eksportu.
3. **Biblioteka, kopiowanie tekstu i eksport z aplikacji są niedostępne**, dopóki istnieje co najmniej jedno nierozstrzygnięte ostrzeżenie dla bieżącej wersji dokumentu. Gdy wszystko obsłużone — można je wykonać. Każda zmiana treści potencjalnie odsłaniająca dane unieważnia poprzednią ocenę i wymaga kontroli nowego wyniku. Normalny podgląd i korekta pozostają dostępne podczas oceny.
4. **S3 bez zmian:** awaria silnika/Guarda/NER = nieprzezwyciężalna błędem użytkownika blokada operacji; `Zostaw` nie usuwa awarii. Nie wolno osłabić blokady awarii w celu wprowadzenia ostrzeżeń.
5. Decyzje są przypisane do konkretnego ostrzeżenia i rewizji wyniku. Obowiązuje ochrona S5; trwały, minimalny rejestr decyzji wzorowany na Elnath Rota jest osobnym zadaniem końcowym (`LYNX-GUARD-DECISION-LOG`). Nie udawać, że teraz mamy audyt nieprzerwany od pierwszego wdrożenia.
6. **Jeden byt = jeden token**, w tym odmiany gramatyczne i warianty zapisu tej samej osoby, o ile identyczność jest wiarygodnie ustalona. W `Przywróć`/ręcznym `Odkryj` dopuszcza się postać kanoniczną (mianownik), bez gwarancji zachowania fleksji/wielkich liter; zabronione jest łączenie różnych osób. Nie zmieniać w tym zadaniu tokenów, mapy, `.lynxdict` ani reguł rozpoznawania.

## Krytyczna relacja do dotychczasowych S3/S4

Obecnie S4 HIGH przypisuje automatyczną blokadę pojedynczemu trafieniu, a `GuardMode.REDACT` może zwracać `[REDACTED]`. W nowym wariancie wykrycie jest **ostrzeżeniem wymagającym reakcji użytkownika**, nie automatycznym maskowaniem; **stan „brak reakcji” nadal blokuje udostępnienie**, a awaria nadal jest odmową S3. Zmiana wymaga aktualizacji testów starego S4, nie usuwania ich na ślepo.

Nie mieszaj do tej zmiany blokady wejścia token injection, polityki OCR, strony zewnętrznej sieci, pamięci Elnath ani instalatora. Żadne wdrożenie pod pretekstem tego pliku bez osobnej autoryzacji OWNERA.
