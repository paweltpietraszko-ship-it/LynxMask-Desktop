# LYNX-MANUAL-REVEAL — kontrakt v3: odkrycie bez pętli alarmów

Data 2026-10-20. **STATUS: PROPOZYCJA ARCHITEKTA / OWNER_DECISION_NEEDED. NIE IMPLEMENTOWAĆ JESZCZE.** Zastępuje brief v2 `306c597ca99fd02e4bdd4e18a0a8b409bf85f60a`, po zwrocie Codexa `5ed8d61cf847873ae27073dd10424f9d7326c0f4`. Raport r2 `ebfa55d` potwierdzał wyłącznie wykonalność szwu API, nie brak pętli.

## Cel i rozdział ról

Na ekranie `Zamaskuj` użytkownik może w podglądzie wskazać i ręcznie odkryć **jedno wystąpienie** tokenu błędnie zakrywającego zwykłe słowo, a potem skopiować/zapisać **dokładnie ten widoczny tekst**. Jest już pole „Dodaj i zakryj”; obok prosta akcja „Odkryj tutaj”, z komunikatem „Jeżeli to słowo nie jest daną osobową, możesz odkryć je tylko w tym miejscu”. Bez JSON homonimów, reguł czasownikowych, nowego NER, zmian słowników i redesignu OSOBA.

**Role:** silnik dokonuje maskowania; OutputGuard wykrywa wycieki i inne podejrzane pozostałości; interfejs umożliwia człowiekowi *świadomą korektę* wcześniejszego nadmaskowania. Guard nie rozstrzyga, czy Róża jest kwiatem.

## Kolejność operacji i zgoda użytkownika

1. `/preview`: normalna pseudonimizacja oraz dotychczasowy Guard. **Przed odkrywaniem** wszystkie alerty muszą być obsłużone na obowiązujących zasadach. Jeżeli stan końcowy wyniku jest zablokowany, silnik/Guard zwrócił błąd albo pozostał niezakończony alert: żadnego odkrycia, wyślij po poprawieniu/ponownej pseudonimizacji. Samo kliknięcie „obsłużone” nie odblokowuje HIGH. Zmiana frozen S4 na ogólny model ostrzeżeń NIE należy do tego Tasku.
2. Użytkownik wskazuje **całe, pojedyncze wystąpienie tokenu** (nie wartość we wszystkich miejscach) i wybiera `Odkryj tutaj — potwierdzam, że to nie PII w tym miejscu`. Zgoda dotyczy tylko tej lokalizacji w bieżącym dokumencie. Może ją cofnąć; nie trafia do `GuardAllowlist`, profilu, `.lynxdict` ani globalnego wyjątku.
3. Kontrola finalnego tekstu respektuje tę konkretną potwierdzoną operację. **Nie może generować ponownie tego samego `MAP_LEAK` dla zatwierdzonej pozycji** — to byłaby nieskończona pętla. Nie wyłącza jednak żadnego innego alarmu ani innej lokalizacji.

**Ograniczenie fazy 1:** tylko pojedynczy token z jednoznaczną mapą do **jednego słowa**; nie umożliwiać częściowego odsłonięcia `OSOBA_001 → Anna Malina` ani świadomego ujawnienia całego wielowyrazowego tokenu bez odrębnej zgody produktowej. Brak tokenu w mapie, niejednoznaczny span lub zaznaczenie kilku tokenów → odmowa z instrukcją „Zaznacz jeden cały token”.

## Przykład obowiązkowy (ten sam token, dwie role)

Tekst wynikowy:
```
01. OSOBA_033 zakwitła rano na rabacie.
02. Pani OSOBA_033 odebrała dokument.
```
Mapa: `OSOBA_033 → Róża`. Zgoda na odkrycie pierwszego wystąpienia daje:
```
01. Róża zakwitła rano na rabacie.
02. Pani OSOBA_033 odebrała dokument.
```
Eksport tego wyniku MUSI być możliwy po prawidłowej, wąsko określonej zgodzie i pomyślnej kontroli innych zagrożeń. Drugie wystąpienie pozostaje zakryte. Nie wolno `replaceAll`, globalnych allowlist ani globalnego wyciszenia wartości `Róża`.

## Kontrakt techniczny, bez nowego silnika i bez zmiany reguł Guarda

**Szew:** istniejące `frontend/src/screens/Pseudonimizuj.tsx` oraz minimalny punkt API `backend/pseudominizer_api.py` (np. `POST /preview/validate-final`). Bez ponownego `pseudonymize_document`; tokeny w wejściu edytora nie są nowym dokumentem do `/preview`. Nie zmieniać `backend/output_guard.py`, `pipeline`, formatów map/archiwum ani `/profile/guard-allowlist`.

**Serwerowa prawda:** krótki kontekst w pamięci procesu (PSE + identyfikator sesji, bazowy tekst po Guardzie, mapa token→oryginał, stan zgód), bez zapisywania jawnych PII na dysk. Token API i PSE same w sobie nie autoryzują operacji; po restarcie/wygaśnięciu kontekstu STOP i komunikat „Przetwórz dokument ponownie”. Żądanie klienta nie jest autorytatywne co do mapy, oryginalnych wartości, obecnych blokad ani indeksów.

**Zgoda lokalna:** wyłącznie identyfikator danego wystąpienia w niezmiennym wyniku bazowym (np. `(sesja, ordinal wystąpienia, offset źródłowy, token)`) wraz z jawnym potwierdzeniem. Serwer sam oblicza tekst docelowy ze zbioru zatwierdzonych odkryć i weryfikuje pełną zgodność z `finalText`, łącznie z prefiksem PSE, interpunkcją i pozostałymi tokenami. Inne dowolne edycje nie są uprawnione. Dwa identyczne tokeny mają różne identyfikatory wystąpień. Można mieć kilka osobnych zgód w tym dokumencie, ale każda wymaga osobnego działania użytkownika. Cofnięcie usuwa tylko właściwą zgodę.

**Dwie niezależne kontrole (klucz do uniknięcia pętli):**
- Na **rzeczywistym, odkrytym `finalText`** wykonać istniejącą kontrolę strukturalnych HIGH/MEDIUM (PESEL, NIP, IBAN, EMAIL, dowód, paszport, REGON, telefon) według `GuardMode.REDACT`, bez żadnego wyłączenia dla odkrytej lokalizacji. Jeśli Guard blokuje, ma błąd lub chce redagować tekst zamiast go zaakceptować, to NIE zatwierdzać nieredagowanego `finalText`.
- Na **projekcji do kontroli mapy**: identyczny tekst, ale *tylko* świadomie odkryte i zweryfikowane pozycje zastąpione z powrotem ich bazowymi tokenami, uruchomić niezmieniony `guard_output_with_map` z profilem/znanymi wartościami *serwera*. Dzięki temu `MAP_LEAK` od tej dokładnej zatwierdzonej pozycji nie wraca, natomiast pozostałe jawne nazwiska, miejsca, wycieki i nieautoryzowane zmiany nadal są widoczne dla map-checku. **Nie wycinać wartości globalnie ze znanych nazw.** Projektowany mechanizm projekcji jest **wąską zmianą polityki użycia Guarda**, a nie zmianą jego wzorców.
  
Nie utożsamiać `APPROVED` z decyzją użytkownika: `APPROVED` wymaga poprawnego kontekstu, dozwolonej operacji, bazowego statusu bez blokad oraz przejścia *obu* kontroli. `BLOCKED` i `ERROR` zawsze uniemożliwiają kopiowanie/zapis/eksport edytowanej treści; błędy nie tworzą domyślnej zgody. Alert HIGH może zablokować wynik, ale nie powoduje powtarzanych pytań o tę samą świadomą korektę.

**Rewizje i wyjście:** każda nowa operacja odkrycia/cofnięcia, domaskowania, zmiana dokumentu albo tekstu unieważnia poprzedni wynik walidacji `APPROVED`. Dotychczasowe zgody dla innych poprawnych wystąpień mogą pozostać w sesji, lecz pełny *nowy* `finalText` musi ponownie przejść walidację; wynik spóźnionej odpowiedzi dla starej rewizji nie autoryzuje nowej. Jedna kanoniczna wartość `finalText` obsługuje ekran, kopiowanie i zapis, nie `result.anonymized_preview`. Przy `/archive` backend nadal dostaje szyfrogram — kontrola, że zaszyfrowano dokładnie zatwierdzony tekst, odbywa się w UI i testach; nie przedstawiać archiwum jako niezależnie zweryfikowanego przez backend.

## Granica frozen spec i niezbędna decyzja OWNERA

Dziś `arch/spec.md` S3/S4 oraz `output_guard.guard_output_with_map` blokują `MAP_LEAK`. Przeprowadzenie map-checku na projekcji ukrywającej **wyłącznie wcześniej potwierdzone konkretne wystąpienie** jest wyjątkiem od tej praktyki. Nie wolno traktować starego PASS r2 ani samego polecenia korekty jako zgody na ten wyjątek.

**Rekomendowana, precyzyjna decyzja do zatwierdzenia:** „Po normalnym przejściu Guarda użytkownik może świadomie odkryć wskazane pojedyncze wystąpienie tokenu. Ponowna kontrola wyłącza jedynie mapowy alarm `MAP_LEAK` wywołany przez to zatwierdzone wystąpienie; wszystkie pozostałe pozycje oraz reguły HIGH/MEDIUM i S3 nadal obowiązują. Zgoda nie przechodzi między dokumentami, nie jest trwałym wyjątkiem i może zostać cofnięta.” Tę zasadę należy po osobnej aprobacie OWNERA wpisać jawnie do S4 i ponownie zamrozić zgodnie z procedurą repo. **Do tego czasu NIE IMPLEMENTOWAĆ.**

## Test i kolejność prac

**Codex** może przejrzeć ten kontrakt pod kątem spójności po decyzji OWNERA; nie kierować v2 do CC. **CC** po zatwierdzeniu recenzuje minimalny owner/API i budżet (>150 linii zmian, pliki >600 linii, funkcja >50, ratio >5:1 wymagają zgody OWNERA przed kodowaniem), a potem implementuje jedynie w uzgodnionym zakresie. Codex następnie audytuje exact SHA; żaden PASS nie oznacza automatycznego merge.

Kontrpróby: `Róża` dwa wystąpienia, odkrycie tylko pierwszego; drugi jawny `Róża` *bez zgody* powoduje nadal map alarm; trzy wystąpienia i cofnięcie jednego; nowy dokument i reset zgód; ten sam token/dwa różne wystąpienia; zawyżony offset, wielowyrazowy oryginał, brak sesji, ponowione zatwierdzenie, wyścig walidacji z nową rewizją, restart serwera, awaria Guarda, `HIGH` odkryty w kontrolowanej lokalizacji, nieuprawniona edycja poza tokenem; każde wyjście ma używać tego samego zaakceptowanego `finalText`. Żadnych autentycznych dokumentów/PII w repo i logach.

Dalsza kolejność nie zmienia się: po MANUAL-REVEAL osobny `K1a` HerBERT jako ostatnia siatka na nadal jawne fragmenty, następnie punktowe ograniczanie nadmaskowania. Duży OSOBA-REDESIGN oraz JSON homonimów pozostają odłożone.
