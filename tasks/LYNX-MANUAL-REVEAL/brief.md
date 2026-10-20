# LYNX-MANUAL-REVEAL — ręczne odkrycie pojedynczego wystąpienia (brief do Codex BRIEF_ONLY)

Data: 2026-10-20. Kierunek zaakceptowany przez OWNERA w rozmowie po obejrzeniu ekranu Desktop. Bez zgody na merge i bez zmiany spec S4.

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
- **OutputGuard zachowuje odrębną rolę i sprawdza ostateczną treść przed udostępnieniem.** Samo sprawdzenie starej wersji przed edycją nie wystarcza. Zmodyfikowanego tekstu NIE wolno kopiować, zapisać ani eksportować bez ponownego, wiarygodnego przejścia warunków bezpieczeństwa. Zamrożony `arch/spec.md` S3/S4 obowiązuje; nie tworzyć obejścia HIGH/blocked. Jeśli obecne API nie obsługuje ponownego sprawdzenia albo blokuje nawet świadomie zaakceptowane odkrycie — **zatrzymać implementację**, pokazać najmniejszy reproduktor i wrócić do Architekta/OWNERA po osobne rozstrzygnięcie spec/API.
- `Przywróć`: testować na docelowym tekście po korekcie i pierwotnej lokalnej mapie; oryginalny tekst ma dać się odtworzyć 1:1 tam, gdzie jest to technicznie możliwe. Nie dopuszczać kolizji tokenów, uszkodzeń spacji czy znaków. Bez utrwalania jawnych PII w logach, rapportach, nowym nieszyfrowanym pliku ani dodatkowym profilu.
- Tryb Express ma osobną politykę kopiowania/archiwum — nie zmieniać jej przy okazji. Zmiana istniejącej akcji „Dodaj i zakryj” i zachowania Guarda jest poza zakresem.

## Fakty o obecnym kodzie, do sprawdzenia na exact SHA przed pracą

- `frontend/src/screens/Pseudonimizuj.tsx`: `HighlightedText` renderuje tokeny; `previewRef` i `selectionchange` istnieją; `handleAddEntity` ponawia `/preview`; „Kopiuj tekst” kopiuje `result.anonymized_preview`; `handleSave` szyfruje ten sam tekst razem z `result.tokens` i archiwizuje; UI ma istniejący `guardBlocked`.
- `frontend/src/screens/Depseudonimizuj.tsx` to odzyskiwanie po sesji, nie miejsce ręcznej korekty tekstu przed wysyłką.
- Mobile `TextPreviewModal.kt` ma „Odkryj”, lecz obecne `revealedTokens` ujawnia wszystkie miejsca identycznego tokenu; nie kopiować tej wady.
- Przed kodem CC punktowo ustala, czy jest istniejący **backendowy** szew do ponownego sprawdzenia finalnej treści przez OutputGuard oraz jak obecne archiwum zachowuje mapę i poprawiony tekst. Brak szwu oznacza precheck/blocker, nie domyślną zgodę na nowy endpoint.

## Zakres i odbiór

`TASK_SCOPE` do prechecku: minimalna zmiana UI `frontend/src/screens/Pseudonimizuj.tsx` + wyłącznie najmniejszy istniejący test/ui helper niezbędny do per-wystąpienie, po audycie budżetu. Backend/API/schemat archiwum **nie są autoryzowane** w tym briefie. Jeżeli wymagane, CC ma wskazać docelowy istniejący owner i zwrócić `OWNER_DECISION_NEEDED` z minimalną propozycją rozszerzenia — nie pisać jej bez zgody. Unikać rozrastania już dużego pliku UI; limit repo (>150 zmienionych linii, >5:1, >600 plik, >50 funkcja) sprawdzić przed implementacją i poprosić o zgodę, jeśli nie da się uniknąć.

Kontrpróby Codexa i CC: 2× ten sam `OSOBA_033` i ujawnione tylko pierwsze wystąpienie; 2 różne tokeny o tej samej oryginalnej wartości; token wielowyrazowy; brak mapy; wybór niepełny i obejmujący wiele tokenów; „Cofnij”; nowy dokument; ponowne maskowanie; `Przywróć` 1:1; zgodność wyświetlenie/kopiowanie/zapis; kontrola udostępnienia po edycji przez Guard; blokada S3/S4 pozostaje skuteczna. Dodatkowo bez zmian w profilu i bez regresji obecnego domaskowania.

**Codex BRIEF_ONLY jako pierwszy:** oceń 1) wykonalność per-wystąpienie w istniejącym UI, 2) bezpieczeństwo kopii/archiwum po edycji i kontrolę przez Guarda, 3) ewentualną zależność od frozen S4, 4) minimalny owner i budżet. Nie uruchamiaj kodu w prechecku. PASS PREIMPLEMENTATION lub krótka lista braków / `OWNER_DECISION_NEEDED`. Dopiero potem CC recenzuje brief, implementuje uzgodniony zakres i gate; Codex audytuje **dokładny SHA**, a OWNER decyduje o merge. Raporty tylko syntetyczne, bez rzeczywistych danych osobowych.

## Następne prace — niezależne od tego zadania

1. `LYNX-K1-PERSONS-FIRMS / K1a`: osobny, późniejszy krótki brief HerBERT jako **ostatnia siatka** na wciąż jawnych fragmentach, bez cofania już zakrytych tokenów i bez dopisywania wykrywania do Guarda. Pierwszy pomiar: nowe prawidłowe maski vs fałszywe maski, czasu/VRAM, brak regresji i offline.
2. Dopiero po pomiarach **kosmetyka/jakość OSOBA**: redukcja niepotrzebnych zakryć i błędnych granic tokenów w istniejących warstwach, wąskimi taskami z regresją; duży `LYNX-OSOBA-REDESIGN` bez wznowienia na podstawie samej estetyki wyniku.

Dawny `LYNX-OSOBA-HOMONYM-TEST` (JSON+Guard) jest zakończonym, odłożonym kierunkiem; nie wznowić przypadkiem.
