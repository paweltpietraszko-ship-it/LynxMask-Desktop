# Niezależna ocena diagnozy 2026-10-18 — r1

**Werdykt: DO POPRAWY — dotyczy wniosków i podstaw do briefów, nie jest FAIL dostawy silnika.**

Objawy opisane przez CC są rzeczywiste. Odtworzyłem wszystkie 17 przebiegów: wynik tekstowy, mapy tokenów i lista podpowiedzi HerBERT-a są identyczne z lokalnymi zapisami CC. Nie akceptuję jednak obecnego przypisania wszystkich przyczyn i deklaracji zamknięcia klas w K1–K5. Wystarczy jedna korekta raportu według zamkniętej listy R1–R5 poniżej; nie trzeba powtarzać całej diagnozy ani pisać nowej architektury.

- Data: 2026-10-18. Odbiorca: CC / Architekt.
- Exact SHA ocenianego raportu i narzędzi: `961f7d8dbaf569f8055023af198174b8e388b590`.
- Backend badany przez działające `/preview`: kod produkcyjny zgodny z `c63114ac916903d7c0d217ecfedf0c0625d05026`.
- Weryfikacja pochodzenia: proces `pseudominizer_api.py`, PID 11296, katalog `backend` tego repo; brak zmienionych produkcyjnych plików Python po starcie procesu. Drzewo backend/frontend/spec jest identyczne między c63114a a gałęzią diagnozy. `/version`: API `1.35-TAURI`, OCR `1.0`. Endpoint nie podaje SHA załadowanego procesu — zgodność źródeł ustalono powyższymi kontrolami, nie samym numerem wersji.
- Zasada oceny: zamrożone `arch/spec.md` S1–S5, instrukcje niezależnego audytu, raport jako propozycja oraz jawne granice istniejących Tasków. Wiersz BOARD i kierunkowa zgoda na propozycję nie zmieniają PRODUCT_TRUTH.

## Co sprawdziłem niezależnie

1. Ponowne uruchomienie opublikowanego `diag.py` na dokładnie tych samych 17 plikach, przez istniejący lokalny backend z jego bieżącym profilem i lokalny ONNX. To 12 PDF i 5 TXT; 16 pozycji jest w `dev`, KIO 578/11 jest dodatkowym plikiem publicznym. Holdout nie był używany.
2. Wszystkie 17 odpowiedzi przetworzone; 5 dokumentów blokuje Guard, we wszystkich pięciu jest `MAP_LEAK`; 4 dokumenty przekraczają limit 15000 znaków. Mapy łącznie mają 502 wpisy, lista HerBERT-a 231 podpowiedzi — **te liczby nie są liczbami prawidłowo wykrytych encji ani wycieków**.
3. Punktowo przejrzałem odtworzone wyniki tekstowe/mapy i reprezentatywne przykłady A1–A7/B/C1–C6. Zgodność plików wynikowych nie jest niezależnym potwierdzeniem wszystkich przybliżonych liczników klas z raportu (`~13`, `~9`, `~8`) ani nowym pomiarem recall/precyzji.
4. Punktowy trace na KIO 578/11, KIO_uzp_16714 i C047: istniejące warstwy do miejsca NER, prawdziwy SpaCy, `process_ner`, dosłowne wartości mapy i ich obecność w tekście. **Trace miał pusty profil porównawczy**; nie zastępuje powyższego przebiegu HTTP z profilem Pawła i nie korzystał z atrap detektora.
5. Minimalne seedowanie wyłącznie w pamięci: `NameError`, bez zapisu profilu. Pierwszy commit seedu `301def0` ma ten sam błąd odwołania do niezdefiniowanego limitu w metodzie wsadowej. Obecny limit z modułu inicjalizacji to 100, a zasoby seedu dają 12288 wpisów przed deduplikacją pomiędzy hasłami.
6. Porównanie adaptera z `ffeaff339f32b56169bda50a9a7e2fb21774ee85` i c63114a na jednym syntetycznym, kontrolowanym wyniku NER: sama wartość `z o.o` trafia do głównej podmiany na obu SHA, a syntetyczna nazwa firmy zostaje jawna. To dowód starego braku ochrony w adapterze, **nie pełny historyczny przebieg starego backendu z realnym NER**. Aktualny objaw na dokumentach potwierdza HTTP.
7. Sprawdziłem realne zasoby lokalnego Mobile, repo HEAD `450204b8a12fbb866dac68d2db8c92021cd0039e`: 38783 wpisy `surnames_extended.json`, 769 `city_surname_overlap.json`, 99 `surname_suffixes.json`. Nie uruchamiałem aplikacji na telefonie. Relacja Pawła/CC o wyniku Mobile pozostaje ich dowodem, nie moim niezależnym testem; odmienne wejście OCR wyklucza ranking obu silników na tej jednej parze.

Wyniki z pełnym tekstem i diagnostyka pozostały lokalnie poza repo. Do tej oceny trafiają wyłącznie identyfikatory dokumentów, liczby, SHA i opis mechanizmów. Nie zmieniałem kodu produktu, profilu, modelu, wcześniejszych raportów ani specyfikacji; bez pełnej suity i merge.

## Ocena klas i przyczyn

| Klasa | Ocena po odtworzeniu |
|---|---|
| A1 | Osoby w osobnych wierszach rzeczywiście zostają jawne. Na KIO 578/11 i KIO_uzp_16714 **SpaCy już obejmuje wskazane osoby**, lecz encja obejmuje nowe linie; `process_ner` zamienia białe znaki na spacje i wartość nie występuje dosłownie w tekście. Adapter odrzuca ją przy rejestracji/podmianie. Potwierdzony mechanizm NER-MULTILINE, nie dowód konieczności nowego detektora. |
| A2 | Wyliczenie osób w C047 jest problemem rzeczywistym. Trace również pokazuje objęcie nazwisk przez wielowierszowe encje SpaCy oraz niedopasowanie znormalizowanych wartości. Sama odmiana nie wyjaśnia tego przypadku. Potrzebna ta sama korekta przyczyny co w A1. |
| A3 | Potwierdzone: C024 zawiera jawne osoby obok firmy; w C025 imię dostaje `OSOBA_020`, a nazwisko zostaje dosłownie w wyniku. HerBERT proponuje szerszy PER. C024/C025 są dziś blokowane — nie opisywać ich jako odblokowanych wyników do skopiowania. |
| A4 | Potwierdzone na sześciu wskazanych dokumentach: token wartości będącej samą formą prawną, nazwa poza nim. W KIO_114738 dziewięć podmian takiego tokenu jest poprzedzonych nazwą i `Sp.`. Filtr samej formy jest w ścieżce wariantów adaptera, ale nie chroni głównej mapy. To stary błąd niezależny od wyboru nowego NER; porównanie komponentu opisano wyżej. |
| A5 | Jawne nazwy/konsorcja/przełamania są potwierdzone. To jednak zbiór objawów: brak kandydata, fragment kandydata, utrata dopasowania oraz nieobjęte powtórzenie wymagają odróżnienia przed przypisaniem do NO-CANDIDATE, MULTILINE albo BARE-REPEAT. Nie dowiedziono jednej wspólnej przyczyny „za słaby SpaCy”. |
| A6 | Potwierdzone częściowe/jawne adresy i podpowiedzi LOC obejmujące więcej adresu niż aktualna mapa. Nie dowodzi to jeszcze poprawnego działania istniejącego ownera ADRES po integracji nowego źródła. Samo LOC bywa błędne: C006 ma dwie podpowiedzi LOC na końcowym członie nazwy miasta, w kontekście miasta, a nie pełnego adresu. |
| A7 | Potwierdzone obcięcie czterech wejść. KIO_uzp_15777: 63507 → 15000, około 76,4% odczytanego tekstu poza przetwarzaniem. To utrata/nieprzetworzenie treści, **nie wyciek obciętej części w wyniku**. Osobny TEXT-LIMIT-15K pozostaje właściwy. |
| B | Pięć blokad odtworzone. Przyczynę konkretnych trafień trzeba odróżnić od polityki blokowania: pozostała rzeczywista wartość a śmieciowa encja w mapie to różne przypadki. Ostrzeganie zamiast blokady nadal jest proponowaną zmianą spec, nie naprawą do wykonania bez formalnego rozstrzygnięcia. |
| C1 | Błędna/niepożądana klasyfikacja instytucji jako FIRMA i fragmentaryczne podmiany są widoczne. Sam ORG z HerBERT-a nie odróżnia prywatnej firmy od instytucji publicznej; model tego sam nie zamknie. Politykę docelową należy określić w briefie, nie wyprowadzać jej z etykiety modelu. |
| C2 | Potwierdzone tokeny zwykłych słów. HerBERT także dokłada PER dla tytułów/stanowisk i ORG na ułamkach. Unia bez kwalifikowania kandydatów zwiększa również zbiór FP. |
| C3 | Potwierdzone mapy zawierające wyliczenie kilku osób, m.in. interpelacja_1739 i bip_7d1cff548e. Lepszy podział przez HerBERT jest sygnałem przydatności, nie dowodem usunięcia problemów agregacji, nakładania i podmiany. |
| C4 | Różne tokeny dla odniesień do jednej instytucji/adresu są widoczne. **Sama wielość tokenów nie jest błędem**, gdy tekstowe wartości są różne i mają być przywracane dosłownie. Nie wolno naprawiać prezentacji przez wstawianie pełnej nazwy w miejsce skrótu lub odmiany. |
| C5 | Potwierdzony ADRES na fragmencie cytowania Dz. U.; mapa obejmuje przekształcone `ul. Nr ...`. To klasa wierności/normalizacji i fałszywego adresu, nie brak NER. Istniejący normalizator dopuszcza `U.` jako prefiks ulicy. |
| C6 | Potwierdzony pojedynczy FIRMA zawierający nazwę instytucji oraz datę w KIO 578/11. To granice/kategoria encji, nie argument za samą deduplikacją. |

## Zamknięta lista korekt przed akceptacją — R1–R5

**R1. Oddzielić objaw od przyczyny i obietnicy naprawy.**
W §3/§6 skorygować A1/A2 zgodnie z powyższym trace; jawnie powiązać je z otwartym NER-MULTILINE. W A5 rozróżniać istniejącego kandydata utraconego w podmianie od prawdziwego NO-CANDIDATE i od BARE-REPEAT. Zastąpić „HerBERT zamyka A1, A2, A3, A5, A6” stwierdzeniem o wykrytych dodatkowych kandydatach i hipotezie korzyści, z zamknięciem dopiero przez cały łańcuch. Przy A6 zastrzec, że LOC/LOC_PUB nie gwarantuje prawidłowej polityki dla miast.

Uściślić też M1/§2.2: **martwe jest automatyczne seedowanie profilu, nie wszystkie istniejące zasoby imion/nazwisk**. Obecny `ner_blocklist._PERSON_FORMS` ma 12154 form używanych przez filtry; adapter ma 10080 form nazwisk dla inicjałów. Brak seedowania nie oznacza nieistnienia tych mechanizmów. Argument za osobnym słownikiem jest nadal merytoryczny, ale nie należy opierać go na szerszym, fałszywym skrócie.

**R2. Doprecyzować K2 bez ponownego błędu wartości mapy.**
„Jedna rzecz = jeden token dla powtórzeń i odmian” jest za szerokie jako podstawa briefu. Deduplikacja identycznych napisów, rozpoznanie tej samej osoby i bezstratne przywrócenie różnych napisów to różne zagadnienia. Zachować granicę BARE-REPEAT: pełna firma z formą prawną i goły zapis nie mogą zostać automatycznie uznane za identyczną wartość ani podmiot. K2 ma wykluczać dopisanie formy, cudzych słów, sklejonego wyliczenia lub innej osoby. Nie proponuję tu nowego formatu mapy ani alokatora; chodzi o niesprzeczny cel zachowania. K2 nie zamyka B tylko przez zmniejszenie liczby tokenów.

**R3. Oddzielić propozycję Guarda od obowiązującego kontraktu.**
W §4 i K4 napisać wprost, że LYNX-SPEC-S4-GUARD-WARN nadal oczekuje formalnej decyzji i zmiany S4/FROZEN.lock. Aktualne S4 opisuje blokowanie, a S3 zachowuje fail-closed przy awarii. Relacja Pawła o pierwotnej intencji i zgoda CC nie są już dokonaną zmianą spec. Oceniam proponowaną rolę ostrzegania jako odrębny kierunek do rozstrzygnięcia wraz z realnym sposobem poprawki/potwierdzenia przed udostępnieniem wyniku; nie zatwierdzam tu obejścia blokady ani nie wymagamy od Pawła kolejnej decyzji w ramach tego przeglądu. Otwarty wiersz pozostaje właściwą ścieżką.

**R4. Poprawić interpretację pomiarów, nie usuwać niewygodnych porażek.**
Ręczny przegląd jest potrzebny do poprawienia błędnego gold i oceny znaczenia, ale nie unieważnia automatycznie jawnego powtórzenia lub częściowego PII. Miara na wystąpienie odpowiada na inne pytanie niż miara na osobę/dokument; obie mogą być prawdziwe. Częściowe zamaskowanie pozostaje niepełną ochroną, jeśli fragment identyfikuje osobę — jego wagi nie rozstrzyga sama nazwa metryki. Oddzielić obliczony wynik z PII od wyniku odblokowanego dla użytkownika, a A7 od wycieków. Wniosek „reszta encji działa dobrze” ograniczyć do zaobserwowanych przykładów; ta diagnoza nie certyfikuje całych kategorii NIP/PESEL/IBAN. Ocena okiem Pawła jest odbiorem użytkowym, nie zamiennikiem S1–S5 ani podstawą do ukrycia niezaliczonego przypadku.

**R5. Uzupełnić znaczenie zamknięcia w §7 i uporządkować zależności K1–K5.**
Lista zawiera wszystkie 14 klas A1–A7/B/C1–C6 oraz M1/M2 — nie brakuje wiersza obserwacji. Brakuje rozróżnienia: „detektor wskazał”, „poprawny span został zastosowany”, „wynik nie zawiera wskazanego PII”, „mapa/Przywróć nie wstawia obcej treści”. Przy powtórzeniach i sklejonych osobach odnotować te istniejące obowiązki jako warunek potwierdzenia, nie samo odczucie czystszego wyniku. Dodać odnośnik do pełnej listy dokładnych wejść (poniżej) i zachować rozdział danych dev od przyszłego odbioru.

Kolejność nie jest jeszcze uzasadniona jako sztywne K1→K2→K3: znane błędy MULTILINE/podmiany są już źródłem A1/A2; ograniczenie 15K uniemożliwia wykazanie zamknięcia całych długich dokumentów; agregacja C3/C6 wpływa na interpretację kandydatów. Trzeba jawnie uwzględnić te zależności przed obietnicą efektu K1. K1 może pozostać zadaniem według obszaru — **nie żądam ponownego cięcia go na objawy**. K5 jako propozycja po pomiarze jest rozsądnie warunkowy, lecz reguła przez newline musi odróżniać jedną osobę przełamaną wierszem od dwóch osób/komórek; sama wielka litera tego nie rozstrzyga. M2 pozostaje osobną obserwacją uruchamiania, a nie potwierdzoną przeze mnie awarią: nie uruchamiałem dev.bat/uruchom.vbs ani Tauri.

## Ocena kierunku §6

- **HerBERT jako dodatkowe źródło kandydatów: sensowny kierunek do pomiaru**, nie dowód konieczności zastąpienia SpaCy i nie integracja gotowa do zaakceptowania. W obecnych wynikach są zarówno użyteczne wykrycia, jak i FP/fragmenty. Słowo „kandydat” ma znaczenie: etykieta ORG/LOC nie jest automatycznym werdyktem prywatnej firmy/adresu. Regexy, istniejące ownery, alokacja, mapa i Guard zachowują swoje odpowiedzialności.
- **Osobny słownik zasobów programu zamiast 12 tys. encji profilu biura: uzasadniony kierunek**. Zasoby Mobile i ich liczebności są potwierdzone; ich skuteczność jako nowej warstwy Desktop nie została jeszcze zmierzona. Wielka litera oraz rozróżnianie nazwisk pospolitych/miast przez kontekst wymagają kontrprób, również na początku zdania i w nagłówku. Nie przywracać wadliwego seedu jako rzekomo gotowego rozwiązania.
- **A4 jako stary błąd kodu: potwierdzone w zakresie opisanej próby historycznego komponentu i obecnego wyniku**, niezależne od HerBERT-a. Nie ustanawiam nowej bisekcji ani pełnego historycznego wyniku jakości.
- Kierunek „dokument → wynik → ocena → mała poprawka” jest właściwy. Te 17 dokumentów to jednak obejrzany dev, a nie niezależny odbiór przyszłych zmian; zakres deklaracji musi odpowiadać temu dowodowi.

[Karta modelu producenta](https://huggingface.co/lexedit/herbert-polish-legal-ner), sprawdzona 2026-10-18, deklaruje CC BY 4.0 i etykiety LOC/LOC_PUB, lecz zastrzega pozostałe pominięcia oraz potrzebę dodatkowego przetwarzania i oceny człowieka. To wspiera potraktowanie modelu jako warstwy pomocniczej, nie gwarancji pełnego maskowania. Deklarowane metryki autora nie są pomiarem Desktop.

Lokalny model ONNX SHA256: `5ed91aabec29e07d2d5c7f370a5463283d4d88acbf44dd1ceedd0bca67330b50`; config: `10d72599fc1b58425c7dc8e24c4a84cdc69b9defcdd032549d968fa527461991`; tokenizer: `2e045c82c9ea8b5bc54162d92d5c72141492df88eff098f3e5436e499d1e29fb`. Użyto opublikowanego progu PER 0.2. Sprawdzono pokrycie wejść przez tokenizer: w tych 17 dokumentach brak ucięcia przez `[:512]`, maksymalnie 340 tokenów w kawałku. To nie certyfikuje dowolnego przyszłego tekstu z bardzo długą linią. Nie dokonywałem reprezentatywnego pomiaru wydajności ani testu instalatora.

## Zakres i dalszy krok

Warstwy: rzeczywisty HTTP + istniejący profil + lokalny HerBERT; lektura rzeczywistych wyników; punktowy trace prawdziwego SpaCy z pustym profilem; pamięciowy reproduktor seedu; kontrolowany komponent historyczny; zasoby Mobile; spec i powiązane otwarte wiersze.

**NOT_CHECKED:** integracja HerBERT/słownika z produktem, pełna macierz przyszłych briefów, pełna regresja/benchmark, odbiór Tauri/telefon, OCR Mobile i nowe skany/DOCX, aktualność wszystkich historycznych procentów. Nie zmieniono ani nie cofnięto wcześniejszych PASS wąskich dostaw.

Następny krok: CC koryguje tylko R1–R5 na podstawie zachowanych dowodów. Ponowna ocena może być ograniczona do korekty dokumentu; te same 17 wyników nie wymagają ponownego przeliczania bez zmiany kodu/wejść. Briefy dopiero po usunięciu opisanych sprzeczności. Bez merge i bez traktowania tej opinii jako decyzji OWNERA o nowym zachowaniu.

## Dokładne wejścia odtworzone w tej ocenie

Identyfikatory odpowiadają lokalnym partiom; wartości pól i dokumenty nie są publikowane.

| Wejście | SHA256 oryginalnych bajtów | Pełny odczyt / tekst API |
|---|---|---|
| `A_bip_bip_4724bbe26b` | `267604cedf0dd0ee7e69491b8383114504522903ea040421cc529264424c84af` | 1564 / 1560 |
| `A_bip_bip_4d6b2c8f5e` | `99d4e4746a7577454a257e00c36d71e422c6c2158cacd1cfa348f1d2f52c4b46` | 1239 / 1221 |
| `A_bip_bip_7d1cff548e` | `23a9a07b1d31ebadd97122a9954097e78138884fbd68b1af311a7d9e8e696017` | 2667 / 2663 |
| `A_sejm_interpelacja_1739` | `e00656ff98b04d9ba80440b93be91d412770b1bf3b1137652470e5bb94f5bb36` | 4938 / 4938 |
| `A_sejm_interpelacja_3823` | `7151a1510cf273df0ee901e972aed77366d27a8a9648b91701ae8892c7308096` | 6095 / 6095 |
| `A_sejm_odpowiedz_5791` | `ff0143dd3b26ba8e32bbf24cbb4e409497fd534e54858a1e162219587f57e169` | 8978 / 8978 |
| `A_uzp_KIO_uzp_10838` | `8585e515dec0abc55452310db11e160c07421118f7a336c3d015ffc95eea9a6f` | 3736 / 3735 |
| `A_uzp_KIO_uzp_15777` | `74c9bc7325822fdbbd29bd87c5d49d2bf4b6822139fc9c558bca3d9c476b0ea0` | 63507 / 15000 |
| `A_uzp_KIO_uzp_16714` | `f2094020287fb2692621eea1d5bbd45a8c3e18e4abb9073d8ef10ac2dfdceb32` | 6883 / 6882 |
| `B_kio_KIO_114738` | `3620f815783d4ade1ddb5639f76746af7af2d120a0da86ef2c1bf20b557ae867` | 17635 / 15000 |
| `B_kio_KIO_118215` | `476c728d267e80d5504cbd367d90765f67895c7cdc053d6503260e1d72724c71` | 22419 / 15000 |
| `C_codex_C006` | `2258aa52691fb3dabf43fe99fd1dd2698d330234e56200b1c505331bc71e5aae` | 5725 / 5642 |
| `C_codex_C022` | `febdccf056f82d28cd9745789bb5f9038e57bb95fe68020499e68cce08e7c25e` | 3479 / 3465 |
| `C_codex_C024` | `6f48e692c0d9a43fd722769c5ed046f8a12a917d0167c556908e3ad98debc58e` | 2724 / 2723 |
| `C_codex_C025` | `6e6eee42bb90fdb0420301e8d9e0c064be7522cd2363dc03e6519d3c2055ae8b` | 9263 / 9262 |
| `C_codex_C047` | `07f4146126036fa05fc3382df3896328e51506bcd9f7c40ada850508d8aac6e4` | 2357 / 2355 |
| `KIO_578-11 (dodatkowy PDF)` | `f73d75f2c04dfc87ea59c3f681c8dd9b16a0067c4234f69f8a7895c6c2e5fc01` | 16016 / 15000 |
