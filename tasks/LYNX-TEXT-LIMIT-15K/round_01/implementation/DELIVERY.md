# LYNX-TEXT-LIMIT-15K — DELIVERY r1 (CC)

Gałąź `task/LYNX-TEXT-LIMIT-15K` (brief architekta `af8c451` + nagłówek TASK_SCOPE `4240176`; PASS PREIMPLEMENTATION `e69111e`), zsynchronizowana z main `bf57999` (merge `eac220a`, zawiera NER-MULTILINE). Kod: `22460b7`.

## Zmiana (`backend/pseudominizer_api.py`, +19/−13 wg git diff)
- usunięte `MAX_TEXT_CHARS = 15_000` i oba `[:MAX_TEXT_CHARS]` (`/preview`, `/preview-express`); `text.strip()` bez zmian;
- `from anonymizer_init import INPUT_LIMIT_BYTES` w bloku importów (jedno źródło prawdy, 500 000 B; import bez cyklu — sprawdzony uruchomieniem);
- `_text_rejection(text, tag, pse_code)` zastępuje zduplikowany blok „pusty tekst → 400” w obu endpointach i dodaje: `len(text.encode("utf-8")) > INPUT_LIMIT_BYTES` → HTTP 413, `{"error": "Dokument jest za długi (N KB tekstu, limit 500 KB). Podziel go na części.", "blocked": true}` — bez wyniku, mapy, tokenów i `original_text`; log tylko kategoria i rozmiary w bajtach (bez treści). Wołane po ekstrakcji i strip, przed token-injection i pipeline. Granica równa limitowi przechodzi.
- bez zmian: `MAX_FILE_BYTES` 5 MB, `MAX_TOKENS_PER_REQUEST` 500, `MAX_BLOB_BYTES` 512 KB (archiwum ma własny jawny błąd „Blob za duży (max 512 KB)”), pipeline, Guard, NER, Express bez NER.
- UI: `Pseudonimizuj.tsx` i `ExpressModeScreen.tsx` dla `!res.ok` wyświetlają `errData.error` — komunikat 413 dociera do użytkownika bez zmian frontendu.

## Testy (`backend/tests/test_text_limit_15k.py`, nowy, 93 linie, uruchamiany jawnie; TestClient bez lifespanu, stan silnika z `audyt/engine_quality.build_state`)
| Test | baza (API sprzed zmiany) | gałąź |
|---|---|---|
| PESEL + e-mail tylko w końcówce tekstu 17–18 tys. znaków, `/preview` i `/preview-express`: pełne `original_text`, brak PII w wyniku, Przywróć (symulacja) = wejście | FAIL ×2 | PASS ×2 |
| granica UTF-8: polskie litery, dokładnie 500 000 B → przechodzi, 500 001 B → 413 (znaki < bajty) | FAIL | PASS |
| ponad limitem przez oba endpointy: 413, `blocked`, bez `anonymized_preview`/`tokens`/`original_text`, brak PESEL w odpowiedzi | FAIL ×2 | PASS ×2 |
| regresje: pusty → 400, token injection → 422, krótki TXT z PESEL i polskimi znakami | PASS ×2 | PASS ×2 |
Razem: baza 5 failed / 2 passed; gałąź 7 passed.
Syntetyk ma „PESEL: ” z dwukropkiem — wariant „PESEL ” bez dwukropka wraca z Przywróć z dopisanym dwukropkiem (znany TEXT-FIDELITY-F3, poza zakresem).
Regresje: `tests/` z działającym backendem z gałęzi 167 passed, 2 skipped, 1 xfailed; `test_audyt_2026_10.py` 131 passed, 10 xfailed; `test_layers.py` + `test_ner_multiline.py` 143 passed.
`test_pseudominizer.py:482` — komentarz „backend tnie do MAX_TEXT_CHARS=15000” nieaktualny (plik poza TASK_SCOPE; asercja nie osłabiona) — finding.

## Pomiar: 54 dokumenty > 15 000 znaków z `dataset_real_public` przez działający `/preview` (profil biura Pawła)
Baza: backend z main `bf57999`; gałąź: backend z `22460b7` z tym samym profilem (`ANONYMIZER_PROFILE_DIR`), osobny `ARCHIVE_DIR`. Dane lokalnie, tylko liczby.

| | baza | gałąź |
|---|---|---|
| dokumenty z pełną długością przekazaną do pipeline | 0 / 54 | **54 / 54** |
| znaki przetworzone (suma) | 810 000 z 2 386 817 (**66% treści odcięte**) | 2 386 817 |
| kody HTTP | 200 ×54 | 200 ×54 (żaden nie przekracza 500 000 B) |
| czas `/preview`: mediana / max (i7-14650HX) | 0,8 s / 0,9 s | 1,6 s / 8,8 s |
| max tokenów w dokumencie | 50 | 165 (limit 500) |
| błędy | 0 | 0 |
| **blokady Guarda** | 27 | **40** (13 nowych, wszystkie `MAP_LEAK`; 0 zdjętych) |

Ryzyko z briefu potwierdzone: przy pełnej długości 13 dokumentów, które dawały obcięty wynik, dostaje blokadę `MAP_LEAK` (wartość z mapy jawna w dalszej części tekstu — niespójne maskowanie, klasa B diagnozy). Stan uczciwszy (brak ukrytej utraty 66% treści), ale 40/54 długich dokumentów zablokowanych do czasu K2 (spójność) i rozstrzygnięcia LYNX-SPEC-S4-GUARD-WARN.

## Gate (dosłownie)
```
STATUS: FAIL
HEAD_SHA: 22460b7fa996eb7cc66d639965981acd6dcb88de
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
REASON:
  - SIZE_FILE: backend/pseudominizer_api.py has 1129 lines (max 600, before 1123)
WYMAGA_DECYZJI:
  - RATIO: 112/13 = 8.6:1 (threshold 5:1)
```
Wzrost +6 linii pliku legacy: nowa odpowiedź 413 i funkcja wspólna dla dwóch endpointów (zduplikowany blok pustego tekstu zastąpiony wywołaniem). Bez sztucznego zagęszczania; zgodnie z briefem wymaga odnotowanej decyzji Pawła. `ruff`: 6 błędów przed i po (bez nowych).

**OWNER_ACCEPTED 2026-10-18 (Paweł, dosłownie):** „Akceptuję przekroczenie limitu ale limit nie jest z palca wyssany, za duże pliki wszystkim utrudniają życie a pseudominizer był już po refaktorze a i tak urósł.” — dotyczy gate SIZE_FILE (+6 linii `pseudominizer_api.py`, 1123 → 1129) i RATIO tej dostawy; uwaga o rozmiarze → osobne zgłoszenie w BOARD (LYNX-API-SIZE).
