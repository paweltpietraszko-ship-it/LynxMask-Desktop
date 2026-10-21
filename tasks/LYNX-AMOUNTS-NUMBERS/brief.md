# LYNX-AMOUNTS-NUMBERS — kwoty i numery, których Desktop nie zakrywa, a Mobile tak (CC, 2026-10-21; poprawka bez Architekta)

Paweł 21.10: „kwoty bez zł i PLN nie są zamaskowane. Mobile maskuje. Jesteśmy do tyłu z regułami.” Źródło listy braków: porównanie
silników Mobile (`450204b`, test JVM) vs Desktop (`cc70822`) na tych samych 693 tekstach syntetycznych (testy Mobile, `dataset_clean`,
`dataset_stress`, `Pliki testowe`, teksty OCR obrazów benchmarku); diagnoza pomocnika CC na przykładach i sondach warstw (lokalnie
`%TEMP%\lynx_cc_review\mobile_compare\`, `%TEMP%\lynx_cc_review\kwoty_numery\`). Polityka: samo miasto nie jest PII (różnica
„Mobile maskuje miejscowość” to NIE brak Desktop); przy wątpliwości nadmaskowanie zamiast wycieku.

## Braki potwierdzone (realne przykłady, nie artefakty porównania)
- **A. Kwota słowna z cyframi** (~167 wystąpień, szablon „(słownie: 44 tysięcy 813 złotych)”): `verbal_amounts._mask_verbal_amounts`
  skanuje wstecz od waluty tylko po słowach liczebników, cyfry dopuszcza tylko w groszach → „44 tysięcy 813 złotych” jawne,
  „15 tysięcy złotych” → „15 KWOTA_001” (cyfra jawna). Sondy: „813 złotych”, „15 000 złotych”, „pięćset zł”, „dwadzieścia tysięcy zł”
  niemaskowane — `_CURRENCY_RE` nie zna gołego „zł”, `layers/amount.py` `_AMOUNT_RE` (:30–34) nie zna „złotych/złote/złoty”.
  Mobile: `AnchorEngine.kt:429–445` (A.9d, cyfra + mnożnik; zostawia „813 złotych”) i `StructuralEngine.kt:727–760`.
- **B. Kwota z groszami bez waluty w tabeli** (`Pliki testowe/doc_lvl3_faktura_zlecenie.txt`: „350,00   2 800,00”, „Razem 2 800,00”):
  `_AMOUNT_RE` wymaga waluty. Mobile: `AnchorEngine.kt:394–426` (A.9c, kształt liczby z 2 cyframi groszy).
- **C. Numer dokumentu po „nr”** (18 wystąpień: „UMOWA … nr U-00726/2025”, „nr Z-00931/2023”): `layers/numeric.py:17–19` zna tylko
  `UMW/\d{4}/\d{3,6}`; wzorzec ukośnikowy w `legal.py` wymaga 3+ segmentów. Mobile: `AnchorEngine.kt:597–625` (A.12: „nr/numer” +
  token z cyfrą i separatorami, bramka: słowo faktur|umow|zlecen… w 60 znakach wstecz).
- **E. Sygnatura komornicza wielkimi literami** („nr KM 8923/2023” → „/2023” jawne): `legal.py:21–28` `_CASE_SIG_RE` zna „Km”, nie „KM”.
- Bez zmian: KW — Desktop zakrywa (lepiej niż Mobile); pozostałe „sygnatury” z porównania to szum (telefony, komentarze plików testowych).

## Zakres
1. **A — `backend/verbal_amounts.py`:** skan wstecz od waluty akceptuje także liczby zapisane cyframi (grupy `\d{1,3}`, także „15 000”),
   gdy w zebranym fragmencie jest co najmniej jedno słowo liczebnika/mnożnika (tysięcy, milionów…); `_CURRENCY_RE` zna „zł”. Token
   obejmuje całą kwotę: od pierwszej cyfry/liczebnika po walutę i ewentualne „00/100” (lepiej niż Mobile — bez jawnego „813 złotych”).
2. **A/B — `backend/layers/amount.py`:** (a) waluta słowna w postaci cyfrowej: `złotych|złote|złoty|zł` po liczbie („813 złotych”,
   „15 000 złotych”); (b) drugi wzorzec KWOTA bez waluty: liczba z przecinkiem i dokładnie 2 cyframi groszy, tysiące oddzielone spacją
   (zwykłą lub twardą), np. „2 800,00”, „350,00”; bez cyfry, `.`/`,`+cyfra, `/`, `-` bezpośrednio przed i po; **nie** gdy za liczbą
   `%` lub jednostka (kg, g, m, m2, m²,
   km, l, szt, godz, h). Kropka dziesiętna nie (daty, wersje). Uruchamiany po wzorcu z walutą (dłuższe dopasowanie wygrywa).
3. **C — `backend/layers/numeric.py`:** numer po „nr”/„numer” (opcjonalnie „.”/„:”), zawierający cyfrę i (separator `/`, `-`, `.` albo
   ≥ 4 znaki), gdy w 60 znakach wstecz jest słowo zaczynające się od faktur|umow|zlecen|zamówien|aneks; maskowany sam numer (NUMER),
   „nr” zostaje. Nie dotyczy fragmentów już będących tokenem.
4. **E — `backend/layers/legal.py`:** `_CASE_SIG_RE` przyjmuje „KM/KMP/KO/KMS” w dowolnej wielkości liter (cała sygnatura z „/rok”).
- Bez zmian: format tokenów, `TOKEN_RE`, OCR-normalizer, spaCy, Guard, API, KW, adresy/miejscowości. Nie przenosimy fałszywych alarmów
  Mobile (numeracja listy „1. Os” jako KWOTA, daty „08.07”).

## ROZSZERZENIE CC (ta sama klasa co E — końcówka sygnatury jawna; dopisane przed kodem tej części)
Reproduktor: „Sprawa egzekucyjna nr KM 8923/2023” → `NUMER_001/2023`. Przyczyna: `layers/credentials.py` (wcześniej niż `legal`) —
wzorzec „Tablica rejestracyjna pojazdu” w `backend/credential_patterns.json` dopasowuje „KM 8923”, `legal` nie dostaje całości.
Zmiana: wzorzec tablicy nie dopasowuje, gdy bezpośrednio za nim jest „/cyfra” (`(?!/\d)`); całą sygnaturę bierze `_CASE_SIG_RE`.
Test: „nr KM 8923/2023” → jedna wartość „KM 8923/2023”; tablica „KR 4AB67” nadal NUMER.

TASK_SCOPE:
- backend/credential_patterns.json
- backend/verbal_amounts.py
- backend/layers/amount.py
- backend/layers/numeric.py
- backend/layers/legal.py
- backend/tests/test_amounts_numbers.py
- backend/tests/test_audyt_2026_10.py

`test_audyt_2026_10.py::test_wiernosc_tekstu_i_maskowanie` używał „Faktura nr 12/2026” jako stałego tekstu wokół e-maila — po zmianie C
numer faktury jest zakryty (zgodnie z Zakresem 3); w teście zmieniona tylko ta kotwica („Faktura nr NUMER_001. Kontakt”), sprawdzenie
wierności reszty tekstu i maskowania kontaktu bez zmian.

## Odbiór
Testy celowane (`test_amounts_numbers.py`, przez warstwy i `run_pipeline_new` bez anonymizera): „(słownie: 44 tysięcy 813 złotych)” → jedna
KWOTA bez jawnych cyfr; „15 tysięcy złotych”, „813 złotych”, „15 000 złotych”, „pięćset zł”, „dwadzieścia tysięcy zł” → KWOTA; tabela
z lvl3 („350,00   2 800,00”, „Razem 2 800,00”) → KWOTA; negatywne bez zmian: „12,50 kg”, „23,50%”, „wersja 1,05”, „08.07.2024”, „3,5 m2”;
„UMOWA … nr U-00726/2025”, „Faktura nr Z-00931/2023” → numer NUMER, „nr” jawne; „pokój nr 12” bez słowa dokumentu → bez zmian;
„nr KM 8923/2023” → cała sygnatura. Przywróć 1:1 (mapa zwraca dokładny oryginał) dla każdej nowej klasy.
Pomiar (pomocnik CC): ponowne porównanie Mobile vs Desktop tym samym narzędziem — klasy A/B/C/E znikają lub maleją, **żadna nowa klasa
„Desktop zakrył, Mobile nie” powyżej 5 wystąpień** bez wyjaśnienia (nadmaskowanie ocenione na przykładach); `/preview` przed/po na tych
samych zbiorach: osoby gold bez pogorszenia, liczba nowych KWOTA/NUMER z podziałem na prawdziwe/FP. Szacunek: ~45–55 l. kodu + ~60 l. testów.

## Znalezione przy okazji (zgłoszone osobno, nie w tym Tasku)
- Mapa zwrotna zapisuje wartość po OCR-normalizerze, nie oryginał („PO1P/00793300/9” → w mapie „POiP/00793300/9”) — Przywróć zwróciłby
  zmieniony numer (FINDING do sprawdzenia).
- Numer działki „711878.0052.5931/5” — Desktop zakrywa bez „/5”.
