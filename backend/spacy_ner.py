"""
Triangulum — spacy_ner.py  v1.7
==============================
Automatyczna detekcja encji (PERSON, ORG) w tekście polskim.

Wejście:  surowy tekst dokumentu
Wyjście:  lista NERResult(text, label, confidence, start, end)

Etykiety SpaCy mapowane na typy Triangulum:
  persName / PERSON → TOKEN_OSOBA  ("OSOBA")
  orgName  / ORG    → TOKEN_FIRMA  ("FIRMA")

Integracja:
  Wywoływać przed Anonymizer.anonymize().
  Wyniki przekazać do anonymize_with_ner().

Zmiany v1.7:
  [AUD-02] Usunięcie PII z logów produkcyjnych — naruszenie RODO Art. 5(1)(f).
          Linia 382: logger.warning blokady NER — zamiast '{ner.text}' loguje
          [len=N] gdzie N to długość encji. Treść imienia/nazwiska nie trafia do logu.
          Linia 411: logger.warning blokady regex — zamiast '{candidate}' loguje
          [len=N]. Identyczna zmiana.
          Poziom WARNING jest aktywny w produkcji — logi były dostępne w plikach
          na dysku. Zmiana nie wpływa na działanie blokady pipeline.

Zmiany v1.6:
  [FIX-SYNTAX-1] Docstring linia 18-19: \\s zamienione na \\\\s.
          v1.5 opisywał naprawę SyntaxWarning w docstringu, ale sam opis
          zawierał \\s bez podwojenia — fix nie naprawił siebie.
          Python 3.12+ SyntaxWarning, 3.14+ SyntaxError.
          Linie dotknięte: 18, 19. Kod bez zmian.
  [FIX-LOGGER] logger zmieniony z "triangulum.spacy_ner" na "lynxmask.spacy_ner".
          Plik nie jest współdzielony z Triangulum — mylący prefiks utrudniał
          analizę logów. Linia 84.

Zmiany v1.5:
  [SyntaxWarning] Linia ~28 w docstringu: r'^[\\s.,]*$' → r'^[\\\\s.,]*$'.
          Python 3.14 traktuje \\s w zwykłym stringu (docstring) jako
          invalid escape sequence. Zmiana tylko w komentarzu — regex
          w kodzie był już poprawny (raw string).

Zmiany v1.4:
  [BUG-D] _merge_adjacent_entities: dodanie cudzysłowu prostego `"` do regex
          linia ~199. SpaCy zwracał `„Nazwa Firmy"` i `Sp. z o.o.` jako dwie
          osobne encje FIRMA z cudzysłowem zamykającym jako przerwą — scalanie
          nie zachodziło. Efekt: FIRMA = "z o.o." zamiast pełnej nazwy,
          wyciek nazwy firmy w pseudonimizowanym tekście.
          Zmiana bezpieczna: cudzysłów jako przerwa między fragmentami NER
          tej samej kategorii jest jednoznaczny w kontekście nazw firm.

Zmiany v1.3:
  [BUG-3] _merge_adjacent_entities: dodanie myślnika do regex linia ~199.
          Poprzedni regex r'^[\\s.,]*$' nie zawierał myślnika — nazwiska
          dwuczłonowe (np. "Irena Mazur-Kowalska") dostawały dwa tokeny
          zamiast jednego.
          Zmiana bezpieczna: myślnik jako przerwa NER jest jednoznaczny
          w kontekście nazwisk złożonych.

Zmiany v1.2:
  [FIX-NER-ML-2] detect_entities: encja PERSON nie może obejmować wielu linii.
          SpaCy błędnie scala "Paweł Pietraszko\nAnny Jagiellonki" (imię+adres
          z bloku PDFa) jako jedną encję PERSON. Skutek: replace() trafia tylko
          tam gdzie separator to \n — nie trafia tam gdzie to przecinek lub
          samodzielne wystąpienie nazwiska w innym zdaniu.
          Fix: gdy mapped == TOKEN_OSOBA i entity_text zawiera \n lub \r,
          bierzemy tylko pierwszą linię. Zasada ogólna: imię i nazwisko nie
          zajmuje wielu linii w dokumencie. Adres na kolejnej linii to osobna
          encja obsługiwana przez warstwę regex (TOKEN_ADRES).
          Nie dotyczy FIRMA — nazwy firm mogą legalnie zajmować wiele linii
          w niektórych formatach dokumentów.

Zmiany v1.1:
  [NER-1] _merge_adjacent_entities: scala sąsiadujące encje tej samej kategorii
          gdy są bezpośrednio obok siebie w tekście (max 4 znaki przerwy).
          Naprawia fragmentację "Sp. z o.o." i "S.A." przez SpaCy.

Blokada wysyłki:
  Jeśli wykryto wzorzec imię+nazwisko (dwie wielkie litery,
  pierwsze słowo w słowniku imion) i encja NIE ma tokenu
  w AnonymizerMap — pipeline rzuca NERBlockError.
  Fail-closed: surowe nazwy własne nie wychodzą nigdy.

Ograniczenia (do zbenchmarkowania przed produkcją):
  - pl_core_news_lg recall ~85-90% na polskich tekstach
    prawno-biznesowych; niższy dla nazwisk złożonych i obcych
    nazw firm
  - Confidence per encja: SpaCy nie dostarcza; używamy heurystyki
    opartej na liczbie słów
  - Słownik imion: ~70 pozycji + zdrobnienia; nie jest wyczerpujący
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger("lynxmask.spacy_ner")

# ============================================================
# Typy tokenów — spójne z decyzją architektoniczną (ASCII)
# ============================================================
TOKEN_FIRMA = "FIRMA"
TOKEN_OSOBA = "OSOBA"
TOKEN_NUMER = "NUMER"

# ============================================================
# SpaCy — lazy load (model ~500 MB, ładuj raz per proces)
# ============================================================
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("pl_core_news_lg")
            logger.info("spacy_ner: pl_core_news_lg załadowany")
        except OSError:
            raise RuntimeError(
                "Model SpaCy pl_core_news_lg nie jest zainstalowany.\n"
                "Uruchom: python -m spacy download pl_core_news_lg"
            )
    return _nlp


# ============================================================
# Słownik polskich imion — heurystyka blokady
# Lista intentionally ograniczona; rozszerzać na podstawie
# błędów FN na realnych dokumentach biura.
# ============================================================
# Polskie słowa funkcyjne — wykluczone z dopasowania wzorca imię+nazwisko
_PL_STOPWORDS: set[str] = {
    "czy", "jak", "gdzie", "kiedy", "kto", "co", "ile", "który", "która", "które",
    "pan", "pani", "przez", "przy", "nad", "pod", "bez", "dla", "przed", "po",
    "ale", "lecz", "oraz", "też", "już", "nie", "tak", "gdy", "więc", "zatem",
    "tego", "tej", "ten", "tam", "tutaj", "lub", "albo", "ani", "ani",
    "jego", "jej", "ich", "nas", "nam", "was", "wam", "ją", "go",
    "dnia", "roku", "spółka", "firma", "ustawa", "kodeks", "sąd", "urząd",
}

_POLISH_FIRST_NAMES: set[str] = {
    "adam", "adrian", "agnieszka", "aleksander", "aleksandra",
    "alicja", "andrzej", "anna", "barbara", "bartosz", "beata",
    "bogdan", "cezary", "dariusz", "dawid", "dominik", "dorota",
    "edyta", "elżbieta", "emil", "ewa", "filip", "grzegorz",
    "halina", "irena", "jacek", "jadwiga", "jakub", "jan", "joanna",
    "józef", "julia", "kamil", "karol", "katarzyna", "krystyna",
    "krzysztof", "łukasz", "marek", "maria", "mariusz", "marta",
    "michał", "mikołaj", "monika", "natalia", "paweł", "piotr",
    "przemysław", "rafał", "robert", "roman", "sebastian",
    "stanisław", "szymon", "tomasz", "urszula", "waldemar",
    "witold", "wojciech", "zbigniew", "zofia", "zuzanna",
    # zdrobnienia i formy potoczne
    "kasia", "ania", "asia", "basia", "magda", "ola", "ela", "iza",
    "arek", "bartek", "darek", "jarek", "krzysiek", "mirek",
    "piotrek", "sławek", "staszek", "tomek", "wiesiek", "zbyszek",
}

# Wzorzec: dwa słowa z wielkiej litery — fallback gdy SpaCy nie wykryje
_NAME_PATTERN = re.compile(
    r"\b([A-ZŁŚŹĆŃ][a-złśźćń]{2,})\s+([A-ZŁŚŹĆŃ][a-złśźćń]{2,})\b"
)

# ============================================================
# Mapowanie etykiet SpaCy → typy Triangulum
# None = pomijamy (geograficzne nie są PII per se)
# ============================================================
_SPACY_LABEL_MAP: dict[str, str | None] = {
    "persName": TOKEN_OSOBA,
    "PERSON":   TOKEN_OSOBA,
    "orgName":  TOKEN_FIRMA,
    "ORG":      TOKEN_FIRMA,
    "geogName": None,
    "GPE":      None,
    "LOC":      None,
    "DATE":     None,
    "TIME":     None,
    "MONEY":    None,  # kwoty obsługuje anonymizer warstwa 2
}


# ============================================================
# Wyjątki
# ============================================================

class NERBlockError(Exception):
    """
    Wykryto imię+nazwisko bez tokenu w mapie anonimizacji.
    Pipeline zablokowany — nie wysyłamy surowych danych osobowych.
    """
    def __init__(self, entities: list[str]):
        self.entities = entities
        super().__init__(
            f"Wykryto niezanonimizowane nazwy własne: {entities}. "
            f"Zanonimizuj encje przed wysłaniem."
        )


# ============================================================
# NERResult
# ============================================================

@dataclass
class NERResult:
    text:       str
    label:      str   # TOKEN_FIRMA | TOKEN_OSOBA
    confidence: float # heurystyczna, 0.0–1.0
    start:      int   # offset w oryginalnym tekście
    end:        int


# ============================================================
# Heurystyka confidence
# SpaCy pl_core_news_lg nie daje score per encja.
# Dłuższa encja = mniej dwuznaczna = wyższy confidence.
# ============================================================

def _confidence(text: str) -> float:
    words = len(text.split())
    if words >= 3:
        return 0.9
    if words == 2:
        return 0.8
    return 0.6  # 1 słowo — dużo false positives


# ============================================================
# Główna funkcja detekcji
# ============================================================

# ============================================================
# Scalanie sąsiadujących encji [NER-1]
# ============================================================

def _merge_adjacent_entities(
    results: list["NERResult"],
    text: str,
    max_gap: int = 4,
) -> list["NERResult"]:
    """
    Scala sąsiadujące encje tej samej kategorii gdy przerwa między nimi
    ≤ max_gap znaków i przerwa zawiera tylko spacje, kropki, przecinki, myślniki, cudzysłowy.

    Przykład: SpaCy zwraca ["Kwantowa Innowacja Technologiczna Sp.", "z o.o."]
    jako dwie encje FIRMA z przerwą " " — scalamy do jednej. [NER-1]

    Nie scala encji różnych kategorii (FIRMA + OSOBA).
    """
    if len(results) < 2:
        return results

    # Sortuj po pozycji startowej
    sorted_r = sorted(results, key=lambda r: r.start)
    merged: list[NERResult] = []
    i = 0

    while i < len(sorted_r):
        current = sorted_r[i]
        j = i + 1

        while j < len(sorted_r):
            nxt = sorted_r[j]
            if nxt.label != current.label:
                break
            gap = nxt.start - current.end
            if gap < 0 or gap > max_gap:
                break
            # Sprawdź czy przerwa to tylko spacje, kropki, przecinki, myślniki, cudzysłowy
            gap_text = text[current.end:nxt.start]
            if gap_text and not re.match(r'^[\s.,\-"]*$', gap_text):  # [BUG-3][BUG-D]
                break
            # Scalaj
            current = NERResult(
                text=text[current.start:nxt.end].strip(),
                label=current.label,
                confidence=min(current.confidence, nxt.confidence),
                start=current.start,
                end=nxt.end,
            )
            j += 1

        merged.append(current)
        i = j

    return merged



def detect_entities(text: str) -> list[NERResult]:
    """
    Wykrywa encje PERSON i ORG w tekście polskim.

    Nie rzuca wyjątków przy błędach SpaCy — loguje i zwraca [].
    Blokada pipeline jest wywoływana osobno przez check_and_block().
    Deduplikuje encje — ta sama wartość pojawia się raz nawet gdy
    wielokrotnie w tekście.
    """
    if not text or not text.strip():
        return []

    try:
        nlp = _get_nlp()
        doc = nlp(text)
    except RuntimeError:
        raise  # błąd instalacji — propaguj
    except Exception as e:
        logger.error(f"spacy_ner: błąd SpaCy: {e}")
        return []

    results: list[NERResult] = []
    seen: set[tuple[str, str]] = set()

    for ent in doc.ents:
        mapped = _SPACY_LABEL_MAP.get(ent.label_)
        if mapped is None:
            continue

        entity_text = ent.text.strip()

        # [FIX-NER-ML-2] PERSON nie może obejmować wielu linii.
        # SpaCy błędnie scala "Paweł Pietraszko\nAnny Jagiellonki"
        # (imię + linia adresowa z PDFa) jako jedną encję PERSON.
        # Skutek: replace() trafia tylko przy separatorze \n — nie trafia
        # gdy to przecinek lub samodzielne wystąpienie w innym zdaniu.
        # Fix: bierzemy tylko pierwszą linię encji PERSON.
        # FIRMA pomijamy — nazwy firm mogą legalnie zajmować wiele linii.
        if mapped == TOKEN_OSOBA and ("\n" in entity_text or "\r" in entity_text):
            entity_text = re.split(r"[\n\r]+", entity_text)[0].strip()
            if not entity_text:
                continue

        key = (entity_text.lower(), mapped)
        if key in seen:
            continue
        seen.add(key)

        conf = _confidence(entity_text)
        results.append(NERResult(
            text=entity_text,
            label=mapped,
            confidence=conf,
            start=ent.start_char,
            end=ent.end_char,
        ))
        logger.debug(f"spacy_ner: [{mapped}] '{entity_text}' conf={conf:.1f}")

    results = _merge_adjacent_entities(results, text)  # [NER-1]
    return results


# ============================================================
# Blokada pipeline
# ============================================================

def check_and_block(
    text: str,
    ner_results: list[NERResult],
    known_entities: set[str],
) -> None:
    """
    Rzuca NERBlockError jeśli tekst zawiera wzorzec imię+nazwisko
    który nie jest zanonimizowany (brak w known_entities).

    known_entities: zbiór oryginalnych wartości znanych AnonymizerMap,
                    np. {"Jan Kowalski", "ABC Sp. z o.o."}
                    Przekazywać jako anon_map.data["entities"].keys()
                    lub dedykowaną metodę get_entity_names().

    Dwie ścieżki detekcji:
      1. Encje SpaCy OSOBA o confidence >= 0.8 (2+ słowa)
         gdzie pierwsze słowo jest w słowniku imion
      2. Regex _NAME_PATTERN jako fallback (łapie co SpaCy pominął)

    Ścieżka 2 generuje więcej false positives — akceptowalne,
    bo fail-closed jest priorytetem nad UX.
    """
    known_lower = {v.lower() for v in known_entities}
    blocked: list[str] = []

    # Ścieżka 1: SpaCy OSOBA
    for ner in ner_results:
        if ner.label != TOKEN_OSOBA:
            continue
        if ner.confidence < 0.8:
            continue
        if ner.text.lower() in known_lower:
            continue
        words = ner.text.split()
        if len(words) >= 2 and words[0].lower() in _POLISH_FIRST_NAMES:
            blocked.append(ner.text)
            logger.warning("spacy_ner: blokada (NER) — [len=%d]", len(ner.text))

    # Ścieżka 2: szukamy znanych imion w tekście, potem sprawdzamy czy po nich
    # następuje słowo z wielkiej litery (możliwe nazwisko)
    # Unikamy problemu nakładających się dopasowań regex
    _cap_word = re.compile(r"\b([A-ZŁŚŹĆŃ][a-złśźćń]{2,})\b")
    # Zbierz wszystkie słowa z wielkiej litery z ich pozycjami
    cap_words = [(m.start(), m.end(), m.group(1)) for m in _cap_word.finditer(text)]

    for i, (start, end, word) in enumerate(cap_words):
        first_lower = word.lower()
        if first_lower not in _POLISH_FIRST_NAMES:
            continue
        # Szukaj kolejnego słowa z wielkiej litery bezpośrednio po
        if i + 1 >= len(cap_words):
            continue
        next_start, next_end, next_word = cap_words[i + 1]
        # Musi być bezpośrednio po (tylko spacje między nimi)
        gap = text[end:next_start].strip()
        if gap:
            continue  # coś pomiędzy — nie jest to imię+nazwisko
        second_lower = next_word.lower()
        if second_lower in _PL_STOPWORDS:
            continue
        candidate = f"{word} {next_word}"
        if candidate.lower() in known_lower:
            continue
        if candidate not in blocked:
            blocked.append(candidate)
            logger.warning("spacy_ner: blokada (regex) — [len=%d]", len(candidate))

    if blocked:
        raise NERBlockError(blocked)


# ============================================================
# Podsumowanie — do logów i UI
# ============================================================

def summarize(ner_results: list[NERResult]) -> dict:
    return {
        "firms":   [r.text for r in ner_results if r.label == TOKEN_FIRMA],
        "persons": [r.text for r in ner_results if r.label == TOKEN_OSOBA],
        "total":   len(ner_results),
    }