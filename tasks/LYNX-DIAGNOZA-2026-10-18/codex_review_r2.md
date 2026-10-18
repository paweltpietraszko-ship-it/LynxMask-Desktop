# Wąska ocena korekty diagnozy — r2

**Werdykt: AKCEPTUJĘ. Uwagi R1–R5 zamknięte.**

- Data: 2026-10-18. Odbiorca: CC / Architekt.
- Exact SHA zaakceptowanego dokumentu: `4f6c38064f86e5aa93015f2abddef7527c811993`.
- Dokument: `arch/DIAGNOZA_2026-10-18.md`.
- Baza oceny: raport Codexa r1, `1679a3a49ad046fa796587a0373f1ad7ffbd4edb`; porównano cały zakres `1679a3a..4f6c380`, obejmujący także zapis potwierdzeń obserwacji Pawła w `e2e769b`.
- Zakres: wyłącznie merytoryczna korekta diagnozy. W tym zakresie zmienił się jeden plik dokumentacji; backend, frontend, narzędzia audytowe, specyfikacja i FROZEN.lock pozostały bez zmian.

## Zamknięcie uwag

| Uwaga r1 | Weryfikacja na 4f6c380 | Wynik |
|---|---|---|
| R1 — przyczyny a korzyść detektora | A1/A2 przypisano do NER-MULTILINE i utraty dopasowania już wykrytych encji. A5 rozdziela brak/fragment kandydata, utratę podmiany i powtórzenie. HerBERT dostarcza kandydatów; korzyść pozostaje hipotezą do potwierdzenia całym łańcuchem. Zapisano ograniczenie LOC/LOC_PUB. M1 dotyczy martwego seedu, przy zachowaniu informacji o działających zasobach pomocniczych. | ZAMKNIĘTA |
| R2 — różne napisy i wartości mapy | K2 ogranicza współdzielenie tokenu do identycznego napisu, wymaga dosłownego przywracania odmiennych wartości i zachowuje granicę pełna firma / goły zapis. Wyklucza dopisywanie formy, cudzych słów, sklejonego wyliczenia lub innej osoby. Nie wprowadza nowego formatu mapy ani alokatora. | ZAMKNIĘTA |
| R3 — status Guarda | §4/K4 wyraźnie określają ostrzeganie jako propozycję zależną od formalnego rozstrzygnięcia i zmiany S4/FROZEN.lock. Nadal obowiązują aktualne S4 oraz S3. Brak zgody na obejście blokady w tej diagnozie. | ZAMKNIĘTA |
| R4 — znaczenie pomiarów i ochrony | Rozróżniono miary wystąpień i ocenę dokumentu, zachowano znaczenie częściowego PII i jawnych powtórzeń. Oddzielono wynik obliczony od odblokowanego; A7 przeniesiono do utraty treści. Poprawne zachowania ograniczono do obejrzanych przykładów; odbiór Pawła nie zastępuje S1–S5. | ZAMKNIĘTA |
| R5 — poziom zamknięcia i zależności | §7 rozdziela wykrycie, zastosowanie spanu, wynik bez wskazanego PII, mapę/Przywróć i odbiór. K0 obejmuje MULTILINE/15K przed oceną korzyści K1; opisano wpływ C3/C6 oraz granice reguły K5 przez newline. Zachowano zadanie K1 według obszaru, odnośnik do dokładnych wejść i przyszły odbiór poza obejrzanym dev. Potwierdzenia Pawła dotyczą objawów i nie zamykają ich jako naprawionych. | ZAMKNIĘTA |

## Znaczenie akceptacji i dowody zachowane

Diagnoza na wskazanym SHA może stanowić podstawę do opracowania briefów według poprawionych zależności. Akceptuję spójność diagnozy, rozróżnienie potwierdzonych obserwacji od hipotez i skorygowany kierunek prac. Nie jest to akceptacja implementacji HerBERT-a, nowego słownika, szczegółowych reguł przyszłych Tasków ani zmiana PRODUCT_TRUTH/decyzja OWNERA.

Zachowuję dowody z r1: odtworzenie 17/17 dokumentów na backendzie zgodnym z `c63114a`, punktowe trace, próby seedu i historycznego adaptera oraz ich jawne ograniczenia. Dane i wyniki z treścią pozostają lokalnie; nie publikowano nowych danych rzeczywistych.

W r2 nie uruchamiano backendu, modeli, reproduktorów, testów ani benchmarku ponownie. Powodem jest wyłącznie dokumentacyjna zmiana i zamknięty zakres R1–R5. Nie rozszerzam wcześniejszych wyników na nowe SHA produktu, inne wejścia, UI, telefon ani przyszłą integrację.

Nie ma pozostałej uwagi blokującej do tej korekty. Następny krok: CC/Architekt przygotowuje briefy; formalne decyzje produktowe, w tym zmiana S4, pozostają w swoich zadaniach. Bez zmian kodu produktu i bez merge.
