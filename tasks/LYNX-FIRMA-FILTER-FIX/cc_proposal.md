# LYNX-FIRMA-FILTER-FIX — propozycja CC: forma prawna nie jest firmą + lista wykluczeń z kontekstem (2026-10-21)

STATUS: cc_proposal → brief → Codex precheck → CC szacunek / zgoda OWNERA → implementacja (pomiar: pomocnik CC) → audyt → merge na słowo OWNERA.
Niezależny od `LYNX-HERBERT-NET` (brief HerBERT zabrania ukrytych napraw FIRMA; te błędy dotyczą dziś także spaCy).

**Paweł 21.10:** „To cholerne zakrywanie samotnego »z o.o.« jako FIRMA załatwiłby biały słownik, ale go nie mamy. Nie rozumiem,
dlaczego Piekarnia jest na jakiejś liście wykluczeń — może tam są jakieś inne nonsensy?” oraz: „dla mnie równie ważne jest
wprowadzenie poprawek do listy wykluczeń, bo ona działa jak tępy księgowy. Jeśli w okolicy Piekarnia jest forma prawna, to nie
powinna być stosowana.”

## Dowody (pomiar pomocnika CC 21.10, obecny main, `/preview`, pusty profil; `%TEMP%\lynx_cc_review\firma_fp\`)
- FIRMA cierpi na **wycieki**: `dataset_clean` 26 z 43 firm jawnych + 5 częściowo; `firma_sweep` 64/160 jawnych. Najczęstszy wzorzec:
  **token FIRMA tylko na „z o.o”, nazwa jawna** („Doradztwo Biznesowe EXPERT Sp. FIRMA_001”) — clean 17, obrazy 1, Mobile 3, sweep 12.
- **Lista wykluczeń „tępy księgowy”:** `ner_blocklist._NER_BLOCKLIST_PREFIXES` = pierwsze **8 liter** każdego jednowyrazowego wpisu
  blocklisty, w tym ~34 tys. nazw geograficznych (miasta, wsie, ulice, placówki) → 34 141 prefiksów. `ner_layer._prefix_rejects`
  odrzuca każdą encję, której pierwsze 8 liter pasuje (wyjątek: pierwsze słowo = imię/nazwisko). Wieś Piekarnia → „piekarni” odrzuca
  każdą piekarnię; ul. Piękna → „Piękna Dekoracja Sp. z o.o.”. Reguła od pierwszego commita (318e005, 06.2026), działa dla spaCy i HerBERT.

## Zakres proponowany (istniejący owner `backend/ner_layer.py` + miejsce tworzenia FIRMA; bez nowej architektury)
1. **Sama forma prawna nigdy nie jest samotnym tokenem FIRMA:** kandydat FIRMA, którego wartość to wyłącznie forma prawna
   (`_LEGAL_SUFFIX_RE`: „z o.o.”, „S.A.”, „Sp. k.”…), jest rozszerzany o bezpośrednio poprzedzającą nazwę (słowa z wielkiej litery /
   WIELKIMI, do granicy linii lub słowa-kotwicy) — jedna wartość mapy „ALFA Sp. z o.o.” (Przywróć 1:1); gdy przed nim brak nazwy —
   tokenu nie tworzymy. Do ustalenia w briefie, w którym miejscu powstaje dziś token „z o.o” (warstwa FIRMA / NER / regex).
2. **Lista wykluczeń z kontekstem:** prefiks z listy geo **nie odrzuca** encji, gdy w niej lub tuż obok (to samo zdanie/linia, ±N słów)
   jest forma prawna (`_LEGAL_SUFFIX_RE`) albo kotwica firmy („firma”, „spółka”, „Sprzedawca:”, „Wykonawca:”…). Bez zmian dla instytucji
   publicznych (osobne reguły sądów/urzędów zostają).
3. **Przegląd samej listy („inne nonsensy”):** pomiar, ile prefiksów odrzuca słowa pospolite i nazwy branżowe (piekarnia, apteka,
   budowa, kwiaciarnia…) i ile prawdziwych osób/firm z gold odpada przez regułę prefiksową; propozycja zawężenia (np. prefiks tylko
   dla słów, które są wyłącznie nazwą geograficzną wg Morfeusza, albo dopasowanie odmian zamiast 8 liter) — decyzja po liczbach.

## Pomiar (pomocnik CC; miarka = wycieki i fałszywe alarmy na końcu łańcucha)
`dataset_clean` (gold osób + „gold firm z tekstu”), `firma_sweep` 160, benchmark 50 obrazów, testy Mobile: firmy jawne/częściowe/
zakryte i FP per klasa (instytucja, słowo pospolite, adres…) przed/po; OSOBA bez pogorszenia (0 nowych wycieków); strażnik
`benchmark.py`; Przywróć 1:1. Plik porównawczy do oka OWNERA.

## Szacunek CC
Pkt 1–2: ~40–80 l. kodu + ~80 l. testów; pkt 3 — najpierw pomiar (bez kodu), zmiana listy po decyzji. Razem prawdopodobnie <150–200 l.
Droga: proponuję jak `LYNX-DEPS-UPDATE` — brief CC (poprawka w istniejącym ownerze, bez nowej architektury) + Codex precheck/audyt;
Architekt tylko jeśli Codex/OWNER uznają zmianę reguł filtra za pytanie o kontrakt.
