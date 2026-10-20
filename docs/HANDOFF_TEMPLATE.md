# Formatka przekazania pałeczki (wzór CC, do dobrowolnego użycia)

Wzór, którego używają instancje Claude Code przy przekazaniu pracy następcy (u CC plik przekazania żyje w lokalnej pamięci). Architekt i Codex mogą z niego korzystać, jeśli uznają to za przydatne — nie zastępuje `ARCHITECT_START_HERE.md` ani `CODEX_HANDOFF.md`. Na prośbę OWNERA 20.10.

Paweł 20.10 (propozycja, przyjęta przez CC): każda instancja przekazywała „jak uważała”. Odtąd przekazanie = **jeden plik `project_handoff.md` (nadpisywany, nie dopisywany)** + pamięć przejrzana pod kątem nieaktualności. Zaprojektowane tak, jak CC chce dostać informację: najpierw co robić, potem dlaczego, na końcu historia (w git, nie w pamięci).

## Kiedy
Przy ~70% okna albo na prośbę Pawła — przed rozpoczęciem nowego zadania, nie w jego środku. Jeśli zadanie w toku: doprowadź do stanu z SHA (commit + push), opisz dokładnie, gdzie stoisz.

## Sekcje `project_handoff.md` (w tej kolejności, max ~80 linii)
1. **Nagłówek:** data/godzina, kto przekazuje, main `<sha>`, „przeczytaj najpierw: BOARD → TERAZ”.
2. **ZRÓB NAJPIERW (1 rzecz):** jedno następne działanie z dokładnymi wskaźnikami (wiersz BOARD, gałąź, ścieżka briefu, SHA, status prechecku/audytu) i co już ma (np. zgoda Pawła na rozmiar — liczba linii, data).
3. **W toku / czeka na kogo:** tabela ID | stan | czeka na (Codex/Architekt/Paweł/CC) | wskaźnik. Tylko otwarte.
4. **Środowisko teraz:** czy silnik 8765 działa i z jakiego katalogu/SHA; worktree CC i gałęzie (które można usunąć); lokalne zasoby poza repo (modele, zbiory, skrypty w scratchpadzie — ścieżki pełne); co Paweł musi zrobić po restarcie (ikona).
5. **Ustalenia z tej sesji, których nie ma w BOARD/repo:** decyzje i preferencje Pawła (dosłownie, z datą) → każda także jako osobna notatka feedback/project; tu tylko link `[[...]]`.
6. **Liczby, na których stoją decyzje:** 3–6 pozycji z miarką i poleceniem odtworzenia (żeby następca nie liczył od nowa ani nie wierzył starym procentom).
7. **Pułapki napotkane w tej sesji:** tylko nowe; trwałe → do `reference_pitfalls.md`.
8. **Otwarte pytania do Pawła** (lub „brak”).
9. **Checklista przeglądu pamięci:** usunięte/zaktualizowane notatki; potwierdzenie, że MEMORY.md wskazuje `project_handoff.md` jako CZYTAJ NAJPIERW.

## Zasady
- Nie powielaj BOARD ani git — linkuj (SHA, ścieżka). Pamięć trzyma to, czego nie ma w repo.
- Nie zostawiaj dziennika („potem zrobiłem…”); stan, nie historia.
- Głos Pawła zapisuj jako propozycję, chyba że wprost zdecydował (`AGENTS.md` → OWNER_INPUT_IS_A_PROPOSAL).
- Przegląd pamięci: każda notatka typu project/state sprzed tej sesji — aktualna? jeśli nie, usuń albo popraw; feedback sprzeczny z nowym ustaleniem — popraw.
- Następca: przeczytaj `project_handoff.md`, potem BOARD → TERAZ, potem zrób sekcję 2. Nie zaczynaj od ponownego pomiaru tego, co jest w sekcji 6.
