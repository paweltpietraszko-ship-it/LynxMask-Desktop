"""
ner_layer.py  v1.17
Detekcja encji NER (SpaCy) i budowanie mapy tokenów OSOBA/FIRMA.
Wydzielony z pseudominizer_api.py v1.18.

Historia zmian:
  v1.16 — [FIX-NER-COURTS] _COURT_PREFIX_RE — każda encja zaczynająca się od
           "sąd ", "naczelny sąd ", "wojewódzki sąd " lub "trybunał " jest
           filtrowana niezależnie od miasta (SpaCy widział "Sąd Rejonowy w
           Gdańsku" jako FIRMA, choć blocklist miał tylko generyczne formy).
  v1.15 — [BUG-ADJECTIVE-MULTIWORD] Filtr _ADJECTIVE_ENDINGS_RE stosowany tylko
           dla jednowyrazowych encji OSOBA. Poprzednio "Jana Kowalskiego" było
           filtrowane bo końcówka -skiego pasuje do przymiotnikowej, ale to
           dopełniacz osoby w zdaniu, nie przymiotnik. Wielowyrazowe encje OSOBA
           (imię+nazwisko w dowolnym przypadku) teraz nie są odfiltrowane.
  v1.14 — [BUG-NER-FP-GRANICE] Trzy nowe filtry redukujące 52 FP dla ORGANIZACJA/FIRMA:
           1. Nagłówki ALL-CAPS ≤2 słów bez sufiksu prawnego → pomiń jako FIRMA.
              SpaCy widzi "ZAKRES OBOWIĄZKÓW" → ORG, ale to nagłówek, nie firma.
           2. Czyste akronimy [A-Z]{2,6} bez cyfr/sufiksu → pomiń.
              ERP/CRM/IT jako samodzielna encja to skrót systemowy, nie firma.
           3. Przymiotnik jako jedyne słowo FIRMA — _ADJECTIVE_ENDINGS_RE teraz
              stosowany też dla FIRMA gdy encja to jedno słowo przymiotnikowe.
  v1.13 — [BUG-2] Encja SpaCy otoczona cudzysłowem wymusza typ FIRMA.
           "Wiśniewski i Wspólnicy" w cudzysłowie = nazwa handlowa, nie OSOBA.
           Wykrycie PRZED strip('"') — ner.start/end w oryginalnym tekście.
  v1.12 — [BUG-FIRMA-ZUS-MIX] _filter_institutions: encja FIRMA zawierająca
           fragment instytucji publicznej (ZUS, NFZ itp.) jest pomijana.
           Regex _INSTITUTION_IN_FIRMA_RE sprawdza całą treść encji.
           [BUG-OCR-DEDUP] Przed _person_stem w _process_ner aplikujemy
           normalize_ocr(entity_text) — "P4nina" i "Paulina" dają ten sam
           stem i trafiają do tego samego tokenu OSOBA. entity_text (wartość
           tokenu) pozostaje niezmieniona.
  v1.11 — [BUG-FIRMA-TRUNC] SpaCy zatrzymuje granicę encji przed sufiksem
           prawnym w cudzysłowie, np. "ALTEX" Sp → "ALTEX" Sp. z o.o.
           Naprawa: po zebraniu entity_text sprawdzamy czy kończy się na
           skróconym wskaźniku spółki ("Sp", "S.A" itp.) i czy zaraz za
           ner.end w oryginalnym tekście jest dopełnienie sufiksu (". z o.o."
           itp.). Jeśli tak — entity_text rozszerzany o dopełnienie
           i typ wymuszany na FIRMA.
  v1.10 — [BUG-1] Deduplikacja wieloczłonowych form fleksyjnych OSOBA.
           Poprzednio "Jana Kowalskiego" dostawało osobny token OSOBA_002
           mimo że "Jan Kowalski" był już OSOBA_001. Przyczyną był _ner_stem
           zwracający "jana kowal" != "jan kowal" — różne klucze w stem_to_token.
           BUG-5 (z v1.7) łapał tylko jednoczłonowe odmiany (" " not in entity_text).
           Naprawa: dodana funkcja _person_stem zwracająca tuple invariantny
           na fleksję: (words[0][:3], words[1][:3] lub "", words[-1][:4]).
           Nowy słownik person_stem_to_token w _process_ner — sprawdzany przed
           BUG-5 dla każdej wieloczłonowej encji OSOBA.
           Kolizje niemożliwe: różne osoby mają różne imię lub nazwisko
           co daje różny tuple.
  v1.9 — [AUD-03] _TOKEN_RE rozszerzony o INSTYTUCJA i EMAIL (linia 88).
          Tokeny INSTYTUCJA_NNN i EMAIL_NNN są teraz filtrowane przez
          _filter_institutions — nie trafią do SpaCy jako kandydaci encji.
          Spójność z TOKEN_RE w pipeline.py i pseudominizer_api.py.
  v1.8 — [FIX-SYNTAX-1] Docstring linia 14: \\s i \\t zamienione na \\\\s i \\\\t.
          Python 3.12+ SyntaxWarning, 3.14+ SyntaxError dla invalid escape
          sequences w zwykłych stringach (docstringach). Dotyczyło wyłącznie
          tekstu opisowego — regexes w kodzie używały już poprawnych raw stringów.
          Linie dotknięte: 14, 16.
  v1.7 — [BUG-5] Deduplikacja jednoczłonowych odmian nazwisk. Jednoczłonowa
          encja OSOBA (np. "Wiśniewska") sprawdzana jako potencjalny ostatni
          wyraz istniejącej wieloczłonowej encji OSOBA ("Anna Wiśniewska").
          Jeśli pasuje — traktowana jako wariant, nie nowy token.
          Bezpieczne: ner_sorted przetwarza dłuższe encje pierwsze — token
          wieloczłonowy zawsze istnieje przed jednoczłonowym.
          Linia dotknięta: ~213.
          [BUG-7] Normalizacja whitespace — re.sub(r"\\s+", " ") zaraz po
          ner.text.strip(). Tabulator i wielokrotne spacje w tekstach TSV/CSV
          tworzyły tokeny z \\t wewnątrz wartości (np. "Jan\\tKowalski").
          re jest już importowany.
          Linia dotknięta: ~163.
  v1.6 — [BUG-H] Strip interpunkcji końcowej z entity_text.
          SpaCy zwracał "Stanisław Wiśniewski," z przecinkiem — inny stem
          niż "Stanisław Wiśniewski" bez przecinka, deduplikacja nie zachodziła,
          ta sama osoba dostawała dwa tokeny OSOBA.
          Zmiana: entity_text.rstrip(",.;:!?()") po strip('"').
          rstrip działa tylko na końcu — środek i początek nazwy nienaruszony.
          Linia dotknięta: ~166.
  v1.5 — [BUG-G] Strip cudzysłowu prostego `"` z entity_text zaraz po
          ner.text.strip(). Pipeline normalizuje „ na " przed NER — SpaCy
          zwracał encję zaczynającą się od " który filtr typograficzny (linia ~160)
          nie łapał (sprawdza tylko \u201e \u201c \u2018 \u2019).
          Encja z " na początku dostawała osobny token zamiast być scalona.
          strip() działa tylko na krawędziach — środek nazwy nienaruszony.
          Linia dotknięta: ~140.
          [BUG-A weryfikacja] Potwierdzono że _process_ner() nie dodaje do
          reverse_map encji odrzuconych przez filtry wewnętrzne — każdy filtr
          w pętli trafia na continue przed przypisaniem do reverse_map. Śmieci
          FIRMA nie wchodzą do mapy. Usunięcie FIX-NER-JUNK-CLEANUP z pipeline.py
          v1.10 było słuszne.
          [BUG-B analiza] Sygnatura process_ner() NIE zmieniona. Zmiana
          tuple[dict,dict] na tuple[dict,dict,list] złamałaby każde wywołanie
          z unpackingiem w pipeline.py. Opis wymaganej zmiany: patrz raport.
  v1.4 — [BUG-B] process_ner() re-raisuje NERBlockError zamiast ją połykać
          w ogólnym except Exception. Wcześniej blokada bezpieczeństwa była
          cicho połykana — pipeline.py nigdy jej nie widział.
          Przeniesienie check_and_block() do _process_ner() odłożone —
          wymaga analizy pipeline.py v1.7 (patrz raport 06.06.2026).
          Linia dotknięta: ~117-120 (process_ner).
          [BUG-F] Usunięta gałąź `s in entity_lower` z warunku sufiksu prawnego
          — substring match powodował wymuszanie typu FIRMA na encjach nie będących
          firmami (np. "transport", "aspiracja"). Zostało samo endswith.
          Linia dotknięta: ~147.
  v1.3 — [FIX-NER-ADDR-PREFIX] _filter_institutions pomija encje zaczynające
          się od prefiksu adresowego (ul./al./os./gen. itp.) — SpaCy błędnie
          klasyfikował "os. Bolesława Chrobrego", "ul. gen. Andersa" jako OSOBA.
          [FIX-NER-INTERNAL-ORG] _filter_institutions pomija wewnętrzne działy
          organizacyjne (Dział X, Wydział X) jako FIRMA.
  v1.2 — dane (blocklista, sufiksy prawne) przeniesione do ner_blocklist.py.
          [FIX-QUOTES] Cudzysłów prosty " usunięty z filtru startswith.
          [FIX-STEM] _ner_stem strip znaków niealfanumerycznych przed stemowaniem.
          [FIX-LEGAL-SUFFIX] Sufiks prawny w encji wymusza typ FIRMA.
  v1.1 — [FIX-NER-FP] Rozszerzona _NER_BLOCKLIST, _ORDER_CODE_RE.
  v1.0 — wydzielenie z pseudominizer_api.py v1.18.

API publiczne:
  process_ner(text, spacy_ner_mod) -> tuple[dict, dict]
    reverse_map:  {OSOBA_001: "Jan Kowalski", ...}
    all_variants: {"Jan Kowalski": "OSOBA_001", "Jana Kowalskiego": "OSOBA_001", ...}
  NERBlockError propaguje się przez process_ner() do pipeline.py — nie jest łapana.

Zależności: re, logging (stdlib) + spacy_ner (zewnętrzny) + ner_blocklist (lokalne).
"""

import re
import logging

from ner_blocklist import (
    _LEGAL_SUFFIXES_LOWER,
    _NER_BLOCKLIST,
    _NER_BLOCKLIST_PREFIXES,
)

logger = logging.getLogger("pseudominizer.ner_layer")

_TOKEN_RE      = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b")
_ORDER_CODE_RE = re.compile(r"^[A-Z]{2,6}_\d{4,}$")

# [BUG-NER-FP-GRANICE] Czyste akronimy bez cyfr/sufiksu prawnego — skróty systemowe
# (ERP, CRM, IT, HR, BHP) błędnie klasyfikowane przez SpaCy jako FIRMA/ORG.
_PURE_ACRONYM_RE = re.compile(r"^[A-Z]{2,6}$")

# Sufiks prawny — jeśli obecny, akronim jest legalną nazwą firmy (ABC S.A.)
_LEGAL_SUFFIX_RE = re.compile(
    r'\b(?:S\.A\.?|Sp\.?\s*z\s*o\.o\.?|Sp\.?\s*k\.?|s\.c\.?|p\.s\.a\.?|Ltd\.?|LLC|GmbH|s\.k\.a\.?)\b',
    re.IGNORECASE,
)

# [FIX-NER-ADDR-PREFIX] Encje zaczynające się od prefiksu adresowego
# są adresami, nie osobami — pomiń.
_ADDR_PREFIX_RE = re.compile(
    r"^(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar|gen|dr|inż|prof)"
    r"\.?\s+",
    re.IGNORECASE,
)

# [BUG-NER-FP] Filtr przymiotników dla encji OSOBA — port z NameEngine.kt linie 287-362.
# SpaCy klasyfikuje polskie przymiotniki jako OSOBA (KONTROLNA, Encje itp.).
# Stosowany tylko dla OSOBA — firmy mogą mieć przymiotniki w nazwie legalnie.
_ADJECTIVE_ENDINGS_RE = re.compile(
    r'(?:owego|owej|owym|owych|iego|iej|iem|owy|owa|owe|ową'
    r'|czny|czna|czne|cznego|cznej|cznym|cznych'
    r'|wny|wna|wne|wnego|wnej|wnym|wnych'
    r'|lny|lna|lne|lnego|lnej|lnym|lnych)\b',
    re.IGNORECASE | re.UNICODE,
)

# [FIX-NER-COURTS] Sądy powszechne i administracyjne — instytucje publiczne,
# nie prywatne firmy. Łapie wszystkie formy fleksyjne: "Sąd/Sądu/Sądowi Rejonowy...",
# "Trybunał/Trybunału Konstytucyjny...", "Naczelny/Naczelnego Sąd/Sądu..." itp.
# v1.16 łapało tylko mianownik "sąd "; v1.17 dodaje dopełniacz/celownik.
_COURT_PREFIX_RE = re.compile(
    r"^(?:"
    r"sąd(?:u|owi)?\s"
    r"|naczelny(?:ego)?\s+sąd(?:u|owi)?\s"
    r"|wojewódzki(?:ego)?\s+sąd(?:u|owi)?\s"
    r"|trybunał(?:u|owi)?\s"
    r")",
    re.IGNORECASE | re.UNICODE,
)

# [FIX-NER-INTERNAL-ORG] Wewnętrzne działy i jednostki organizacyjne
# nie są podmiotami zewnętrznymi — pomiń jako FIRMA.
_INTERNAL_ORG_RE = re.compile(
    r"^(?:dział|oddział|wydział|departament|biuro|sekcja|referat|zespół|jednostka)"
    r"\s+",
    re.IGNORECASE,
)

# [BUG-FIRMA-ZUS-MIX] Encja FIRMA zawierająca fragment instytucji publicznej
# (np. "Sp. z o.o. ZUS-Warszawa") — pomiń, to nie jest prywatna firma.
# Ryzyko FP ("ZUS-IT Sp. z o.o.") minimalne — takich firm w Polsce nie ma.
_INSTITUTION_IN_FIRMA_RE = re.compile(
    r'\b(?:ZUS|NFZ|KRUS|PIP|UODO|GUS|NIK|RPO|ARiMR|KNF|UOKiK)\b',
    re.IGNORECASE,
)

# [BUG-FIRMA-TRUNC] SpaCy obcina encję przed sufiksem prawnym.
# Wzorzec dopasowuje dopełnienie sufiksu zaraz za końcem encji w tekście.
# np. entity="ALTEX Sp", text[ner.end:]=" z o.o." → extend.
_TRUNC_ENDINGS: tuple = ("Sp", "S.A", "Sp. k", "s.c", "p.s.a", "s.k.a")
_SUFFIX_COMPLETION_RE = re.compile(
    r'^[\s.]*(?:z\s+o\.o\.?|o\.o\.|S\.A\.?|k\.\s*a\.?|z\.o\.o\.?)',
    re.IGNORECASE,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _filter_institutions(ner_results: list) -> list:
    """Usuwa instytucje publiczne, słowa pospolite i tokeny PSE z wyników NER."""
    out = []
    for ner in ner_results:
        entity_text = ner.text.strip()
        name_lower  = entity_text.lower()

        if _TOKEN_RE.search(entity_text):
            logger.debug("[FILTER] pominięto token: '%s'", entity_text)
            continue
        if _ORDER_CODE_RE.match(entity_text.strip()):
            logger.debug("[FILTER] pominięto kod zamówienia: '%s'", entity_text)
            continue
        if name_lower in _NER_BLOCKLIST:
            logger.debug("[FILTER] pominięto (exact): '%s'", entity_text)
            continue
        if name_lower[:8] in _NER_BLOCKLIST_PREFIXES:
            logger.debug("[FILTER] pominięto (prefix): '%s'", entity_text)
            continue
        # [FIX-NER-ADDR-PREFIX] Pomiń encje będące adresami (ul., os., gen. itp.)
        if _ADDR_PREFIX_RE.match(entity_text):
            logger.debug("[FILTER] pominięto adres jako encję: '%s'", entity_text[:40])
            continue
        # [FIX-NER-COURTS] Pomiń sądy i trybunały — instytucje publiczne, nie firmy
        if _COURT_PREFIX_RE.match(entity_text):
            logger.debug("[FILTER] pominięto sąd/trybunał: '%s'", entity_text[:60])
            continue
        # [FIX-NER-INTERNAL-ORG] Pomiń wewnętrzne działy jako FIRMA
        if ner.label == "FIRMA" and _INTERNAL_ORG_RE.match(entity_text):
            logger.debug("[FILTER] pominięto dział wewnętrzny: '%s'", entity_text[:40])
            continue
        # [BUG-FIRMA-ZUS-MIX] Pomiń encję FIRMA zawierającą fragment instytucji publicznej
        if ner.label == "FIRMA" and _INSTITUTION_IN_FIRMA_RE.search(entity_text):
            logger.debug("[FILTER] pominięto FIRMA z instytucją: '%s'", entity_text[:60])
            continue
        # [BUG-NER-FP] Pomiń jednowyrazowe encje OSOBA kończące się na końcówki przymiotnikowe.
        # TYLKO jednowyrazowe — "Jana Kowalskiego" to dopełniacz osoby, nie przymiotnik.
        # Wielowyrazowe: "Jan Kowalski", "Jana Kowalskiego" → zawsze OSOBA (fleksja).
        if (ner.label == "OSOBA"
                and " " not in entity_text.strip()
                and _ADJECTIVE_ENDINGS_RE.search(entity_text)):
            logger.debug("[FILTER] pominięto przymiotnik jako OSOBA: '%s'", entity_text[:40])
            continue

        # [BUG-NER-FP-GRANICE] Jednoslowna FIRMA będąca przymiotnikiem → pomiń.
        # Wieloslowna nazwa "Firma Handlowa X" jest legalna — filtrujemy tylko jedno słowo.
        if (ner.label == "FIRMA" and " " not in entity_text.strip()
                and _ADJECTIVE_ENDINGS_RE.search(entity_text)
                and not _LEGAL_SUFFIX_RE.search(entity_text)):
            logger.debug("[FILTER] pominięto jednosłowny przymiotnik jako FIRMA: '%s'", entity_text[:40])
            continue

        # [BUG-NER-FP-GRANICE] Czyste akronimy bez sufiksu prawnego → pomiń.
        # "ERP", "CRM", "IT" to skróty systemowe — nie firmy.
        if (ner.label in ("FIRMA", "ORGANIZACJA") and _PURE_ACRONYM_RE.match(entity_text.strip())
                and not _LEGAL_SUFFIX_RE.search(entity_text)):
            logger.debug("[FILTER] pominięto czysty akronim jako FIRMA/ORG: '%s'", entity_text)
            continue

        # [BUG-NER-FP-GRANICE] Nagłówki ALL-CAPS (≤2 słowa, brak sufiksu) → pomiń.
        # "ZAKRES OBOWIĄZKÓW", "DANE OSOBOWE" to nagłówki dokumentów, nie firmy.
        words = entity_text.split()
        if (ner.label in ("FIRMA", "ORGANIZACJA")
                and len(words) <= 2
                and entity_text == entity_text.upper()
                and not _LEGAL_SUFFIX_RE.search(entity_text)
                and not any(c.isdigit() for c in entity_text)):
            logger.debug("[FILTER] pominięto nagłówek ALL-CAPS jako FIRMA/ORG: '%s'", entity_text[:40])
            continue

        out.append(ner)
    return out


def _ner_stem(text: str) -> str:
    """Klucz deduplikacji — pierwsze 5 znaków każdego słowa, lowercase.
    Strip znaków niealfanumerycznych — & i . w nazwie firmy nie mogą psuć klucza.
    """
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(w[:5] for w in clean.split() if len(w) >= 2)


def _person_stem(text: str) -> tuple | None:
    """
    Klucz deduplikacji dla wieloczłonowych odmian fleksyjnych encji OSOBA. [BUG-1]

    Zwraca (stem_słowa_1[:3], stem_słowa_2[:3], stem_ostatniego[:4]) lub None
    gdy encja jest jednoczłonowa (obsługiwana przez BUG-5).

    Logika: "Jan Kowalski" i "Jana Kowalskiego" mają różne _ner_stem
    ("jan kowal" vs "jana kowal"), więc stem_to_token nie deduplikuje ich.
    _person_stem wyciąga invariantne prefiksy: ('jan', '', 'kowa') dla obu.

    Dla trójczłonowych ("Jan Andrzej Kowalski" vs "Jana Andrzeja Kowalskiego"):
    ('jan', 'and', 'kowa') — pierwsze dwa słowa + ostatnie.

    Kolizja niemożliwa między różnymi osobami: różne imię lub różne nazwisko
    dają różny tuple. Stosowane TYLKO dla typ == "OSOBA" i len(words) >= 2.
    """
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    words = [w for w in words if len(w) >= 2]
    if len(words) < 2:
        return None
    first  = words[0][:3]
    second = words[1][:3] if len(words) > 2 else ""
    last   = words[-1][:4]
    return (first, second, last)


# ── API publiczne ─────────────────────────────────────────────────────────────

def process_ner(text: str, spacy_ner_mod) -> tuple[dict, dict]:
    """Wykrywa encje OSOBA i FIRMA przez SpaCy. NIE modyfikuje tekstu.
    Przy błędzie zwraca ({}, {}) — pipeline degraduje do warstw regex.
    NERBlockError NIE jest łapana — propaguje się do pipeline.py. [BUG-B]
    """
    try:
        return _process_ner(text, spacy_ner_mod)
    except spacy_ner_mod.NERBlockError:  # [BUG-B] re-raise — NERBlockError dostępna przez moduł-argument
        raise
    except Exception as e:
        logger.error("[NER] Nieoczekiwany błąd: %s", e)
        return {}, {}


# ── Implementacja ─────────────────────────────────────────────────────────────

def _process_ner(text: str, spacy_ner_mod) -> tuple[dict, dict]:
    ner_results = spacy_ner_mod.detect_entities(text)
    ner_results = _filter_institutions(ner_results)

    reverse_map:          dict[str, str] = {}
    all_variants:         dict[str, str] = {}
    counters:             dict[str, int] = {"OSOBA": 0, "FIRMA": 0}
    stem_to_token:        dict[str, str] = {}
    person_stem_to_token: dict[tuple, str] = {}   # [BUG-1] klucz fleksyjny dla OSOBA

    ner_sorted = sorted(ner_results, key=lambda r: -(r.end - r.start))

    for ner in ner_sorted:
        entity_text  = ner.text.strip()
        # [BUG-7] Normalizacja whitespace — tabulator i wielokrotne spacje
        # w tekście TSV/CSV tworzą tokeny z \t wewnątrz wartości.
        entity_text  = re.sub(r"\s+", " ", entity_text).strip()
        if not entity_text:
            continue
        # [BUG-G] Pipeline normalizuje „ na " przed NER. SpaCy może zwrócić
        # encję zaczynającą się od " — filtr typograficzny poniżej nie łapie
        # cudzysłowu prostego (sprawdza tylko \u201e \u201c \u2018 \u2019).
        # strip() działa tylko na krawędziach, środek nazwy nienaruszony.
        # [BUG-2] Wykryj cudzysłów wokół encji PRZED stripem — firma w cudzysłowie
        # ("Wiśniewski i Wspólnicy") powinna być FIRMA, nie OSOBA.
        _orig_span = text[ner.start:ner.end]
        _quoted = (
            _orig_span.startswith(('"', '„', '“'))
            or _orig_span.endswith(('"', '”', '“'))
        )
        entity_text  = entity_text.strip('"')
        if not entity_text:
            continue
        # [BUG-H] SpaCy może zwrócić encję z interpunkcją na końcu
        # ("Stanisław Wiśniewski,") — przecinek zmienia stem i tworzy
        # duplikat tokenu dla tej samej osoby. Strip interpunkcji końcowej.
        entity_text  = entity_text.rstrip(",.;:!?()")
        if not entity_text:
            continue
        # [BUG-FIRMA-TRUNC] Rozszerz encję o obcięty sufiks prawny
        # np. "ALTEX" Sp → "ALTEX" Sp. z o.o.
        if entity_text.endswith(_TRUNC_ENDINGS):
            after = text[ner.end:]
            m_suf = _SUFFIX_COMPLETION_RE.match(after)
            if m_suf:
                entity_text = entity_text + m_suf.group(0).rstrip()
        typ          = ner.label
        entity_lower = entity_text.lower()

        # [BUG-2] Cudzysłów wokół encji → nazwa handlowa → wymuś FIRMA
        if _quoted and typ == "OSOBA":
            typ = "FIRMA"

        # [FIX-LEGAL-SUFFIX] Sufiks prawny wymusza FIRMA niezależnie od SpaCy
        # [BUG-F] Usunięta gałąź `s in entity_lower` — substring match powodował
        # fałszywe FIRMA dla encji zawierających "sp", "sa" itp. w środku słowa.
        if any(entity_lower.endswith(s)
               for s in _LEGAL_SUFFIXES_LOWER):
            typ = "FIRMA"

        if typ not in ("OSOBA", "FIRMA"):
            continue

        clean = entity_text.replace(".", "").replace(",", "").strip()
        if len(clean) <= 2:
            continue

        # Filtruj cudzysłowy typograficzne — " prosty celowo pominięty,
        # bo pipeline.py normalizuje typograficzne na " przed NER.
        if entity_text.startswith(("\u201e", "\u201c", "\u2018", "\u2019")):
            continue

        stem = _ner_stem(entity_text)

        if stem in stem_to_token:
            token = stem_to_token[stem]
            all_variants[entity_text] = token
            if "\n" in entity_text or "\r" in entity_text:
                normalized = re.sub(r"\s+", " ", entity_text).strip()
                if normalized:
                    all_variants[normalized] = token
            logger.debug("[NER] wariant '%s' -> %s", entity_text, token)
            continue

        # [BUG-1] Wieloczłonowa odmiana fleksyjna OSOBA — "Jana Kowalskiego"
        # ma inny _ner_stem niż "Jan Kowalski" ("jana kowal" vs "jan kowal"),
        # więc stem_to_token jej nie deduplikuje. Sprawdź _person_stem który
        # jest invariantny na odmiany: ('jan', '', 'kowa') dla obu form.
        # Stosowane tylko dla OSOBA wieloczłonowej — jednoczłonowe obsługuje BUG-5.
        # [BUG-OCR-DEDUP] Przed _person_stem normalizuj OCR-leet żeby "P4nina"
        # dało ten sam stem co "Paulina". Normalizacja tylko do celów kluczowania —
        # entity_text (wartość tokenu) pozostaje oryginalna (lub już znorm. przez pipeline).
        if typ == "OSOBA" and " " in entity_text:
            try:
                from layers.ocr_normalizer import normalize_ocr as _norm_ocr
                _entity_for_stem = _norm_ocr(entity_text)
            except Exception:
                _entity_for_stem = entity_text
            pstem = _person_stem(_entity_for_stem)
            if pstem is not None and pstem in person_stem_to_token:
                existing_token = person_stem_to_token[pstem]
                all_variants[entity_text] = existing_token
                logger.debug("[NER] odmiana wieloczłonowa '%s' -> %s", entity_text, existing_token)
                continue

        # [BUG-5] Jednoczłonowa encja OSOBA może być odmianą nazwiska
        # istniejącej wieloczłonowej encji (np. "Wiśniewska" → "Anna Wiśniewska").
        # Sprawdź czy entity_text jest ostatnim wyrazem istniejącego tokenu OSOBA.
        # ner_sorted przetwarza dłuższe encje pierwsze — wieloczłonowa encja
        # już ma token gdy jednoczłonowa jest przetwarzana.
        if typ == "OSOBA" and " " not in entity_text:
            entity_lower_check = entity_text.lower()
            matched_token = next(
                (tok for tok, val in reverse_map.items()
                 if tok.startswith("OSOBA_")
                 and val.lower().endswith(" " + entity_lower_check)),
                None,
            )
            if matched_token:
                all_variants[entity_text] = matched_token
                logger.debug("[NER] odmiana '%s' -> %s", entity_text, matched_token)
                continue

        counters[typ] += 1
        token = f"{typ}_{counters[typ]:03d}"
        reverse_map[token]        = entity_text
        all_variants[entity_text] = token
        stem_to_token[stem]       = token

        # [BUG-1] Zarejestruj _person_stem dla encji OSOBA wieloczłonowej
        # żeby kolejne formy fleksyjne ("Jana Kowalskiego") trafiały na ten sam token.
        if typ == "OSOBA" and " " in entity_text:
            pstem = _person_stem(entity_text)
            if pstem is not None:
                person_stem_to_token[pstem] = token

        if "\n" in entity_text or "\r" in entity_text:
            normalized = re.sub(r"\s+", " ", entity_text).strip()
            if normalized:
                all_variants[normalized] = token

        logger.debug("[NER] nowa encja '%s' -> %s", entity_text, token)

    return reverse_map, all_variants
