"""
verbal_amounts.py  v1.4
Maskowanie kwot zapisanych słownie.
Wydzielony z pseudominizer_api.py v1.18.

Historia zmian:
  v1.3 — [AUD-03] _TOKEN_RE rozszerzony o INSTYTUCJA i EMAIL (linia 45).
          Tokeny INSTYTUCJA_NNN i EMAIL_NNN nie będą nigdy traktowane jako
          kwoty słowne. Spójność z TOKEN_RE w pipeline.py, pseudominizer_api.py
          i output_guard.py.
  v1.2 — [BUG-7] Dodanie obsługi cyfr arabskich w pętli grosze_indices.
          Fraza "i 78 groszy" nie była maskowana bo "78" nie należy do
          _PL_NUMBER_WORDS. Warunek w pętli rozszerzony o clean_w.isdigit().
          Linia dotknięta: ~172.
          DIAGNOZA BUG-7:
          1. Funkcja obsługuje grosze przez blok else po frac_m — skanuje
             rest tekstu i szuka liczebników + kotwicy walutowej. Problem:
             cyfry arabskie (np. "78") nie były w _PL_NUMBER_WORDS — pętla
             zbierająca grosze_indices przerywała na cyfrze.
          2. _PL_NUMBER_WORDS nie zawiera "groszy" ani wariantów — poprawnie,
             bo grosze są kotwicą walutową w _CURRENCY_RE (grosz\\w+|grosza|groszy).
          3. Skanowanie wsteczne od kotwicy walutowej obsługuje "i X groszy"
             tylko jeśli X jest słowem liczebnikowym. Cyfra arabska nie była
             obsługiwana — naprawiono.
  v1.1 — [FIX-SPAN-START] Obliczanie span_start przez re.finditer zamiast
          rekonstrukcji stringa. Oryginał używał ' '.join(words) co normalizowało
          wielokrotne spacje i dawało błędny offset. Teraz pozycja pochodzi
          wprost z indeksu znaków w oryginalnym tekście.
          [FIX-DEAD-CODE] Usunięto _SLOWNIE_RE — zdefiniowany w oryginale,
          nigdy nie wywoływany. Przypadek 'Słownie: sto złotych' działa
          bez niego (skaner wstecz zatrzymuje się naturalnie na 'Słownie:').
  v1.0 — wydzielenie z pseudominizer_api.py v1.18.

Przeniesione fixy (zachowane bez zmian):
  [FIX-FRACTION-CURRENCY] _FRACTION_RE pochłania opcjonalną walutę po ułamku.
  [FIX-VERBAL-PLN]        PLN/EUR/USD/GBP jako kotwice walutowe w _CURRENCY_RE.

API publiczne:
  mask_verbal_amounts(text, reverse_map, kwota_counter) -> tuple[str, dict]

Zależności: re, logging (stdlib only).
"""

import re
import logging

logger = logging.getLogger("pseudominizer.verbal_amounts")

_TOKEN_RE = re.compile(r"\b(FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}\b")

# ── Stałe ─────────────────────────────────────────────────────────────────────

_PL_NUMBER_WORDS: frozenset[str] = frozenset({
    "zero",
    "jeden", "jedna", "jedno", "jednego", "jednej", "jednemu",
    "dwa", "dwie", "dwóch", "dwu", "dwóm",
    "trzy", "trzech", "trzem",
    "cztery", "czterech", "czterem",
    "pięć", "pięciu",
    "sześć", "sześciu",
    "siedem", "siedmiu",
    "osiem", "ośmiu",
    "dziewięć", "dziewięciu",
    "dziesięć", "dziesięciu",
    "jedenaście", "jedenastu",
    "dwanaście", "dwunastu",
    "trzynaście", "trzynastu",
    "czternaście", "czternastu",
    "piętnaście", "piętnastu",
    "szesnaście", "szesnastu",
    "siedemnaście", "siedemnastu",
    "osiemnaście", "osiemnastu",
    "dziewiętnaście", "dziewiętnastu",
    "dwadzieścia", "dwudziestu",
    "trzydzieści", "trzydziestu",
    "czterdzieści", "czterdziestu",
    "pięćdziesiąt", "pięćdziesięciu",
    "sześćdziesiąt", "sześćdziesięciu",
    "siedemdziesiąt", "siedemdziesięciu",
    "osiemdziesiąt", "osiemdziesięciu",
    "dziewięćdziesiąt", "dziewięćdziesięciu",
    "sto", "stu",
    "dwieście", "dwustu",
    "trzysta", "trzystu",
    "czterysta", "czterystu",
    "pięćset", "pięciuset",
    "sześćset", "sześciuset",
    "siedemset", "siedmiuset",
    "osiemset", "ośmiuset",
    "dziewięćset", "dziewięciuset",
    "tysiąc", "tysiące", "tysięcy", "tysiąca",
    "milion", "miliony", "milionów", "miliona",
    "miliard", "miliardy", "miliardów", "miliarda",
    "i",
    # [v1.4] Formy OCR bez polskich znaków diakrytycznych
    "tysiac", "tysiace", "tysiecy",
    "milionow", "miliardow",
    "pieciuset", "szesciuset", "siedmiuset", "osmiuset", "dziewieciuset",
    "piecdziesieciu", "szescdziesieciu", "siedemdziesieciu",
    "osiemdziesieciu", "dziewiecdziesieciu",
    "trzydziestu", "czterdziestu",
    "jedenastu", "dwunastu", "trzynastu", "czternastu", "pietnastu",
    "szesnastu", "siedemnastu", "osiemnastu", "dziewiętnastu", "dziewiętnastu",
    "dwudziestu",
    "pieciu", "szesciu", "siedmiu", "osmiu", "dziewieciu", "dziesieciu",
    "dwoch", "trzech",
})

_CURRENCY_RE = re.compile(
    r"\b(z[łl]ot\w+|grosz\w+|grosza|groszy|euro|cent\w+|PLN|EUR|USD|GBP)\b",
    re.IGNORECASE,
)

_FRACTION_RE = re.compile(
    r"\s+\d{1,2}/100(?:\s+(?:PLN|EUR|USD|GBP|zł))?",
    re.IGNORECASE,
)


# ── API publiczne ─────────────────────────────────────────────────────────────

def mask_verbal_amounts(
    text: str,
    reverse_map: dict,
    kwota_counter: list,
) -> tuple[str, dict]:
    """
    Maskuje kwoty zapisane słownie w tekście.
    Zwraca (tekst_z_tokenami, reverse_map).
    Przy błędzie zwraca (oryginalny_tekst, reverse_map) bez rzucania wyjątku.
    """
    try:
        return _mask_verbal_amounts(text, reverse_map, kwota_counter)
    except Exception as e:
        logger.error("[VERBAL-AMT] Nieoczekiwany błąd: %s", e)
        return text, reverse_map


# ── Implementacja ─────────────────────────────────────────────────────────────

def _mask_verbal_amounts(
    text: str,
    reverse_map: dict,
    kwota_counter: list,
) -> tuple[str, dict]:
    """
    Maskuje kwoty zapisane słownie w tekście.

    Dla każdej kotwicy walutowej skanuje wstecz zbierając polskie liczebniki.
    Pozycje znaków pochodzą z re.finditer — odporne na wielokrotne spacje.
    Zastępowanie od prawej do lewej — offsety lewostronne pozostają nienaruszone.
    """
    spans: list[tuple[int, int]] = []

    for m in _CURRENCY_RE.finditer(text):
        anchor_start = m.start()
        anchor_end   = m.end()

        pre = text[max(0, anchor_start - 20):anchor_start]
        if _TOKEN_RE.search(pre):
            continue

        before = text[:anchor_start].rstrip()

        # Indeks pozycji słów — zachowuje oryginalne offsety znaków
        word_positions = [
            (wm.start(), wm.end(), wm.group())
            for wm in re.finditer(r"\S+", before)
        ]

        collected_indices: list[int] = []
        for i in range(len(word_positions) - 1, -1, -1):
            clean_w = word_positions[i][2].strip(",:;()").lower()
            if clean_w in _PL_NUMBER_WORDS:
                collected_indices.append(i)
            else:
                break

        if not collected_indices:
            continue

        collected_indices.reverse()
        span_start = word_positions[collected_indices[0]][0]
        span_end   = anchor_end

        # Opcjonalnie: ułamek "99/100" bezpośrednio po kotwicy
        frac_m = _FRACTION_RE.match(text, span_end)
        if frac_m:
            span_end = frac_m.end()
        else:
            # Opcjonalnie: część groszowa — liczebniki + kotwica walutowa
            rest = text[span_end:]
            rest_stripped = rest.lstrip(" ,i")
            offset = len(rest) - len(rest_stripped)
            grosze_positions = [
                (wm.start(), wm.end(), wm.group())
                for wm in re.finditer(r"\S+", rest_stripped)
            ]
            grosze_indices: list[int] = []
            for i, (_, _, w) in enumerate(grosze_positions):
                clean_w = w.strip(",:;()").lower()
                # [BUG-7] Cyfry arabskie (np. "78") dopuszczone jako część
                # frazy groszowej — "i 78 groszy" nie przechodziło bo "78"
                # nie jest w _PL_NUMBER_WORDS.
                if clean_w in _PL_NUMBER_WORDS or clean_w.isdigit():
                    grosze_indices.append(i)
                else:
                    break
            if grosze_indices:
                last_g_end = grosze_positions[grosze_indices[-1]][1]
                after_nums = rest_stripped[last_g_end:].lstrip()
                gm = _CURRENCY_RE.match(after_nums)
                if gm:
                    gap = len(rest_stripped[last_g_end:]) - len(after_nums)
                    span_end = span_end + offset + last_g_end + gap + gm.end()
                    frac2 = _FRACTION_RE.match(text, span_end)
                    if frac2:
                        span_end = frac2.end()

        spans.append((span_start, span_end))

    if not spans:
        return text, reverse_map

    # Filtruj nakładające się spany
    sorted_spans = sorted(spans, key=lambda x: x[0])
    non_overlapping: list[tuple[int, int]] = []
    last_end = -1
    for start, end in sorted_spans:
        if start >= last_end:
            non_overlapping.append((start, end))
            last_end = end

    for start, end in sorted(non_overlapping, key=lambda x: x[0], reverse=True):
        verbal = text[start:end].strip()
        if not verbal or _TOKEN_RE.search(verbal):
            continue

        existing = next(
            (tok for tok, val in reverse_map.items()
             if tok.startswith("KWOTA_") and val == verbal),
            None,
        )
        if existing:
            token = existing
        else:
            kwota_counter[0] += 1
            token = f"KWOTA_{kwota_counter[0]:03d}"
            reverse_map[token] = verbal

        text = text[:start] + token + text[end:]
        logger.debug("[VERBAL-AMT] '%s' -> %s", verbal, token)

    return text, reverse_map
