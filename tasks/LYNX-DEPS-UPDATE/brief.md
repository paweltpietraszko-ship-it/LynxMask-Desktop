# LYNX-DEPS-UPDATE — zakres (CC, 2026-10-21; bez Architekta — zadanie mechaniczne)

Paweł 21.10: „Po co nam architekt? Przecież to nie projektowanie apki, tylko aktualizacja.” CC się zgadza: CLAUDE.md — drobne,
mechaniczne zmiany: gate + Codex PASS. Paweł wybrał **osobne środowisko Pythona dla LynxMask** (zamiast aktualizacji globalnego
`py -3`, wspólnego z innymi projektami). Propozycja i inwentaryzacja: `tasks/LYNX-DEPS-UPDATE/cc_proposal.md`.

## Etap A (ten Task teraz): własne środowisko + aktualizacje bezpieczeństwa, działanie silnika bez zmian
1. `backend/requirements.txt` — przypięte (`==`) wersje pakietów, których silnik faktycznie używa (importy produkcyjne backendu),
   plus `pytest` w osobnej sekcji/komentarzu dla dewelopera. Model spaCy `pl_core_news_lg==3.8.0` z przypiętego adresu wheel.
   Aktualizacje bezpieczeństwa: Pillow 13.0.0, cryptography 50.0.2, fastapi (z starlette ≥1.3.1, najnowsza zgodna), python-multipart
   0.0.32, urllib3 ≥2.8 (jeśli w drzewie). Pozostałe — wersje obecnie zainstalowane (bez zmian zachowania; morfeusz2 bez zmian w etapie A).
2. Środowisko `.venv` w katalogu głównym repo (poza git). `LynxMask.vbs`: jeśli istnieje `.venv\Scripts\python.exe` — uruchom silnik nim,
   inaczej dotychczasowe `py -3` (zapas). Docelowo środowisko tworzy instalator (`LYNX-INSTALLER`).
3. `frontend/src-tauri/Cargo.lock`: `cargo update -p rustls -p rustls-webpki -p anyhow` (tylko te; bez podnoszenia tauri).
4. Poprawki zgodności API w kodzie backendu tylko, jeśli nowe wersje tego wymagają (lista plików dopisywana tu przed zmianą).

TASK_SCOPE:
- backend/requirements.txt
- LynxMask.vbs
- .gitignore
- frontend/src-tauri/Cargo.lock

Odbiór (na `.venv`, porównanie z globalnym `py -3` na main): pełne testy backendu — te same wyniki; `crypto_selftest` i próby startowe
OK; **archiwum zaszyfrowane starą wersją odczytywalne nową** (syntetyk); benchmark-strażnik `dataset_20260627_095419` — wynik
identyczny; obraz JPEG/PNG przez `/preview` działa; build aplikacji (Cargo.lock) OK. Bez danych realnych w repo.

## Etap B: nowy słownik Morfeusza
morfeusz2 1.99.12 (sgjp-2025.11.10) → 1.99.15 z PyPI (sgjp-2026.06.01) — jedna linia w `backend/requirements.txt`. Pomiar przed/po
(pomocnik CC): 389 dokumentów (`dataset_clean` 300, testy Mobile 39, obrazy benchmarku 50) przez `/preview` — 0 różnic; 3169 słów —
identyczne analizy. Najnowszy build SGJP 2026-10-18 jest tylko do ręcznego pobrania → `LYNX-INSTALLER` (bez ręcznych kroków).
