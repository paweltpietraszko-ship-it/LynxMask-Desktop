r"""
pipeline.py  v1.23
Orchestrator pseudonimizacji â€” wywoĹ‚uje warstwy w ustalonej kolejnoĹ›ci.
Wydzielony z pseudominizer_api.py v1.18.

Historia zmian:
  v1.21 â€” [FEATURE-USE-NEW-PIPELINE] USE_NEW_PIPELINE=False â€” przeĹ‚Ä…cznik testowy nowego
           pipeline opartego na TokenAllocator. Gdy True: _run_pipeline() wywoĹ‚uje
           run_pipeline_new() i zwraca wynik jako PipelineResult. Stary kod nienaruszony.
           anonymize() wywoĹ‚ane ze skip_guard=True â€” guard dziaĹ‚a na poziomie API (AUD-01).
  v1.20 â€” [FIX-TOKEN-COUNTER-COLLISION] Przekazuje reverse_map jako existing_reverse_map
           do anonymize(). Anonymizer inicjalizuje liczniki powyĹĽej tokenĂłw pipeline'u,
           eliminujÄ…c kolizje NUMER_NNN (dowĂłd/sygnatura vs PESEL/telefon).
  v1.19 â€” [FIX-ADMIN-SIG] Dodano _ADMIN_SIG_RE dla sygnatur administracyjnych
           formatu XX.DDDDDD.RRRR (np. PT.046166.2021, SA.092213.2021).
           Warstwa 2d po warstwie 2c (_CASE_SIG_RE).
  v1.18 â€” [FIX-CASE-SIG-KOMORNICZA] _CASE_SIG_RE rozszerzony o prefiksy komornicze
           (Km, Kmp, Ko, Kms) i sÄ…dowe jednoliterowe (GC, C, K, W).
           Poprzedni wzorzec obsĹ‚ugiwaĹ‚ tylko cyfry rzymskie â€” "Km 10478/2024"
           trafiaĹ‚o bĹ‚Ä™dnie do ADRES_NNN przez _ADDR_RE.
  v1.17 â€” [BUG-PIPELINE-GUARD] Zbieranie pipeline_tokens przed anonymize() i
           przekazanie jako known_tokens â€” guard injection w anonymize() nie rzuca
           na NUMER_001/ADRES_001 wstawione przez warstwy 2a/3 wĹ‚asnego pipeline.
           Linie dotkniÄ™te: warstwa 5 (~359).
  v1.16 â€” [FIX-CASE-SIG-MULTICHAR] _CASE_SIG_RE: [A-Z][a-z]? â†’ [A-Z][A-Za-z]{0,4}
           Poprzedni wzorzec nie Ĺ‚apaĹ‚ wieloliterowych czĹ‚onĂłw jak ACa, Ca, GC, Ns.
           Linia dotkniÄ™ta: _CASE_SIG_RE (~154).
  v1.15 â€” [BUG-PERF-1] _ADDR_PREFIX_RE i _BARE_SUFFIX_RE przeniesione na poziom
           moduĹ‚u (przed klasÄ… AppState). Poprzednio kompilowane wewnÄ…trz
           _run_pipeline() przy kaĹĽdym wywoĹ‚aniu â€” koszt re.compile() na kaĹĽde
           ĹĽÄ…danie. Zmiana czysto kosmetyczna, zachowanie identyczne.
  v1.14 â€” [BUG-6] _TOKEN_RE rozszerzony o EMAIL (linia 103).
           Email tokenizowany jako EMAIL_NNN â€” Guard i pipeline rozpoznajÄ… token.
  v1.14 â€” REVERT-BUG-1: usunieto opcjonalne bloki lokalizacji
           z _INSTITUTION_RE â€” NER fine-tuning zalatiwi to lepiej.
  v1.13 â€” BUG-1: opcjonalna lokalizacja w _INSTITUTION_RE (Opcja A).
           BUG-2: dopeĹ‚niacz dla kaĹĽdej instytucji w _INSTITUTION_RE.
           BUG-3: KNF, RPO, TK, PIP, PPK dodane do _INSTITUTION_RE.
           BUG-4: skrĂłty PPK/KNF/RPO/TK/PIP/GUS/NIK/UOKiK w _INSTITUTION_RE.
           Linie dotkniÄ™te: ~110-145 (_INSTITUTION_RE).
  v1.12 â€” FIX-T24: dodano Wydzial sadowy do _INSTITUTION_RE â€”
           pattern Wydzial + cyfra rzymska/arabska + nazwa.
           T24 test_pipeline.py: Wydzial I Cywilny zakryty.
  v1.11 â€” BUG-B2: check_and_block dostaje wĹ‚aĹ›ciwy list[NERResult] przez
           osobne detect_entities() przed process_ner(). ĹšcieĹĽka 1 SpaCy
           aktywna. Koszt: podwĂłjny czas NER â€” akceptowalny.
  v1.10 â€” SYNTAX-WARN: \s -> \\s w komentarzu naglowka (linia 7).
           BUG-A: usuniÄ™ty blok FIX-NER-JUNK-CLEANUP â€” ner_layer.py v1.4
           filtruje smieci u zrodla (len(clean)<=2), blok byl zbedny.
           BUG-B-C: komentarz check_and_block zaktualizowany â€” Opcja C,
           known_entities z anon_map przekazywane poprawnie.
  v1.9 â€” FIX-INSTITUTION-NEWLINE: _INSTITUTION_RE uzywal \\s w grupach
          lokalizacji co powodowalo wciaganie kolejnych linii (Wydzial,
          ul.) do tokenu INSTYTUCJA. Zamieniono \\s na [ \\t] w grupach
          lokalizacji â€” regex zatrzymuje sie na koncu linii.
  v1.8 â€” BUG-C: ochrona kontraktu typow ner_variants linia ~329 â€”
          if not isinstance(ner_variants, dict): loguj i podstaw {}.
  v1.7 â€” FIX-NER-JUNK-CLEANUP: po Warstwie 6 usuwane sa z reverse_map
          tokeny OSOBA/FIRMA ktore nie przeszly zadnego filtru â€” smieci
          NER (np. ''Sp.'') nie trafiaja do Guarda jako plain text sesji.
          Linia dotkniÄ™ta: ~363 (nowy blok po petli FIX-NER-GLOBAL).
  v1.6 â€” BUG-GUARD-FP-FIX: filtr known_plain uzywa re.sub do usuniecia
          cudzysĹ‚owow i whitespace przed sprawdzeniem dlugosci â€” '" Sp.'
          ma 3 znaki po oczyszczeniu i odpada. Poprzedni warunek strip()
          nie usuwal cudzysĹ‚owu i wartosc przechodzila jako 5 znakow.
  v1.5 â€” BUG-GUARD-FP: filtrowanie known_plain przed guard_output_with_map â€”
          usuniÄ™cie wartoĹ›ci krĂłtszych niĹĽ 5 znakĂłw i sufiksĂłw prawnych
          (_FIRMA_SUFFIXES) eliminuje faĹ‚szywe alarmy Guarda na Ĺ›mieciach NER.
          BUG-5-TYPE: check_and_block dostaje ner_results=[] zamiast sĹ‚ownika
          (process_ner() nie zwraca NERResult); aktywna tylko Ĺ›cieĹĽka 2 (regex).
          Linie dotkniÄ™te: ~225 (Warstwa 1), ~362 (Warstwa 7).
          Dlaczego bezpieczne: nie zmieniono kolejnoĹ›ci warstw; filtr known_plain
          jest addytywny â€” Guard nadal widzi wszystkie wartoĹ›ci >= 5 znakĂłw
          i spoza listy sufiksĂłw prawnych.
  v1.4 â€” BUG-1: zmiana guard_output na guard_output_with_map (linia 337);
          BUG-5: wywoĹ‚anie check_and_block po warstwie NER (linia ~210).
          Linie dotkniÄ™te: ~49 (import), ~210 (Warstwa 1), 337 (Warstwa 7).
          Dlaczego bezpieczne: nie zmieniono kolejnoĹ›ci warstw, nie zmieniono
          logiki NER, guard_output_with_map jest addytywny â€” rozszerza nie
          zastÄ™puje guard_output.
  v1.3 â€” [FIX-NER-TOKEN-IN-TOKEN] FIX-NER-GLOBAL pomija warianty zawierajÄ…ce
          juĹĽ token (np. ADRES_002 wciÄ…gniÄ™ty do wartoĹ›ci FIRMA po warstwie 3).
          [FIX-NER-ADDR-PREFIX] FIX-NER-GLOBAL pomija warianty zaczynajÄ…ce siÄ™
          od prefiksu adresowego (ul./al./os. itp.) â€” NER bĹ‚Ä™dnie klasyfikowaĹ‚
          "os. BolesĹ‚awa Chrobrego" jako OSOBA.
          [FIX-NER-JUNK-FIRMA] FIX-NER-GLOBAL pomija FIRMA zĹ‚oĹĽone wyĹ‚Ä…cznie
          z sufiksu prawnego lub krĂłtsze niĹĽ 4 znaki (np. "z o.o.", '" Sp.').
          [FIX-NER-TRAILING-PUNCT] FIX-NER-GLOBAL stripuje koĹ„cowÄ… interpunkcjÄ™
          przed podmianÄ… â€” eliminuje duplikaty "WiĹ›niewski," vs "WiĹ›niewski".
  v1.2 â€” [FIX-FIRMA-CLEANUP] Czyszczenie cudzysĹ‚owĂłw i sufiksĂłw prawnych
          po tokenach FIRMA w FIX-NER-GLOBAL.
  v1.1 â€” [FIX-T22] Regex dla numeru dowodu osobistego (ABC 123456) dodany
          przed ADDR_RE â€” wczeĹ›niej trafiaĹ‚ jako ADRES zamiast NUMER.
          [FIX-T24] Regex dla instytucji publicznych z lokalizacjÄ…
          (SÄ…d Rejonowy dla X, UrzÄ…d Skarbowy w X itp.) â€” zwraca INSTYTUCJA.
          Regex dla sygnatury akt (I C 123/2026, XII Ns 45/25) â€” NUMER.
  v1.0 â€” wydzielenie z pseudominizer_api.py v1.18.
          [FIX-PIPELINE-ORDER] KolejnoĹ›Ä‡ warstw ustalona na podstawie
          analizy interakcji miÄ™dzy nimi.
          [FIX-ADDR-RE-LEVEL] _ADDR_RE przeniesiony na poziom moduĹ‚u.

ZaleĹĽnoĹ›ci:
  stdlib: re, logging, dataclasses
  lokalne: ner_layer, verbal_amounts
  opcjonalne: output_guard (fail-open jeĹ›li niedostÄ™pny)
  przez AppState: spacy_ner (moduĹ‚), anonymizer (instancja)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any

import ner_layer
import verbal_amounts
from ner_blocklist import _LEGAL_SUFFIXES_LOWER as _FIRMA_SUFFIXES

logger = logging.getLogger("pseudominizer.pipeline")

# â”€â”€ Output guard â€” opcjonalny â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

try:
    from output_guard import guard_output, guard_output_with_map, GuardMode
    _GUARD_AVAILABLE = True
    logger.info("[PIPELINE] output_guard zaĹ‚adowany")
except ImportError:
    _GUARD_AVAILABLE = False
    logger.warning("[PIPELINE] output_guard niedostÄ™pny â€” blokada wyjĹ›ciowa wyĹ‚Ä…czona")

# â”€â”€ StaĹ‚e â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b")

# [FIX-T22] Numer dowodu osobistego â€” 3 wielkie litery + spacja + 6 cyfr.
# Musi byÄ‡ PRZED _ADDR_RE w pipeline bo ADDR_RE Ĺ‚apie "ABC 123456" jako adres
# (dopasowanie "ABC 12" pasuje do wzorca ulicy bez numeru domu).
_ID_CARD_RE = re.compile(
    r"\b[A-Z]{3}\s?\d{6}\b",
    re.UNICODE,
)

# [FIX-T24] Instytucje publiczne z lokalizacjÄ….
# Blocklista w ner_blocklist.py chroni przed SpaCy ale nie przed przypadkiem
# gdy SpaCy w ogĂłle nie wykryje encji (brak FIRMA/ORG dla peĹ‚nej nazwy).
# Regex Ĺ‚apie wzorzec: <rodzaj_sÄ…du/urzÄ™du> [Rodzaju] dla/w/we <Lokalizacja>
# PrzykĹ‚ady: "SÄ…d Rejonowy dla Krakowa-ĹšrĂłdmieĹ›cia", "UrzÄ…d Skarbowy w Tarnowie"
# [BUG-2] Mianownik + dopeĹ‚niacz dla kaĹĽdej instytucji.
# [BUG-3] Nowe instytucje: KNF, RPO, TK, PIP, PPK.
# [BUG-4] SkrĂłty: PPK, KNF, RPO, TK, PIP, GUS, NIK, UOKiK.
# [BUG-1] Opcjonalna lokalizacja po nazwie instytucji (Opcja A).
_INSTITUTION_RE = re.compile(
    r"(?:"
    r"(?:SÄ…d|SÄ…du|SÄ…dowi)\s+(?:Rejonowy|Rejonowego|Rejonowemu|OkrÄ™gowy|OkrÄ™gowego|OkrÄ™gowemu|Apelacyjny|Apelacyjnego|Administracyjny|Administracyjnego|NajwyĹĽszy|NajwyĹĽszego)"
    r"|(?:Naczelny|Naczelnego)\s+(?:SÄ…d|SÄ…du)\s+Administracyjny(?:ego)?"
    r"|(?:WojewĂłdzki|WojewĂłdzkiego)\s+(?:SÄ…d|SÄ…du)\s+Administracyjny(?:ego)?"
    r"|(?:UrzÄ…d|UrzÄ™du|UrzÄ™dowi)\s+(?:Skarbowy|Skarbowego|Celno-Skarbowy|Celno-Skarbowego|Pracy|Ochrony\s+Danych\s+Osobowych)"
    r"|(?:Prokuratura|Prokuratury|Prokuraturze)\s+(?:Rejonowa|Rejonowej|OkrÄ™gowa|OkrÄ™gowej|Apelacyjna|Apelacyjnej|Krajowa|Krajowej)"
    r"|(?:Powiatowy|Powiatowego|WojewĂłdzki|WojewĂłdzkiego)\s+(?:UrzÄ…d|UrzÄ™du)\s+Pracy"
    r"|(?:ZakĹ‚ad|ZakĹ‚adu|ZakĹ‚adowi)\s+UbezpieczeĹ„\s+SpoĹ‚ecznych"
    r"|WydziaĹ‚[ \t]+(?:[IVX]+|[0-9]+)[ \t]+[\w\u00c0-\u017e][\w \t\-\u00c0-\u017e]{0,30}"
    r"|(?:Komisja|Komisji|KomisjÄ™)\s+Nadzoru\s+Finansowego"
    r"|(?:Rzecznik|Rzecznika|Rzecznikowi)\s+Praw\s+Obywatelskich"
    r"|(?:TrybunaĹ‚|TrybunaĹ‚u|TrybunaĹ‚owi)\s+Konstytucyjn(?:y|ego|emu)"
    r"|(?:PaĹ„stwowa|PaĹ„stwowej)\s+Inspekcja\s+Pracy|PaĹ„stwowej\s+Inspekcji\s+Pracy"
    r"|(?:Pracownicze|Pracowniczych|Pracowniczymi)\s+Plan(?:y|Ăłw|ami)\s+KapitaĹ‚ow(?:e|ych|ymi)"
    r"|\bPPK\b|\bKNF\b|\bRPO\b|\bTK\b|\bPIP\b|\bGUS\b|\bNIK\b|\bUOKiK\b"
    r")",
    re.IGNORECASE | re.UNICODE,
)

# Sygnatura administracyjna â€” format XX.DDDDDD.RRRR (np. PT.046166.2021, SA.092213.2021)
_ADMIN_SIG_RE = re.compile(
    r"\b[A-Z]{2}\.\d{6}\.\d{4}\b",
    re.UNICODE,
)

# [FIX-T24] Sygnatura akt sÄ…dowych.
# Format: cyfry_rzymskie/litery + spacja + litery + spacja + liczba/rok.
# PrzykĹ‚ady: "I C 123/2026", "XII Ns 45/25", "II K 789/2024", "III Ca 12/2026"
# Musi byÄ‡ przed anonymizer ĹĽeby nie kolidowaÄ‡ z NUMER tokenami z regex warstwy.
_CASE_SIG_RE = re.compile(
    r"\b(?:"
    r"(?:I{1,3}V?|VI{0,3}|IX|XI{0,2}|XII)\s+[A-Z][A-Za-z]{0,4}"
    r"|Km|Kmp|Ko|Kms|GC|C|K|W"
    r")\s+\d{1,6}/\d{2,4}\b",
    re.UNICODE,
)

# Regex adresĂłw z prefiksem ul./al. â€” kompilowany raz przy imporcie moduĹ‚u.
_ADDR_RE = re.compile(
    r"(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar)"
    r"\.?[ \t]+[A-Z\u0141\u015a\u0179\u0106\u0143]"
    r"[\w\u00f3\u017c\u017a\u0107\u0144\u0142\u015b\u0105\u0119\- ]{1,40}"
    r"[ \t]+\d+(?:[a-zA-Z])?(?:/\d+(?:[a-zA-Z])?)?"
    r"(?:[,\s]+\d{2}-\d{3}[,\s]+"
    r"[A-Z\u0141\u015a\u0179\u0106\u0143][\w ,]{2,25})?",
    re.IGNORECASE | re.UNICODE,
)

# [FIX-FIRMA-CLEANUP] Po FIX-NER-GLOBAL: usuĹ„ cudzysĹ‚Ăłw prosty i sufiks prawny
# otaczajÄ…cy token FIRMA â€” SpaCy czÄ™sto zwraca samÄ… nazwÄ™ bez cudzysĹ‚owĂłw/sufiksu,
# co zostawia "FIRMA_001" S.A. zamiast FIRMA_001.
# Budowany raz przy imporcie z aktualnej listy sufiksĂłw z ner_blocklist.py.
_FIRMA_SUF_PAT = "|".join(
    re.escape(s) for s in sorted(_FIRMA_SUFFIXES, key=len, reverse=True)
)
_FIRMA_CLEANUP_RE = re.compile(
    r'"?(FIRMA_\d{3})"?(?:\s+(?:' + _FIRMA_SUF_PAT + r'))?',
    re.IGNORECASE,
)

# [BUG-PERF-1] _ADDR_PREFIX_RE i _BARE_SUFFIX_RE skompilowane raz przy imporcie
# moduĹ‚u â€” poprzednio kompilowane wewnÄ…trz _run_pipeline() przy kaĹĽdym wywoĹ‚aniu.
_ADDR_PREFIX_RE = re.compile(
    r"^\s*(?:ul|al|pl|os|aleja|ulica|plac|osiedle|skwer|rondo|bulwar)"
    r"\.?\s+",
    re.IGNORECASE,
)

_BARE_SUFFIX_RE = re.compile(
    r'^["\s]*(?:' + _FIRMA_SUF_PAT + r')["\s]*$',
    re.IGNORECASE,
)


# â”€â”€ Struktury danych â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@dataclass
class AppState:
    """
    Stan aplikacji inicjalizowany raz przy starcie serwera.
    Przekazywany do pseudonymize_document() jako dependency injection.
    Wszystkie pola read-only po inicjalizacji.
    """
    spacy_ner_mod: Any = None   # moduĹ‚ spacy_ner
    anonymizer:    Any = None   # instancja Anonymizer
    anon_map:      Any = None   # instancja AnonymizerMap
    morf_env:      Any = None   # Ĺ›rodowisko Morfeusz2


@dataclass
class PipelineResult:
    """Wynik pseudonimizacji zwracany do endpointu /preview."""
    text:          str
    reverse_map:   dict = field(default_factory=dict)
    guard_blocked: bool = False
    guard_reasons: list = field(default_factory=list)
    error:         str | None = None


# â”€â”€ API publiczne â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def pseudonymize_document(text: str, state: AppState) -> PipelineResult:
    """
    Pseudonimizuje tekst przechodzÄ…c przez wszystkie warstwy w kolejnoĹ›ci.
    Fail-soft: bĹ‚Ä…d w warstwie loguje ostrzeĹĽenie i przechodzi dalej.
    Fail-closed dla output_guard: blokada jest respektowana.
    """
    try:
        return _run_pipeline(text, state)
    except Exception as e:
        logger.error("[PIPELINE] Nieoczekiwany bĹ‚Ä…d: %s", e)
        return PipelineResult(text=text, error=f"BĹ‚Ä…d pseudonimizacji: {e}")


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _apply_regex_layer(
    text: str,
    reverse_map: dict,
    pattern: re.Pattern,
    prefix: str,
    min_len: int = 3,
) -> tuple[str, dict]:
    """
    WspĂłlna logika dla warstw regex (dowĂłd, instytucja, sygnatura, adres).
    Iteruje od koĹ„ca tekstu ĹĽeby nie rozjeĹĽdĹĽaĹ‚y siÄ™ offsets po replace.
    Zwraca (nowy_tekst, zaktualizowana_reverse_map).
    """
    counter = sum(1 for k in reverse_map if k.startswith(f"{prefix}_"))
    for m in sorted(pattern.finditer(text), key=lambda x: x.start(), reverse=True):
        matched = m.group(0).strip()
        if len(matched) < min_len:
            continue
        if _TOKEN_RE.search(matched):
            continue
        counter += 1
        token = f"{prefix}_{counter:03d}"
        reverse_map[token] = matched
        text = text[:m.start()] + token + text[m.end():]
        logger.debug("[PIPELINE] %s: '%s' -> %s", prefix, matched, token)
    return text, reverse_map


# â”€â”€ PrzeĹ‚Ä…cznik nowego pipeline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Ustaw True ĹĽeby testowaÄ‡ pipeline oparty na TokenAllocator (pipeline_new.py).
# Stary kod pozostaje nienaruszony â€” zmiana jednej staĹ‚ej przeĹ‚Ä…cza Ĺ›cieĹĽkÄ™.
USE_NEW_PIPELINE: bool = True

# â”€â”€ Implementacja â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _apply_guard(
    text: str,
    reverse_map: dict,
    state: AppState,
    force_block: bool = False,
) -> PipelineResult:
    # Wspolna sciezka output_guard dla obu pipelinow.
    # force_block=True: blokada prewencyjna gdy wczesniejszy etap zglosil blad (MED-1).
    guard_blocked = force_block
    guard_reasons: list = ["[FORCE_BLOCK] Blad wczesniejszego etapu"] if force_block else []

    if _GUARD_AVAILABLE and not force_block:
        try:
            guard_result = guard_output_with_map(
                text,
                state.anon_map,
                mode=GuardMode.REDACT,
                known_plain=[
                    v for v in reverse_map.values()
                    if len(re.sub(r'[\s\"\'“”„‟]+', '', v)) >= 5
                ],
            )
            guard_blocked = guard_result.blocked
            guard_reasons = guard_result.reasons
            if guard_blocked:
                logger.error("[PIPELINE] Guard zablokował eksport: %s", guard_reasons)
            elif guard_result.redacted:
                logger.warning("[PIPELINE] Guard zamazał fragmenty: %s", guard_reasons)
                text = guard_result.redacted_text
        except Exception as e:
            # [MED-1] Wyjatek guarda -> blokada prewencyjna zamiast przepuszczenia.
            guard_blocked = True
            guard_reasons = [f"[GUARD_EXCEPTION] {e}"]
            logger.error("[PIPELINE] output_guard wyjatek -- BLOKADA prewencyjna: %s", e)

    return PipelineResult(
        text=text,
        reverse_map=reverse_map,
        guard_blocked=guard_blocked,
        guard_reasons=guard_reasons,
        error=None,
    )


def _run_pipeline(text: str, state: AppState) -> PipelineResult:
    if USE_NEW_PIPELINE:
        from pipeline_new import run_pipeline_new
        new_text, new_map = run_pipeline_new(text, state.spacy_ner_mod, state.anonymizer)
        return _apply_guard(new_text, new_map, state)

    reverse_map: dict = {}

    # â”€â”€ Normalizacja cudzysĹ‚owĂłw typograficznych â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    text = text.replace("\u201e", '"').replace("\u201d", '"')
    text = text.replace("\u00ab", '"').replace("\u00bb", '"')

    # â”€â”€ Warstwa 1: NER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ner_variants: dict = {}
    if state.spacy_ner_mod:
        try:
            # [BUG-B2] detect_entities() osobno â€” przekazujemy list[NERResult]
            # do check_and_block, aktywujÄ…c Ĺ›cieĹĽkÄ™ 1 (SpaCy confidence).
            # Koszt: SpaCy przetwarza tekst dwa razy (tu + wewnÄ…trz process_ner).
            ner_entity_list = []
            try:
                ner_entity_list = state.spacy_ner_mod.detect_entities(text)
            except Exception as _det_err:
                logger.warning("[PIPELINE] detect_entities bĹ‚Ä…d: %s â€” check_and_block bez Ĺ›cieĹĽki SpaCy", _det_err)
            ner_reverse, ner_variants = ner_layer.process_ner(text, state.spacy_ner_mod)
            reverse_map.update(ner_reverse)
            logger.debug("[PIPELINE] NER: %d encji", len(ner_reverse))
            known = (
                state.anon_map.get_entity_names()
                if (state.anon_map and hasattr(state.anon_map, "get_entity_names"))
                else set()
            )
            try:
                state.spacy_ner_mod.check_and_block(
                    text,
                    ner_entity_list,
                    known_entities=known,
                )
            except Exception as _cab_err:
                # fail-soft: bĹ‚Ä…d check_and_block nie zatrzymuje pipeline
                logger.warning("[PIPELINE] check_and_block bĹ‚Ä…d: %s â€” kontynuujÄ™", _cab_err)
        except Exception as e:
            logger.warning("[PIPELINE] NER bĹ‚Ä…d: %s â€” kontynuujÄ™ bez NER", e)

    # â”€â”€ Normalizacja IBAN ze spacjÄ… â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    text = re.sub(
        r"\bPL\s+(\d{2}(?:\s?\d{4}){6})\b",
        lambda m: "PL" + m.group(1).replace(" ", ""),
        text,
        flags=re.IGNORECASE,
    )

    # â”€â”€ Warstwa 2a: numer dowodu osobistego â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # [FIX-T22] Musi byÄ‡ PRZED ADDR_RE â€” inaczej "ABC 123456" Ĺ‚apane jako adres.
    text, reverse_map = _apply_regex_layer(
        text, reverse_map, _ID_CARD_RE, "NUMER", min_len=9
    )

    # â”€â”€ Warstwa 2b: instytucje publiczne z lokalizacjÄ… â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # [FIX-T24] SpaCy blokowany w ner_blocklist ale tu Ĺ‚apiemy peĹ‚nÄ… nazwÄ™
    # z dopeĹ‚niaczem geograficznym ("SÄ…d Rejonowy dla Krakowa-ĹšrĂłdmieĹ›cia").
    text, reverse_map = _apply_regex_layer(
        text, reverse_map, _INSTITUTION_RE, "INSTYTUCJA", min_len=5
    )

    # â”€â”€ Warstwa 2c: sygnatura akt sÄ…dowych â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # [FIX-T24] Format "I C 123/2026" â€” kontekstowe PII (numer sprawy).
    text, reverse_map = _apply_regex_layer(
        text, reverse_map, _CASE_SIG_RE, "NUMER", min_len=7
    )

    # â”€â”€ Warstwa 2d: sygnatura administracyjna â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    text, reverse_map = _apply_regex_layer(
        text, reverse_map, _ADMIN_SIG_RE, "NUMER", min_len=12
    )

    # â”€â”€ Warstwa 3: ADDR regex â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    addr_counter = 0
    for m in sorted(_ADDR_RE.finditer(text), key=lambda x: x.start(), reverse=True):
        addr_text = m.group(0).strip()
        if len(addr_text) < 8:
            continue
        if _TOKEN_RE.search(addr_text):
            continue
        addr_counter += 1
        addr_token = f"ADRES_{addr_counter:03d}"
        reverse_map[addr_token] = addr_text
        text = text[:m.start()] + addr_token + text[m.end():]
        logger.debug("[PIPELINE] ADDR: '%s' -> %s", addr_text, addr_token)

    # â”€â”€ Warstwa 4: kwoty sĹ‚owne â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    kwota_counter = [0]
    text, reverse_map = verbal_amounts.mask_verbal_amounts(
        text, reverse_map, kwota_counter
    )
    logger.debug("[PIPELINE] verbal_amounts: %d KWOTA tokenĂłw", kwota_counter[0])

    # â”€â”€ Warstwa 5: anonymizer (warstwy 1-5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _anonymizer_failed = False
    if state.anonymizer:
        try:
            # [BUG-PIPELINE-GUARD] Zbierz tokeny wstawione przez warstwy 1-4
            # i przekaĹĽ do anonymize() jako known_tokens â€” guard injection
            # nie rzuca na wĹ‚asne tokeny pipeline'u.
            pipeline_tokens = frozenset(
                m.group(0) for m in _TOKEN_RE.finditer(text)
            )
            anon_text, anon_reverse = state.anonymizer.anonymize(
                text,
                known_tokens=pipeline_tokens,
                existing_reverse_map=reverse_map,
                skip_guard=True,
            )
            reverse_map.update(anon_reverse)
            text = anon_text
            logger.debug("[PIPELINE] anonymizer: %d tokenĂłw Ĺ‚Ä…cznie", len(reverse_map))
        except Exception as e:
            # [MED-1] Blad anonymizera -> guard dostalby niepelna mape -> force_block.
            _anonymizer_failed = True
            logger.error("[PIPELINE] anonymizer blad: %s -- BLOKADA guard prewencyjna", e)
    else:
        logger.warning("[PIPELINE] anonymizer niedostÄ™pny â€” pomijam warstwy regex")

    # â”€â”€ Warstwa 6: FIX-NER-GLOBAL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    # [BUG-C] Ochrona kontraktu typĂłw â€” jeĹ›li process_ner() zmieni sygnaturÄ™
    # i drugi element krotki nie bÄ™dzie sĹ‚ownikiem, pÄ™tla rzuci AttributeError
    # Ĺ‚apany przez zewnÄ™trzny try/except bez komunikatu o bĹ‚Ä™dzie NER.
    if not isinstance(ner_variants, dict):
        logger.warning(
            "[PIPELINE] ner_variants nieprawidĹ‚owy typ: %s â€” pomijam FIX-NER-GLOBAL",
            type(ner_variants),
        )
        ner_variants = {}

    for variant_text, token in ner_variants.items():
        if not (token.startswith("OSOBA_") or token.startswith("FIRMA_")):
            continue

        # [FIX-NER-ADDR-PREFIX] PomiĹ„ warianty bÄ™dÄ…ce adresem â€” NER bĹ‚Ä™dnie
        # klasyfikuje "os. BolesĹ‚awa Chrobrego" jako osobÄ™. Regex na poziomie moduĹ‚u.
        if _ADDR_PREFIX_RE.match(variant_text):
            logger.debug("[PIPELINE] FIX-NER-ADDR-PREFIX: pominiÄ™to '%s'", variant_text[:40])
            continue

        # [FIX-NER-JUNK-FIRMA] PomiĹ„ FIRMA zĹ‚oĹĽone wyĹ‚Ä…cznie z sufiksu prawnego
        # lub krĂłtsze niĹĽ 4 znaki (np. '"z o.o."', '" Sp.', '"\nul.'). Regex na poziomie moduĹ‚u.
        if token.startswith("FIRMA_"):
            clean = re.sub(r'[\s"\n\r]', "", variant_text)
            if len(clean) < 4 or _BARE_SUFFIX_RE.match(variant_text):
                logger.debug("[PIPELINE] FIX-NER-JUNK-FIRMA: pominiÄ™to '%s'", variant_text[:40])
                continue

        # [FIX-NER-TOKEN-IN-TOKEN] Wariant zawiera juĹĽ token (np. ADRES_002
        # wciÄ…gniÄ™ty do nazwy FIRMA po warstwie 3) â€” pomiĹ„.
        if _TOKEN_RE.search(variant_text):
            logger.debug("[PIPELINE] FIX-NER-TOKEN-IN-TOKEN: pominiÄ™to '%s'", variant_text[:40])
            continue

        # [FIX-NER-TRAILING-PUNCT] Wariant z przecinkiem/kropkÄ… na koĹ„cu
        # (duplikat "StanisĹ‚aw WiĹ›niewski," obok "StanisĹ‚aw WiĹ›niewski") â€”
        # strip interpunkcji przed podmianÄ….
        stripped = re.sub(r"[,\.;:!?\s]+$", "", variant_text).rstrip()
        if stripped and stripped != variant_text:
            text = text.replace(variant_text, token)
        text = text.replace(stripped or variant_text, token)

        if "\n" in variant_text or "\r" in variant_text:
            normalized = re.sub(r"\s+", " ", variant_text).strip()
            if normalized and normalized != variant_text:
                if not _TOKEN_RE.search(normalized):
                    text = text.replace(normalized, token)

    # [FIX-FIRMA-CLEANUP] WyczyĹ›Ä‡ "FIRMA_001" S.A. â†’ FIRMA_001
    text = _FIRMA_CLEANUP_RE.sub(r"\1", text)

    return _apply_guard(text, reverse_map, state, force_block=_anonymizer_failed)



