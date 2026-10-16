# PROPOSAL 2026-10-16 — test szczelności na dużych słownikach + słownik „zawsze maskuj" w programie

Autor zapisu: CC (lokalnie), na podstawie rozmowy z OWNEREM 2026-10-16. Ocena merytoryczna CC w §4.
To zlecenie dla Architekta (brief), nie brief. Status w `BOARD.md`: LYNX-DICT-LEAKTEST.
Nic w tym pliku nie jest zamrożoną decyzją OWNERA (`AGENTS.md` → OWNER_INPUT_IS_A_PROPOSAL).
Architekt i Codex mogą każdy punkt zakwestionować z uzasadnieniem.

## 1. Propozycja OWNERA (dosłownie)

> „Musimy zrobić z dużego słownika nazwisk, imion, miast, testy, przepuścić po poprawkach przez silnik
> i to co nie będzie zamaskowane wprowadzić do czarnego słownika programu. On korzysta z niego i nasze
> wyjątkowe słowa też zostaną zamaskowane."

Słownik: **„czarny słownik"** w języku OWNERA = lista słów, które silnik **zawsze maskuje**.
UWAGA NA NAZWY: w kodzie `ner_blocklist.py` („blocklista") oznacza odwrotność — słowa, których NIE wolno
traktować jako encji. Słownik z tego zlecenia NIE trafia do `ner_blocklist.py`. Jego odpowiednikiem
w kodzie jest słownik profilu (trie, `layers/trie_layer.py`) / seed (`seed_profile.py`).

## 2. Kierunek wstępnie uzgodniony (rekomendacje CC, które OWNER wybrał spośród opcji)

To rekomendacje CC — OWNER wybrał je z przedstawionych opcji, co oznacza zgodę na kierunek, nie zamrożoną
decyzję. Jeśli architekt lub Codex widzi lepsze rozwiązanie, proponuje je z uzasadnieniem.

D1. **Miasta — tylko w adresie.** Nazwa miejscowości jest maskowana jako część adresu (ulica, kod,
    miasto). Samo „pracuje w Radomiu" zostaje. Test miast = zdania adresowe.
D2. **Nazwiska będące też słowami pospolitymi (Piątek, Mazur, Zając, Osoba, Zapłata) — tylko
    w kontekście.** Nie trafiają do słownika „zawsze maskuj". Maskowane, gdy stoją przy imieniu,
    tytule („pan", „pani", „mec.", „dr") lub etykiecie (PESEL, „pracownik", „dłużnik"). „W piątek"
    zostaje, „Jan Piątek" jest maskowany.
D3. **Słownik żyje w programie.** Plik dołączony do aplikacji, ładowany przy starcie u każdego
    użytkownika, aktualizowany z wersjami. Nie miesza się ze słownikiem użytkownika (użytkownik nie
    widzi tysięcy wpisów na swojej liście).

## 3. Źródła danych (istniejące)

| Dane | Desktop `backend/` | Mobile: GitHub `paweltpietraszko-ship-it/LynxMask` (master), `app/src/main/assets/` |
|---|---|---|
| Imiona + odmiany | `names_inflected.json` (199) | `names_inflected.json` (~3 600, ze zdrobnieniami) |
| Nazwiska | `surnames_top1000.json` (1 000) | `surnames_top1000.json`, `surnames_extended.json` (~38 800), `surname_suffixes.json` |
| Miasta + odmiany | `cities.json` (31 tys.), `cities_forms.json` | te same + `city_surname_overlap.json` (769 kolizji miasto/nazwisko) |
| Ulice | `street_names.json` | `street_names.json` |
| Generator zdań | `audyt/rota_leak_test.py` (36 zdań koordynatora, Morfeusz) | — |
| Narzędzie „niezamaskowane → słownik" | `dict_auto_builder.py` (z wyników benchmarku) | — |

Morfeusz 2 (już zależność) daje kwalifikatory `imię` / `nazwisko` / `nazwa_pospolita` / `nazwa_geograficzna`
— mechaniczne rozstrzygnięcie D2 bez ręcznych list (`arch/FINDING_2026-10_MOBILE_PORT.md` §5a).

## 4. Ocena merytoryczna CC (do uwzględnienia w briefie)

1. **Kolejność:** dopiero po LYNX-T01 (filtr prefiksów NER), LYNX-T03 (alokacja tokenów) i decyzji
   w LYNX-T04 (seed). Dziś 30% form ucieka przez T01 — słownik zbudowany przed poprawkami spuchłby
   o wpisy, które silnik ma łapać sam.
2. **Brak cyrkularności:** słownik budowany z jednej części danych, pomiar szczelności na rozłącznej
   części lub innym źródle — inaczej test z definicji daje 100%. Raport musi podawać szczelność
   silnika BEZ słownika i Z nim osobno.
3. **Ochrona przed FP:** kandydat do słownika, którego Morfeusz zna jako `nazwa_pospolita` lub
   `nazwa_geograficzna` (albo jest w `city_surname_overlap.json`), nie wchodzi do słownika (D2/D1);
   trafia do osobnej listy kontekstowej. Test FP: zdania bez osób („w piątek", „zapłata",
   „w Radomiu") nie mogą być maskowane.
4. **Jedna osoba = jeden token** (wszystkie formy odmiany pod jednym tokenem), formy żeńskie
   nazwisk, tokeny 3-cyfrowe zgodne z `arch/spec.md` S2 — problemy z BUG-SEED-DEAD.
5. **Reuse:** rozszerzyć `dict_auto_builder.py` / `audyt/rota_leak_test.py`, nie pisać nowego narzędzia.
   Słownik programowy (D3) to dane, nie nowa warstwa — wpięcie przez istniejący trie lub warstwę
   słownikową na końcu (Mobile W4a „zbieracz resztek" — konflikt z obecnym L0b w Desktop, do decyzji
   architekta w ramach briefu, z uzasadnieniem).
6. **Raport szczelności = artefakt RODO** (por. integracja z Rotą, `ODLOZONE.md`): liczba form,
   przepuszczone przed/po, FP, data, SHA silnika; powtarzalny jednym poleceniem.
7. **Rozmiar:** ~38 800 nazwisk × odmiany → setki tysięcy form; ocenić wpływ na start i RAM trie
   (dziś `pickle`, BUG-S5-TRIE-PLAINTEXT — słownik programowy nie zawiera danych użytkownika, więc
   jawny plik jest tu akceptowalny, ale nie może się mieszać z trie profilu).

## 5. Poza zakresem (pokusy)

- Maskowanie miast poza adresem (wykluczone przez D1).
- Dopisywanie czegokolwiek do `ner_blocklist.py` w tym zadaniu.
- Zmiana formatu tokenu / TOKEN_RE (S2, osobno LYNX-T08).
- Import słownika do profilu użytkownika (wykluczone przez D3).

## 6. Rozszerzenie 2026-10-16: pomiar stanu silnika (propozycja CC, OWNER: „dopisz”)

Kontekst: OWNER nie przetestuje ręcznie tylu dokumentów, ile przerobi pomiar automatyczny; obecny benchmark
(`benchmark.py`/`generator.py`) jest użyteczny jako regresja przed/po (T01: wykrył nowe FP, których nie złapały testy),
ale jego liczby bezwzględne nie opisują silnika (`LynxMask/docs/BRIEF_Wlasciciel_Benchmark_v2.md`, 2026-06-22:
OCR zmieszany z silnikiem; generator z tych samych list co słownik; KWOTA i warianty OCR liczone jako FP;
klucze GT spoza mapowania — np. `autor` — liczone jako FP). Propozycja: test szczelności z §1–4 jako część
jednego pomiaru o trzech osobnych warstwach, bez jednej zbiorczej liczby.

**M1. Szczelność silnika na czystym tekście (bez OCR).** Szablony zdań z realnych rodzajów pism (pismo urzędowe,
faktura, umowa, pytanie koordynatora) × encje z danych ROZŁĄCZNYCH ze słownikiem silnika (np. Mobile
`surnames_extended.json`, imiona spoza `names_inflected.json`) × generowane warianty: 7 przypadków, formy żeńskie
i odmężowskie, CAPS, brak polskich znaków, inicjały, nazwiska dwuczłonowe, tytuł przed nazwiskiem („mec.”, „Pan”,
„dr”), nazwisko w dopełniaczu po rzeczowniku („wniosek Kowalskiego”), sąsiedztwo tokenu i interpunkcji.
Wynik: macierz wycieków (forma jawna w wyniku) wariant × kategoria (OSOBA, FIRMA, ADRES, PESEL/NIP/IBAN, telefon,
e-mail), z przykładami. Odpowiada na pytanie „co przecieka”, a nie „ile procent”. Wzorzec: `holdout_measure.py` z T01.

**M2. Zbiór bez PII (fałszywe trafienia wprost).** Zdania, w których nie ma żadnej danej osobowej, ale są pułapki:
ulice patronimiczne, instytucje (sądy, SKO, urzędy), nazwiska będące słowami pospolitymi („w piątek”, „zapłata”),
miasta poza adresem (kierunek D1), nagłówki CAPS, akronimy, kwoty, daty. Każdy token = FP, bez dopasowywania do GT.

**M3. Wierność tekstu.** Zamaskuj → Przywróć → porównanie z oryginałem: ile znaków zmieniło się POZA spanami tokenów
(sklejanie spacji, OCR-normalizacja słów — BUG-GLOBAL-SPACE-GLUE, BUG-OCR-NORMALIZER-WORDS, BUG-UNMASK-FIDELITY;
audyt: dziś 0/7 dokumentów wraca 1:1).

**Wymagania:** deterministyczny (ziarno), uruchamiany jednym poleceniem, bez backendu HTTP i bez profilu użytkownika
(profil tymczasowy), wynik z SHA silnika i datą (artefakt RODO z §4 pkt 6); porównanie przed/po dla każdego Tasku
silnika. OCR oceniany osobno jako bramka przyjęcia dokumentu (zgodnie z briefem z 22.06), nie mieszany z M1–M3.

**Ograniczenie (świadome):** pomiar nie wykryje klas błędów, których nikt nie przewidział w wariantach
(„dokument #101”, `LynxMask/MASTER_LynxMask_Mobile.md` §7) — okresowy przegląd realnych dokumentów pozostaje
uzupełnieniem, nie główną metodą. Kandydaci na słownik programu (§1–4) wynikają z M1, akceptowani tylko po M2.
