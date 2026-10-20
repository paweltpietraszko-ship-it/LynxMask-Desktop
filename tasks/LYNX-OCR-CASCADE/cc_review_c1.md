# CC — recenzja wykonalności C1 (przed kodem), 2026-10-20

Podstawa: brief `d2664e3`, precheck Codexa PASS `e164352`. Brief ma linię `TASK_SCOPE:` (gate ją czyta).

## Wykonalność geometrii — próbka 2 obrazów (doc_00004, doc_00012, `dataset_20260627_095419`)
Jednorazowa sonda poza repo: PP (`ocr_rapid._get_engine`, jedno wywołanie) + Tesseract `image_to_data` (`pol`, `--psm 3`)
na tych samych bajtach PNG, linie Tesseracta z kluczy `block/par/line`, para = nakładanie pionowe >0,5 i poziome >0,5
(względem mniejszej ramki).
- **Ten sam układ współrzędnych:** PP zwraca ramki w pikselach oryginału (1240×1754), Tesseract też; `--psm 3` nie obraca
  obrazu. Na doc_00004 21/21 ramek PP ma dokładnie jednego kandydata (nakładanie pionowe 0,88–1,0, poziome 0,99–1,0);
  1 linia tylko u Tesseracta. Parowanie liniowe jest więc wykonalne prostą regułą, bez nowego frameworku.
- **doc_00004 (NIP):** PP gubi jedną cyfrę (zły kształt — 9 cyfr), Tesseract w tym samym polu czyta inną, też błędną wartość.
  Druga opinia **nie naprawia** tego przypadku → oczekiwany status `CONFLICT_REVIEW`, nie `PP_DISTORTED_TESS_VALID`.
  Uwaga dla C2: zły kształt identyfikatora po etykiecie „NIP:” jest wykrywalny już z samego odczytu PP.
- **doc_00012 (IBAN):** PP nie ma ramki w rejonie linii IBAN; Tesseract ma tam linię (oraz 4 kolejne linie, których PP
  nie zwrócił), ale odczyt jest nieczytelny, bez poprawnej sumy. Geometria **wykrywa brak pokrycia**, ale nie daje
  wartości do uzupełnienia → `PP_MISSING_TESS_PRESENT` bez kandydata z sumą kontrolną.
- Koszt na tej próbce: PP 1,5–1,9 s, Tesseract TSV 0,8–0,9 s na stronę.

Wniosek przed kodem: C1 jest wykonalne i warto je zrobić, ale uczciwa prognoza jest taka, że wartość kaskady
leży raczej w **wykrywaniu obszarów, których PP nie przeczytał** (alarm pokrycia), niż w „ratowaniu” cyfr sumą kontrolną
— Tesseract zawodzi zwykle na tych samych zdegradowanych fragmentach. C1 ma to zmierzyć na 50 + 100 obrazach; sonda
z 2 obrazów nie jest wynikiem.

## Doprecyzowania implementacyjne (w granicach briefu)
1. Sumy kontrolne: `python-stdnum` wprost (`stdnum.pl.pesel/nip/regon`, `stdnum.iban`) — ta sama biblioteka co warstwa
   walidacji produktu; bez nowego walidatora.
2. Etykiety gold: reużycie `benchmark_ocr_diagnostics.classify_miss` i stałych z `pp_quality.py` (hashe modeli) przez
   import, bez kopiowania.
3. Reguła parowania (zamrożona przed holdoutem): nakładanie pionowe i poziome >0,5 względem mniejszej ramki; więcej niż
   jeden kandydat lub ramka PP obejmująca kilka linii Tesseracta → `CONFLICT_REVIEW`/niejednoznaczne, nie scalanie.
4. Alarm pokrycia liczony osobno: linia Tesseracta bez pary PP z ≥1 znakiem alfanumerycznym; plus osobny licznik
   „linii-śmieci” (bez słowa ≥3 liter i bez ≥4 cyfr), żeby szum nie udawał pokrycia.

## Szacunek rozmiaru
- `tasks/LYNX-OCR-CASCADE/measure/paired_ocr.py` ≈ 300 l. (linie TSV, parowanie, sumy, statusy, dopasowanie gold, raport, CLI).
- `backend/tests/test_ocr_cascade_probe.py` ≈ 170 l. (7 grup kontrprób z briefu na sztucznych ramkach).
- Razem ≈ 470 l. (>150) → wymagana zgoda Pawła przed kodem.
