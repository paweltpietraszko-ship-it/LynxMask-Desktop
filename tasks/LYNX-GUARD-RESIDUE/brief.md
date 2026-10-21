# LYNX-GUARD-RESIDUE — brief Architekta v1.2: ostrzegaj, wymagaj decyzji, blokuj wyjście

**2026-10-21 · READY_FOR_CODEX / BRIEF_ONLY.** Tylko kontrakt, bez implementacji. Źródło decyzji OWNERA: `BOARD.md` → „DECYZJA OWNERA 21.10 — GUARD”. Propozycja zmiany zamrożonego S4 leży osobno w `tasks/LYNX-GUARD-RESIDUE/s4_change_proposal.md` — to **NIE jest jeszcze aktualizacja PRODUCT_TRUTH**. Dotychczasowy S3 pozostaje bez zmian. Zmiana S4 wymaga formalnego zatwierdzenia, oddzielnego commitu i `guard.py freeze --recompute`.

**Korekta zakresu 21.10 (Codex na polecenie Pawła, po wyjaśnieniu audytu r1):** Guard pyta, użytkownik zakrywa lub świadomie zostawia, po obsłużeniu wszystkich ostrzeżeń można zapisać dokument. Wycofano C1 audytu dotyczące kryptograficznego potwierdzania treści klientowskiego blobu. Pozostaje bramka statusu bieżącego dokumentu i osobne S3. Architekt zamyka opis C2 w poniższej macierzy v1.2 (to propozycja do świeżego prechecku, NIE PASS Codexa). Nie ustala to nowego silnika reguł ani nie zatwierdza frozen S4.

## Efekt dla użytkownika

Po dotychczasowym silniku (w tym opcjonalnym HerBERT) Guard **nie maskuje tekstu automatycznie**. Pokazuje tylko jawne, podejrzane fragmenty w istniejącym ekranie, np. `Marcin S.`, `Śludkowskiego`, resztę numeru lub fragment uszkodzony przez OCR; każdy z krótkim powodem. Pytania wyłącznie o to, co pozostało jawne. Jedno ostrzeżenie można rozstrzygnąć `Zakryj` lub `Zostaw`. **Nie ma „Zostaw wszystko” ani „zapisz mimo ostrzeżeń”.** Gdy brak ostrzeżeń lub każde zostało obsłużone dla aktualnego wyniku, odblokowują się **Kopiuj tekst, Zapisz do biblioteki oraz eksport/udostępnianie obsługiwane przez aplikację**. Nierozstrzygnięte ostrzeżenia = bramka STOP dla tych operacji, ale można poprawiać i czytać podgląd.

**`Zakryj`:** zastosuj istniejącą ścieżkę dodania wartości do maskowania, ponów pseudonimizację i kontrolę Guarda na zmienionym wyniku, z aktualną mapą. **`Zostaw`:** świadome potwierdzenie *konkretnego* wystąpienia/ostrzeżenia; nigdy zbiorowa akceptacja. Jeśli użytkownik wybiera zapamiętanie „Zostaw” na przyszłość, musi być to osobna świadoma opcja w bezpiecznej allowliście (jak Mobile), a nie automatyczna globalna whitelist każdego wystąpienia podobnego słowa. Nie zmieniać formatu `.lynxdict`.

**Stan i błędy:** `DO_OCENY` (≥1 ostrzeżenie), `GOTOWE` (0 nierozstrzygniętych na aktualnym wyniku) oraz odrębne `AWARIA_S3` (silnik/Guard/NER nie działa; bez kopii, eksportu lub archiwizacji i bez opcji `Zostaw`). Każde nowe przetworzenie/zmiana danych, profilu, allowlisty lub ręczne `Odkryj` mogące odsłonić dane **unieważnia wcześniejsze dopuszczenie do wysłania**; użytkownik dostaje aktualną ocenę/ponowne potwierdzenie. `Odkryj` jednej pozycji i kanoniczny mianownik po `Przywróć` są zaakceptowane przez OWNERA; nie wprowadzać mapy odmian ani nowej logiki OSOBA.

**Interfejs przy błędzie:** „Dokument nie jest gotowy do wysłania. Sprawdź i rozstrzygnij [N] ostrzeżeń — wybierz Zakryj albo Zostaw przy każdym fragmencie.” Przy S3: „Nie udało się sprawdzić dokumentu. Nie można go zapisać ani udostępnić. Spróbuj ponownie; jeśli problem się powtarza, zgłoś błąd.” Nie udawać, że aplikacja kontroluje ręczne wysłanie treści innym programem poza LynxMask.

## C2 — dokładny zakres ostrzeżeń v1 (do BRIEF_ONLY, bez rozszerzeń)

**Wejście = wynik po obecnym pipeline**, przed ewentualnym kopiowaniem/archiwizacją. Wszystkie klasy działają **tylko na nadal jawnych fragmentach** i nie obejmują znaków wewnątrz `KATEGORIA_NNN`. **Pierwsza wersja obejmuje dokładnie 4 rodziny** poniżej; nie domyślamy się innych klas ani nie budujemy ogólnego klasyfikatora PII. **Wyniki istniejących wzorców HIGH/MEDIUM i MAP_LEAK także zawsze są ostrzeżeniami** (nie znika żadna dotychczasowa detekcja; nie wykonujemy automatycznego `[REDACTED]`). Każde **wystąpienie** ma pozycję w bieżącym tekście, kategorię przyczyny i osobny wybór użytkownika.

**R1 — nierozpoznane prawdopodobne nazwy osób.** Jawne słowa z wielkiej litery w środku zdania, których nie da się bezpiecznie uznać za pospolite/techniczne, oraz jawne słowa z wielkiej litery potwierdzone jako imię/nazwisko przez **już istniejące** formy Mobile/Morfeusza, nawet gdy mają również znaczenie pospolite (np. `Baran`, `Maj`). Nie wymyślać nowych list nazwisk; wykluczenia istniejących list technicznych, nagłówków i instytucji. Dla spornych homonimów preferować pokazanie do decyzji, nie automatyczne zamaskowanie.
**R2 — inicjał przy osobie.** Jawny inicjał bezpośrednio przy jawnym imieniu, np. `Marcin S.`, albo jawny samotny inicjał po istniejącym tokenie `OSOBA_NNN`. Nie maskować ani nie obejmować ostrzeżeniem części istniejącego tokenu.
**R3 — szczątki po częściowej podmianie/OCR.** Jawne resztki związane bezpośrednio z już zakrytym identyfikatorem/adresem, np. cyfra przy etykiecie `NIP` i tokenie `NUMER_NNN`, uszkodzony fragment kodu pocztowego lub ulicy tuż przy `ADRES_NNN`. Sama cyfra w numerze listy nie wystarcza. Nie rekonstruować danych ani nie poprawiać OCR — tylko wskazać podejrzenie.
**R4 — nierozpoznane identyfikatory w jawnie znaczącym kontekście.** Np. `nr działki 128/7`, `identyfikator klienta AX72B-91C`, `ur. 03.11.1993`, `tel. 123 456 789` jeżeli całe pozostają jawne. Krótkich liczb, dat lub ciągów alfanumerycznych bez kontekstu **nie** traktować hurtowo jako PII; nie łapać daty zwykłego pisma, sygnatury sądowej i cytatu przepisu.

**Macierz odbioru — lokalny syntetyczny tekst już po maskowaniu (wskazany span = JAWNY fragment do ostrzeżenia; nigdy token):**

| Wejście do Guarda (syntetyk) | Oczekiwane ostrzeżenie na spanie | Powód |
|---|---|---|
| `Świadek Śludkowskiego nie stawił się.` | `Śludkowskiego` | R1: rzadkie nazwisko w środku zdania |
| `W protokole zeznawał Baran.` | `Baran` | R1: homonim nazwiska i słowa pospolitego |
| `Maj przekazał protokół.` | `Maj` | R1: znana forma nazwiska; początku zdania nie wyłączaj automatycznie |
| `Wezwano Marcina S. na rozprawę.` | `S.` (lub cały jawny `Marcina S.`, jeśli nie został zamaskowany) | R2: inicjał przy imieniu |
| `Przesłuchano OSOBA_001 S.` | `S.` | R2: nie ruszać tokenu |
| `NIP: 7 NUMER_021` | `7` | R3: resztka przy etykiecie i tokenie |
| `ADRES_003, 32-5 00 Chrzanow` | `32-5 00` | R3: połamany kod pocztowy przy tokenie, nie dopisywać automatycznie miasta |
| `nr działki 128/7` | `128/7` | R4: identyfikator działki |
| `data urodzenia: 03.11.1993` | `03.11.1993` | R4: data urodzenia |
| `NIP: NUMER_021` | **brak nowego ostrzeżenia R3** | wszystko już zakryte |
| `Maj był chłodnym miesiącem.` | **może zostać wskazane `Maj`** | świadomy FP dla homonimu, oceni człowiek, nie wymagaj bezbłędnej semantyki |
| `RODO, art. 5 ust. 1.` | **brak R1–R4** | techniczny skrót/cytat prawa |
| `Sygn. akt II K 128/26.` | **brak R1–R4** | sygnatura, nie samodzielnie PII |
| `Warszawa, dnia 21.10.2026 r.` | **brak R1–R4** | samotne miasto i data pisma |
| `Sąd Rejonowy, INSTYTUCJA_001` | **brak R1–R4** | instytucja jawna zgodnie z polityką, token pomijamy |
| `OSOBA_001, FIRMA_002, ADRES_003` | **brak ostrzeżeń** | bez pozostałego jawnego podejrzenia |

**Pierwszeństwo i eliminacja powtórek:** ten sam fizyczny span wykryty przez dwie rodziny = **jedno** ostrzeżenie z wieloma powodami; nie wolno pokazywać użytkownikowi tej samej pozycji dwa razy. Jeśli dopasowanie przekracza token, skrócić do wiarygodnego jawnego fragmentu lub nie zgłosić; nigdy nie wskazywać tokenu jako jawnego PII. Nazwy miast bez powiązania z innym podejrzeniem i instytucje publiczne nie są w v1 powodem ostrzeżenia. Zbyt krótki/niewiarygodny odczyt OCR nie ma tworzyć automatycznej odmowy, ale awaria reguł Guarda to S3.

**STOP scope:** brak w v1 pełnej analizy kontekstu prawnego, rozbudowy słowników, dopasowań semantycznych, uczenia modelu, naprawiania OCR, przerabiania wszystkich REGEX-ów i trwałego logu. Po implementacji CC może zmierzyć FN/FP i zaproponować kolejny Task, ale **nie poszerza tych czterech rodzin bez nowej zgody**.

## Minimalna implementacja, żadnego nowego silnika

**Obecni właściciele:** `backend/output_guard.py` (rozpoznane jawne podejrzenia, bez redakcji), punkt wywołania `backend/pipeline.py`, `backend/pseudominizer_api.py` (status/egress), `frontend/src/screens/Pseudonimizuj.tsx` (lista + decyzje + bramka), istniejące słownik i allowlista. **Bez** dodawania drugiego NER, arbitra, kolejnych tokenów czy odtwarzania odmian. Warianty gramatyczne tej samej osoby mogą współdzielić `OSOBA_NNN`; po odkryciu/przywróceniu możliwa kanoniczna postać, ale nie wolno scalać różnych osób.

**Niezbędny kontrakt techniczny, wymagający PRECHECKU wykonalności:**
- Każde ostrzeżenie ma lokalny identyfikator oraz jest związane z **konkretną rewizją finalnego tekstu** (PSE + rewizja), a decyzja dotyczy tej wersji, nie starej listy. Bez zapisywania jawnego PII do ogólnych logów. W pierwszym kroku wystarczy stan bieżącej sesji; **nie budować teraz trwałego dziennika decyzji**, przeniesiony do `LYNX-GUARD-DECISION-LOG` na koniec.
- **Bramka zakończenia obsługi ostrzeżeń:** backend przed `/archive` sprawdza utrzymywany po swojej stronie status bieżącego PSE/rewizji: brak nierozstrzygniętych ostrzeżeń i brak awarii S3. Nie opiera się na samym `guard_blocked` z żądania klienta. Backend **nie ocenia ponownie wyboru użytkownika**: zarówno `Zakryj`, jak i `Zostaw` rozstrzygają wskazane ostrzeżenie. `Kopiuj` i eksport w aplikacji respektują ten sam stan aktualnego dokumentu. **Nie wymaga się dowodu, że klientowski ciphertext zawiera oceniony tekst, odszyfrowywania blobu przez backend ani nowego protokołu kryptograficznego.** Szyfrowanie klienta pozostaje obecne. Nie obiecywać systemowej blokady schowka OS.
- **Znane obejście:** w `Pseudonimizuj.tsx` `handleSave(forceBypassGuard=true)` po zbiorowym `To nie PII — zapisz mimo to` omija blokadę. W `pseudominizer_api.py:/archive` `guard_blocked` jest odczytywany z client body, domyślnie `false`, po tym jak zapisano blob. Należy uniemożliwić taki zapis **przed skutkami ubocznymi**, również przez wywołanie HTTP bez UI. Przy nieoczekiwanym błędzie nie wolno pozostawić gotowego do użycia archiwum.
- **S5/allowlista:** `_save_guard_allowlist` dziś utrwala frazy **jawnie** w `guard_allowlist.json`; nie dodawać tam kolejnych decyzji ani nowych jawnych danych. Codex ma rozstrzygnąć, czy istniejąca bezpieczna pamięć profilowa wystarcza, czy potrzebne jest małe osobne zadanie/STOP przed aktywacją opcji „zapamiętaj”. Zwykłe `Zostaw` dla bieżącego dokumentu nie wymaga trwałej allowlisty.
- **Brak rozszerzania skanera na oślep:** obowiązuje wyłącznie R1–R4 i dotychczasowe wykrycia HIGH/MEDIUM/MAP_LEAK opisane w macierzy C2. Nie projektować piątej klasy ani pełnego rozpoznawania nazw, nie deklarować gwarancji „każde słowo” na dowolnym dokumencie. Jeśli R1–R4 nie da się zrealizować prosto na istniejących ownerach, Codex ma wskazać najmniejszy **STOP** i kolejność minimalnych części, a nie wymyślać nową architekturę.

## Niezbędne dowody po ewentualnym wdrożeniu (nie w BRIEF_ONLY)

1. Syntetyczny dokument z 2–3 podejrzeniami: `Kopiuj`/`Zapisz`/eksport zablokowane przed decyzją, po jednej decyzji nadal zablokowane, po wszystkich można wykonać; `Zakryj` skutkuje poprawnym tokenem i mapą, `Zostaw` pozostawia tylko świadomie zaakceptowany fragment; cofnięcie/zamiana tekstu/unieważnienie/repreview odtwarza bramkę.
2. `AWARIA_S3` nie jest możliwa do zaakceptowania; test bezpośredniego POST `/archive` z fałszywym `guard_blocked=false`, obcy PSE, stara rewizja, brak rozstrzygnięcia co najmniej jednego ostrzeżenia lub awaria S3 → nie zapisuje nic. Po rozstrzygnięciu wszystkich ostrzeżeń dla aktualnej rewizji zapis jest dozwolony, także gdy użytkownik wybrał `Zostaw`. Nie bada się zgodności wnętrza ciphertextu z tekstem.
3. Obecny przypadek `handleSave(true)`, różne wielkości liter `Rogalik/rogalików`, nazwisko w kilku odmianach z jednym tokenem, `Odkryj` po `GOTOWE`, biała lista, brak PII w logach, brak regresji S1–S3/S5.
4. Małe reprezentatywne dane biurowe + OCR, wyniki **jawne niezauważone / zakryte / pokazane człowiekowi**, osobno liczba pytań i blokad; wycofanych procentów nie używać jako dowodów. Nie trzeba pełnego benchmarku w prechecku.

## TASK_SCOPE / kolejność

To **nowa funkcja i zmiana S4**, nie poprawka bez Architekta. **Dwie bramki niezależne:** (1) propozycja S4 z osobnego pliku po formalnej zgodzie OWNERA; (2) bezpieczeństwo drogi `preview → decyzje → GOTOWE → zapis`. **Jeśli druga nie mieści się w małym istniejącym szwie, STOP do Architekta i OWNERA**, a nie kolejna piętrowa infrastruktura. CC po PASS przedstawia szacunek plików/linii i minimalną propozycję; OWNER zatwierdza koszt przed kodem. Zakaz rozbudowy OSOBA/FIRMA, HerBERT, Mobile, instalatora i trwałych audit receipts w tym Tasku.

**Codex BRIEF_ONLY — ŚWIEŻA INSTANCJA / TYLKO C2:** przeczytaj tylko ten brief, propozycję S4 i wskazane istniejące szwy na exact SHA. Sprawdź **TYLKO** czy R1–R4 i macierz przykładowa zamykają dotychczasowe C2: jednoznaczność dodatnich/ujemnych spanów, proporcjonalność skanera, niewprowadzanie drugiego silnika. **C1 został wycofany w raporcie r2 na polecenie OWNERA — nie otwierać ponownie kryptograficznej weryfikacji ciphertextu.** S3, S4, rewizje, allowlista i bramka statusu pozostają zgodnie z v1.1, o ile nowe C2 nie generuje wyraźnej sprzeczności. Bez uruchamiania testów/modeli/kodu i bez implementacji. Wynik: `PASS PREIMPLEMENTATION` albo jedna krótka lista braków (`WYMAGA_DECYZJI`/`BLOCKER`). **PASS Codexa nie jest zgodą OWNERA na zmianę S4, budżet ani merge.**
