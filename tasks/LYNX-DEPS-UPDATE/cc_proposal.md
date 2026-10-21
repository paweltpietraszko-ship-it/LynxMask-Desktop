# LYNX-DEPS-UPDATE — propozycja CC: przypięte zależności + aktualizacje bezpieczeństwa + nowy słownik Morfeusza (2026-10-21)

STATUS: cc_proposal → Architekt (brief) → Codex precheck → CC szacunek / zgoda OWNERA → implementacja → audyt → merge na słowo OWNERA.
Paweł 21.10: „musimy sprawdzić, czy wszystkie programy, które mamy w apce typu Morfeusz, są aktualne” → inwentaryzacja (pomocnik CC,
tylko odczyt); po niej: „musimy zająć się aktualizacjami”. Jeden Task w dwóch etapach (zasada OWNERA: mniej szwów).

## Stan (inwentaryzacja 21.10; pełna tabela lokalnie u CC, źródła: PyPI, npm, crates.io, OSV, download.sgjp.pl)
- **Brak listy zależności w repo** (żadnego `requirements*.txt` / `pyproject`): silnik używa globalnego `py -3` (Python 3.14.4)
  współdzielonego z innymi projektami. Nikt nie wie, w jakich wersjach program działa — ryzyko procesowe i blokada dla `LYNX-INSTALLER`.
- **Bezpieczeństwo (aktualizować):**
  - Pillow 12.2.0 → 13.0.0 (major): 22 advisory, w tym CRITICAL `GHSA-8g5g-8vmr-9782` (dekoder JPEG); silnik otwiera obrazy użytkownika
    (`ocr_engine.py`). **Nie ma go w `LYNX-SEC-DEPENDENCIES`.**
  - cryptography 46.0.7 → 50.0.2 (major): m.in. wheel z podatnym OpenSSL (HIGH, poprawka od 48.0.1); używamy AES-GCM/KDF.
  - fastapi 0.135.3 → 0.156.x (starlette 1.0.0 → 1.9.0; HIGH w `request.form()`), python-multipart 0.0.26 → 0.0.32 (HIGH DoS);
    ekspozycja tylko 127.0.0.1:8765 — ryzyko niskie, poprawka tania.
  - Rust (`cargo update`): rustls 0.23.41 → 0.23.46, rustls-webpki, anyhow 1.0.102 → 1.0.104 (RUSTSEC 2026).
- **Jakość:** Morfeusz2 1.99.12 → 1.99.15, słownik SGJP 2025-11-10 → 2026-10-18 (~11 mies. zaległości; pip 1.99.15 niesie
  2026-06-01, najnowszy build ręcznie z download.sgjp.pl). Bez CVE; zmienia lematyzację i odmianę → wpływ na OSOBA/ADRES.
- **Mogą poczekać (ZOSTAW/ROZWAŻ):** Tesseract 5.5.0 → 5.5.3 (dziś tylko zapas), onnxruntime 1.25 → 1.31 i numpy 2.4 → 2.5 (zmiana
  czytnika PP — tylko z pomiarem odczytu), spaCy 3.8.13 → 3.8.16 (model pl_core_news_lg 3.8.0 jest najnowszy), Tauri 2.11 → 2.12,
  PyMuPDF 1.27 → 1.28, phonenumbers 9.0.30 → 9.0.41; React 19 / Vite 8 / TypeScript 7 — duże skoki bez luk w produkcie (osobno).

## Zakres proponowany
**Etap A — bezpieczeństwo, bez zmiany działania silnika:**
1. `backend/requirements.txt` (nowy): przypięte (`==`) wersje wszystkich pakietów, których silnik faktycznie używa — podstawa
   powtarzalności i dla `LYNX-INSTALLER`. Instrukcja dla dewelopera; użytkownik nic nie instaluje (instalator).
2. Aktualizacja: Pillow, cryptography, fastapi/starlette, python-multipart; `cargo update` dla rustls/rustls-webpki/anyhow
   (`frontend/src-tauri/Cargo.lock`). Poprawki zgodności API, jeśli major tego wymaga (Pillow 13, cryptography 50).
3. Odbiór: pełne testy backendu (porażki = jak przed), `crypto_selftest` i próby startowe, odczyt archiwum zapisanego przed aktualizacją
   (zgodność szyfrogramów!), benchmark-strażnik `dataset_20260627_095419` main vs gałąź (identyczny wynik), build aplikacji.
**Etap B — słownik Morfeusza:**
4. morfeusz2 1.99.15 + najnowszy słownik SGJP (wersja i SHA zapisane); pętla poprawka → dokumenty: benchmark, testy Mobile `testy/*.txt`,
   `dataset_clean` (300) — porównanie przed/po (osoby, adresy, odmiany, Przywróć 1:1). Zmiany w wykrywaniu → plik porównawczy do oka OWNERA.

## Do rozstrzygnięcia przez Architekta
Czy etap B razem z A (jeden Task) czy po `LYNX-OSOBA-REDESIGN` (słownik wpływa na decyzję o osobie); polityka aktualizacji na przyszłość
(np. przegląd OSV co miesiąc); czy `requirements.txt` także dla narzędzi pomiarowych. Bez kodu do briefu.
Szacunek CC: A ~40–80 l. (głównie requirements + ewentualne poprawki API) + pomiary (pomocnik); B — kod raczej 0, pomiary.
