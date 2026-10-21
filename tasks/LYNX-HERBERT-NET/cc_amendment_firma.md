# LYNX-HERBERT-NET — poprawka CC do briefu v1 `ceefa2a`: ORG → FIRMA w tej samej siatce (2026-10-21)

Paweł 21.10: „OSOBA to za wąski zakres dla HerBERTa, bo FIRMA też daje dużo FP i wycieków. Ale architekt zaraz zaproponuje 1000 linii
kodu i piętrowe zależności. Jak to pogodzimy?” Na prośbę Pawła CC zmierzył FIRMA (pomocnik, obecny main, prawdziwy `/preview`, pusty
profil; skrypty lokalnie: `%TEMP%\lynx_cc_review\firma_fp\` — `run.py`, `an1.py`, `an2.py`, `fin.py`, `raport.md`).

## Dane (syntetyki; zbiory nie mają kluczy firm w ground_truth → „gold z tekstu”: blok SPRZEDAWCA + forma prawna = dolna granica)
| zbiór | firm | zakryte | częściowo | jawne | tokeny FIRMA: TP / FP | FP: instytucje publiczne |
|---|---|---|---|---|---|---|
| dataset_clean (300) | 43 | 12 | 5 | 26 | 15 / 82 | 78 |
| benchmark obrazy (48) | 3 | 1 | 0 | 2 | 1 / 22 | 21 |
| testy Mobile (30) | 10 | 2 | 3 | 5 | 4 / 8 | 2 |
| firma_sweep (160) | 160 | 96 | 0 | 64 | 96 / 0 | 0 |
OSOBA dla porównania: 477 osób gold — 0 jawnych; FP nieliczne (głównie śmieci OCR na obrazach).
**Wniosek:** FIRMA cierpi na **wycieki**; FP to w ~90% instytucje publiczne (nadmaskowanie bez ryzyka prywatności). Siatka na końcu
(dokłada, nie cofa) trafia dokładnie w problem FIRMA; dla samego PER na tych zbiorach niewiele by dodała.
Wzorce wycieków: (1) token tylko na „z o.o”, nazwa jawna („Doradztwo Biznesowe EXPERT Sp. FIRMA_001”) — clean 17, Mobile 3, sweep 12;
(2) nazwy z łącznikiem w gołej linii (Pro-Eko, Bud-Expert) — sweep 52; (3) krótkie nazwy sprzedawcy bez formy prawnej (ALFA,
Biuro Rachunkowe RACHMISTRZ); (4) zakryta tylko część nazwy; (5) JDG z osobą w nazwie — reszta nazwy jawna.

## Proponowana zmiana briefu (mała)
1. **ORG → FIRMA w tym samym module i miejscu** co PER (nie osobny Task, nie FIRMA-REDESIGN), przez **istniejący** filtr instytucji
   publicznych (polityka: sądy, urzędy, ZUS jawne) — bez tego siatka dołoży kolejne FP klasy „instytucja”.
2. **Span przylegający do istniejącego tokenu FIRMA** (wzorzec 1): jawna część spanu ORG bezpośrednio przed/po tokenie FIRMA → zakryć
   tą samą wartością mapy co sąsiedni token (rozszerzenie zakrycia, nie zmiana istniejącej decyzji). Pozostałe spany przecinające token —
   odrzucane jak w v1.
3. **Osobne przełączniki i pomiar:** `LYNX_HERBERT=PER`, `=PER,ORG`, `=off`; raport „co dołożyła siatka” osobno dla PER i ORG.
   LOC/ID — nadal tylko mierzone. Do pomiaru ORG: harness pomocnika (gold z tekstu + firma_sweep 160) — CC dołoży go do `tasks/`.
4. **Twardy limit:** całość ≤ ~350 linii z testami, jeden nowy plik produkcyjny (`backend/herbert_net.py`) + testy, wywołanie przed
   Guardem; bez zmian istniejących warstw FIRMA/OSOBA i bez nowych zależności poza `tokenizers`. Przekroczenie = STOP i decyzja OWNERA,
   nie rozbudowa.
