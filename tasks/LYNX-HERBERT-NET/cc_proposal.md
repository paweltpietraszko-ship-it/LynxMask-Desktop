# LYNX-HERBERT-NET — propozycja CC: HerBERT jako ostatnia siatka bezpieczeństwa (2026-10-21)

STATUS: cc_proposal → Architekt (brief) → Codex precheck → CC szacunek / zgoda OWNERA → implementacja → audyt → merge na słowo OWNERA.
Zastępuje K1a z `LYNX-K1-PERSONS-FIRMS` (wariant „siatka na resztki” 19.10). Kolejność Architekta z briefu MANUAL-REVEAL v4/v5:
„po MANUAL-REVEAL osobny K1a HerBERT jako ostatnia siatka na nadal jawne fragmenty” — MANUAL-REVEAL zmergowany `c426211`.

**Paweł 21.10:** „Teraz kończymy budowę architektury programu, wkładamy HerBERTa. Jeśli się okaże, że nic nie wnosi, to go wyłączymy
lub usuniemy. Ustalaliśmy, że będzie siatka bezpieczeństwa na końcu pipeline, a nie konkurent spaCy. Ale może to on powinien iść jako
pierwszy, a spaCy na koniec — ja nie wiem, oceń zasadną architekturę.”

## Ocena CC: HerBERT na końcu (siatka), NIE na początku — z pomiarem, który rozstrzygnie zamianę później
Zachowane ustalenia: 19.10 (Paweł: „w testach pomagał i nie szkodził; sztuka — miejsce, w którym nie przeszkadza”), 20.10 (CC błędnie
proponował HerBERT jako główny sygnał — Paweł poprawił: ostatnia warstwa, dokłada, nigdy nie cofa). CC po ponownej ocenie podtrzymuje:
1. **Brak regresji z konstrukcji.** Siatka na końcu działa tylko na tym, co nadal jawne; nie zmienia ani nie cofa żadnej decyzji
   wcześniejszych warstw → wszystko, co dziś jest zakryte, zostaje zakryte. HerBERT na początku zastępuje spaCy w każdej decyzji
   o osobie → każde dzisiejsze poprawne zakrycie wraca do gry i wymaga pełnego ponownego pomiaru i naprawiania.
2. **Brak dowodu, że HerBERT jest lepszy od spaCy.** Jedyne porównania to pilot Areny („oba gorzej” = artefakt arbitra) i benchmark
   17.10 (wycofany jako niewiarygodny). Zamiana kolejności bez dowodu = zakład.
3. **Koszt błędu siatki jest dziś niski:** gdy HerBERT zakryje za dużo, użytkownik odkrywa to jednym kliknięciem (MANUAL-REVEAL,
   zgodnie z polityką „nadmaskowanie zamiast wycieku”). Gdy HerBERT jako pierwszy przepuści osobę, której spaCy by nie przepuścił —
   wyciek bez ostrzeżenia.
4. **Rozstrzygnięcie na danych, w tym samym pomiarze:** obok „co dołożyła siatka” mierzymy osobno HerBERT sam vs spaCy sam na tym samym
   gold (osoby: trafione / przegapione / fałszywe). Jeśli HerBERT wyraźnie wygrywa — osobna propozycja zamiany kolejności, z liczbami.
   Jeśli siatka nic nie wnosi — wyłączamy (przełącznik) albo usuwamy, jak chce Paweł.

## Zakres proponowany
- **Miejsce:** `backend/pipeline.py` → `_apply_guard(text, reverse_map, state)` — wspólne dla obu ścieżek pipeline; siatka tuż przed
  Output Guardem (w pliku tylko wywołanie; ratchet rozmiaru). Logika w nowym module `backend/herbert_net.py`.
- **Działanie:** HerBERT (ONNX, `herbert-polish-legal-ner`, model kwantyzowany, tokenizer `tokenizers`) czyta cały tekst (kontekst), ale
  wynik bierzemy **tylko ze spanów w całości jawnych** (nie przecinają tokenu). PER → zakrycie jako OSOBA przez istniejący mechanizm mapy
  (ten sam token dla tej samej wartości, Przywróć 1:1). Filtry przeciw: nazwy typów tokenów, słowa techniczne, nagłówki WIELKIMI
  LITERAMI bez innych dowodów, instytucje (te same listy co dziś). ORG/LOC/ID — w pierwszej wersji **tylko mierzone**, nie stosowane
  (FIRMA ma osobną politykę). Próg pewności PER — z pomiaru na znanym zbiorze, nie na kontrolnym.
- **Przełącznik** (domyślnie włączony, gdy model jest; `LYNX_HERBERT=off` wyłącza) — żeby „wyłączyć, jeśli nic nie wnosi” było jednym
  ustawieniem.
- **Awarie (do decyzji Architekta, propozycja CC):** model wymagany, gdy siatka włączona — wpis w `startup_check` (jak spaCy); błąd
  inferencji w trakcie → S3 fail-closed jak NER (siatka bezpieczeństwa, która cicho nie działa, jest gorsza niż brak). Weryfikacja SHA256
  modelu; tylko pliki lokalne (`backend/models/herbert/`, jak modele OCR; dostarcza instalator); telemetria ONNX wyłączona (już jest).
- **Czas:** diagnoza 18.10: 1–6 s do ~10 tys. znaków, ~40 s przy 63 tys. — dzielenie długich tekstów na okna z zakładką i ten sam limit
  wątków ONNX co OCR (6). Budżet czasu do ustalenia przez Architekta.
- **Zależności:** nowy pakiet `tokenizers` w `backend/requirements.txt`; licencja modelu CC BY 4.0 — atrybucja w aplikacji/README.

## Pomiar (miarka = cel produktu; wykonanie: pomocnik CC, Codex odtwarza)
Zbiory naraz: `dataset_clean` Mobile (300, gold), testy Mobile `testy/*.txt`, benchmark 50 obrazów (przez PP), firma_sweep, dokumenty dev
OWNERA (lokalnie, tylko agregaty). Miary:
1. **Co dołożyła siatka:** liczba dołożonych zakryć; każde sklasyfikowane: prawdziwa osoba dotąd jawna (zysk) / nadmaskowanie (koszt,
   z klasą: słowo pospolite, nagłówek, instytucja, miasto); dziury przed/po; wpisy-śmieci w mapie = 0.
2. **HerBERT sam vs spaCy sam** na tym samym gold osób (trafione / przegapione / fałszywe) — podstawa ewentualnej zamiany kolejności.
3. Strażnik `benchmark.py` (bez spadku), Przywróć 1:1, czas na dokument (mediana/p95, długi dokument), RAM.
4. Plik porównawczy przed/po do oceny okiem OWNERA.
Kryterium „wnosi”: ≥1 prawdziwa osoba odzyskana na zbiorach przy akceptowalnym nadmaskowaniu (próg do ustalenia z OWNEREM przed pomiarem).

## Szacunek CC
`herbert_net.py` ~150 l., wywołanie w `pipeline.py` ~5 l., `startup_check` ~10 l., testy ~120 l., requirements 1 l. — razem ~290 l.
(>150 → zgoda OWNERA przed kodem; zgoda na ~350 l. dla K1a z 19.10 dotyczyła tego samego zakresu).

## Do rozstrzygnięcia przez Architekta
Fail-closed vs wyłączenie siatki przy awarii; budżet czasu i okna dla długich tekstów; próg PER; czy ORG wchodzi w tym Tasku;
relacja z `LYNX-OSOBA-REDESIGN` (proponuję: siatka niezależna, redesign później w tym samym miejscu łańcucha nic nie zmienia).
