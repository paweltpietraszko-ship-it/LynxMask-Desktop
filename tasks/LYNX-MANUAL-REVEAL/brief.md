# LYNX-MANUAL-REVEAL — ręczne odkrycie pojedynczego wystąpienia (brief v2, korekta C1 Codexa)

Data: 2026-10-20. Kierunek zaakceptowany przez OWNERA w rozmowie po obejrzeniu ekranu Desktop. Korekta po BRIEF_ONLY r1 Codexa, raport `db43feedb2c1cc173696fa43e1858b05267f8e11` (jeden problem C1: brak szwu kontroli finalnego tekstu). Bez zgody na merge i bez zmiany spec S4.

## Cel użytkownika

Na aktualnym ekranie „Zamaskuj”, obok działającego już pola „Dodaj i zakryj”, dodać prostą możliwość korekty **nadmiernego maskowania**. Użytkownik widzi zakryte słowo, zaznacza **konkretne wystąpienie tokenu** w podglądzie i wybiera „Odkryj”. Tekst pomocniczy: „Jeżeli LynxMask zakrył słowo, które nie jest daną osobową, zaznacz je w podglądzie i wybierz «Odkryj». Zmiana dotyczy tylko tego miejsca.”

Nie budować JSON homonimów, analizy zdania, nowego NER ani „drugiego silnika” w Guardzie. Nie potrzebujemy automatycznie odróżniać owocu od człowieka. **Użytkownik sam decyduje**, czy w tym konkretnym wystąpieniu zakrycie było błędem. Pozostawienie zakrytego tekstu jest prawidłową decyzją i nie powinno powodować natarczywych alarmów.

## Warunek krytyczny: dwie identyczne wartości, jedna korekta

W danych syntetycznych:
```
01. Róża zakwitła rano na rabacie.       → 01. OSOBA_033 zakwitła rano na rabacie.
02. Pani Róża odebrała dokument.        → 02. Pani OSOBA_033 odebrała dokument.
```
Użytkownik odkrywa **wyłącznie token w 01**, a 02 nadal pokazuje `OSOBA_033`. Nie wolno wykonać globalnego `replaceAll("OSOBA_033", "Róża")`. Nie wolno globalnie wyłączyć „Róża” w słowniku profilu, `.lynxdict` lub `GuardAllowlist`. Przy takim samym tokenie w dwóch miejscach potrzebny jest identyfikator pozycji (offset tekstu wyjściowego lub równoważny stabilny indeks wystąpienia); sam identyfikator tokenu nie wystarcza.

## Zasady bezpieczeństwa i zgodności

- Interfejs pozwala odkryć tylko **całe wskazane wystąpienie tokenu** z mapą token→oryginał. Zaznaczenie swobodnego kawałka zwykłego tekstu nie jest żądaniem odkrycia; token spoza mapy, zaznaczenie wielu tokenów, brak jednoznacznej pozycji → kontrolowana odmowa z instrukcją „Zaznacz pojedynczy zamaskowany token w podglądzie”.
- **Token zawierający wiele słów**, np. `OSOBA_001 → Anna Malina`, może ujawnić więcej danych, niż użytkownik zamierza. Nie próbować odsłaniać wewnętrznego słowa bez wiarygodnego spanu. Na pierwszym etapie bezpiecznie odmówić odkrycia części takiego tokenu z wyjaśnieniem „Ten token obejmuje więcej niż jedno słowo; nie można odkryć tylko jego fragmentu”. Czy dopuścić świadome odkrycie *całego* wielowyrazowego tokenu, to osobna decyzja OWNERA.
- Odkrycie nie zmienia oryginalnej mapy sesji; ma być odwracalne przyciskiem „Cofnij odkrycie” i resetowane przy nowym dokumencie/przetworzeniu. Wygenerowany wynik dla kopiowania, eksportu i zapisu musi odpowiadać **temu samemu tekstowi**, który widzi użytkownik, a nie staremu `result.anonymized_preview`.
- **OutputGuard zachowuje odrębną rolę i sprawdza ostateczną treść przed udostępnieniem.** Samo sprawdzenie starej wersji przed edycją nie wystarcza. Zmodyfikowanego tekstu NIE wolno kopiować, zapisać ani eksportować bez świeżej pozytywnej walidacji *dokładnie tej treści*. Zamrożony `arch/spec.md` S3/S4 obowiązuje; bez automatycznego wyjątku dla ręcznie odkrytych nazw i bez obejścia HIGH/blocked. W tym Tasku walidacja może zwrócić blokadę — wtedy użytkownik może cofnąć odkrycie albo pozostawić dokument niewysłany. To **nie jest zgoda na łagodniejsze zachowanie S4**. Jeżeli w teście nawet poprawne odkrycie owocu wywoła `MAP_LEAK`, CC raportuje defekt użyteczności/konflikt polityki; **nie wycisza** go i nie dopisuje globalnego wyjątku. Osobna decyzja OWNERA i osobny Task/spec byłyby potrzebne, by taki przypadek zwalniać z blokady.
- `Przywróć`: testować na docelowym tekście po korekcie i pierwotnej lokalnej mapie; oryginalny tekst ma dać się odtworzyć 1:1 tam, gdzie jest to technicznie możliwe. Nie dopuszczać kolizji tokenów, uszkodzeń spacji czy znaków. Bez utrwalania jawnych PII w logach, rapportach, nowym nieszyfrowanym pliku ani dodatkowym profilu.
- Tryb Express ma osobną politykę kopiowania/archiwum — nie zmieniać jej przy okazji. Zmiana istniejącej akcji „Dodaj i zakryj” i zachowania Guarda jest poza zakresem.

## Fakty o obecnym kodzie, do sprawdzenia na exact SHA przed pracą

- `frontend/src/screens/Pseudonimizuj.tsx`: `HighlightedText` renderuje tokeny; `previewRef` i `selectionchange` istnieją; `handleAddEntity` ponawia `/preview`; „Kopiuj tekst” kopiuje `result.anonymized_preview`; `handleSave` szyfruje ten sam tekst razem z `result.tokens` i archiwizuje; UI ma istniejący `guardBlocked`.
- `frontend/src/screens/Depseudonimizuj.tsx` to odzyskiwanie po sesji, nie miejsce ręcznej korekty tekstu przed wysyłką.
- Mobile `TextPreviewModal.kt` ma „Odkryj”, lecz obecne `revealedTokens` ujawnia wszystkie miejsca identycznego tokenu; nie kopiować tej wady.
- **C1 rozstrzygnięte kontraktem architekta:** istniejące `/preview` nie nadaje się do ponownego sprawdzania odkrytego tekstu (wywołuje pipeline na wejściu z tokenami); `/archive` dostaje szyfrogram, nie może sprawdzić plain-text; `/export-pdf` też nie waliduje. Autoryzowany **minimalny szew w `backend/pseudominizer_api.py`**: odrębna operacja *walidacji finalnego tekstu*, wywołująca istniejący `output_guard.guard_output_with_map` z już istniejącymi ustawieniami S3/S4. Nie tworzyć nowego NER i nie modyfikować reguł `output_guard.py`. Reprezentacja request/response i mały mechanizm kontekstu opisane niżej. CC ma zrecenzować wykonalność i budżet przed kodem.

## Korekta C1: autoryzowany szew walidacji finalnej treści (wyłącznie dla tego Tasku)

**Właściciel zmiany:** `backend/pseudominizer_api.py` — nowa, lokalna operacja np. `POST /preview/validate-final`, z obowiązującym tokenem API, oraz minimalne przekazanie kontekstu z istniejącego `/preview`. **Właściciel zasad** pozostaje niezmieniony: `backend/output_guard.py::guard_output_with_map` (`GuardMode.REDACT` jak dzisiejsze `pipeline._apply_guard`), bez zmian implementacji tej funkcji i bez nowej allowlisty. Implementer może zaproponować inną nazwę endpointu, ale nie inny zakres odpowiedzialności.

**Kontrakt wejścia:** jednoznaczna identyfikacja bieżącego wyniku `/preview` (PSE + kontekst, który serwer rzeczywiście wydał) oraz **pełny, finalny tekst bajt w bajt**, z zastosowanymi lokalnymi odkryciami. Nie wywoływać ponownie `pseudonymize_document` na tekście zawierającym tokeny. Nie ufać przekazanej przez klienta liście tokenów, wartości oryginałów, deklaracji `guard_blocked` ani pozycji odkryć jako wyłącznemu źródłu prawdy. Walidator musi mieć wiarygodny kontekst mapy z danego `/preview` (np. mały krótkotrwały kontekst w pamięci backendu, przypisany do PSE; **bez utrwalania jawnej mapy w pliku**). Przy braku kontekstu po restarcie/przekroczeniu limitu → odmowa z instrukcją „Przetwórz dokument ponownie”. Baza liczb/statusów i rozmiar/TTL kontekstu do minimalnej recenzji CC, bez budowy trwałego menedżera sesji. `PSE` bez weryfikowalnego kontekstu nie wystarcza do pozytywnej autoryzacji.

**Sprawdzenie:** serwer porównuje żądany tekst z aktualnym źródłowym wynikiem i dozwolonymi *pojedynczymi operacjami odkrycia* — jedyna różnica może dotyczyć kompletnego, istniejącego wystąpienia tokenu i dokładnej oryginalnej wartości z lokalnej mapy; nie wolno zmienić innych znaków, pozostałych tokenów, prefiksu PSE czy dowolnie „poprawiać” dokumentu. Cofnięcie to usunięcie decyzji o odkryciu. Niejednoznaczność, ułamkowy token, niedozwolony wielowyrazowy oryginał lub brak mapy → BLOCKED, bez tekstu w diagnostyce. Dopiero wtedy wykonuje **istniejący** OutputGuard na finalnym tekście, z sesyjnymi znanymi wartościami z *serwera*, nie ze swobodnej listy klienta, i z dotychczasową polityką S3/S4. Zablokowany `/preview` nie może uzyskać zatwierdzenia przez ten szew. Jeżeli Guard proponuje redakcję innego tekstu niż przesłany, nie zatwierdzać oryginalnej, nieredagowanej treści.

**Wynik walidacji:** (1) `APPROVED` tylko gdy brak `blocked`, błędu i modyfikacji/redakcji przez Guarda, a weryfikowany tekst jest tożsamy z tekstem do wyświetlenia/udostępnienia; (2) `BLOCKED` — brak zgody, bez zwrotu jawnych wartości, krótki komunikat „Nie można udostępnić po odkryciu — cofnięcie odkrycia lub poprawienie dokumentu”; (3) `ERROR` (brak kontekstu, awaria Guarda/sieci) — fail-closed, użytkownik otrzymuje „Cofnij odkrycie albo przetwórz dokument ponownie”. Domyślna odmowa przy nieznanej odpowiedzi. Walidacja **nie tworzy wyjątku** `MAP_LEAK` dla ręcznie odkrytej „Róża”; jego ewentualne blokowanie to jawny wynik do oceny OWNERA, nie powód do zmiany S4 po cichu.

**Powtórne zmiany i wyjścia:** UI utrzymuje wersję/revizję edytowanego tekstu oraz jedną kanoniczną wartość `finalText`. Każde odkrycie, cofnięcie, nowe maskowanie, załadowanie innego dokumentu lub zmiana treści **unieważnia** poprzedni `APPROVED`. Przed akcją „Kopiuj tekst”, „Zapisz” oraz eksportem, jeśli jest dostępny, aplikacja sprawdza najnowszą rewizję i przekazuje backendowi dokładnie `finalText`; w razie zmiany podczas trwania żądania odpowiedź jest nieaktualna i należy walidować ponownie. Odpowiedź pozytywna może autoryzować **wyłącznie dokładną, niezmienioną** treść, która potem trafia do schowka/zaszyfrowanego archiwum/eksportu. Nie wystarczy samo `guardBlocked=false` z pierwotnego `/preview`. Bezpieczne ścieżki bez ręcznej korekty nie mogą ulec regresji. `/archive` pozostaje formatowo bez zmian: ponieważ serwer dostaje zaszyfrowany blob, CC ma wykazać testem, że UI szyfruje tę samą zatwierdzoną treść; to **nie** jest obietnica, że /archive niezależnie waliduje zawartość szyfrogramu.

**Budżet i STOP:** autoryzowany jest mały właścicielski szew API, **nie** zmiana polityki OutputGuarda, `pipeline`, schematu archiwum ani S4. `TASK_SCOPE` ograniczony do `frontend/src/screens/Pseudonimizuj.tsx`, `backend/pseudominizer_api.py` i minimalnych testów istniejącego właściciela. Oba pliki są duże: **żadna implementacja nie rusza**, jeśli CC nie zaproponuje redukcji i nie uzyska od OWNERA wymaganego przez budżet repo zatwierdzenia rozmiaru (>150 linii, plik >600, funkcja >50 lub ratio >5:1). Jeśli minimalnego kontekstu w backendzie nie da się zrealizować bez trwałego, jawnego przechowywania PII albo rozszerzenia S4, CC zgłasza `OWNER_DECISION_NEEDED` przed implementacją.

## Zakres i odbiór

`TASK_SCOPE` do prechecku (dwa istniejące ownery, bez nowego modułu produktu): 
- `frontend/src/screens/Pseudonimizuj.tsx` — ręczne odkrycie po pozycji, cofnięcie, jeden `finalText`, gating kopiowania/archiwum, unieważnianie walidacji po każdej zmianie.
- `backend/pseudominizer_api.py` — minimalny szew walidacji finalnego tekstu i krótki lokalny kontekst mapy powiązany z `/preview`.
- Celowane testy istniejących szwów jako materiał audytu; nie rozbudowywać frameworka i nie dodawać nowych produkcyjnych modułów bez osobnego zgłoszenia.

OUT_OF_SCOPE: zmiana reguł `output_guard.py`, `pipeline`, `ner_layer`, S3/S4, trwałych słowników/allowlist, reanonymizacja przy odkryciu, schemat `/archive`, obsługa nowego modelu. Unikać rozrastania już dużych plików. Limity (>150 linii, >5:1, 600 linii/pliku, 50 linii/funkcję) sprawdzić przed kodem; potrzebna osobna zgoda OWNERA na odstępstwo, nie automatyczna.

Kontrpróby Codexa i CC: 2× ten sam `OSOBA_033` i ujawnione tylko pierwsze wystąpienie; 2 różne tokeny o tej samej oryginalnej wartości; token wielowyrazowy; brak mapy; wybór niepełny i obejmujący wiele tokenów; „Cofnij”; nowy dokument; ponowne maskowanie; `Przywróć` 1:1; zgodność wyświetlenie/kopiowanie/zapis; kontrola udostępnienia po edycji przez Guard; blokada S3/S4 pozostaje skuteczna. Dodatkowo bez zmian w profilu i bez regresji obecnego domaskowania.

**Codex BRIEF_ONLY — wąski recheck C1:** oceń tylko, czy po zmianie briefu jest autoryzowany minimalny szew `pseudominizer_api.py` i jednoznaczna polityka `APPROVED/BLOCKED/ERROR`, z wiarygodnym kontekstem mapy i unieważnianiem zgody po każdej edycji; czy wynik Guard `MAP_LEAK` pozostaje blokujący zgodnie z frozen S3/S4; czy nie ma zgody na reguły/allowlisty ani założenia, że szyfrowane archiwum jest serwerowo zwalidowane. Precheck BEZ uruchamiania kodu; PASS PREIMPLEMENTATION lub jedna zamknięta lista braków. Potem CC recenzuje wykonalność i budżet; przed przekroczeniem limitów zgłasza OWNEROWI; po akceptacji implementuje, Codex audytuje **dokładny SHA**, a OWNER decyduje o merge. Raporty tylko syntetyczne, bez rzeczywistych danych osobowych.

## Następne prace — niezależne od tego zadania

1. `LYNX-K1-PERSONS-FIRMS / K1a`: osobny, późniejszy krótki brief HerBERT jako **ostatnia siatka** na wciąż jawnych fragmentach, bez cofania już zakrytych tokenów i bez dopisywania wykrywania do Guarda. Pierwszy pomiar: nowe prawidłowe maski vs fałszywe maski, czasu/VRAM, brak regresji i offline.
2. Dopiero po pomiarach **kosmetyka/jakość OSOBA**: redukcja niepotrzebnych zakryć i błędnych granic tokenów w istniejących warstwach, wąskimi taskami z regresją; duży `LYNX-OSOBA-REDESIGN` bez wznowienia na podstawie samej estetyki wyniku.

Dawny `LYNX-OSOBA-HOMONYM-TEST` (JSON+Guard) jest zakończonym, odłożonym kierunkiem; nie wznowić przypadkiem.
