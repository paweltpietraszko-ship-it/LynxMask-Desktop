# CC — ocena merytoryczna briefu LYNX-T10-BUILD-TS (r1)

Brief na `30b4061` (precheck Codexa: PASS PREIMPLEMENTATION). Werdykt CC: **PRZYJĘTY** — bez zmian zakresu,
z trzema doprecyzowaniami wykonania (jeśli Architekt/Codex się nie zgadza — sygnał przed audytem).

1. **Pomiar Origin/Host bez kodu produktu.** Brief zabrania logowania nagłówków w produkcji. CC uruchomi backend T02
   (`dc49836`, osobny worktree) przez zewnętrzną nakładkę testową (ASGI wrapper zapisujący WYŁĄCZNIE nazwy i wartości
   `Origin`/`Host` + ścieżkę/metodę/status), plik w `tasks/LYNX-T10-BUILD-TS/round_01/implementation/` — artefakt, nie produkt.
   Profil i archiwum tymczasowe (env `ANONYMIZER_PROFILE_DIR`/`ARCHIVE_DIR`/`PROFILE_DIR`).
2. **Bundle instalatorów.** `targets: "all"` buduje MSI/NSIS (WiX/NSIS pobierane z sieci). Jeśli bundling zawiedzie z powodu
   narzędzi/pobierania, CC użyje `npm run tauri build -- --no-bundle` (ten sam `beforeBuildCommand`, ten sam plik .exe) i opisze to
   jako ograniczenie, nie zmieniając konfiguracji.
3. **Smoke UI (klikanie motywu, przycisków, Zapisz).** CC w tej sesji nie ma sterowania oknem aplikacji desktopowej. Ruch
   sieciowy przy starcie (`/health`, `/express/token`) wystarcza do pomiaru nagłówków; klikalny smoke wykona OWNER (instrukcja
   w DELIVERY) albo Codex z narzędziem do UI — inaczej warstwa NOT_CHECKED, nie PASS.
