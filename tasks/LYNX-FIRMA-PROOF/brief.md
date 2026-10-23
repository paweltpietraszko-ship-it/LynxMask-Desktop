# LYNX-FIRMA-PROOF — FIRMA tylko z dowodem; instytucja i data pisma wg RODO; wartość zakryta wszędzie; Guard bez numerów strukturalnych

23.10.2026, CC. Poprawka bez Architekta (reguły wykrywania + filtr Guarda) — jeden blok zamiast kilku Tasków (zasada „mniej szwów”).
Polecenie Pawła 23.10 po obejrzeniu panelu Guarda na publicznych orzeczeniach KIO („Guard nadal jest wysypiskiem, a firmy dalej
są nieskończone… Najważniejsza jest dobra ogólna reguła, która zamyka 85–90% przypadków, a brzegowe dopisuje się naprawą. Rób jak
najlepiej umiesz.”). Zastępuje wiersz BOARD `LYNX-OVERMASK-POLICY` (data dokumentu, instytucje).
Kolejność jak w OSOBA-LAYOUT: kod powstał na prototypach (scratchpad CC v1–v11) przed briefem — Codex robi precheck briefu i audyt
kodu w jednym kroku.

## Problem (stan main `948c3bb`)
Panel Guarda na 40 orzeczeniach KIO (`backend/dataset_real_public/B_kio/docs`, publiczne): **272 pozycje do decyzji, 6,8/pismo**.
- **Śmieciowe FIRMA w silniku** → lawina czerwonych MAP_LEAK. spaCy zwraca jako firmę urzędy („Krajowa Izba Odwoławcza”, „Izba”,
  „Rady Ministrów”, „Skarb Państwa”), zwykłe słowa („Rejonu”, „Nadzoru”, „Bezsporne”, „Uzasadniał”), ustawy („Prawo Budowlane”),
  produkty („Microsoft Office”). Silnik zakrywa je raz, a Guard zgłasza każde inne wystąpienie słowa („rejonu ×75”).
  Na 40 pismach 513 różnych wartości FIRMA/INSTYTUCJA, duża część nie-firm. Dotychczasowe filtry to ~15 wersji list wyjątków.
- **Złe granice firm:** słowo roli w nazwie („Wykonawca POLSUPER Sp. z o.o”, „Odwołującego - Siemens Sp. z o.o”);
  ta sama firma raz zakryta, raz jawna („STRABAG Sp. z o.o” vs „Strabag Sp. z o.o.”, „Honda”/„HONDA”).
- **Ta sama wartość raz zakryta, raz jawna:** numer/data/znak sprawy złapany w jednym kontekście („nr 75/06”, „dnia 02.11.2011 r.”),
  a powtórzenie („zaświadczenia nr 75/06.”, „02.11.2011r.”, „postępowaniu nr 1/2016”) jawne → czerwone MAP_LEAK.
- **Guard R4 („Numer lub data”) na strukturze pisma:** „Dz. U. z 2010 r. Nr 113”, „droga krajowa nr 87”, „załącznik nr 2”,
  „pytanie nr 21”, a także słowo-klucz „numer” wewnątrz tokenu („PN-NUMER_010:1999”).
- **Zbędne zakrycia GOLD (dev 69/440, test 152/880):** data pisma 40, instytucja publiczna 23 (diagnoza `LYNX-OVERMASK-POLICY`).

## Podstawa (sprawdzona w źródłach, nie wybór Pawła)
- RODO art. 4 pkt 1, motyw 14 (osoba prawna nie jest daną osobową), motyw 26 (identyfikacja pośrednia) —
  https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=CELEX:32016R0679
- EDPB, Wytyczne 01/2025 o pseudonimizacji, pkt 101–104 (quasi-identyfikatory usuwać/uogólniać, gdy ochrona przed podmiotem
  zewnętrznym — tu dostawca AI): https://www.edpb.europa.eu/system/files/2025-01/edpb_guidelines_202501_pseudonymisation_en.pdf
  (wersja z konsultacji publicznej).
- Reguły anonimizacji Portalu Orzeczeń (SO Warszawa, 2013): pkt 3.2 czas jawny poza datą urodzenia; pkt 3.3 nazwy organów/sądów
  jawne, ale miejsce (właściwość miejscowa) i wydział zakrywane; pkt 2.6/2.8 numery szkół, nazwa i adres placówki zakrywane —
  https://bip.warszawa.so.gov.pl/uploads/files/migration/mstoleczne/portalOrzeczen/REGULY_ANONIMIZACJI.doc
- UODO, Biuletyn 4/06/23 s. 14–15: imię rodzica + nazwa szkoły + klasa identyfikują osobę mimo pseudonimizacji —
  https://uodo.gov.pl/pl/file/4376

## Zasady (słowami)
1. **FIRMA tylko z dowodem** (jak OSOBA „udowodnij, że jesteś osobą”). Kandydat ze spaCy zostaje FIRMA, gdy ma:
   (a) formę prawną w wartości lub tuż za nią (także w następnej linii), (b) rzeczownik rodzaju firmy („Przedsiębiorstwo”,
   „Zakład”, „Agencja”, „Pracownia”…) + słowo wyróżniające (WIELKIE, z cyfrą, w cudzysłowie, nieznane słownikowi albo nazwisko),
   (c) imię + nazwisko lub nazwę JDG (dane osobowe — zawsze), (d) nazwę w cudzysłowie, (e) słowo z wielkiej litery nieznane
   polskiemu słownikowi (nie skrótowiec: „Testopolia”, „Remondis”, nie „GDDKiA”), (f) jest początkiem firmy udowodnionej w tym
   piśmie („AG-Complex” po „AG-COMPLEX Sp. z o.o.”). Bez dowodu — jawne. Słowo roli i numeracja na początku nie należą do nazwy.
   **Koszt:** firma z samych polskich słów, bez formy i rodzaju, wspomniana tylko tak (rzadkie) — jawna; nazwa osoby prawnej
   nie jest daną osobową (motyw 14); nazwiska w nazwach nadal zakrywa warstwa osób.
2. **Firma zakrywana bez względu na wielkość liter** („Strabag” = „STRABAG”). Przywróć oddaje wartość z mapy (zapis z pierwszego
   wystąpienia) — różnica wielkości liter, nie treści.
3. **Instytucja publiczna:** sama nazwa jawna („ZUS”, „Sąd Najwyższy”, „Urząd Skarbowy”, „KNF”); z tym, co ją zawęża —
   miejscowością („w Legnicy”), numerem („nr 18”), wydziałem — cała fraza INSTYTUCJA. Przed instytucją nie dokleja się słowo roli;
   miejscowością nie jest token.
4. **Data pisma jawna:** linia „Miejscowość, [dnia] DD.MM.RRRR [r.]” (albo odwrotnie), bez dwukropka, rok z ostatnich 5 lat.
   Każda inna data zakryta jak dotąd (urodzenia, zdarzenia, w zdaniu, w tabeli) — silnik nie odróżni jej od urodzenia.
5. **Wartość zakryta raz — zakryta wszędzie:** po wszystkich warstwach każda wartość z cyfrą (NUMER, KWOTA, ADRES, EMAIL,
   INSTYTUCJA) zastępuje swoje pozostałe dokładne wystąpienia tym samym tokenem.
6. **Guard R4 bez numerów strukturalnych:** „nr” po Dz.U./M.P./Dzienniku/Biuletynie (okno do 45 znaków, także przez koniec linii)
   albo po rzeczowniku porządkowym/aktu publicznego (załącznik, pytanie, droga, linia, decyzja, uchwała, LEX…); bez słowa-klucza
   wewnątrz tokenu; resztka obok tokenu to R3, nie R4. Numery umów, pism, dowodów, działek — nadal pytanie.

## Zmiany
1. **Nowy `backend/firma_proof.py`** — `firma_proof(text, ner_results)`, `has_proof`, `strip_role`; wołany w
   `ner_layer._process_ner` po filtrach (import + 1 linia; plik 597 → 599 l.).
2. `backend/firma_context.py` — rdzeń firmy z łącznikiem („AG-COMPLEX”) też jest rdzeniem (1 linia).
3. `backend/layers/ner_adapter.py` — podmiana FIRMA bez względu na wielkość liter (`_whole(value, ci)`).
4. `backend/layers/institution.py` — nowy wzorzec: rodzaj instytucji + miejscowość/numer, wydział; sama nazwa jawna.
5. `backend/layers/amount.py` — `_doc_date` (pominięcie daty pisma) dla `_DATE_PL_RE`.
6. `backend/layers/fallback.py` — `apply_value_propagation`; `backend/pipeline_new.py` — wywołanie po warstwie instytucji.
7. `backend/guard_residue.py` — R4: `_STRUCT_NR_RE`, klucz w tokenie, resztka obok tokenu.
8. Testy: nowy `backend/tests/test_firma_proof.py`; `tests/test_pseudominizer.py` (klasa instytucji przepisana na nową zasadę:
   sama nazwa jawna, z miejscem/numerem/wydziałem zakryta); `tests/test_map_fidelity.py` (fikstura „Beta Grupa” → „Betanex Grupa”:
   test dotyczy podmiany całych wyrazów, nazwa bez dowodu firmy przestała być FIRMA).

## Czego NIE ma (świadomie)
- Słowa obce w R1 („Display”, „Service”, „Southampton”) — nadal pytanie (wybór Pawła 23.10). Zmniejszenie wymaga listy słów
  angielskich jako „słów ze zwykłym znaczeniem” — nowy zasób, osobna propozycja dla Pawła.
- Numery norm („PN-EN ISO 7779:2005”) zakrywane jako NUMER (nadmiar) — osobna sprawa.
- Mobile: zasady 3–4 różnią Desktop od Mobile (Mobile zakrywa każdą datę, instytucje zostawia zawsze) — do wytycznych dla Mobile
  po merge (format tokenu/taksonomia bez zmian).

TASK_SCOPE:
- backend/firma_proof.py
- backend/firma_context.py
- backend/ner_layer.py
- backend/layers/ner_adapter.py
- backend/layers/institution.py
- backend/layers/amount.py
- backend/layers/fallback.py
- backend/pipeline_new.py
- backend/guard_residue.py
- backend/tests/test_firma_proof.py
- backend/tests/test_pseudominizer.py
- backend/tests/test_map_fidelity.py
- tasks/LYNX-FIRMA-PROOF/brief.md
- tasks/LYNX-FIRMA-PROOF/repo_before.hash
- tasks/LYNX-FIRMA-PROOF/round_01/implementation/DELIVERY.md

## Odbiór
- `tests/test_firma_proof.py` (nowy): nie-firmy bez dowodu, firmy z dowodem, słowo roli, początek udowodnionej firmy, OSOBA bez
  zmian, instytucja jawna/zakryta, data pisma, propagacja wartości, R4.
- Regresja: każdy plik `backend/tests/test_*.py` osobno na main i na gałęzi — bez nowych faili (lista w DELIVERY).
- Pomiar (powtarzalny, polecenia w DELIVERY): KIO 40 (pozycje panelu, firmy z formą prawną jawne przed/po), GOLD dev/test
  (`human_view.py`), `testset_owner/run_testset.py`, ślepy zbiór 600 dokumentów.
