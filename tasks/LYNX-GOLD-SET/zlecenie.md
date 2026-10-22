# LYNX-GOLD-SET — zlecenie dla Codexa: świeży zbiór dokumentów biurowych z ground truth

22.10.2026, CC na prośbę OWNERA. Cel: niezależna miarka tego, co ostatecznie widzi człowiek (tekst po zakryciu + ostrzeżenia Guarda).
Dokumenty piszą i oznaczają agenci Codexa. CC nie pisze dokumentów ani ground truth, tylko puszcza zbiór przez silnik i liczy wynik.

## Kto co robi
1. **Agent-autor (Codex odpala własnego agenta):** pisze dokumenty i **jednocześnie** listę danych, które w nich umieścił (ground truth). Lista powstaje razem z dokumentem, a nie po fakcie.
2. **Agent-weryfikator (świeży, inny niż autor, bez wiedzy o silniku LynxMask):**
   - sprawdza każdy dokument z jego listą: brakujące dane, zbędne pozycje, zgodność z zasadami niżej, pozycje start/end;
   - uruchamia skrypt unikalności na całym zbiorze;
   - pisze raport.
3. **Codex:** odbiera raport weryfikatora, poprawia lub odrzuca dokumenty, oddaje zbiór.
4. **CC:** tylko pomiar.
   - **Części kontrolnej CC nie otwiera**, korzysta z niej wyłącznie przez skrypt liczący wynik. Na niej nie wolno stroić reguł.
   - Część roboczą wolno oglądać i na niej poprawiać.

## ZAKAZ POWTARZANIA (OWNER 22.10: „agent bez zakazu powielania encji będzie je powielać”)
- **Każda wartość danej jest unikalna w całym zbiorze.** Dotyczy to imienia z nazwiskiem, nazwiska, firmy, adresu, PESEL, NIP, REGON, KRS, numeru dowodu i paszportu, IBAN, telefonu, e-maila, numeru działki, KW, sygnatury, numeru umowy i faktury oraz daty urodzenia.
  - Ta sama osoba nie występuje w dwóch dokumentach.
  - Dwa dokumenty nie mają tego samego nazwiska, nawet przy innym imieniu.
- **Zakaz nazw-wzorców:** Kowalski, Nowak, Wiśniewski, Wójcik, Kowalczyk, Jan Kowalski, Anna Nowak, „ABC sp. z o.o.”, „XYZ”, „Przykładowa”, „Testowa”, ul. Lipowa / Długa / Kwiatowa, Acme. Także żadnych nazw z istniejących zbiorów repo (`backend/dataset_*`, `Pliki testowe/`, pliki testowe repo Mobile `testy/`).
- **Nazwiska z różnych typów:** pospolite (-ski/-cki), rzadkie, dwuczłonowe, obce, nazwiska będące zwykłymi słowami (np. Malina, Kawa, Zielona, Wrona, Kot — każde najwyżej raz w zbiorze).
- **Imiona:** zróżnicowane, różne formy fleksyjne.
- **Wewnątrz jednego dokumentu** ta sama osoba lub firma może wystąpić kilka razy, także w odmianie („Pani Malinowska… Malinowskiej…”). To sprawdza spójność tokenu i jest pożądane. Każde wystąpienie jest osobną pozycją listy z tym samym `entity_id`.
- **Weryfikator uruchamia skrypt unikalności:** normalizacja do małych liter i bez spacji/myślników, porównanie wartości między dokumentami. Każde powtórzenie między dokumentami to błąd do poprawki.

## Zasady oznaczania (propozycja CC z ustaleń OWNERA; OWNER zatwierdza przed startem)
Dane do zakrycia (`pii`):
- **OSOBA:** imię i/lub nazwisko osoby fizycznej w każdej odmianie, pseudonim osoby, inicjał przy imieniu („Marek T.”).
  - Imię i nazwisko razem = jedna pozycja.
  - Patron w nazwie ulicy albo instytucji („ul. Jana Pawła II”, „Szpital im. Jana Pawła II”) to NIE osoba, tylko część adresu albo nazwy instytucji.
- **FIRMA:** nazwa przedsiębiorstwa prywatnego z formą prawną albo bez, w tym banki i kancelarie. Urzędy, sądy, gminy, ZUS, KRUS, NFZ, szkoły publiczne to NIE firma.
- **ADRES:** ulica z numerem, kod pocztowy z miejscowością, albo całość. **Samo miasto bez ulicy i kodu NIE jest daną.**
- **NUMER:** PESEL, NIP, REGON, KRS, dowód, paszport, IBAN/konto, telefon, numer działki, KW, numer klienta, umowy, faktury, polisy, sygnatura akt, data urodzenia (także bez „ur.”).
- **EMAIL:** adres e-mail.
- **KWOTA:** kwota pieniężna (cyfrowo albo słownie).

NIE dane (`not_pii`, oznaczać jawnie, bo sprawdzamy zbędne zakrycia):
- etykiety i role: Nabywca:, Sprzedawca:, Zamawiający, Wykonawca, Strony, Pracodawca, OCZEKIWANE:;
- zwykłe słowa z wielkiej litery w znaczeniu pospolitym („W ogrodzie rosła Malina”, „Zielony płot”);
- nazwy urzędów i sądów, samo miasto, daty pisma, nazwy ustaw i artykuły, miesiące, nazwy produktów i usług.

## Zamówienie trudnych przypadków (każdy rodzaj w kilku dokumentach)
- nazwisko będące zwykłym słowem obok tego samego słowa w znaczeniu pospolitym;
- etykieta z dwukropkiem na początku linii, także WIELKIMI literami;
- układ w dwóch kolumnach (Sprzedawca | Nabywca w jednej linii, odstęp spacjami);
- lista kilku nazwisk po przecinkach;
- patron ulicy i miasto wieloczłonowe (Jelenia Góra, Zielona Góra, Nowy Targ);
- adres w odwróconej kolejności („Wrocław, 50-001”), adres bez kodu;
- inicjał przy imieniu, imię z nazwiskiem w odmianie, sama forma grzecznościowa („Pani Malinowska”);
- firma bez formy prawnej po roli („Wykonawca: Biuro Rachunkowe …”), firma z formą prawną w środku zdania;
- numery z separatorami i bez, zniekształcenia OCR w ok. 20% dokumentów (l↔1, O↔0, rozbite spacje, sklejone słowa);
- ten sam PESEL lub nazwisko dwa razy w jednym dokumencie.

## Rodzaje i liczba (razem 120)
umowy 25 · faktury i rachunki 20 · pisma i decyzje urzędowe 20 · wezwania i monity 15 · protokoły i notatki 15 · pełnomocnictwa i oświadczenia 10 · korespondencja e-mail biurowa 15.
Długość: zwykle 150–600 słów; kilka dłuższych (do 1500).

## Format i miejsce (lokalnie; `backend/dataset_*` jest w `.gitignore`)
- `backend/dataset_gold_20261022/dev/` (40 dok.) i `backend/dataset_gold_20261022/test/` (80 dok.). Podział losowy, proporcjonalny do rodzajów.
- Każdy dokument: `doc_NNN.txt` (UTF-8) + `doc_NNN.json`:
  ```json
  {"doc_type": "umowa", "ocr_noise": false, "layout": "zwykły|dwie_kolumny",
   "pii": [{"entity_id": "E1", "type": "OSOBA", "text": "Marka Malinowskiego", "start": 120, "end": 139}],
   "not_pii": [{"text": "Malina", "start": 300, "end": 306, "why": "owoc"}]}
  ```
  Pozycje start/end w punktach kodowych (Python `len`), `text == plik[start:end]`.
- Raport weryfikatora: `tasks/LYNX-GOLD-SET/round_01/tests/verify_r1.txt` (bez treści dokumentów; liczby, błędy z numerem dokumentu i pozycji).

## Odbiór
Zbiór uznajemy za gotowy, gdy:
- weryfikator ma 0 powtórzeń między dokumentami;
- każda pozycja ma poprawne start/end;
- każdy trudny przypadek z listy występuje co najmniej w 3 dokumentach;
- raport weryfikatora jest w repo.

Dopiero wtedy CC uruchamia pomiar. Wyniki: ciche wycieki (dana jawna bez ostrzeżenia Guarda), wycieki z ostrzeżeniem, zbędne zakrycia `not_pii`, ostrzeżenia na dokument.
