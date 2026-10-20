# LYNX-OSOBA-REDESIGN — propozycja CC: jedno miejsce decyzji „czy to osoba” (2026-10-20)

STATUS: cc_proposal → Architekt (brief) → Codex precheck → szacunek CC / zgoda OWNERA → implementacja. Zastępuje K1a/K1b/K1c
(`LYNX-K1-PERSONS-FIRMS`, część OSOBA) i łatanie OSOBA zgłaszane w `LYNX-OCR-GATE-COMPARE` (etap 2b zostaje jako stan przejściowy).

## Dlaczego od nowa (OWNER 20.10, CC się zgadza)
Pozostałe typy tokenów (NUMER, ADRES, EMAIL, KWOTA) działają prawie dobrze; OSOBA nie — i każdy nowy plik testowy przynosi nowe błędy,
które dotąd zamykaliśmy pojedynczo („reagujemy na pojedyncze bugi, zamykamy źródło, pojawia się nowy plik… i tak bez końca”).
Przyczyna jest w budowie, nie w regułach: o osobie decyduje dziś kilka **niezależnych** miejsc, z których każde zakrywa samodzielnie:
spaCy (`ner_layer._process_ner` + filtry instytucji/prefiksów/geo), propagacja odmian, inicjały, imię przy osobie / po Pan/Pani,
od 20.10 samotne słowo ze słownika (`ner_adapter._apply_dictionary_names`). Nikt nie waży dowodów razem, a „przeciw” istnieje tylko
jako kolejne listy wyjątków dopisywane po błędach.
Dowody z jednego pliku Mobile (`testy/test_b_word_boundary_diacritics_08_07.txt`, ten sam wynik na main i gałęzi): spaCy oznacza jako
osoby nagłówki WIELKIMI LITERAMI (KONTROLA, OCZEKIWANE, MIESZANE) i słowa-typy tokenów (KWOTA, OSOBA, TOKEN) oraz „Anchor”,
„AddressEngine” → trafiają do mapy i profilu → fałszywe `MAP_LEAK [GLOBALNY_PLAIN]` Guarda w kolejnych tekstach; jednocześnie samotne
„Kowaliński” (spoza słownika 1000 nazwisk, bez kontekstu) zostaje jawne. Mobile (bez spaCy, słowniki + kontekst) ma tu 0 takich błędów.
HerBERT: nie przegrał żadnego wiarygodnego pomiaru (pilot Areny „oba gorzej” = artefakt arbitra; motywacja częściowo na niewiarygodnym
benchmarku 17.10; K1a ma zgodę na ~350 l. od 19.10, brief nie powstał). **Pozycja HerBERT — bez zmian względem ustalenia 19.10
(OWNER: „w testach pomagał i nie szkodził; sztuka — miejsce, w którym nie przeszkadza”; BOARD `LYNX-K1-PERSONS-FIRMS`):** ostatnia
warstwa na tekście już zamaskowanym, tylko na fragmentach wciąż jawnych; dokłada zakrycie albo pytanie, **nigdy nie zmienia ani nie
cofa** decyzji wcześniejszych warstw → brak regresji z konstrukcji. (Wersja `7ca10ba` tej propozycji błędnie stawiała HerBERT jako
główny, konkurujący sygnał — poprawione po uwadze OWNERA 20.10.)

## Projekt (do oceny Architekta)
1. **Kandydaci** (jeden przebieg na tekście po warstwach strukturalnych, przed instytucjami/fallback): spany 1–4 słów zaczynających się
   wielką literą w obrębie linii (w tym WIELKIE LITERY) i spany PER ze spaCy (także w środku zdania).
2. **Dowody za / przeciw (bez HerBERT — on działa po, pkt 3a) — każdy liczony niezależnie, zapisywany w śladzie decyzji:**
   - spaCy PER (obecny model);
   - Morfeusz: interpretacja imię/nazwisko vs wyłącznie pospolita/przymiotnik;
   - słowniki imion/nazwisk (pełne z Mobile, z progiem częstości ≥100 i wyczyszczone jak w Mobile `15e7e8c`/`2e9a232`);
   - kontekst w oknie (Pan/Pani, ur., PESEL, zam., „Imię i nazwisko:”, podpis, funkcja w umowie, przecinek „Kowaliński, Tomasz”);
   - przeciw: linia-nagłówek WIELKIMI LITERAMI bez innych dowodów, nazwy typów tokenów i słowa techniczne (CamelCase, `_`), słowo jest
     częścią instytucji/adresu/firmy już zakrytej, jedna wspólna lista wyjątków (`OSOBA_DENYLIST` Mobile + polityka OWNERA).
3a. **HerBERT jako ostatnia warstwa (ustalenie 19.10):** po decyzji z pkt 3 i po fallbacku, przed Guardem — PER/ORG tylko w miejscach
   wciąż jawnych (span nie przecina tokenu), przez te same dowody przeciw; wynik: dołożone zakrycie albo pytanie do Guarda. Mierzone
   wprost jako „co HerBERT dołożył”; wariant `herbert-polish-legal-ner-ocr` (odporny na OCR) do porównania; fail-closed jak NER.
3. **Decyzja trójstopniowa:** silne dowody → zakryj (OSOBA, z mapą i Przywróć jak dziś); słabe → **zapytaj** (Guard pokazujący resztę,
   `LYNX-GUARD-RESIDUE`); brak → zostaw. Progi i wagi wybierane na zbiorze znanym, kontrola na odłożonym; przy wątpliwości — zakryj
   albo zapytaj, nigdy cicho przepuść (polityka: nadmaskowanie zamiast wycieku).
4. **Jedna implementacja zamiast warstw rozproszonych:** nowy moduł (np. `backend/person_decision.py`), w istniejących dużych plikach
   tylko wywołanie (ratchet); obecne ścieżki OSOBA wyłączane po kolei za porównaniem baza vs gałąź, nie kasowane na ślepo.
5. **Wymagania wspólne z produktem:** ten sam token i polityka mapy (S1/S2), Przywróć 1:1, fail-closed przy awarii modelu (S3),
   brak danych w logach (S5), praca offline (`LYNX-OFFLINE-GUARANTEE`: HerBERT/onnxruntime bez sieci), budżet czasu (diagnoza:
   HerBERT 1–6 s do ~10 tys. znaków, ~40 s przy 63 tys. — Architekt ustala budżet albo dzielenie tekstu).

## Pomiar (miarka = cel produktu, nie procent jednej warstwy)
- Zbiory **naraz**, nigdy jeden plik: testy Mobile `testy/*.txt` (golden — porównanie z Mobile), `dataset_clean` Mobile (300, gold),
  syntetyki 50/100 (tekst z PP-OCRv6, narzędzie `chain_compare.py`), dokumenty dev OWNERA (17, lokalnie), firma_sweep.
- Miary: osoby jawne i niepokazane (dziury), pytania Guarda na dokument, nadmaskowanie per klasa (instytucja / słowo pospolite /
  nagłówek / typ tokenu), wpisy-śmieci w mapie (KWOTA/OSOBA/TOKEN jako osoba = 0), Przywróć 1:1, czas na długich dokumentach.
- Strażnik regresji `benchmark.py` (bez spadku), kryteria zapisane przed pomiarem; ocena okiem OWNERA na plikach porównawczych.
- Etapy w jednym Tasku (OWNER: mniej szwów): E1 pomiar obecnego stanu tą miarką + ślad dowodów (bez zmiany decyzji),
  E2 nowa decyzja za przełącznikiem, porównanie, E3 przełączenie i wyłączenie starych ścieżek.

## Do rozstrzygnięcia przez Architekta
Wagi/progi jako stałe vs prosty model (regresja logistyczna na śladzie dowodów); budżet czasu HerBERT; pełny słownik nazwisk (pamięć);
czy firmy (FIRMA) wchodzą od razu, czy po OSOBA; relacja z `LYNX-GUARD-RESIDUE` (proponuję: ten sam Task dla części OSOBA).
Czyszczenie profili ze śmieciowych wpisów OSOBA (KONTROLA, KWOTA…) — po wdrożeniu, osobną operacją na profilach testowych.
