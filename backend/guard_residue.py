"""
guard_residue.py — [LYNX-GUARD-A] lista ostrzeżeń Guarda zamiast automatycznego [REDACTED] (S4 22.10).

Guard wskazuje JAWNE fragmenty finalnego tekstu, każdy do decyzji użytkownika (Zakryj/Zostaw). Nic tu nie maskuje.
Źródła: dotychczasowe wzorce HIGH/MEDIUM i MAP_LEAK (`output_guard`) + grupy pozostałości R1–R5 (brief v2):
R1 nierozpoznane imiona/nazwiska, R2 inicjały, R3 resztki przy tokenach, R4 identyfikatory w kontekście, R5 nazwy firm.
Cel: wiarygodne podejrzenia, nie każde słowo z wielkiej litery (dokumenty biurowe: „Zamawiający”, „Umowa” — bez alarmu).
Wartości fragmentów trafiają tylko do odpowiedzi dla UI, nigdy do logów (S5).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from osoba_not_person import OSOBA_DENYLIST, WHITE_LISTS
from output_guard import _LEAK_HIGH, _LEAK_MEDIUM, _TOKEN_RE

_UP = "A-ZĄĆĘŁŃÓŚŹŻ"
_LO = "a-ząćęłńóśźż"
_WORD_RE = re.compile(rf"(?<![\w-])[{_UP}][{_LO}]{{2,}}(?:-[{_UP}][{_LO}]{{2,}})?(?![\w-])")
_TITLES = {"p", "pan", "pani", "dr", "mgr", "inż", "prof", "hab", "adw", "św"}
_TITLE_BEFORE_RE = re.compile(r"(?:^|[\s(])(?:[Pp]an(?:a|u|em|i|ią)?|[Pp]\.|dr|mgr|inż\.|prof\.|adw\.|mec\.)[ \t]+$")
_OFFICE_TERMS = {"strona", "strony", "stronę", "stron", "stronami", "stronom", "stronie",  # Morfeusz: także nazwisko
                 "pan", "pana", "panu", "panem", "pani", "panią", "państwo", "państwa", "państwu"}
_DEFINED_RE = re.compile(r"zwan\w*[ \t]+(?:dalej[ \t]+)?[„\"]?$", re.IGNORECASE)  # „zwanym dalej Zleceniobiorcą”
# słowo nieznane Morfeuszowi (często szum OCR) — alarm tylko przy końcówce nazwiska
_SURNAME_END_RE = re.compile(r"(?:[scd]k|dzk)(?:i|a|ie|iego|iej|iemu|im|imi|ą|ich)$|[iy]cz(?:a|owi|em|u)?$"
                             r"|(?:czyk|czuk|iak|uk)(?:a|owi|iem|em|u)?$")
_GEO_PREP_RE = re.compile(r"(?:^|\s)(?:w|we|z|ze|do|na|pod|nad|przy|koło|od|dla)\s+$", re.IGNORECASE)
_INSTITUTION_RE = re.compile(
    r"\b(?:Sąd\w*|Urz[ąę]d\w*|Gmin\w*|Powiat\w*|Starostw\w*|Województw\w*|Skarb\w* Państwa|Prokuratur\w*|Policj\w*"
    r"|Ministerstw\w*|Szkoł\w*|Komornik\w*|Rad\w* Miasta|Izb\w*|ZUS|NFZ|KRUS|GUS|NIK|UODO|KNF|UOKiK|Wydział\w*|Oddział\w*"
    r"|Kolegi\w*|Inspektorat\w*|Dyrekcj\w*|Agencj\w*|Fundusz\w*|Rzecznik\w*|Zarząd\w*|Departament\w*|Ośrod\w*|Centrum"
    r"|Instytut\w*|Uniwersytet\w*|Politechnik\w*|Szpital\w*|Przychodni\w*|Przedszkol\w*|Regionaln\w*|Kas\w+)\b")
# słowo w ciągu nazwy instytucji: „Urząd Marszałkowski Województwa Mazowieckiego”, „Urząd Gminy Warszawa-Wola”
_IN_INSTITUTION_RE = re.compile(rf"(?:[ \t\-]+(?:[{_UP}][\w\-]*|w|we|przy|dla|ds\.|i|do|spraw))*[ \t\-]*")
# R2: imię albo token osoby + jedna wielka litera z kropką (bez „S.A.”)
_INITIAL_RE = re.compile(rf"\b(?:(OSOBA_\d{{3}})|([{_UP}][{_LO}]+))[ \t]+([{_UP}])\.(?![ \t]?[A-Za-z]\.)")
# R3: cyfry tuż przed/po tokenie NUMER/ADRES, kod pocztowy (+ miejscowość) po ADRES, litery doklejone do tokenu
_DIGITS_BEFORE_RE = re.compile(r"(?<![\w/.-])(\d[\d \-]{0,10}?)[ \t]?$")
_DIGITS_AFTER_RE = re.compile(r"[ \t]?(\d[\d\-]*(?:[ \t]\d+)?)(?![\w/])")
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
    r"([^\n,;]{2,80})")
_FORM = r"(?i:sp\.[ \t]*z[ \t]*o\.[ \t]*o\.?|sp\.[ \t]*k\.[ \t]*a\.?|sp\.[ \t]*[jkp]\.?|s\.[ \t]*a\.|s\.[ \t]*c\.|p\.[ \t]*s\.[ \t]*a\.?)"
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


def _sentence_start(text: str, start: int) -> bool:
    before = text[:start].rstrip(" \t„\"(")
    if not before or before[-1] in "\n!?:;•–-" or re.search(r"(?:^|\n)\s*\d+[.)]?$", before):
        return True
    if before[-1] == ".":
        prev = re.search(r"([\w]+)\.$", before)
        return not (prev and prev.group(1).lower() in _TITLES)
    return False


def _person_word(text: str, m: re.Match) -> bool:
    """R1: słowo z wielkiej litery w środku zdania, nieznane jako zwykłe słowo albo znane jako imię/nazwisko."""
    word, low = m.group(0), m.group(0).lower()
    if _TITLE_BEFORE_RE.search(text[max(0, m.start() - 8):m.start()]):
        return True  # „Pan Rogalik” — tytuł to dowód osoby niezależnie od słownika
    before = text[max(0, m.start() - 80):m.start()]
    if low in OSOBA_DENYLIST or low in WHITE_LISTS or low in _OFFICE_TERMS or _sentence_start(text, m.start()) \
            or _DEFINED_RE.search(before) or _in_institution(before):
        return False
    parts = [_morf_interps(w) for w in word.split("-")]
    if any(p is None for p in parts):
        return True
    quals = [{q.split("_(")[0] for i in p for q in i[2][3]} for p in parts]
    if len(parts) > 1 and any("nazwa_geograficzna" in q for q in quals):
        return False  # „Kraków-Śródmieście”
    if quals[0] & {"imię", "nazwisko"}:
        return not ("nazwa_geograficzna" in quals[0] and _GEO_PREP_RE.search(before))
    if all(i[2][2] == "ign" for i in parts[0]):  # nieznane: nazwisko albo szum OCR
        return bool(_SURNAME_END_RE.search(low))
    return False  # znane wyłącznie jako zwykłe słowo/miejsce → bez alarmu


def _in_institution(before: str) -> bool:
    line = before[before.rfind("\n") + 1:]
    return any(_IN_INSTITUTION_RE.fullmatch(line, k.end()) for k in _INSTITUTION_RE.finditer(line))


def _r1(text: str):
    for m in _WORD_RE.finditer(text):
        if _person_word(text, m):
            yield m.start(), m.end(), "R1", "Możliwe imię lub nazwisko, którego silnik nie zakrył"


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
                               (_POSTAL_AFTER_RE, "Kod pocztowy obok zakrytego adresu")):
                a = rx.match(text, t.end())
                if a and (rx is _DIGITS_AFTER_RE or kind == "ADRES"):
                    found.append((a.span(1), reason))
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
    return bool(re.search(rf"[{_UP}]", frag)) and not _INSTITUTION_RE.search(frag)


def _r5(text: str):
    for m in _ROLE_RE.finditer(text):
        s, frag = m.start(1), m.group(1)
        cut = _TOKEN_RE.search(frag)
        frag = (frag[:cut.start()] if cut else frag).rstrip(" \t.-–(")
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


def load_allowlist() -> list[str]:
    """Istniejąca allowlista profilu (tylko odczyt; brief v2: nie poszerzamy jawnego pliku)."""
    path = Path(os.environ.get("PROFILE_DIR", str(Path.home() / ".pseudominizer" / "profile"))) / "guard_allowlist.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        return []


_RED = ("HIGH", "MAP_LEAK")


def collect_warnings(text: str, map_values: list[str] | None = None, allowlist: list[str] | None = None) -> list[dict]:
    """Ostrzeżenia dla finalnego tekstu: [{id, start, end, fragment, rule, level, reasons}], posortowane po pozycji.
    Fragmenty nachodzące na siebie → jedna pozycja (wszystkie powody); nic wewnątrz tokenów; allowlista wycisza fragment."""
    tokens = [m.span() for m in _TOKEN_RE.finditer(text)]
    masked = _TOKEN_RE.sub(lambda m: "#" * len(m.group(0)), text)
    allow = {a.strip().casefold() for a in allowlist or [] if isinstance(a, str) and a.strip()}
    hits = []
    for src in (_patterns(masked), _map_leaks(masked, map_values or []), _r1(text), _r2(text), _r3(text), _r4(text), _r5(text)):
        for s, e, rule, reason in src:
            if s < e and not any(ts < e and s < te for ts, te in tokens) and text[s:e].strip().casefold() not in allow:
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
