# CODEX_HANDOFF — LynxMask Desktop

Aktualizacja: **22.10.2026, po audycie GUARD-B r3 i odświeżeniu BOARD**.
Zamówienie Pawła: sprawdzić i uaktualnić dokumenty przed przejściem do nowej sesji.
To migawka przekazania, nie nowy kontrakt ani polecenie rozpoczęcia wszystkich zadań.
Czytaj też `CODEX_START_HERE.md` i `AGENTS.md`; aktualny wiersz Tasku odśwież zdalnie.

## 1. Gdzie naprawdę jesteśmy

**GUARD A+B są już na main**: merge `9465f96517902e385213d263651c9bbb75260cf6`.
Potwierdzone w historii origin/main i aktualnym BOARD podczas tego przekazania.
Nie wracaj do starego „czekamy na polecenie scalenia A+B” — było aktualne przy audycie, ale potem CC wykonał merge.
Ostatni odczyt origin/main przed zmianą tych dokumentów: `0482610f7d225d435c79a321fec140a43d406db1`.

Ostatni zakończony audyt Codexa:
- **GUARD-A:** PASS r2 na `8b69fd65e5f490bd2c61a6438e6516e67d267826`;
  raport `f47fdb93fbd6d03c2dcb6210a5c2f00eeef60a91`,
  `tasks/LYNX-GUARD-A/round_01/tests/tests_r2.txt`.
- **GUARD-B:** PASS poprawki/sprawdzonego zakresu r3 na `ae9eceb26c0bb2beaedf1bae5788e8d19c9f95dc`;
  raport `ab7842928593b4c46fe6d270902a35f8be52246e`,
  `tasks/LYNX-GUARD-B/round_01/tests/tests_r3.txt`.
  Wszystkie zgłoszone F1–F3 zamknięte. Repro r1 7/7, repro r2 4/4, 18 testów Node i tsc PASS.
- Paweł potwierdził: **„optycznie jest poprawnie, przyciski działają poprawnie”**.
  Zachowaj tę ocenę; nie otwieraj estetyki przy poprawce logiki.
- PASS jest ograniczony do opisanych warstw/SHA. Nie oznacza pełnego odbioru wszystkich scenariuszy GUI, schowka,
  archiwum Tauri, słownika, Express i skuteczności na dowolnych dokumentach; granice są w raportach.

## 2. Najbliższa praca — NIE rozpoczęta w tym przekazaniu

### LYNX-GUARD-FIX1 — nowa dostawa CC oczekuje na audyt

W aktualnym BOARD: READY_FOR_CODEX.
Gałąź `task/LYNX-GUARD-FIX1`, HEAD `cb81de7cc3842d7d04855e7583bf9eb09bfc033f`
(kod `e9eb78a`), baza `75be0ff`.
Brief: `tasks/LYNX-GUARD-FIX1/brief.md`.
Dotyczy fałszywych ostrzeżeń w dwóch kolumnach: R5 bierze etykietę Nabywca/kolejną kolumnę,
R1 pyta o Przychodnia. Wskazany syntetyk:
`Pliki testowe/doc_stresstest_silnik_guard_lvl0_3.txt`, okolice 112–113.
CC zgłasza 44 testy, gate PASS i bez zmiany 25/150 — **to przekazanie CC, jeszcze nie niezależny audyt Codexa**.
Następca po zleceniu audytu ma zacząć od briefu, wąskiego diffu i tych przypadków, nie od powtarzania całego A/B.
Wiersz BOARD bywa rozbity literalnymi nowymi liniami w cytacie — odczytaj cały wpis, nie tylko pierwszy wiersz.

### LYNX-GOLD-SET — odrębne zlecenie zbioru, gotowe według BOARD

Źródło: `tasks/LYNX-GOLD-SET/zlecenie.md` na gałęzi `task/LYNX-GOLD-SET`.
Aktualny odczyt zawiera wymagania ilościowe oraz pola `rodo`; przed rozpoczęciem czytaj go w całości.
**Nie realizuj wcześniejszego pomysłu 20 dokumentów i gold pisanych przez CC** — został zastąpiony:
- 120 dokumentów biurowych: dev 40 / test 80.
- Agent-autor tworzy dokument i gold razem; świeży inny agent-weryfikator sprawdza kompletność, spany i unikalność.
  CC nie jest autorem ani annotatorem; tylko mierzy, nie ogląda części test i nie stroi na niej.
- Docelowy lokalny katalog: `backend/dataset_gold_20261022/{dev,test}/` (ignorowany przez git);
  raport weryfikatora w `tasks/LYNX-GOLD-SET/round_01/tests/`, bez treści dokumentów.
- Start/end w punktach kodowych Pythona, literalny wycinek musi równać się `text`.
- Zakaz powtarzania wartości/nazwisk między dokumentami i nazw-wzorców; sprawdzanie skryptem również względem
  istniejących zbiorów. Powtórzenia/odmiany w jednym dokumencie mają wspólny entity_id.
- Minima ze zlecenia są obowiązkowe, nie opcjonalne: OSOBA ≥700 wystąpień/≥320 osób, FIRMA ≥250,
  ADRES ≥260, NUMER ≥620 z rozbiciem, EMAIL ≥90, KWOTA ≥180, not_pii ≥350; dalsze podlimity i proporcje w zleceniu.
  Nie zastępuj całej tabeli tym skrótem.
- Wymagane trudne przypadki, w tym dwie kolumny, homonimy, inicjały, patroni ulic, odwrócone adresy i OCR
  w ≥24 dokumentach; oddzielaj wyniki clean/OCR w interpretacji.
- Politykę FIRMA/EMAIL i `rodo` weź ze zlecenia jako regułę tego zbioru, nie wywód prawny od nowa.
  Wszystkie firmy nadal maskowane; urząd/samo miasto nie stają się automatycznie PII.
- Po podjęciu tego osobnego zadania autor/weryfikator mają dostać wyłącznie potrzebny kontrakt danych;
  świeży agent bez historii silnika (`fork_turns="none"`), bez kodu i wcześniejszych wyników.
  To nie jest zgoda na delegowanie zwykłych audytów.
W tym przekazaniu **nie uruchomiono agentów, nie wygenerowano dokumentów i nie dokonano odbioru zlecenia**.
Kolejność podjęcia FIX1/GOLD potwierdź z bieżącym poleceniem Pawła i aktualnym BOARD, nie zgaduj z historii.

### Dalsza kolejka, nie automatyczne zlecenie

- `LYNX-GUARD-ALLOWLIST-S5`: trwałe „nie zakrywaj w przyszłości” po wyraźnym wyborze, szyfrowanie/migracja
  starego jawnego `guard_allowlist.json`, mały brief CC. Obecne okno już nie dopisuje tam Zostaw.
- `LYNX-GUARD-DECISION-LOG`: dopiero na końcu; bez importu Elnath Memory Engine i bez fikcyjnej historii receipts.
- HerBERT jest na main, **domyślnie OFF**. ON/usunięcie po pomiarze i rozstrzygnięciu; nie włączaj przy audycie.
- Duży OSOBA-REDESIGN, kolory i stary SIGNALS-PILOT są odłożone; nie przywracaj ich z pamięci.
  Pozostałe priorytety/uwagi OWNERA czytaj w aktualnym BOARD tylko przy zależności.

## 3. Zamrożony kierunek Guarda i świadome granice

OWNER zatwierdził brief v2 `52d83580c4209fbf578f54e11a2dcd23cc27acdc` oraz kierunek S4 22.10;
PASS PREIMPLEMENTATION r4 `93c656cc037d9ca1a05bfa61f1bf53874cfa4e99`.
Formalny S4+lock: `94a795424715aebb997f7528be8d3affeb31a99e`, następnie weszły na bazę A i merge A+B.

- Guard wskazuje jawne podejrzenia, nie maskuje ich automatycznie `[REDACTED]`.
- R1 osoby/pseudonimy, R2 inicjały, R3 resztki przy tokenach/OCR, R4 identyfikatory w kontekście, R5 firmy.
  HIGH/MEDIUM/MAP_LEAK nie znikają; jedna pozycja może mieć kilka powodów.
- Każdy wiersz Maskuj/Zostaw jawne; to samo słowo tego samego rodzaju/poziomu może być grupą ×N,
  a decyzja dotyczy wskazanych wystąpień. To zatwierdzone rozszerzenie, nie zbiorcze Zostaw wszystko.
- Nierozstrzygnięte ostrzeżenia wstrzymują zwykły zapis/kopię/eksport z aplikacji. S3 jest osobną awarią bez Zostaw.
- Odkryj jest świadomą decyzją dla tego miejsca; nie zgłaszaj tego samego miejsca na nowo jako MAP_LEAK.
  Reszta wyniku nadal kontrolowana. Zostaw i Odkryj nie tworzą trwałej allowlisty.
- Maskuj może budować szyfrowany słownik biura przez istniejące `/profile/add-entity`;
  przełącznik domyślnie włączony, Express bez profilu, krótkie cyfry/inicjały/lata tylko lokalnie.
  Odmowa zapisu słownika ma komunikat, maskowanie dokumentu zostaje.
- Zostaw/zakrycia przeżywają przeliczenie tylko dla tego samego rozpoznawalnego fragmentu i kontekstu (U2),
  nie automatycznie dla innego podobnego miejsca.
- Jedna wiarygodnie ustalona osoba może mieć wspólny token przy odmianach; przy Przywróć dopuszczony mianownik.
  Nie wymagaj nowej mapy odmian/wielkości liter. Nie wolno sklejać różnych osób.
- **Wycofane C1:** poświadczenie zawartości klientowskiego ciphertextu, odszyfrowywanie go przez backend,
  osobny serwerowy nadzorca PSE/rewizji i ochrona przed celowym obchodzeniem lokalnego UI/API.
  Poprzedni Codex nadmiernie rozszerzył ten wymóg; Paweł go zakwestionował i zakres poprawiono.
  Nie wskrzeszaj go jako nowego findingu ani warunku PASS.
- Nie obiecujemy wykrycia wszystkich PII ani blokowania wysłania oryginału inną aplikacją.

## 4. Zachowane findingi i dowody — użyj, nie odkrywaj ponownie

**A:** filtr instytucji usuwał prywatne Centrum/Instytut z formą prawną. Naprawione i zamknięte r2.
39 testów ownera + macierz 16/16, pion Guard/API; samo R5 nie dowodzi, że wcześniejszy silnik przepuszcza taką firmę.

**B:** zamknięte F1–F3:
1. Python code points vs JS UTF-16 — przy emoji Maskuj trafiał obok numeru.
   Pierwsza poprawka zgadywała jednostkę po zgodności fragmentu; przy dwóch identycznych numerach przypisywała oba do pierwszego.
   Ostateczna poprawka używa jawnego znacznika `utf16`, bez zgadywania po tekście.
2. Częściowe zakrycie słowa zamykało całe ostrzeżenie firmy, pozostawiając drugie nazwisko jawne.
   Teraz częściowe pokrycie nie rozstrzyga całości; późniejsze Maskuj całości zastępuje wewnętrzne zakrycia.
3. JS `\w` nie obejmowało polskich liter: Kawa psuła Kawałek. Granice poprawiono na Unicode.

Reprodukcje w repo:
- `tasks/LYNX-GUARD-B/round_01/tests/repro_r1.mjs` — 7 syntetyków, 7/7 PASS na ostatnim SHA.
- `tasks/LYNX-GUARD-B/round_01/tests/repro_r2.mjs` — 0/1/20/21 emoji i dwa identyczne numery, 4/4 PASS.
- Node 24: `node --test tests/revealText.test.mjs` w frontend, 18 PASS; `tsc --noEmit` PASS.
Te JSON-y pochodzą z realnego izolowanego API, ale **stub wcześniejszego silnika dostarczał finalną pozostałość**;
realne były Guard/API/przesunięcie PSE i funkcje JS. Nie nazywaj tego pełnym testem skuteczności wcześniejszego silnika
ani automatycznym oglądem aplikacji.

Pomiary sprawdzone w audycie A r1:
- 150 zapisanych wyników CC: ponowiono reguły na exact SHA, NIE OCR.
  25 ostrzeżeń, śr. 0,1667, mediana 0, max 3, 130 bez ostrzeżeń.
  R1=14/R3=9/R4=10 sumują się do 33 powodów, nie 33 pozycji.
- KPWr 75: ponowiono silnik+Guard, 141 ostrzeżeń, 1,88/dok.; 17 z 33 jawnych słów osób wskazane.
  Odtworzono metrykę CC opartą na słowach/podciągach, NIE semantyczne precision/recall.
- Cache CC: `%TEMP%/lynx_cc_review/guard_a/results.json`;
  SHA256 `baedd9cbaf9622b52ee20f194e6d5d950247185c1a00432e6c69a161eca1e5a5`.
- R2/R5 nie miały trafień w tych obrazach. Mała liczba pytań nie dowodzi pełnej ochrony.
Nie powtarzaj tych pomiarów przy małym fixie, chyba że konkretny kontrakt/ryzyko tego wymaga.
Gdy CC wprost prosi o sprawdzenie wyników, można odtworzyć metrykę/cache w izolacji, jasno podając ograniczenia.

Inne zamknięte dostawy:
- FORMATS-PACK2: ISO/forma prawna/krótkie kody, ostatni PASS r3 `e9dce21`, kod `369abc7`.
- NAMES-DICT-CLEAN: kod `ad8b0d7`, PASS r2 `039d432`.
  R1 o pozostawieniu Inną jawnie OWNER zaakceptował jako poprawne zachowanie.
  Akceptacja dotyczyła tego przypadku — nie dorabiaj globalnego wyłączenia wszystkich imion obcych.
- AMOUNTS-NUMBERS: PASS r2 `00e39dd`, kod `d3f9674`.
Są już na main według bieżącego BOARD; starsze raporty zachowują swoje exact SHA i granice.
Stare znane niepowodzenia testów są w raportach/CLAUDE.md/ENGINE-BACKLOG; nie traktuj ich bez TRACE/REPRO jako nowej regresji.

## 5. W praktyce współpracy

- Wąski audyt, zamknięta lista rzeczywistych błędów, STOP po dowodzie. Nie dodawaj kolejnego projektu bezpieczeństwa do małego zadania.
- Korekty logiki tej samej klasy idą do CC. Zamknięte F2/F3 lub estetyka nie wracają przy kolejnym fixie F1.
- Jeśli zachowany repro przechodzi, a wąski diff wprowadza konkretną niejednoznaczność tej samej klasy,
  sprawdź minimalny wariant; nie rozszerzaj mechanicznie na całe repo.
- Rozróżniaj akceptację produktu, techniczny PASS, supporting evidence CC i NOT_CHECKED.
- Raporty niezmienne, kolejne r<n>; raport na gałęzi Tasku, BOARD na main. Publikację zweryfikuj świeżym odczytem.
- Zgody odnotowane w aktualnym briefie/BOARD (np. koszt A/B, U1–U5) nie są pretekstem do ponownego pytania;
  nie rozszerzaj ich na nowy jeszcze nieprzedstawiony koszt.
- Żadnych zmian kodu, merge ani subagentów przy zwykłym „sprawdź dostawę”.
- Poprawka tych dokumentów została zamówiona; nie jest poleceniem aktualizacji pamięci ani rozpoczęcia nowego Tasku.

## 6. Środowisko i ochrona równoległej pracy

Repo: `C:/Users/p_pie/Desktop/LynxMask-Desktop`.
Podczas przekazania trzy cudze nieśledzone pliki: `8298.jpg`, `8299.jpg`, `Zrzut ekranu (657).png`.
Nie usuwać, nie otwierać bez potrzeby, nie stage'ować. Przed każdą edycją `git status -sb`.

Stary worktree `%TEMP%/lynx-codex-audit-20261019` jest czysty, detached na
`7401ec3471145d232f62fbbc5e1a41a1303ee019` (sprawdzone teraz); **nie** na dawnym `4c75236`.
Nie jest aktualną bazą Guarda. Nie przełączaj katalogu CC/Pawła na badaną gałąź.

Do ostatnich audytów używano własnych kopii `git archive <exact SHA>` w Temp:
`lynx-guard-a-audit-r1/r2`, `lynx-guard-b-audit-r1/r2/r3`.
Najnowsze źródła: `%TEMP%/lynx-guard-b-audit-r3/exact/`.
W katalogach r1/r2 zachowane helpery API, JSON-y i wyniki; repo zawiera trwałe raporty/repro.
Temp nie jest gwarantowanym magazynem między komputerami — sprawdź istnienie.

Własny Python (sprawdzony jako istniejący):
`C:/Users/p_pie/.codex/visualizations/2026/10/19/01a152b6-e997-7cb0-a9e3-752fdcfd00f0/deps-audit-A/venv/Scripts/python.exe`.
Używano `-B -X utf8`, Python 3.14, Morfeusz 1.99.15, rzeczywisty `pl_core_news_lg`; Node 24.15.
Frontendowe zależności istnieją w `frontend/node_modules`; do typechecku kopii w Temp używano własnego junction,
bez instalacji i bez zmian produktu. W razie odmowy dostępu skorzystaj ze zwykłej ścieżki uprawnień, nie omijaj jej.

Przed importem backendu ustaw izolowane ścieżki:
`ANONYMIZER_PROFILE_DIR`, `PROFILE_DIR`, `PSE_REGISTRY`, `ARCHIVE_DIR`, `HARDWARE_PROFILE`.
Testowe mapy/token API nie mogą lądować w repo. `API_TOKEN_PATH` jest zależne od pliku źródłowego,
dlatego samo przestawienie profilu nie zastępuje izolowanej kopii źródeł.
Nie czytaj/nie wypisuj tokena działającego backendu Pawła i nie restartuj portu 8765.
Własny TestClient na URL 127.0.0.1:8765 działał w procesie, nie łączył się z backendem Pawła;
odcinano połączenia zewnętrzne i realne połączenie z 8765. Windows może wymagać uprawnienia na lokalny socket testu.

Nie uruchamiaj wszystkich backendowych plików testów w jednym procesie — odnotowano segfault bibliotek natywnych.
W jednym podejściu harness audytora wyłączał logowanie i sztucznie psuł dwa testy S3; naprawiono harness, nie produkt.
Rozróżniaj własny błąd środowiska od findingu.

Raporty w repo nie zawierają realnych danych. Nie publikuj `dataset_real`, `preview_real_results`, profili,
kluczy, map ani surowych wyników dokumentów Pawła. Nie zapisano nowej pamięci w ramach tego przekazania.
