"""
Triangulum — anonymizer.py  v4.25
Zmiany v4.25:
  [FEATURE-SKIP-GUARD] anonymize() przyjmuje skip_guard=False. Gdy True, guard injection
  jest pomijany — API-level check ([AUD-01] w pseudominizer_api.py) wystarczy dla
  tekstów przychodzących z pipeline'u. Eliminuje podwójną walidację.
  [FIX-LOGGER] logger zmieniony z "triangulum.anonymizer" na "lynxmask.anonymizer".
          output_guard.py miał już poprawny prefix po renaming projektu.
          anonymizer.py pozostawał z "triangulum" — utrudniało analizę logów.
          Linia 220 (przed zmianą numeracji).
Zmiany v4.24:
  [FIX-CTR-SCAN] _layer2_regex: dodano skan tekstu przez TOKEN_SPAN_RE po pętli
  inicjalizującej liczniki z reverse_map. Działa jako niezależna warstwa bezpieczeństwa —
  chroni przed kolizją nawet gdy existing_reverse_map nie został przekazany.
Zmiany v4.23:
  [FIX-TOKEN-COUNTER-COLLISION] anonymize() przyjmuje existing_reverse_map (pipeline's
  reverse_map). _layer2_regex inicjalizuje liczniki z tego słownika zamiast z pustego {},
  co eliminuje kolizje NUMER_NNN między tokenami pipeline'u (dowód, sygnatura) a tokenami
  anonymizera (PESEL, telefon). Linie: anonymize() sygnatura (~928), reverse_map init (~955).
Zmiany v4.22:
  [BUG-PIPELINE-GUARD] anonymize() dostawał tekst z tokenami wstawionymi przez
          własny pipeline (NUMER_001 z _ID_CARD_RE, ADRES_001 z _ADDR_RE).
          Guard [BUG-3] widział je jako atak injection i rzucał ValueError.
          Pipeline łapał wyjątek cicho — całe STRUCTURAL_PATTERNS pomijane.
          PESEL, NIP, IBAN, EMAIL, TELEFON nigdy nie trafiały do _layer2_regex.
          Naprawa: parametr known_tokens: frozenset w anonymize() — guard rzuca
          tylko gdy znaleziony token NIE jest w known_tokens (naprawdę zewnętrzny).
          anonymize_with_ner() przekazuje pusty frozenset — guard nadal chroni.
          pipeline.py przekazuje tokeny które sam wstawił przed wywołaniem.
          Linie dotknięte: anonymize() sygnatura i guard (~917-938).
Zmiany v4.21:
  [BUG-3] Token injection w anonymize() — walidacja przed warstwami.
          Użytkownik mógł wstrzyknąć FIRMA_001 w tekście wejściowym.
          _layer2_regex dodawał go do occupied (przez _token_spans/TOKEN_SPAN_RE)
          i pomijał jako "już zamaskowany". Deanonymize następnie go podmieniał
          na wartość z reverse_map sesji — ujawniając dane z mapy.
          Naprawa: TOKEN_SPAN_RE.search(text) przed warstwami w anonymize().
          Token w tekście wejściowym → ValueError. Spójne z AUD-01
          w pseudominizer_api.py /preview (TOKEN_RE.search).
          Uwaga: TOKEN_SPAN_RE użyty zamiast TOKEN_RE — TOKEN_SPAN_RE
          to wersja bez grup przechwytujących (search-only), wydajniejsza.
Zmiany v4.20:
  [BUG-6] TOKEN_EMAIL dodany do importu z anonymizer_init.
          TOKEN_EMAIL dodany do self._counters w AnonymizerMap.__init__.
          TOKEN_EMAIL dodany do counters w _layer2_regex.
          Wzorzec email w STRUCTURAL_PATTERNS (anonymizer_init.py) zmieniony
          z TOKEN_NUMER na TOKEN_EMAIL — email tokenizowany teraz jako EMAIL_NNN
          zamiast NUMER_NNN.
          Dotknięte linie: import (~190-200), _counters (~554-558), counters (~1184).
Zmiany v4.19:
  [LEAK-LOG-1] _layer2_regex: usunięto PII z logów DEBUG.
               PHONE-L5 logował raw (numer telefonu plaintext) i region.
               POSTAL-L3 logował addr_text[:50] (adres plaintext).
               Zastąpiono długością wartości: len(raw), len(addr_text).
Zmiany v4.18:
  [FIX-POSTAL-SAFELIST] _init_postal_patterns: EU_COUNTRIES ograniczone do
          PL/DE/FR/IT/ES/NL/GB. Kody 4-cyfrowe (AT,CH,BE,DK,NO,HU) i NNN NN
          (CZ,SK) zbiegały się z datami (2020→Austria) i kwotami (500 00→Czechy)
          w dokumentach biurowych. Dokumenty z adresami innych krajów: człowiek.
Zmiany v4.17:
  [FIX-ADDR-NOPREFIX-REMOVE] Usunięto wzorzec FIX-ADDR-NOPREFIX z STRUCTURAL_PATTERNS.
          Łapał "słowo + cyfra" bez kotwicy → masowe false positives na fakturach
          (numery, kody produktów, daty, kwoty). Pokrycie adresów bez prefiksu
          zapewniają FIX-ADDR-FULL, warstwa postal i _ADDR_RE w pipeline.py.
Zmiany v4.16:
  [FIX-ESCAPE] Docstringi: \\s \\d \\w \\S zamienione na \\\\s \\\\d \\\\w \\\\S.
          Python 3.12 SyntaxWarning, 3.14 SyntaxError — naprawione prewencyjnie.
Zmiany v4.15:
  [FIX-STDNUM] Warstwa 4 (_layer4_stdnum): walidacja numerów przez python-stdnum.
          Walidatory: VAT-EU (PL/DE/FR/AT/CZ+), IBAN, PESEL, NIP-PL, REGON,
          EDRPOU-UA (kod firmy ukraińskiej), RNTRC-UA (NIP osoby fizycznej UA).
          Walidacja przez checksum — zero false positives dla poprawnych numerów.
          Nowa zależność: pip install python-stdnum
  [FIX-PHONENUMBERS] Warstwa 5 (_layer5_phonenumbers): wykrywanie telefonów
          przez phonenumbers (libphonenumber Google). Obsługuje 200+ krajów,
          formaty lokalne (bez prefiksu) i międzynarodowe (+48, +380, +49...).
          PhoneNumberMatcher wyciąga numery z tekstu — nie potrzeba regex.
          Nowa zależność: pip install phonenumbers
Zmiany v4.14:
  [FIX-POSTAL-LIB] Warstwa 3 (_layer3_postal_addresses): wykrywanie adresów
          przez kody pocztowe jako kotwice. Używa postal-codes-tools (ECB)
          z regex dla 26 krajów UE. Obsługuje PL, DE, FR, NL, GB, AT, CZ, SE
          i inne automatycznie. Separator między komponentami adresu może być
          dowolny (spacja, przecinek, •, /, –) — kontekst ±60/30 znaków.
          Opcjonalna zależność: brak biblioteki = fallback do warstwy 2.
          Nowa zależność: pip install postal-codes-tools
Zmiany v4.13:
  [FIX-ADDR-SEP] Separator kod/miasto we wszystkich wzorcach adresowych:
          `[ \t]+` → `[,\\s]+`. Obsługuje spację, przecinek, przecinek+spację.
          Łapie: "65-510, Zielona Góra", "28-133, Pacanów", "65-510 Zielona Góra".
  [FIX-ADDR-NUM] Uogólniony format numeru domu: digit, digit+litera, digit/digit,
          digit+litera/digit. Poprzednio wymagał litery przed ukośnikiem (3A/9).
          Teraz łapie też: "4/6", "30", "12a".
  [FIX-ADDR-CHARSET] Kompletny zestaw polskich wielkich liter w nagłówku słowa:
          dodano Ą, Ę, Ó, Ż. Poprzednio "Zborówek" nie matchował bo ó nie było
          w [a-złśźćń]. Teraz ciało słowa używa \\w (unicode).
  [FIX-ADDR-FULL] Nowy wzorzec: pełny adres jednoliniowy z kodem pocztowym jako
          kotwicą. Łapie: "Sokola 4/6, 65-510, Zielona Góra".
Zmiany v4.12:
Zmiany v4.12:
  [FIX-NIP-PL] Nowy wzorzec TOKEN_NUMER: NIP z prefiksem PL (format unijny
          "PL6551979313"). Poprzedni wzorzec wymagał samych cyfr — NIP z PL
          nie był zakrywany, output_guard widział go jako krótki IBAN i blokował.
  [FIX-DIGITS-CATCHALL] Siatka bezpieczeństwa: wszystkie ciągi cyfr 8+ jako
          TOKEN_NUMER. Łapie EAN, CN, numery zamówień i inne niezdefiniowane
          formaty. False positives akceptowalne — oryginał w sejfie.
          Wzorzec ostatni w STRUCTURAL_PATTERNS — specyficzne wyżej mają priorytet.
  [FIX-IBAN-DASH] Nowy wzorzec TOKEN_NUMER: konto bankowe z myślnikami
          (format "61-12403347-1111001124737720"). Uzupełnia FIX-IBAN-PL
          który obsługiwał tylko spacje.
  [FIX-KWOTA-YEAR] Wzorzec TOKEN_KWOTA: poprzedni \\d[\\d\\s]* łapał rok+kwotę
          jako jedną wartość (np. "2025 78,69 PLN"). Nowy wzorzec ogranicza
          liczbę do max 1 spacji-separatora-tysięcy — eliminuje false positive.
  [FIX-B10-NUM] Wzorzec TOKEN_ADRES multiline: poprzedni [\\w/\\-]{1,10} dla numeru
          łapał dowolne słowo (np. "Góra" z "Zielona Góra") jako numer domu.
          Poprawka: numer musi zaczynać się od cyfry.
Zmiany v4.11:
Zmiany v4.11:
  [FIX-ADDR-NOPREFIX] Nowy wzorzec TOKEN_ADRES: ulica bez prefiksu "ul./al."
          z numerem mieszkania w formacie Litera/Cyfra (np. "Anny Jagiellonki 3A/9").
          Frakcja z literą jest charakterystyczna dla polskich adresów — eliminuje
          false positives na nazwach firm i datach.
  [FIX-TRACKING] Nowy wzorzec TOKEN_NUMER: numer przesyłki kurierskiej — 24 cyfry.
          Numer InPost/DHL/DPD identyfikuje nadawcę, odbiorcę i adres dostawy — PII.
          Wzorzec: dokładnie 24 cyfry z granicą słowa.
Zmiany v4.10:
  [FIX-B12-INIT] load_trie: gdy cache pusty i entities istnieją, zawsze rebuild
                 zamiast pickle.load(trie.pkl). trie.pkl mógł być zbudowany przed
                 FIX-B12-TRIE i zawierać atomy (np. "Jan" z "Jan Kowalski").
                 add_entity jest idempotentne — gdy encja już istnieje w mapie,
                 nie wywołuje _rebuild_trie() i _trie_cache pozostaje None.
                 Teraz load_trie() zawsze daje trie zgodne z bieżącym kodem.
Zmiany v4.9:
  [FIX-B12-CACHE] load_trie / _rebuild_trie: trie cache w pamięci (_trie_cache).
                  _rebuild_trie ustawia cache PO make_automaton, PRZED zapisem na dysk.
                  Zapis trie.pkl w bloku try/except — błąd zapisu (Permission Denied)
                  nie blokuje działania, trie jest aktywne w pamięci.
                  load_trie sprawdza cache przed pickle.load — stary plik na dysku
                  nie nadpisuje świeżo przebudowanego trie.
                  Naprawia B12 w środowiskach read-only (folder testowy bez praw zapisu).
Zmiany v4.8:
  - Numer wewnetrzny/skrocony: wzorzec 3-2-2 (322 19 27) jako ostatni w STRUCTURAL_PATTERNS
  - Akceptacja false positives na krotkich liczbach (decyzja produktowa: za duzo OK)
Zmiany v4.6:
  - Telefon stacjonarny, kontekstowy, sygnatury akt
Zmiany v4.5 (oryginal):
==============================
Moduł anonimizacji i deanonimizacji dla pipeline analitycznego.

Wykrywanie środowiska (raz przy starcie, wynik w hardware_profile.json):
  Linux / Mac natywny  → import morfeusz2 bezpośrednio
  Windows + WSL2       → morfeusz2 przez subprocess WSL2 (stdin/stdout, bez injection)
  Windows bez WSL2     → blokada z instrukcją instalacji

Tokeny:
  FIRMA_{n}  — podmiot / firma
  OSOBA_{n}  — osoba fizyczna
  NUMER_{n}  — numer strukturalny (NIP, PESEL, REGON, KRS, IBAN)
  KWOTA_{n}  — kwota

Zasady nienaruszalne:
  - Anonimizacja = Python + Morfeusz2, nie LLM
  - Walidator blokuje przez ERR_TOKENS, nigdy nie naprawia
  - Token nierozpoznany przy deanonimizacji → ERR_TOKENS

Zmiany v4.5:
  [G3-4] check_blacklist_context: nowy parametr known_plain: list[str] = None
          Ścieżka 3 (GLOBALNY_PLAIN) — skanuje tekst pod kątem surowych nazw
          przekazanych z reverse_map bieżącej sesji, niezależnie od tokenów w mapie.
          Zamyka lukę: encje nierozpoznane przez SpaCy (brak tokenu → brak w mapie)
          były dotąd niewidoczne dla guarda. Kompatybilność wsteczna zachowana.

Zmiany v4.1:
  [FIX-SPACY-1] get_forms_batch: SpaCy lemmatizer + heurystyczne końcówki jako fallback gdy Morfeusz niedostępny
  [FIX-DEANON-1] deanonymize: token_id = group(1)_group(2) zamiast group(1)group(2) — deanon zawsze rzucał ERR_TOKENS
  [FIX-WB-1] _is_word_boundary: end_idx+1 zamiast end_idx — trie nigdy nie znajdowało dopasowań
  [FIX-CBC-1] check_blacklist_context: pomiń formy < 4 znaki łącznie (false positives na "z", "w")
  [FIX-CBC-2] check_blacklist_context: pomiń formy złożone wyłącznie z jednosylabowych słów

Zmiany v4 (na podstawie recenzji v3):
  [V4-1] Cykliczny hash naprawiony — hash liczony TYLKO z entities (bez version
          i trie_version), obie metadane pomijane przy hashowaniu. Eliminuje
          nieskończoną pętlę rebuild trie wywoływaną przez _rebuild_trie→_save→hash_zmiana.
  [V4-2] seen_values — normalizacja strukturalna dla numerów. _canonical_value()
          usuwa myślniki i spacje z NIP/PESEL/REGON/IBAN/telefon przed kluczowaniem.
          "123-456-78-90" i "1234567890" to teraz ten sam token.
  [V4-3] MAX_TOKENS_PER_REQUEST liczy unikalne tokeny (set), nie wszystkie
          wystąpienia. 600 wystąpień jednego NUMER_001 nie przekracza limitu.

Zmiany v3 (zachowane):
  [V3-1] seen_values w _layer2_regex
  [V3-2] _layer2_regex — poprawka last_end przy pominiętym dopasowaniu
  [V3-3] Unicode NFKC tylko do porównań
  [V3-4] Hash z entities (v4 precyzuje: tylko entities)
  [V3-5] Limit tokenów per żądanie
  [V3-6] Limit encji w onboarding batch
  [V3-7] Walidacja niepustej nazwy
  [V3-8] Deduplikacja alertów check_blacklist_context
  [V3-9] Trie: weryfikacja spójności przy ładowaniu

Zmiany v2 (zachowane):
  [KR1] version hash spójny z plikiem
  [KR2] WSL2 subprocess — stdin/stdout JSON
  [KR3] Trie ładowane per wywołanie
  [KR4] Warstwa 2 regex pomija ⟦...⟧
  [KR5] shutil.move zamiast Path.replace()
  [KR6] WSL2 onboarding wsadowy
  [W1]  _resolve_longest_match — sortowanie globalne po długości
  [W2]  Normalizacja Unicode NFKC dla porównań
  [W3]  validate_tokens używa Counter
  [W4]  check_blacklist_context: dwie ścieżki + normalizacja interpunkcji
  [W5]  Limit inputu 500KB

Świadome ograniczenia (odkładamy):
  - get_base_form: fallback do mianownika (pełny tagger: następny sprint)
  - Zamiana ról P1↔P2: post-walidacja relacyjna wyżej w pipeline
  - Podwójny _save w add_entity→_rebuild_trie: przeprojektowanie przy integracji
  - Walidacja sum kontrolnych PESEL/NIP: po testach na realnych dokumentach
  - Cache trie z wersjonowaniem: po pomiarach wydajności
  - NFKC fail mode (tryb strict): po testach
"""

import re
import json
import copy
import pickle
import shutil
import hashlib
import platform
import subprocess
import unicodedata
import logging
from collections import Counter
from pathlib import Path
from typing import Optional

from anonymizer_init import (
    _POSTAL_PATTERNS, _POSTAL_CONTEXT_BEFORE, _POSTAL_CONTEXT_AFTER,
    _STDNUM_VALIDATORS, _STDNUM_CANDIDATE_RE,
    _PHONENUMBERS_AVAILABLE,
    _crypto, _CRYPTO_AVAILABLE,
    TOKEN_FIRMA, TOKEN_OSOBA, TOKEN_NUMER, TOKEN_KWOTA, TOKEN_ADRES, TOKEN_EMAIL,
    TOKEN_RE, TOKEN_SPAN_RE,
    INPUT_LIMIT_BYTES, MAX_TOKENS_PER_REQUEST,
    STRUCTURAL_PATTERNS, _STRUCTURAL_TOKEN_TYPES,
)

logger = logging.getLogger("lynxmask.anonymizer")



# ============================================================
# Pomocnicze
# ============================================================

def _normalize(text: str) -> str:
    """
    NFKC + lower — tylko do PORÓWNAŃ, nigdy do indeksowania. [V3-3]
    NFKC może zmienić długość stringa (np. ﬁ→fi), co przesuwa indeksy.
    """
    return unicodedata.normalize("NFKC", text).lower()


def _canonical_value(token_type: str, raw: str) -> str:
    """
    Klucz idempotentności dla seen_values w warstwie 2. [V4-2]

    Dla TOKEN_NUMER (NIP, PESEL, REGON, IBAN, telefon):
      usuwa myślniki, spacje i kropki → "123-456-78-90" == "1234567890"
    Dla TOKEN_KWOTA i innych:
      zwykła normalizacja NFKC + lower

    Cel: ten sam logiczny numer w różnych formatach → jeden token.
    """
    if token_type in _STRUCTURAL_TOKEN_TYPES:
        return re.sub(r"[\s\-\.]", "", raw).lower()
    return _normalize(raw)


def _strip_punct(word: str) -> str:
    """Usuwa interpunkcję z początku i końca słowa."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", word)


def _token_spans(text: str) -> list[tuple[int, int]]:
    """Zwraca listę zakresów (start, end) tokenów ⟦...⟧ w tekście."""
    return [(m.start(), m.end()) for m in TOKEN_SPAN_RE.finditer(text)]


def _overlaps_any(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    """Sprawdza czy zakres (start, end) nachodzi na którykolwiek ze spans."""
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def _hash_entities(entities: dict) -> str:
    """
    Deterministyczny hash tylko z entities. [V4-1]
    Pomija version i trie_version — eliminuje cykliczną zależność.
    Używany zarówno do version (mapa) jak i trie_version (synchronizacja).
    """
    content = json.dumps(entities, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(content).hexdigest()


# ============================================================
# Skrypt WSL2
# ============================================================

_WSL2_SCRIPT = """
import sys, json, morfeusz2
morf = morfeusz2.Morfeusz()
words = json.load(sys.stdin)
result = {}
for word in words:
    # [FIX] morfeusz2.generate() przyjmuje tylko pojedyncze słowo.
    # Wielowyrazowe encje (np. "Jan Kowalski") rozbijamy na tokeny.
    parts = word.split()
    all_forms = {word}  # zawsze zachowaj pełną oryginalną formę
    for part in parts:
        all_forms.update(r[0] for r in morf.generate(part) if r[0])
    result[word] = list(all_forms)
print(json.dumps(result, ensure_ascii=False))
"""


# ============================================================
# ERR_TOKENS
# ============================================================

class ERR_TOKENS(Exception):
    """Token nierozpoznany lub brakujący — blokada pipeline. Nigdy nie naprawia."""
    pass


# ============================================================
# MorfEnv
# ============================================================

class MorfEnv:
    """Wykrywa dostępny backend Morfeusza i udostępnia jednolite API."""

    NATIVE  = "native"
    WSL2    = "wsl2"
    BLOCKED = "blocked"

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path
        self.mode = self._detect()

    def _detect(self) -> str:
        # Nie cachujemy BLOCKED — przy kazdym starcie probujemy ponownie.
        # Cache dziala tylko dla NATIVE i WSL2 (instalacja sie nie zmienia).
        if self.profile_path.exists():
            try:
                data = json.loads(
                    self.profile_path.read_text(encoding="utf-8")
                )
                mode = data.get("morfeusz_mode")
                if mode in (self.NATIVE, self.WSL2):
                    logger.info(f"Morfeusz2 mode z cache: {mode}")
                    return mode
            except Exception:
                pass
        mode = self._probe()
        self._save_mode(mode)
        return mode

    def _probe(self) -> str:
        system = platform.system()

        if system in ("Linux", "Darwin"):
            try:
                import morfeusz2  # noqa: F401
                logger.info("Morfeusz2: import natywny OK")
                return self.NATIVE
            except ImportError:
                logger.error("Morfeusz2 nie zainstalowany (Linux/Mac)")
                return self.BLOCKED

        if system == "Windows":
            # Najpierw próba natywnego importu — wheel dla Windows istnieje na PyPI
            try:
                import morfeusz2  # noqa: F401
                logger.info("Morfeusz2: import natywny OK (Windows)")
                return self.NATIVE
            except ImportError:
                pass
            # Fallback: WSL2
            try:
                result = subprocess.run(
                    ["wsl", "--status"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    test = subprocess.run(
                        ["wsl", "python3", "-c",
                         "import morfeusz2, json; "
                         "print(json.dumps({'ok': True}))"],
                        input="",
                        capture_output=True, text=True, timeout=15
                    )
                    if test.returncode == 0 and '"ok"' in test.stdout:
                        logger.info("Morfeusz2: WSL2 OK")
                        return self.WSL2
                    logger.warning("WSL2 dostępny ale morfeusz2 nie zainstalowany")
                    return self.BLOCKED
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            logger.warning("Morfeusz2: Windows bez WSL2 — blokada")
            return self.BLOCKED

        return self.BLOCKED

    def _save_mode(self, mode: str):
        try:
            existing = {}
            if self.profile_path.exists():
                existing = json.loads(
                    self.profile_path.read_text(encoding="utf-8")
                )
            existing["morfeusz_mode"] = mode
            self.profile_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Nie można zapisać hardware_profile.json: {e}")

    def get_forms(self, word: str) -> list[str]:
        return self.get_forms_batch([word])[word]

    def get_forms_batch(self, words: list[str]) -> dict[str, list[str]]:
        """Wsadowe generowanie form. Jedno wywołanie Morfeusza/WSL2. [KR6]
        Gdy Morfeusz niedostępny — fallback SpaCy lemmatizer (częściowe odmiany).
        Gdy SpaCy niedostępny — tylko forma podstawowa.
        """
        if not words:
            return {}
        if self.mode == self.NATIVE:
            return self._forms_batch_native(words)
        if self.mode == self.WSL2:
            return self._forms_batch_wsl2(words)
        # Fallback: SpaCy lemmatizer zamiast Morfeusza [FIX-SPACY-1]
        return self._forms_batch_spacy(words)

    def _forms_batch_spacy(self, words: list[str]) -> dict[str, list[str]]:
        """
        Fallback gdy Morfeusz niedostępny. Używa SpaCy lemmatizer + heurystyczne
        końcówki fleksyjne dla polskich nazwisk i imion. [FIX-SPACY-1]

        Pokrycie: ~60-70% odmian dla imion (SpaCy daje lemmy), nazwiska słabiej.
        Wystarczające dla demo z human-in-the-loop.
        """
        # Końcówki fleksyjne dla ostatniego słowa encji (nazwiska, nazwy firm)
        # Najczęstsze w polskich dokumentach biurowych
        _SUFFIXES = [
            "a", "i", "y", "ę", "ą", "owi", "ie", "em",
            "iego", "iemu", "ią", "iej",
        ]

        try:
            import spacy as _spacy
            nlp = _spacy.load("pl_core_news_lg")
        except Exception:
            logger.warning("SpaCy niedostępny — forms fallback (tylko forma podstawowa)")
            return {w: [w] for w in words}

        result = {}
        for word in words:
            all_forms: set[str] = {word}
            parts = word.split()

            # SpaCy lemmatizer na każdym słowie składowym
            # [FIX-B12] Lemmy atomowe dodajemy TYLKO dla jednowyrazowych encji.
            # Dla wielowyrazowych atomy powodują false positives (np. "Jan" z "Jan Kowalski").
            doc = nlp(word)
            for token in doc:
                lemma = token.lemma_
                if lemma and len(lemma) >= 2:
                    if len(parts) == 1:
                        all_forms.add(lemma)
                        if token.text[0].isupper() and lemma[0].islower():
                            all_forms.add(lemma.capitalize())

            # Heurystyczne końcówki na ostatnim słowie (nazwisko/nazwa)
            if parts:
                last = parts[-1]
                prefix = parts[:-1]
                # Znajdź rdzeń — usuń typowe końcówki
                stem = last
                for sfx in sorted(_SUFFIXES, key=len, reverse=True):
                    if last.lower().endswith(sfx) and len(last) - len(sfx) >= 3:
                        stem = last[:-len(sfx)]
                        break
                # Dodaj formy z różnymi końcówkami
                for sfx in _SUFFIXES:
                    form_parts = prefix + [stem + sfx]
                    form = " ".join(form_parts)
                    all_forms.add(form)
                    # Wersja z wielką literą
                    cap_parts = prefix + [(stem + sfx).capitalize()]
                    all_forms.add(" ".join(cap_parts))

            result[word] = list(all_forms)

        return result

    def _forms_batch_native(self, words: list[str]) -> dict[str, list[str]]:
        import morfeusz2
        from itertools import product as iproduct
        morf = morfeusz2.Morfeusz()
        result = {}
        for word in words:
            parts = word.split()
            all_forms: set[str] = {word}  # zawsze zachowaj pełną oryginalną formę

            if len(parts) == 1:
                # Pojedyncze słowo — generuj wszystkie formy fleksyjne
                all_forms.update(r[0] for r in morf.generate(parts[0]) if r[0])
            else:
                # [FIX-B12] Wielowyrazowe encje — generuj kombinacje form składowych,
                # NIE dodawaj atomów (same "Jan" z "Jan Kowalski" powoduje
                # false positives — np. "Jan III Sobieski" byłby zasłaniany).
                # Kombinacje: form("Jan") × form("Kowalski") → "Jana Kowalskiego" itd.
                part_forms = []
                for part in parts:
                    forms = [r[0] for r in morf.generate(part) if r[0]] or [part]
                    part_forms.append(forms)
                MAX_COMBO = 200  # limit — Morfeusz może dać 30+ form na słowo
                count = 0
                for combo in iproduct(*part_forms):
                    all_forms.add(" ".join(combo))
                    count += 1
                    if count >= MAX_COMBO:
                        break

            result[word] = list(all_forms)
        return result

    def _forms_batch_wsl2(self, words: list[str]) -> dict[str, list[str]]:
        """Stdin/stdout JSON — zero interpolacji stringów. [KR2]"""
        payload = json.dumps(words, ensure_ascii=False)
        timeout = max(30, len(words) * 2)
        result = subprocess.run(
            ["wsl", "python3", "-c", _WSL2_SCRIPT],
            input=payload,
            capture_output=True, text=True,
            timeout=timeout,
            encoding="utf-8"
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"WSL2 morfeusz2 błąd (kod {result.returncode}): {result.stderr}"
            )
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"WSL2 zwrócił niepoprawny JSON: {e}")

    def get_base_form(self, word: str) -> str:
        """
        Zwraca formę podstawową (mianownik) jako bezpieczny fallback.
        Pełny tagger morfologiczny: następny sprint.
        """
        forms = self.get_forms(word)
        return forms[0] if forms else word


# ============================================================
# AnonymizerMap
# ============================================================

class AnonymizerMap:
    """
    Zarządza mapą encji klienta: mapa.json + trie.pkl.

    mapa.json:
    {
      "version":      "sha256:...",   ← hash z entities (bez metadanych)
      "trie_version": "sha256:...",   ← ta sama wartość gdy trie zsynchronizowane
      "entities": {
        "P1": {"base": "ABC Sp. z o.o.", "forms": [...]},
        "O1": {"base": "Jan Kowalski",   "forms": [...]},
      }
    }

    Niezmiennik: version == trie_version ↔ trie.pkl jest aktualne.
    Oba hashe liczone przez _hash_entities(entities) — bez cyklicznej zależności. [V4-1]
    """

    def __init__(self, profile_dir: Path, morf_env: MorfEnv):
        self.profile_dir = profile_dir
        self.morf_env    = morf_env
        self.map_path    = profile_dir / "mapa.json"
        self.trie_path   = profile_dir / "trie.pkl"
        self.data: dict  = {"version": "", "trie_version": "", "entities": {}}
        self._counters   = {
            TOKEN_FIRMA: 0, TOKEN_OSOBA: 0,
            TOKEN_NUMER: 0, TOKEN_KWOTA: 0,
            TOKEN_ADRES: 0, TOKEN_EMAIL: 0,
        }
        self._enc_key: bytes = b""
        self._mac_key: bytes = b""
        self._save_lock = __import__("threading").Lock()  # chroni przed race condition
        self._trie_cache = None   # [FIX-B12-CACHE] trie w pamięci — niezależne od dysku
        self._load()

    def _load(self):
        if _CRYPTO_AVAILABLE:
            self._enc_key, self._mac_key = _crypto.get_or_create_keys(self.profile_dir)
            enc_path = _crypto.enc_map_path(self.profile_dir)
            if enc_path.exists():
                try:
                    raw = _crypto.decrypt_map(enc_path.read_bytes(), self._enc_key)
                    self._load_from_dict(raw, verify_macs=True)
                    logger.info(f"Mapa zaszyfrowana: {len(self.data['entities'])} encji")
                    return
                except Exception as e:
                    logger.error(f"Błąd mapa.enc: {e} — próba fallback")
        if self.map_path.exists():
            self.data = json.loads(self.map_path.read_text(encoding="utf-8"))
            self.data.setdefault("trie_version", "")
            self._sync_counters()
            logger.info(f"Mapa plain JSON: {len(self.data['entities'])} encji")
            if _CRYPTO_AVAILABLE:
                self._save()  # migracja do .enc

    def _sync_counters(self):
        for token_id in self.data["entities"]:
            parts = token_id.rsplit("_", 1)
            if len(parts) == 2:
                t_type, t_num_str = parts
                try:
                    t_num = int(t_num_str)
                    if t_type in self._counters:
                        self._counters[t_type] = max(self._counters[t_type], t_num)
                except ValueError:
                    pass

    def _load_from_dict(self, raw: dict, verify_macs: bool = True):
        self.data = raw
        self.data.setdefault("trie_version", "")
        entities = self.data.get("entities", {})
        valid = {}
        for token_id, entity in entities.items():
            if verify_macs and _CRYPTO_AVAILABLE:
                if not _crypto.verify_entry(token_id, entity, self._mac_key):
                    logger.warning(f"MAC niezgodny: {token_id} — wpis odrzucony")
                    continue
                valid[token_id] = _crypto.strip_mac(entity)
            else:
                valid[token_id] = entity
        self.data["entities"] = valid
        self._sync_counters()
        if len(valid) < len(entities):
            logger.error(f"Odrzucono {len(entities)-len(valid)} wpisów (zły MAC)")

    def _save(self, update_trie_version: bool = False):
        with self._save_lock:
            self._save_locked(update_trie_version)

    def _save_locked(self, update_trie_version: bool = False):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        version = _hash_entities(self.data["entities"])
        self.data["version"] = version
        if update_trie_version:
            self.data["trie_version"] = version

        if _CRYPTO_AVAILABLE:
            entities_with_mac = {
                tid: _crypto.add_mac_to_entry(tid, ent, self._mac_key)
                for tid, ent in self.data["entities"].items()
            }
            data_to_save = {**self.data, "entities": entities_with_mac}
            enc_path = _crypto.enc_map_path(self.profile_dir)
            tmp_path = enc_path.with_suffix(".tmp")
            tmp_path.write_bytes(_crypto.encrypt_map(data_to_save, self._enc_key))
            shutil.move(str(tmp_path), str(enc_path))
            if self.map_path.exists():
                self.map_path.unlink()
            logger.debug(f"Mapa .enc zapisana: {version[:16]}…")
        else:
            tmp_path = self.map_path.with_suffix(".tmp")
            content = json.dumps(self.data, ensure_ascii=False, indent=2)
            tmp_path.write_text(content, encoding="utf-8")
            verify = json.loads(tmp_path.read_text(encoding="utf-8"))
            if verify != self.data:
                tmp_path.unlink(missing_ok=True)
                raise IOError("Atomowy zapis: weryfikacja nieudana")
            shutil.move(str(tmp_path), str(self.map_path))
            logger.debug(f"Mapa JSON zapisana: {version[:16]}…")

    # --- API encji ---

    def add_entity(self, name: str, token_type: str) -> str:
        """
        Dodaje encję. Idempotentne. Waliduje niepustą nazwę po normalizacji. [V3-7]
        """
        if token_type not in self._counters:
            raise ValueError(f"Nieznany typ tokenu: {token_type}")

        norm_name = _normalize(name)
        if not norm_name.strip():
            raise ValueError(
                f"Nazwa '{name}' jest pusta po normalizacji."
            )

        for token_id, entity in self.data["entities"].items():
            if _normalize(entity["base"]) == norm_name:
                return token_id

        self._counters[token_type] += 1
        token_id = f"{token_type}_{self._counters[token_type]:03d}"
        forms_map = self.morf_env.get_forms_batch([name])
        forms = forms_map.get(name, [name])
        all_forms = list(dict.fromkeys([name] + forms))

        self.data["entities"][token_id] = {"base": name, "forms": all_forms}
        self._save()
        self._rebuild_trie()
        logger.info(f"Dodano encję: {token_id} ({len(all_forms)} form)")
        return token_id

    def add_entities_batch(self, entries: list[tuple[str, str]]) -> dict[str, str]:
        """
        Wsadowe dodawanie encji. Transakcyjne — albo wszystkie albo rollback. [KR6]
        """
        if len(entries) > MAX_ONBOARD_BATCH:
            raise ValueError(
                f"Maksymalnie {MAX_ONBOARD_BATCH} encji naraz "
                f"(podano {len(entries)})."
            )

        for name, _ in entries:
            if not _normalize(name).strip():
                raise ValueError(f"Nazwa '{name}' jest pusta po normalizacji.")

        new_entries = []
        result = {}
        for name, token_type in entries:
            norm = _normalize(name)
            existing = next(
                (tid for tid, e in self.data["entities"].items()
                 if _normalize(e["base"]) == norm),
                None
            )
            if existing:
                result[name] = existing
            else:
                new_entries.append((name, token_type))

        if not new_entries:
            return result

        words = [name for name, _ in new_entries]
        forms_map = self.morf_env.get_forms_batch(words)

        backup_data     = copy.deepcopy(self.data)
        backup_counters = dict(self._counters)

        try:
            for name, token_type in new_entries:
                if token_type not in self._counters:
                    raise ValueError(f"Nieznany typ tokenu: {token_type}")
                self._counters[token_type] += 1
                token_id = f"{token_type}_{self._counters[token_type]:03d}"
                forms = forms_map.get(name, [name])
                all_forms = list(dict.fromkeys([name] + forms))
                self.data["entities"][token_id] = {
                    "base": name, "forms": all_forms
                }
                result[name] = token_id
                logger.info(
                    f"Dodano encję (batch): {token_id} "
                    f"({len(all_forms)} form)"
                )

            self._save()
            self._rebuild_trie()

        except Exception:
            self.data      = backup_data
            self._counters = backup_counters
            raise

        return result

    def get_base(self, token_id: str) -> Optional[str]:
        entity = self.data["entities"].get(token_id)
        return entity["base"] if entity else None

    def get_forms(self, token_id: str) -> list[str]:
        entity = self.data["entities"].get(token_id)
        return entity["forms"] if entity else []

    def get_entity_names(self) -> set[str]:
        return {e["base"] for e in self.data["entities"].values()}

    @property
    def version(self) -> str:
        return self.data.get("version", "")

    @property
    def trie_version(self) -> str:
        return self.data.get("trie_version", "")

    # --- Trie ---

    def _rebuild_trie(self):
        """
        Buduje trie i zapisuje mapę z update_trie_version=True — jeden zapis. [V4-1]
        Eliminuje podwójny zapis i cykliczny hash z v3.
        """
        try:
            import ahocorasick
            A = ahocorasick.Automaton()
            for token_id, entity in self.data["entities"].items():
                entity_name   = entity["base"]
                is_multiword  = " " in entity_name
                for form in entity["forms"]:
                    # [FIX-B12-TRIE] Jednowyrazowe formy wielowyrazowych encji pomijamy
                    # w trie. FIX-B12 w _forms_batch blokuje generowanie atomów dla
                    # nowych encji, ale stare dane w .enc (sprzed fixa) mogły zawierać
                    # atomy. Filtr tutaj jest niezależny od historii danych — działa też
                    # retroaktywnie na istniejące encje w mapie.
                    # Przykład: "Jan Kowalski" → "Jan" samodzielnie w trie → false positive
                    # na "Jan III Sobieski". Po fiksie: tylko "Jan Kowalski", "Jana
                    # Kowalskiego" itd. (formy wielowyrazowe) trafiają do trie.
                    if is_multiword and " " not in form:
                        continue
                    key = _normalize(form)
                    if not key.strip():
                        continue
                    if key in A:
                        existing_tid, existing_form = A.get(key)
                        if len(form) > len(existing_form):
                            A.add_word(key, (token_id, form))
                    else:
                        A.add_word(key, (token_id, form))
            A.make_automaton()

            # [FIX-B12-CACHE] Zachowaj w pamięci ZANIM spróbujemy zapisać na dysk.
            # Jeśli zapis się nie powiedzie (Permission Denied w testach, read-only FS),
            # load_trie() wróci ten obiekt z pamięci — stary trie.pkl nie nadpisze fixa.
            self._trie_cache = A

            try:
                tmp = self.trie_path.with_suffix(".tmp")
                with open(tmp, "wb") as f:
                    pickle.dump(A, f)
                shutil.move(str(tmp), str(self.trie_path))
                # Jeden zapis: version + trie_version razem [V4-1]
                self._save(update_trie_version=True)
            except Exception as e:
                logger.warning(
                    f"Nie można zapisać trie.pkl: {e} — trie aktywne tylko w pamięci."
                )

            logger.info(
                f"Trie przebudowane: {len(self.data['entities'])} encji"
            )
        except ImportError:
            logger.warning("pyahocorasick niedostępny — trie nie zbudowane")

    def load_trie(self):
        """
        Ładuje trie. Jeśli trie_version ≠ version → rebuild. [V3-9]
        Dzięki [V4-1] obie wartości są zawsze spójne po normalnym zapisie —
        rebuild potrzebny tylko przy przerwaniu procesu między zapisami.

        [FIX-B12-CACHE v4.9] Cache w pamięci ma priorytet nad plikiem na dysku.
        [FIX-B12-INIT  v4.10] Jeśli cache jest pusty (nowa sesja, add_entity nie
        było wywoływane bo encja już była w mapie), zawsze buildujemy trie od nowa
        z entities z pamięci — nie ładujemy z trie.pkl.
        Powód: trie.pkl mógł być zbudowany przed FIX-B12-TRIE i zawierać atomy
        (np. "Jan" z "Jan Kowalski"). Rebuild jest tani (~100ms) i gwarantuje
        że FIX-B12-TRIE zawsze obowiązuje, niezależnie od historii danych.
        """
        if self.trie_version != self.version and self.version:
            logger.warning(
                "Trie nieaktualne (trie_version ≠ version) — rebuilduję."
            )
            self._rebuild_trie()

        # Cache w pamięci — zawsze aktualny, ustawiany przez _rebuild_trie.
        if self._trie_cache is not None:
            return self._trie_cache

        # Cache pusty → budujemy od nowa z entities (nie ładujemy trie.pkl).
        # Gwarantuje że filtry z bieżącego kodu (FIX-B12-TRIE) zawsze działają.
        if self.data["entities"]:
            self._rebuild_trie()
            return self._trie_cache

        return None


# ============================================================
# Anonymizer
# ============================================================

class Anonymizer:
    """
    Anonimizuje tekst w dwóch warstwach:
      1. pyahocorasick longest-match (encje z mapy klienta)
      2. Regex strukturalny (NIP, PESEL, IBAN, kwoty, emaile, telefony)

    Trie ładowane per wywołanie — zawsze aktualne. [KR3]
    """

    def __init__(self, anon_map: AnonymizerMap):
        self.anon_map = anon_map

    def anonymize_with_ner(self, text: str, ner_results: list) -> tuple[str, dict[str, str]]:
        """Rejestruje encje NER w mapie, potem wywołuje anonymize()."""
        if ner_results:
            known_lower = {n.lower() for n in self.anon_map.get_entity_names()}
            to_add: list[tuple[str, str]] = []
            seen: set[str] = set()
            for ner in ner_results:
                nl = ner.text.lower()
                if nl in known_lower or nl in seen:
                    continue
                seen.add(nl)
                if ner.label == "FIRMA":
                    to_add.append((ner.text, TOKEN_FIRMA))
                elif ner.label == "OSOBA":
                    to_add.append((ner.text, TOKEN_OSOBA))
                elif ner.label == "ADRES":
                    to_add.append((ner.text, TOKEN_ADRES))
            if to_add:
                try:
                    self.anon_map.add_entities_batch(to_add)
                except Exception as e:
                    logger.error(f"anonymize_with_ner: onboarding błąd: {e}")
        return self.anonymize(text)

    def anonymize(self, text: str, known_tokens: frozenset = frozenset(), existing_reverse_map: dict | None = None, skip_guard: bool = False) -> tuple[str, dict[str, str]]:
        """
        Zwraca (tekst_zanonimizowany, mapa_odwrotna).
        mapa_odwrotna: {token_id: oryginalne_pierwsze_wystąpienie}

        known_tokens — tokeny wstawione przez własny pipeline przed wywołaniem
        (np. NUMER_001 z _ID_CARD_RE, ADRES_001 z _ADDR_RE). Guard injection
        rzuca tylko dla tokenów spoza tego zbioru.
        skip_guard — pomiń sprawdzenie injection (gdy API już zweryfikowało wejście).
        """
        if len(text.encode("utf-8")) > INPUT_LIMIT_BYTES:
            raise ValueError(
                f"Tekst przekracza limit {INPUT_LIMIT_BYTES // 1000} KB. "
                "Podziel dokument na mniejsze fragmenty."
            )

        # [BUG-3] Token injection — odrzuć tekst zawierający ZEWNĘTRZNE tokeny maskujące.
        # [BUG-PIPELINE-GUARD] Tokeny wstawione przez własny pipeline (known_tokens)
        # są legalne — guard rzuca tylko dla tokenów spoza known_tokens.
        # skip_guard=True gdy walidacja wykonana na poziomie API (pseudominizer_api [AUD-01]).
        if not skip_guard and TOKEN_SPAN_RE.search(text):
            found = set(TOKEN_SPAN_RE.findall(text))
            external = found - known_tokens
            if external:
                raise ValueError(
                    "Tekst wejściowy zawiera tokeny maskujące. "
                    "Wyczyść tekst przed pseudonimizacją."
                )

        reverse_map: dict[str, str] = dict(existing_reverse_map) if existing_reverse_map else {}
        text, reverse_map = self._layer1_trie(text, reverse_map)
        text, reverse_map = self._layer2_regex(text, reverse_map)
        text, reverse_map = self._layer3_postal_addresses(text, reverse_map)
        text, reverse_map = self._layer4_stdnum(text, reverse_map)
        text, reverse_map = self._layer5_phonenumbers(text, reverse_map)

        # Limit unikalnych tokenów w jednym żądaniu [V4-3]
        unique_tokens = {f"{a}_{b}" for a, b in TOKEN_RE.findall(text)}
        if len(unique_tokens) > MAX_TOKENS_PER_REQUEST:
            raise ValueError(
                f"Zbyt wiele unikalnych tokenów ({len(unique_tokens)} > "
                f"{MAX_TOKENS_PER_REQUEST}). "
                "Podziel dokument na mniejsze fragmenty."
            )

        return text, reverse_map

    def _layer4_stdnum(
        self, text: str, reverse_map: dict
    ) -> tuple[str, dict]:
        """
        Warstwa 4: walidacja numerów przez stdnum. [FIX-STDNUM]

        Wyciąga kandydatów numerycznych z tekstu (regex \\d{6,} z separatorami),
        waliduje każdego przez listę walidatorów (IBAN, PESEL, NIP-PL, REGON,
        EDRPOU-UA, RNTRC-UA, VAT-EU). Używa compact() dla normalizacji.

        Nie duplikuje tokenów — pomija kandydatów już zakrytych przez warstwy 1-3.
        Fallback gdy python-stdnum niedostępne.
        """
        if not _STDNUM_VALIDATORS:
            return text, reverse_map

        occupied = list(_token_spans(text))

        # Wyznacz licznik NUMER z reverse_map
        numer_counter = 0
        for tid in reverse_map:
            parts = tid.rsplit("_", 1)
            if len(parts) == 2 and parts[0] == TOKEN_NUMER:
                try:
                    numer_counter = max(numer_counter, int(parts[1]))
                except ValueError:
                    pass

        replacements: list[tuple[int, int, str]] = []  # (start, end, token)

        for m in _STDNUM_CANDIDATE_RE.finditer(text):
            if _overlaps_any(m.start(), m.end(), occupied):
                continue

            raw = m.group(0)
            # Compact: usuń spacje i myślniki dla walidacji
            compact = re.sub(r'[\s\-]', '', raw)

            for label, validator, tok_type in _STDNUM_VALIDATORS:
                try:
                    if validator.is_valid(compact):
                        numer_counter += 1
                        token = f"{TOKEN_NUMER}_{numer_counter:03d}"
                        reverse_map[token] = raw.strip()
                        replacements.append((m.start(), m.end(), token))
                        logger.debug(
                            "[STDNUM-L4] '%s' (%s) -> %s", raw.strip(), label, token
                        )
                        # Dodaj do occupied żeby kolejne walidatory nie duplikowały
                        occupied.append((m.start(), m.end()))
                        break
                except Exception:
                    continue

        # Zastąp od końca
        for start, end, token in sorted(replacements, key=lambda x: x[0], reverse=True):
            text = text[:start] + token + text[end:]

        return text, reverse_map

    def _layer5_phonenumbers(
        self, text: str, reverse_map: dict
    ) -> tuple[str, dict]:
        """
        Warstwa 5: wykrywanie telefonów przez phonenumbers (libphonenumber). [FIX-PHONENUMBERS]

        Używa PhoneNumberMatcher który sam szuka numerów telefonów w tekście
        dla 200+ krajów. Default region PL — rozpoznaje lokalne formaty bez
        prefiksu (+48). Numery z prefiksem krajowym rozpoznawane globalnie.

        Nie duplikuje tokenów — pomija numery już zakryte przez warstwy 1-4.
        Fallback gdy phonenumbers niedostępne.
        """
        if not _PHONENUMBERS_AVAILABLE:
            return text, reverse_map

        import phonenumbers

        occupied = list(_token_spans(text))

        numer_counter = 0
        for tid in reverse_map:
            parts = tid.rsplit("_", 1)
            if len(parts) == 2 and parts[0] == TOKEN_NUMER:
                try:
                    numer_counter = max(numer_counter, int(parts[1]))
                except ValueError:
                    pass

        replacements: list[tuple[int, int, str]] = []

        for m in phonenumbers.PhoneNumberMatcher(text, "PL"):
            if _overlaps_any(m.start, m.end, occupied):
                continue
            if not phonenumbers.is_valid_number(m.number):
                continue

            raw = m.raw_string
            numer_counter += 1
            token = f"{TOKEN_NUMER}_{numer_counter:03d}"
            reverse_map[token] = raw
            replacements.append((m.start, m.end, token))
            occupied.append((m.start, m.end))
            region = phonenumbers.region_code_for_number(m.number)
            logger.debug("[PHONE-L5] len=%d region=%s -> %s", len(raw), region, token)

        for start, end, token in sorted(replacements, key=lambda x: x[0], reverse=True):
            text = text[:start] + token + text[end:]

        return text, reverse_map

    def _layer3_postal_addresses(
        self, text: str, reverse_map: dict
    ) -> tuple[str, dict]:
        """
        Warstwa 3: wykrywanie adresów przez kody pocztowe jako kotwice. [FIX-POSTAL-LIB]

        Dla każdego kodu pocztowego znalezionego w tekście (26 krajów EU, ECB regex):
          - Bierze kontekst POSTAL_CONTEXT_BEFORE znaków przed kodem
          - Bierze kontekst POSTAL_CONTEXT_AFTER znaków po kodzie
          - Przycina do najbliższej granicy linii lub tokenu
          - Zastępuje cały span tokenem ADRES_NNN

        Deduplication: ta sama pozycja w tekście obsługiwana tylko raz
        (wiele krajów może matchować ten sam kod — bierzemy pierwsze trafienie).

        Fallback: gdy postal-codes-tools niedostępne (_POSTAL_PATTERNS pusty),
        metoda zwraca tekst bez zmian.
        """
        if not _POSTAL_PATTERNS:
            return text, reverse_map

        # Wyznacz istniejące liczniki ADRES z reverse_map
        adres_counter = 0
        for tid in reverse_map:
            parts = tid.rsplit("_", 1)
            if len(parts) == 2 and parts[0] == TOKEN_ADRES:
                try:
                    adres_counter = max(adres_counter, int(parts[1]))
                except ValueError:
                    pass

        occupied = list(_token_spans(text))
        found_positions: set[int] = set()
        spans: list[tuple[int, int]] = []

        for country, pat in _POSTAL_PATTERNS.items():
            for m in pat.finditer(text):
                pos = m.start()
                if pos in found_positions:
                    continue
                if _overlaps_any(m.start(), m.end(), occupied):
                    continue
                # [FIX-POSTAL-BOUNDARY] Pomiń jeśli kod jest fragmentem dłuższej
                # liczby — np. "123456" daje false positive DE/FR/IT/ES/UA dla
                # "12345". Sprawdź czy bezpośrednio po dopasowaniu jest cyfra.
                if m.end() < len(text) and text[m.end()].isdigit():
                    continue
                if m.start() > 0 and text[m.start() - 1].isdigit():
                    continue
                found_positions.add(pos)

                # Kontekst przed kodem — przytnij do początku linii lub początku tekstu
                raw_start = max(0, m.start() - _POSTAL_CONTEXT_BEFORE)
                # Szukaj początku linii lub granicy tokenu w tym oknie
                segment_before = text[raw_start:m.start()]
                nl_pos = segment_before.rfind('\n')
                if nl_pos >= 0:
                    span_start = raw_start + nl_pos + 1
                else:
                    # Przytnij do początku słowa
                    stripped = segment_before.lstrip()
                    span_start = raw_start + (len(segment_before) - len(stripped))

                # Kontekst po kodzie — przytnij do końca linii lub granicy tokenu
                raw_end = min(len(text), m.end() + _POSTAL_CONTEXT_AFTER)
                segment_after = text[m.end():raw_end]
                nl_pos_after = segment_after.find('\n')
                if nl_pos_after >= 0:
                    span_end = m.end() + nl_pos_after
                else:
                    stripped_after = segment_after.rstrip()
                    span_end = m.end() + len(stripped_after)

                if span_start >= span_end:
                    continue
                spans.append((span_start, span_end))

        # Deduplikuj nakładające się spany — zachowaj najwcześniejszy start
        sorted_spans = sorted(spans, key=lambda x: x[0])
        non_overlapping: list[tuple[int, int]] = []
        last_end = -1
        for start, end in sorted_spans:
            if start >= last_end:
                non_overlapping.append((start, end))
                last_end = end

        # Zastąp od końca (bezpieczne dla offsetów)
        for start, end in sorted(non_overlapping, key=lambda x: x[0], reverse=True):
            addr_text = text[start:end].strip()
            if not addr_text or TOKEN_SPAN_RE.search(addr_text):
                continue
            adres_counter += 1
            token = f"{TOKEN_ADRES}_{adres_counter:03d}"
            reverse_map[token] = addr_text
            text = text[:start] + token + text[end:]
            logger.debug("[POSTAL-L3] len=%d -> %s", len(addr_text), token)

        return text, reverse_map

    def _layer1_trie(
        self, text: str, reverse_map: dict
    ) -> tuple[str, dict]:
        trie = self.anon_map.load_trie()
        if trie is None:
            return text, reverse_map

        # NFKC tylko do wyszukiwania — indeksy na oryginalnym tekście [V3-3]
        norm_text = _normalize(text)
        if len(norm_text) != len(text):
            logger.warning(
                "NFKC zmieniło długość tekstu — fallback do text.lower(). "
                "Formy z combining characters mogą nie zostać dopasowane."
            )
            norm_text = text.lower()

        matches: list[tuple[int, int, str, str]] = []

        for end_idx, (token_id, matched_form) in trie.iter(norm_text):
            start_idx = end_idx - len(matched_form) + 1
            if not self._is_word_boundary(norm_text, start_idx, end_idx + 1):
                continue
            original = text[start_idx:end_idx + 1]
            matches.append((start_idx, end_idx + 1, token_id, original))

        matches = self._resolve_longest_match(matches)
        if not matches:
            return text, reverse_map

        result = list(text)
        for start, end, token_id, original in sorted(matches, reverse=True):
            result[start:end] = list(token_id)
            if token_id not in reverse_map:
                reverse_map[token_id] = original

        return "".join(result), reverse_map

    def _layer2_regex(
        self, text: str, reverse_map: dict
    ) -> tuple[str, dict]:
        """
        Warstwa 2: regex strukturalny. [V3-1][V3-2][V4-2]

        seen_values używa _canonical_value — ten sam NIP w różnych formatach
        dostaje ten sam token_id.
        """
        occupied: list[tuple[int, int]] = _token_spans(text)

        # [FIX-L2-CTR] Poprzednia wersja używała tid[0] (jeden znak np. "N" z "NUMER_001")
        # zamiast tid.rsplit("_",1)[0] (cały typ "NUMER"). Pętla była martwa — nigdy
        # nie aktualizowała liczników z warstwy 1. Dodano TOKEN_ADRES (nowe wzorce adresów).
        counters: dict[str, int] = {TOKEN_NUMER: 0, TOKEN_KWOTA: 0, TOKEN_ADRES: 0, TOKEN_EMAIL: 0}
        for tid in reverse_map:
            parts = tid.rsplit("_", 1)
            if len(parts) == 2 and parts[0] in counters:
                try:
                    counters[parts[0]] = max(counters[parts[0]], int(parts[1]))
                except ValueError:
                    pass

        # [FIX-CTR-SCAN] Inicjalizuj liczniki z tokenów już obecnych w tekście
        # (wstawionych przez pipeline przed wywołaniem anonymize())
        for m in TOKEN_SPAN_RE.finditer(text):
            tid = m.group(0)
            parts = tid.rsplit("_", 1)
            if len(parts) == 2 and parts[0] in counters:
                try:
                    counters[parts[0]] = max(counters[parts[0]], int(parts[1]))
                except ValueError:
                    pass

        # Klucz: (canonical_value, token_type) — różne typy nie kolidują [V4-2]
        seen_values: dict[tuple[str, str], str] = {}

        for token_type, pattern in STRUCTURAL_PATTERNS:
            new_text_parts: list[str] = []
            last_end = 0

            for m in pattern.finditer(text):
                if _overlaps_any(m.start(), m.end(), occupied):
                    continue  # last_end nie zmienia się — tekst nie ginie [V3-2]

                canon = _canonical_value(token_type, m.group(0))
                key   = (canon, token_type)

                if key in seen_values:
                    # Ten sam logiczny numer → ten sam token [V3-1][V4-2]
                    tid = seen_values[key]
                else:
                    counters[token_type] += 1
                    tid = f"{token_type}_{counters[token_type]:03d}"
                    reverse_map.setdefault(tid, m.group(0))
                    seen_values[key] = tid

                new_text_parts.append(text[last_end:m.start()])
                new_text_parts.append(tid)
                last_end = m.end()

            new_text_parts.append(text[last_end:])
            text = "".join(new_text_parts)

            # Odśwież occupied po każdym patternie [KR4]
            occupied = _token_spans(text)

        return text, reverse_map

    @staticmethod
    def _is_word_boundary(text: str, start: int, end: int) -> bool:
        before_ok = start == 0 or not text[start - 1].isalnum()
        after_ok  = end >= len(text) or not text[end].isalnum()
        return before_ok and after_ok

    @staticmethod
    def _resolve_longest_match(
        matches: list[tuple[int, int, str, str]]
    ) -> list[tuple[int, int, str, str]]:
        """Longest-match: sortowanie globalne po długości malejąco. [W1]"""
        if not matches:
            return matches
        matches.sort(key=lambda x: -(x[1] - x[0]))
        result:   list[tuple[int, int, str, str]] = []
        occupied: list[tuple[int, int]]           = []
        for m in matches:
            if not _overlaps_any(m[0], m[1], occupied):
                result.append(m)
                occupied.append((m[0], m[1]))
        return result


# ============================================================
# Deanonymizer
# ============================================================

class Deanonymizer:
    """
    Odtwarza tekst z tokenów.
    Token nieznany → ERR_TOKENS. Nigdy auto-naprawa.
    """

    def __init__(self, anon_map: AnonymizerMap, morf_env: MorfEnv):
        self.anon_map = anon_map
        self.morf_env = morf_env

    def deanonymize(
        self, text: str, reverse_map: Optional[dict[str, str]] = None
    ) -> str:
        """
        Zastępuje ⟦X{n}⟧ oryginalnymi wartościami.
        Priorytet: reverse_map (runtime) → mapa klienta (base form) → ERR_TOKENS.
        """
        def replace_token(m: re.Match) -> str:
            token_id = f"{m.group(1)}_{m.group(2)}"

            # Tylko tokeny z bieżącej sesji (reverse_map) mogą być deanonimizowane.
            # Fallback do anon_map celowo usunięty — zapobiega atakowi FIRMA_001
            # gdzie wstrzyknięty token ujawniałby dane z mapy klienta.
            if reverse_map and token_id in reverse_map:
                return reverse_map[token_id]

            raise ERR_TOKENS(
                f"Token {token_id} nieznany lub spoza bieżącej sesji. Pipeline zablokowany."
            )

        return TOKEN_RE.sub(replace_token, text)

    def validate_tokens(
        self, text_before: str, text_after: str
    ) -> tuple[bool, list[str]]:
        """
        Porównuje tokeny wejście vs wyjście przez Counter. [W3]
        Nie wykrywa zamiany ról P1↔P2 — to zadanie post-walidacji relacyjnej.
        """
        def extract_counter(t: str) -> Counter:
            return Counter(f"{a}_{b}" for a, b in TOKEN_RE.findall(t))

        cnt_in  = extract_counter(text_before)
        cnt_out = extract_counter(text_after)
        problems = []

        for tid in sorted(set(cnt_in) | set(cnt_out)):
            n_in  = cnt_in.get(tid, 0)
            n_out = cnt_out.get(tid, 0)
            if n_in > n_out:
                problems.append(f"BRAKUJĄCY: {tid} ({n_in}→{n_out})")
            elif n_out > n_in:
                problems.append(f"NADMIAROWY: {tid} ({n_in}→{n_out})")

        return len(problems) == 0, problems


# ============================================================
# check_blacklist_context
# ============================================================

def check_blacklist_context(
    text: str,
    anon_map: AnonymizerMap,
    window: int = 5,
    known_plain: list[str] | None = None,
) -> list[str]:
    """
    Trzy ścieżki detekcji plain text encji w odpowiedzi modelu. [W4][V3-8][G3-4]

    1. KONTEKSTOWA: plain text w oknie ±5 słów od tokenu strukturalnego (v7)
    2. GLOBALNA: plain text + token tej samej encji, odległość > 3 słów
       (≤3 słów = legalne cytowanie w nawiasie, pominięte)
    3. GLOBALNY_PLAIN [G3-4]: surowe nazwy z known_plain obecne w tekście,
       niezależnie od mapy tokenów. Wykrywa encje nierozpoznane przez SpaCy
       (brak tokenu → brak w mapie → ścieżki 1 i 2 ślepe).

    Wyniki deduplikowane i posortowane.
    """
    raw_words = text.split()
    words     = [_normalize(_strip_punct(w)) for w in raw_words]

    structural_positions = [
        i for i, w in enumerate(raw_words)
        if TOKEN_RE.search(w)
    ]

    tokens_in_text = {f"{a}{b}" for a, b in TOKEN_RE.findall(text)}
    violations: set[str] = set()

    for token_id, entity in anon_map.data["entities"].items():
        for form in entity["forms"]:
            form_words = _normalize(form).split()
            if not form_words:
                continue

            # Pomiń formy zbyt krótkie — eliminuje false positives na przyimkach
            # ("z", "w", "i") które są formami składowych encji wielowyrazowych. [FIX-CBC-1]
            if sum(len(w) for w in form_words) < 4:
                continue
            # Pomiń formy złożone wyłącznie z jednosylabowych słów — zbyt ogólne. [FIX-CBC-2]
            if all(len(w) < 3 for w in form_words):
                continue

            for i in range(len(words) - len(form_words) + 1):
                if words[i:i + len(form_words)] != form_words:
                    continue

                # Ścieżka 1
                for sp in structural_positions:
                    if abs(i - sp) <= window:
                        violations.add(
                            f"[KONTEKST] Plain text '{form}' ({token_id}) "
                            f"w oknie ±{window} słów od tokenu strukturalnego"
                        )
                        break

                # Ścieżka 2
                if token_id in tokens_in_text:
                    token_positions = [
                        j for j, w in enumerate(raw_words)
                        if f"⟦{token_id}⟧" in w
                    ]
                    too_close = any(abs(i - tp) <= 3 for tp in token_positions)
                    if not too_close:
                        violations.add(
                            f"[GLOBALNY] Plain text '{form}' ({token_id}) "
                            f"razem z ⟦{token_id}⟧ (odl. > 3 słów — możliwy wyciek)"
                        )

    # Ścieżka 3: GLOBALNY_PLAIN [G3-4]
    # Surowe nazwy z reverse_map sesji — niezależne od mapy tokenów.
    # Encja której SpaCy nie wykryło → brak tokenu → brak w entities →
    # ścieżki 1 i 2 ślepe → ta ścieżka to jedyna siatka bezpieczeństwa.
    if known_plain:
        text_lower = text.lower()
        for name in known_plain:
            if not name or len(name.strip()) < 4:
                continue  # pomiń zbyt krótkie (spójność z FIX-CBC-1)
            if name.lower() in text_lower:
                violations.add(
                    f"[GLOBALNY_PLAIN] Plain text '{name}' — "
                    f"encja z reverse_map sesji obecna w odpowiedzi modelu"
                )

    return sorted(violations)


# ============================================================
# Onboarding
# ============================================================

def onboard_entity(
    anon_map: AnonymizerMap,
    name: str,
    token_type: str,
    confirm_callback=None
) -> str:
    """
    Onboarding pojedynczej encji.
    confirm_callback(name, forms) → bool  (None = auto w testach)
    """
    forms_map = anon_map.morf_env.get_forms_batch([name])
    forms     = forms_map.get(name, [name])
    all_forms = list(dict.fromkeys([name] + forms))

    if confirm_callback is not None:
        if not confirm_callback(name, all_forms):
            raise ValueError(f"Analityk odrzucił formy dla '{name}'")

    return anon_map.add_entity(name, token_type)


def onboard_entities_batch(
    anon_map: AnonymizerMap,
    entries: list[tuple[str, str]],
    confirm_callback=None
) -> dict[str, str]:
    """
    Wsadowy onboarding. Jedno wywołanie Morfeusza. Transakcyjny. [KR6]
    """
    if len(entries) > MAX_ONBOARD_BATCH:
        raise ValueError(
            f"Maksymalnie {MAX_ONBOARD_BATCH} encji naraz "
            f"(podano {len(entries)})."
        )

    words     = [name for name, _ in entries]
    forms_map = anon_map.morf_env.get_forms_batch(words)

    entries_with_forms = [
        (name, tt, list(dict.fromkeys([name] + forms_map.get(name, [name]))))
        for name, tt in entries
    ]

    if confirm_callback is not None:
        if not confirm_callback(entries_with_forms):
            raise ValueError("Analityk odrzucił wsadowy onboarding")

    batch = [(name, tt) for name, tt, _ in entries_with_forms]
    return anon_map.add_entities_batch(batch)


# ============================================================
# Factory
# ============================================================

def build_anonymizer(
    profile_dir: str | Path,
    hardware_profile: str | Path = "hardware_profile.json"
) -> tuple[Anonymizer, Deanonymizer, AnonymizerMap, MorfEnv]:
    """
    Buduje komplet obiektów.
    Gdy Morfeusz2 niedostępny — działa w trybie degraded (SpaCy + regex, bez form fleksyjnych).
    """
    profile_dir = Path(profile_dir)
    hw_path     = Path(hardware_profile)
    morf_env    = MorfEnv(hw_path)

    if morf_env.mode == MorfEnv.BLOCKED:
        logger.warning(
            "Morfeusz2 niedostępny — tryb degraded: SpaCy + regex, bez form fleksyjnych. "
            "Anonimizacja działa, ale nie wykryje odmian gramatycznych nazw."
        )

    anon_map     = AnonymizerMap(profile_dir, morf_env)
    anonymizer   = Anonymizer(anon_map)
    deanonymizer = Deanonymizer(anon_map, morf_env)

    return anonymizer, deanonymizer, anon_map, morf_env