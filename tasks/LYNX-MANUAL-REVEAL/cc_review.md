# LYNX-MANUAL-REVEAL — recenzja CC briefu v4: ZWROT do Architekta z prostszym kontraktem (2026-10-21)

Brief v4 `5a6f13c5ea8b2e6b095235e2b91b3ed411837161`, precheck Codexa r3 `6e89ce2` (PASS). CLAUDE.md pozwala CC zawrócić brief po PASS
Codexa, gdy zakres jest nieproporcjonalny do problemu. **Werdykt CC: ZWROT — kontrakt jest technicznie spójny, ale za ciężki.**

**Paweł 21.10 (dosłownie):** „Mam wrażenie, że architekt tę prostą rzecz przekombinował. W Mobile mamy odwracanie tokena i nie ma tam
chyba takich kombinacji.” oraz: **„potrzebuję prostego rozwiązania, nie kontroli bezpieczeństwa jak w apce bankowej.”**
CC się zgadza — uzasadnienie niżej.

## Jak to działa w Mobile (wzorzec, sprawdzone w kodzie)
`LynxMask/app/src/main/java/com/lynxmask/app/PseudonymResultPanel.kt` (`revealedTokens`, `outputText`) i `TextPreviewModal.kt`:
odkrycie jest stanem UI na tekście, który Guard już ocenił; kliknięcie tokenu pokazuje oryginał (podkreślony), drugie cofa; tekst do
kopiowania = to, co widać. **Guard nie jest uruchamiany ponownie, nie ma serwera, sesji ani walidacji końcowego tekstu.**
(Mobile odkrywa token we wszystkich wystąpieniach; Desktop może per wystąpienie — to tylko indeks w UI.)

## Dlaczego v4 jest nieproporcjonalny
1. **Ponowna kontrola niczego nie chroni.** Odkryte słowo to dokładnie wartość, którą użytkownik świadomie chce pokazać. Guard
   uruchomiony ponownie może tylko zgłosić to samo — stąd pętla `MAP_LEAK`, a potem projekcja, druga kontrola i wyjątek w S4, żeby
   tę pętlę obejść. Problem pętli powstaje wyłącznie z założenia „po odkryciu trzeba kontrolować ponownie”.
2. **Brak przeciwnika, przed którym chroni serwerowa prawda.** To lokalny program jednego użytkownika; ten sam użytkownik ma oryginał
   dokumentu i może go wkleić do AI. Serwerowa sesja, identyfikatory wystąpień, rekonstrukcja `finalText`, unieważnianie rewizji
   i obsługa spóźnionych odpowiedzi bronią przed podrobieniem żądania przez… samego użytkownika.
3. **Koszt:** nowe API w `pseudominizer_api.py` (>1000 l., nie może rosnąć bez zgody), stan sesji w pamięci, dwa przebiegi Guarda,
   kilkanaście kontrprób, zmiana zamrożonego S4. Szacunek CC: kilkaset linii. Wersja prosta: ~60–80 l. w jednym pliku UI + testy.

## Proponowany kontrakt v5 (prosty, jak Mobile)
- **Zachowane z v4:** odkrywanie dostępne dopiero, gdy wynik `/preview` nie jest zablokowany i alerty Guarda są obsłużone; zgoda tylko
  w tym dokumencie, niezapisywana (bez `GuardAllowlist`, profilu, `.lynxdict`); per **wystąpienie** — przykład obowiązkowy z „Różą”
  (kwiat odkryty, `Pani OSOBA_033` zakryta) zostaje testem odbioru; cofnięcie każdego odkrycia osobno.
- **Mechanika:** w `frontend/src/screens/Pseudonimizuj.tsx` kliknięcie tokenu w podglądzie → „Odkryj tutaj” (komunikat z v4: „Jeżeli to
  słowo nie jest daną osobową, możesz odkryć je tylko w tym miejscu”); stan = zbiór indeksów wystąpień; tekst końcowy liczony w UI
  z `anonymized_preview` + mapy z odpowiedzi; **jedna wartość** dla ekranu, „Kopiuj” i zapisu do archiwum (to zostaje z v4).
- **Bez:** nowego endpointu, sesji serwera, ponownego Guarda, projekcji, zmian `output_guard.py`/pipeline.
- **S4:** zamiast wyjątku dla `MAP_LEAK` — jedno zdanie: „Odkrycie wystąpienia przez użytkownika po zakończeniu kontroli Guarda jest jego
  decyzją, nie wynikiem maskowania; Guard nie ocenia go ponownie.” Czy to wymaga zmiany frozen S4, czy mieści się w obecnym brzmieniu
  — do decyzji Architekta. Zmiana S4 z `4bb9e86`/`eb44b6b` na gałęzi może zostać zastąpiona tym zdaniem.
- Wielowyrazowe tokeny (np. `OSOBA_001 → Anna Malina`): jak w Mobile — odkrywane w całości, świadomie (bez częściowego odsłaniania).
- Testy: przykład „Róży”, cofnięcie, trzy wystąpienia / cofnięcie jednego, nowy dokument czyści odkrycia, wynik zablokowany = brak
  odkrywania, kopiowanie i zapis = ten sam tekst co na ekranie.

## Prośba
Architekt: brief v5 w tej postaci (albo uzasadnienie, jakiego realnego zagrożenia nie pokrywa wersja prosta). Bez kodu do briefu.
