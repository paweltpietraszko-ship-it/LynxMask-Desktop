# Hipoteza Guarda: każde jawne słowo wielką literą w środku zdania

23.10.2026, Codex, na pytanie Pawła. **Diagnostyka, nie zmiana briefu ani wdrożenie reguły.**

## Materiał i metoda

40 dokumentów **GOLD dev**; zapisane wyniki silnika `9f8a07e5eb8f0500c872ac1478c597036b1f80e3` z audytu LYNX-OSOBA-HANDOFF r3. Bez ponownego uruchamiania silnika/OCR/modeli. Nie czytano GOLD test. To obecny silnik, nie jeszcze niezaimplementowany redesign.

Sprawdzono jawne słowa zaczynające się wielką literą (także CAPS), pomijając tokeny maskowania i pierwszy token segmentu zdania. Prosta segmentacja po `.!?`, dwa warianty dla końca linii: traktowany jako granica albo nie. Bez językowego rozpoznawania skrótów. Wyniki są przybliżeniem skutków tej konkretnej definicji „środka zdania”, nie testem gotowej reguły językowej. Nie stosowano białej listy ani filtrów kontekstu, bo pytanie dotyczyło **wszystkich** takich słów.

Stan dotychczasowy: 49 ostrzeżeń wszystkich kategorii (1,23/dok.), w tym 24 wystąpienia R1 (0,60/dok.). Po połączeniu identycznej pisowni bez względu na wielkość liter: 20 grup R1 w 40 dokumentach (0,50/dok.).

## Liczba wskazań

| Miara, 40 dokumentów | Koniec linii = granica | Koniec linii nie kończy zdania |
|---|---:|---:|
| Wystąpienia objęte nową regułą | 337 | 574 |
| Średnio wystąpień/dokument | 8,43 | 14,35 |
| Różne słowa w obrębie dokumentu, suma | 295 | 490 |
| Średnio różnych słów/dokument | 7,38 | 12,25 |
| Mediana różnych słów/dokument | 8 | 12,5 |
| Maksimum różnych słów w dokumencie | 11 | 18 |
| Wskazania nakładające się na oznaczone PII | 79 | 80 |
| Wskazania nakładające się na oznaczone **not_pii** | 187 | 347 |

Grupowanie różnych słów to przybliżenie obciążenia panelu ×N, nie uruchomiony test UI. Obejmuje wyłącznie nową regułę; pozostałe ostrzeżenia nie znikają. Liczb wskazań nakładających się na PII nie należy utożsamiać z liczbą nowych wykrytych osób: mogą to być fragmenty tej samej pozycji i danych już objętych dotychczasowym pytaniem.

W ostrożniejszym wariancie co najmniej 187/337 (55,5%) wskazań trafia w fragmenty gold jawnie oznaczone jako nie-PII. Pozostałych 150 nie ogłaszam automatycznie prawdziwymi alarmami. Definicja gold not_pii jest węższa niż „wszystko, co nie ma etykiety PII”.

## Korzyść ochronna

Zapisane rzeczywiste statusy pozycji bazowych zostały odczytane z `items_dev.jsonl`; odtwarzają 1097 zakrytych / 35 z ostrzeżeniem / 20 cichych. Nie odtwarzano starych offsetów ostrzeżeń przez globalne wyszukiwanie słów do oceny zysku — zapis widoku ich nie zachował.

Nowe wskazania same w sobie pokrywają wszystkie jawne fragmenty **7 dotąd cichych pozycji**:
- 1 OSOBA,
- 6 FIRMA.

W obu wariantach segmentacji te same 7 pozycji dostałoby wskazanie. Przy zachowaniu dotychczasowych ostrzeżeń liczba cichych pozycji wyniosłaby **co najwyżej 13 zamiast 20**; zysku mieszanego pokrycia stare+nowe nie doliczano bez dokładnych starych offsetów. OSOBA: dotychczasowe 1 ciche / 9 z ostrzeżeniem -> 0 cichych / 10 z ostrzeżeniem w tej próbce.

Pokrycie jest oceną według dotychczasowej miarki literalnych jawnych fragmentów GOLD; nie jest uniwersalnym dowodem ochrony semantycznej dokumentu.

## Ocena

Reguła ma realną wartość jako szeroka siatka: w tej próbce podniosła do decyzji człowieka jedno wcześniej pominięte nazwisko i sześć pozycji FIRMA. Nie można jej odrzucić jako pozbawionej korzyści.

Koszt jest jednak duży: około **7–12 różnych słów na dokument** zamiast 0,5 grupy R1 na obecnym GOLD dev, a liczne pytania dotyczą znanych nie-PII. To nie mieści się w docelowym obciążeniu 2–4 R1/dokument z briefu. Nie przeliczam tych średnich na 255 dokumentów publicznych — materiał i dziedziny są inne.

Pełna reguła „o wszystko” pytałaby też o część słów, które biała lista lub pewny kontekst obecnie celowo wyłączają. Jej ewentualne wprowadzenie zmieniałoby kontrakt; nie zrobiono tego podczas analizy. Ewentualny wariant z wyjątkami wymaga osobnego opisania i pomiaru, ponieważ przestaje być sprawdzoną tu regułą bez filtrów.

Nie wybieram teraz progów/wyjątków za Architekta. Hipotezę można zachować jako **diagnostyczny punkt odniesienia pokrycia i kosztu pytań** dla E1. Wynik obecnego silnika nie przewiduje liczby pytań po nowym decyderze, który ma zakrywać więcej rzeczywistych osób.

## Odtworzenie

`analysis/capital_whatif.py <katalog_audytu> <dataset_gold_20261022/dev>`

Katalog audytu zawiera zapisane `gold_out/views/dev_*.txt`, `gold_out/items_dev.jsonl` oraz kopię wcześniejszej miarki `tasks/LYNX-GOLD-SET/measure/human_view.py`. Skrypt wykorzystuje wyłącznie funkcje mapowania i oceny z miarki; nie importuje/uruchamia jej pętli silnika. Dane lokalne i widoki nie są publikowane w repo. Raport zawiera tylko agregaty.
