# MANUAL-REVEAL — zamknięte przekazanie korekty polityki do Architekta

Data: 2026-10-20.
Podstawa: rozmowa Pawła z Codexem po prechecku v2.
Paweł zaproponował odkrywanie po obsłużeniu alertów Guarda. Codex zarekomendował
tę kolejność oraz lokalną zgodę na konkretne wystąpienie.
Paweł polecił doprecyzować za jego zgodą albo cofnąć do Architekta, aby uniknąć pętli.
Wybrana czynność: **zwrot do Architekta z jednym zamkniętym zakresem korekty**.

## Co trzeba poprawić, zamiast budować dalej v2

V2: 306c597ca99fd02e4bdd4e18a0a8b409bf85f60a.
Raport r2: ebfa55d2f6e1e0b29e7faadf07b3526b9c49afa3.
PASS r2 zamykał brak szwu API C1, NIE rozstrzygał użyteczności odkrycia.
Nie traktować tego PASS jako zatwierdzenia konfliktującej polityki.

Kierunek do zapisania w nowej wersji briefu:
1. Maskowanie, następnie obsługa alertów dotychczasowego Guarda.
2. Na tym wyniku świadome odkrycie wskazanego, pojedynczego wystąpienia tokenu.
3. Kopiowanie/zapis/eksport dokładnie widocznego tekstu po korekcie.
   Kontrola spójności i bezpieczeństwa ma respektować tę konkretną operację;
   nie może automatycznie cofać jej wyłącznie dlatego, że ujawniona wartość
   nadal znajduje się w oryginalnej mapie sesji.

Przykład obowiązkowy:
„OSOBA_033 zakwitła” / „Pani OSOBA_033 odebrała dokument”.
Odkrycie pierwszego miejsca daje „Róża zakwitła”; drugie pozostaje zakryte.
Ta świadomie zatwierdzona korekta ma dać się udostępnić, zamiast kończyć
zawsze blokadą MAP_LEAK. Cofnięcie przywraca token.
Bez zgody na inne wystąpienia, globalne wyjątki, trwałą allowlistę,
zmianę mapy sesji, NER, słownik homonimów lub duży redesign OSOBA.

## Jedno zadanie Architekta

Zastąpić sprzeczną część v2 jednoznacznym kontraktem lokalnej zgody:
- kiedy obsługa alertów jest zakończona i kiedy można odkrywać;
- jak zgoda jest powiązana z sesją, konkretnym wystąpieniem i wersją wyniku;
- jak kontrola finalnej treści respektuje zaakceptowane odkrycie, a nadal
  wykrywa pozostałe nieuzgodnione zmiany, inne miejsca i inne naruszenia;
- jakie kategorie/alerty obejmuje ta zgoda, w szczególności relację do
  HIGH i zamrożonego S4: nie zostawiać tego do zgadywania przez CC;
- cofnięcie, nowy dokument i zmiana wyniku unieważniają właściwy kontekst;
  błąd silnika/Guarda i brak wiarygodnego kontekstu nie są akceptacją;
- źródło PRODUCT_TRUTH i najmniejszy zakres zmiany ownera/API.
  Jeżeli rozstrzygnięcie wymaga zmiany frozen spec, wskazać konkretny
  fragment i przedstawić tę zmianę jawnie do zatwierdzenia;
  nie wpisywać, że v2/spec już zezwala na dowolne obejście blokad.

Zgoda Pawła na doprecyzowanie/zwrot nie jest pustą zgodą na wyciszenie
wszystkich HIGH, wyłączanie Guarda lub dowolne ujawnianie PII.
Równocześnie nie wracać do projektu, w którym zwykłe poprawne odkrycie
jest z definicji niemożliwe do udostępnienia.

## Następny krok i koniec obecnej rundy

Architekt poprawia ten jeden konflikt, a CC recenzuje wykonalność/budżet.
Nie rozpoczynać implementacji v2 ani kolejnych rund automatycznego FAIL
w celu projektowania rozwiązania przez audytora.
Codex nie pisze implementacji, nie uruchamia testów i nie zmienia spec.
Historyczne raporty pozostają bez zmian. Brak polecenia merge.
