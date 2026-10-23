"""
guard_residue.py — [LYNX-GUARD-A] lista ostrzeżeń Guarda zamiast automatycznego [REDACTED] (S4 22.10).

Guard wskazuje JAWNE fragmenty finalnego tekstu, każdy do decyzji użytkownika (Zakryj/Zostaw). Nic tu nie maskuje.
Źródła: dotychczasowe wzorce HIGH/MEDIUM i MAP_LEAK (`output_guard`) + grupy pozostałości R1–R5 (brief v2):
R1 słowa nieopisane przez nikogo (`guard_unknown`), R2 inicjały, R3 resztki przy tokenach, R4 identyfikatory w kontekście,
R5 nazwy firm. [LYNX-OSOBA-LAYOUT] Guard nie zgaduje osób w całym tekście: słowa znane Morfeuszowi i decyzje silnika są dla niego
niewidzialne (dawne R1 „słownik/końcówka” i kanał `released` usunięte — osobę rozpoznaje silnik, `person_layout`).
Wartości fragmentów trafiają tylko do odpowiedzi dla UI, nigdy do logów (S5).
"""
from __future__ import annotations

import re

from guard_allowlist import ANY_YELLOW, silenced
from guard_allowlist import load as load_allowlist  # noqa: F401  [S5] zaszyfrowana lista (pipeline)
from guard_unknown import unknown_words
from output_guard import _LEAK_HIGH, _LEAK_MEDIUM, _TOKEN_RE

_UP = "A-ZĄĆĘŁŃÓŚŹŻ"
_LO = "a-ząćęłńóśźż"
_PUBLIC_RE = re.compile(  # R5: tylko urzędy/sądy/samorząd/organy — nie „Centrum”, „Instytut”, „Fundusz” (bywają firmami)
    r"\b(?:Sąd\w*|Urz[ąę]d\w*|Gmin\w*|Powiat\w*|Starostw\w*|Województw\w*|Skarb\w* Państwa|Prokuratur\w*|Policj\w*"
    r"|Ministerstw\w*|Komornik\w*|Rad\w* Miasta|Izb\w* Skarbow\w*|ZUS|NFZ|KRUS|GUS|NIK|UODO|KNF|UOKiK)\b")
# R2: imię albo token osoby + jedna wielka litera z kropką (bez „S.A.”)
_INITIAL_RE = re.compile(rf"\b(?:(OSOBA_\d{{3}})|([{_UP}][{_LO}]+))[ \t]+([{_UP}])\.(?![ \t]?[A-Za-z]\.)")
# R3: cyfry tuż przed/po tokenie NUMER/ADRES, kod pocztowy (+ miejscowość) po ADRES, litery doklejone do tokenu
_DIGITS_BEFORE_RE = re.compile(r"(?<![\w/.-])(\d[\d \-]{0,10}?)[ \t]?$")
_DIGITS_AFTER_RE = re.compile(r"[ \t]?(\d[\d\-]*(?:[ \t]\d+)?)(?![\w/])")
# [LYNX-OSOBA-PACK4] miejscowość tuż po zakrytym adresie („ADRES_003, Ostrów Wielkopolski”) — część adresu, nie „samo miasto”
_CITY_AFTER_RE = re.compile(rf",[ \t]+([{_UP}][{_LO}]+(?:[ \t-][{_UP}][{_LO}]+){{0,2}})(?![\w-])")
_POSTAL_AFTER_RE = re.compile(rf",?[ \t]+(\d\d[ \t]?-[ \t]?\d(?:[ \t]?\d){{2}}(?:[ \t]+[{_UP}][\w-]+)?)")
_GLUED_RE = re.compile(r"([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,})")
# R4: słowo-klucz + wartość z co najmniej dwiema cyframi
_ID_KEY_RE = re.compile(
    r"\b(?:nr|numer\w*|działk\w*|klient\w*|kont[ao]|rachunk\w*|ur\.|urodz\w*|tel\.|telefon\w*|kom\.|PESEL|NIP|REGON|KRS"
    r"|dowod\w*|paszport\w*|legitymacj\w*|KW|księg\w* wieczyst\w*)(?![\w])[ \t]*[.:#]?[ \t]*", re.IGNORECASE)
_ID_VALUE_RE = re.compile(r"[A-Z0-9][A-Z0-9/.\-]*[A-Z0-9]|\d")
_DZU_RE = re.compile(r"Dz\.\s?U|poz\.|art\.|ust\.|§", re.IGNORECASE)
# R5: rola kontrahenta + nazwa; nazwa z formą prawną
_ROLE_RE = re.compile(
    r"\b(?:Sprzedawc\w*|Nabywc\w*|Kontrahent\w*|Usługodawc\w*|Zleceniobiorc\w*|Zleceniodawc\w*|Wykonawc\w*|Dostawc\w*"
    r"|Odbiorc\w*|Zamawiając\w*|Najemc\w*|Wynajmując\w*|Pracodawc\w*|Ubezpieczyciel\w*|Płatnik\w*|Firma)[ \t]*:[ \t]*"
    r"([^\r\n,;]{2,80})")
_FORM = r"(?i:sp\.[ \t]*z[ \t]*o\.[ \t]*o\.?|sp\.[ \t]*k\.[ \t]*a\.?|sp\.[ \t]*[jkp]\.?|s\.[ \t]*a\.|s\.[ \t]*c\.|p\.[ \t]*s\.[ \t]*a\.?)"
_LABEL_RE = re.compile(r"[^\W\d_][\w ]{0,30}:")  # etykieta pola: „Nabywca:”, „Dane kontaktowe:”
_SENTENCE_END_RE = re.compile(rf"\.[ \t]+(?=[{_UP}][{_LO}])")
_FORM_NAME_RE = re.compile(
    rf"(?<![\w„\"])[{_UP}0-9„\"][\w„\"&.\-]*(?:[ \t]+[{_UP}0-9„\"&][\w„\"&.\-]*){{0,4}}[ \t]+{_FORM}(?!\w)")

_morf = None


def _morf_interps(word: str) -> list | None:
    global _morf
    try:
        if _morf is None:
            import morfeusz2
            _morf = morfeusz2.Morfeusz()
        return _morf.analyse(word)
    except Exception:
        return None


def _r2(text: str):
    from ner_layer import _PERSON_FORMS
    for m in _INITIAL_RE.finditer(text):
        if m.group(1):
            yield m.start(3), m.end(), "R2", "Inicjał obok zakrytej osoby"
        elif m.group(2).lower() in _PERSON_FORMS:
            yield m.start(), m.end(), "R2", "Imię z inicjałem nazwiska"


def _r3(text: str):
    for t in _TOKEN_RE.finditer(text):
        kind = t.group(0).split("_")[0]
        found = []
        if kind in ("NUMER", "ADRES"):
            lo = max(0, t.start() - 14)
            b = _DIGITS_BEFORE_RE.search(text[lo:t.start()])
            s0 = lo + b.start(1) if b else 0
            if b and not (s0 and text[s0 - 1] in "/.-" or text[max(0, s0 - 6):s0].rstrip().endswith("dnia")
                          or kind == "ADRES" and len(b.group(1).strip()) == 1):  # „4 ADRES_001” = OCR „ul.”
                found.append(((lo + b.start(1), lo + b.end(1)), "Resztka numeru obok zakrytego fragmentu"))
            for rx, reason in ((_DIGITS_AFTER_RE, "Resztka numeru obok zakrytego fragmentu"),
                               (_POSTAL_AFTER_RE, "Kod pocztowy obok zakrytego adresu"),
                               (_CITY_AFTER_RE, "Miejscowość obok zakrytego adresu")):
                a = rx.match(text, t.end())
                if a and (rx is _DIGITS_AFTER_RE or kind == "ADRES"):
                    found.append((a.span(1), reason))
                    if rx is _POSTAL_AFTER_RE:
                        break  # kod z miejscowością już wskazany — bez drugiej pozycji na samą miejscowość
        g = _GLUED_RE.match(text, t.end())
        if g:
            found.append((g.span(1), "Litery doklejone do zakrytego fragmentu"))
        for (s, e), reason in found:
            frag = text[s:e].rstrip(" \t-")
            if frag.strip():
                yield s, s + len(frag), "R3", reason


def _r4(text: str):
    for k in _ID_KEY_RE.finditer(text):
        v = _ID_VALUE_RE.match(text, k.end())
        if not v or sum(c.isdigit() for c in v.group(0)) < 2 or _TOKEN_RE.match(text, v.start()):
            continue
        if _DZU_RE.search(text[max(0, k.start() - 12):k.start()]):
            continue
        yield v.start(), v.end(), "R4", "Numer lub data w kontekście danych identyfikujących"


def _firm_ok(frag: str) -> bool:
    """R5: forma prawna = firma zawsze (Codex F1: „Centrum Projektowe MODRZEW sp. z o.o.”); bez niej wyłączone tylko
    urzędy publiczne („Centrum”, „Instytut”, „Fundusz” bywają firmami)."""
    if not re.search(rf"[{_UP}]", frag):
        return False
    return bool(re.search(_FORM + r"(?!\w)", frag)) or not _PUBLIC_RE.search(frag)


def _r5(text: str):
    for m in _ROLE_RE.finditer(text):
        s, frag = m.start(1), re.split(r"[ \t]{3,}", m.group(1))[0]  # FIX1: układ w dwóch kolumnach — tylko ta kolumna
        if _LABEL_RE.match(frag):
            continue  # FIX1: „Sprzedawca:   Nabywca:” — po etykiecie kolejna etykieta, nie nazwa
        cut = _TOKEN_RE.search(frag)
        frag = frag[:cut.start()] if cut else frag
        end = _SENTENCE_END_RE.search(frag)  # „RACHMISTRZ. Wczoraj…” → bez następnego zdania; „S.A.” zostaje
        if end:
            frag = frag[:end.start() + 1]
        frag = frag if re.search(_FORM + r"$", frag) else frag.rstrip(" \t.-–(")
        if len(frag) >= 3 and frag[0] not in _LO and _firm_ok(frag):
            yield s, s + len(frag), "R5", "Możliwa nazwa firmy, której silnik nie zakrył"
    for m in _FORM_NAME_RE.finditer(text):
        if not _TOKEN_RE.search(m.group(0)) and _firm_ok(m.group(0)):
            yield m.start(), m.end(), "R5", "Nazwa firmy z formą prawną"


def _patterns(masked: str):
    for label, rx in _LEAK_HIGH:
        for m in rx.finditer(masked):
            yield m.start(), m.end(), f"HIGH {label}", "Wygląda na numer identyfikacyjny"
    for label, rx, _w in _LEAK_MEDIUM:
        for m in rx.finditer(masked):
            yield m.start(), m.end(), f"MEDIUM {label}", "Wygląda na numer lub telefon"


def _map_leaks(text: str, values: list[str]):
    for v in values:
        for m in re.finditer(re.escape(v), text, re.IGNORECASE):
            yield m.start(), m.end(), "MAP_LEAK", "Ta wartość jest zakryta w innym miejscu dokumentu"


_RED = ("HIGH", "MAP_LEAK")


def collect_warnings(text: str, map_values: list[str] | None = None, allowlist: list | None = None) -> list[dict]:
    """Ostrzeżenia dla finalnego tekstu: [{id, start, end, fragment, rule, level, reasons}], posortowane po pozycji.
    Fragmenty nachodzące na siebie → jedna pozycja (wszystkie powody); nic wewnątrz tokenów; allowlista (fragment, reguła) wycisza tylko żółte (S5)."""
    tokens = [m.span() for m in _TOKEN_RE.finditer(text)]
    masked = _TOKEN_RE.sub(lambda m: "#" * len(m.group(0)), text)
    allow = [(a, ANY_YELLOW) if isinstance(a, str) else tuple(a) for a in allowlist or []]
    hits = []
    for src in (_patterns(masked), _map_leaks(masked, map_values or []), unknown_words(text, _morf_interps),
                _r2(text), _r3(text), _r4(text), _r5(text)):
        for s, e, rule, reason in src:
            if s < e and not any(ts < e and s < te for ts, te in tokens) and not silenced(text[s:e], rule, allow):
                hits.append((s, e, rule, reason))
    out: list[dict] = []
    for s, e, rule, reason in sorted(hits):
        if out and s < out[-1]["end"]:
            w = out[-1]
            w["end"] = max(w["end"], e)
            w["fragment"] = text[w["start"]:w["end"]]
            if rule not in w["rules"]:
                w["rules"].append(rule)
            if reason not in w["reasons"]:
                w["reasons"].append(reason)
            continue
        out.append({"start": s, "end": e, "fragment": text[s:e], "rules": [rule], "reasons": [reason]})
    for i, w in enumerate(out):
        w["rule"] = w["rules"][0]
        w["level"] = "RED" if any(r.startswith(_RED) for r in w["rules"]) else "YELLOW"
        w["id"] = f"W{i + 1:03d}"
    return out


def shift_warnings(warnings: list[dict], offset: int) -> list[dict]:
    """Pozycje względem tekstu z nagłówkiem PSE (anonymized_preview)."""
    return [{**w, "start": w["start"] + offset, "end": w["end"] + offset} for w in warnings]
