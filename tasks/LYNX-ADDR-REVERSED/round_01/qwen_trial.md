# LYNX-ADDR-REVERSED — zapis próby Qwen 3.8 (CC, 22.10.2026)

- **Próba 1:** płytki klon gałęzi Codexa `codex/security-review-20261018` (`6cbd0ab`, 18.10), bez `origin`. Kodu nie było. Własny brief w roli Architekta. Diagnoza 4 przypadków trafna; dopisane do briefu.
- **Próba 2:** właściwa gałąź `201c9be`, bez `origin`. Przerwana limitem wywołań narzędzi. Plik `address.py` z pobranych OWNERA wgrany bez zmian (commit „Qwen 3.8 work-in-progress”).

Wynik próby 2 (sonda CC, warstwy bez NER):

| przypadek | przed | Qwen WIP |
|---|---|---|
| Opole, 45-407, ul. Rzemieślnicza 433 | `Opole, 45-407, ADRES_001` | `Opole, ADRES_001` (kod zakryty, miasto jawne) |
| Wrocław, 50-001 | jawne | jawne |
| Warszawa, ul. Marszałkowska 12/4, 00-001 | `Warszawa, ADRES_001` | bez zmian |
| ul. Polna 5, Radom | `ADRES_001, Radom` | **TypeError w warstwie → blokada S3 dokumentu** (bez wycieku) |
| 00-001 Warszawa, Twarda 18 | `ADRES_001, Twarda 18` | **TypeError → blokada S3** |
| Kraków al. Jana Pawła II 15 31-001 | `Kraków ADRES_001-001` | bez zmian |
| CLEAN (Wrocław, data; wyliczenie miast) | bez zmian | bez zmian |

- `gate.py` (`round_01/gate_qwen_wip.txt`): **STATUS: FAIL** — `SIZE_FUNC: apply_address_layer has 61 lines (max 50, before 56)`. Raport Qwena deklarował jedną linię wywołania.
- Testów `test_addr_reversed.py`, DELIVERY i commita od Qwena brak. `test_addr_email_leaks.py`: 22 passed.
- Ocena: rozumienie zadania i diagnoza dobre; wykonanie niedokończone, z błędem typu i z naruszeniem ratchetu; środowisko bez push.
