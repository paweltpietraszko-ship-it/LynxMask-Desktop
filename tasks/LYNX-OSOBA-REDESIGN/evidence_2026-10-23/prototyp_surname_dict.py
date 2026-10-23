"""PROTOTYP SURNAME-DICT (zalążek jednego miejsca decyzji OSOBA): dla pojedynczego słowa ze słownika nazwisk PESEL (≥100 osób)
jedna funkcja `decision` mówi ostatecznie: 'mask' albo 'none'. Słowa spoza słownika → None (dotychczasowa ścieżka).
Uzgodnienia z Pawłem 23.10: biała lista (100–999 osób, użycie małą literą w pismach), próg 1000, miesiące tylko z kotwicą,
w środku zdania zakryj, na początku tylko z czynnością jednej osoby (nie „być”), bez członów nazw, funkcji, miejscowości, ulic."""
import json
import os
import re

_DATA = None
_MORF = None
_STREETS = None
_MONTHS = {"styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"}
_ROLE_WORD_RE = re.compile(r"(?i)(?:protokolant|przewodnicząc|sędzi|prezes|dyrektor|kierownik|mecenas|prokurator|komornik|notariusz"
                           r"|radc|adwokat|minister|wojewod|marszał|burmistrz|wójt|starost|posł|poseł|senator|rzecznik|inspektor|referent"
                           r"|ławnik|biegł|świad|kurator|doktor|profesor|inżynier|kanclerz|premier|prezydent|członk|zastęp|sekretar|skarbnik)")
_SUFFIX = [("skiego", "ski"), ("skiemu", "ski"), ("skim", "ski"), ("ską", "ska"), ("skiej", "ska"), ("ckiego", "cki"), ("ckiemu", "cki"),
           ("ckim", "cki"), ("cką", "cka"), ("ckiej", "cka"), ("dzkiego", "dzki"), ("dzkiej", "dzka"), ("owi", ""), ("em", ""), ("a", ""),
           ("u", ""), ("ie", ""), ("ę", "a"), ("ą", "a"), ("y", "a"), ("i", "a")]
_NB_BEFORE_RE = re.compile(r"(?:^|[\s(„\"])([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)[ \t]+$")
_NB_AFTER_RE = re.compile(r"\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)(?![\w-])")
_LOC_PREP_RE = re.compile(r"(?:^|\s)(?:w|we|na|pod|nad|koło)\s+$", re.IGNORECASE)
_NUM_AFTER_RE = re.compile(r"\s*\d")
_COMMON_SURNAME = 1000   # próg Pawła: nazwisko noszone przez ≥1000 osób zostaje nazwiskiem


def _morf():
    global _MORF
    if _MORF is None:
        import morfeusz2
        _MORF = morfeusz2.Morfeusz()
    return _MORF


def _data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pesel_surnames.json"), encoding="utf-8") as f:
            d = json.load(f)
        _DATA = (d["surnames"], frozenset(d["whitelist"]))
    return _DATA


def _streets() -> frozenset:
    global _STREETS
    if _STREETS is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "street_names.json"), encoding="utf-8") as f:
            d = json.load(f)
        _STREETS = frozenset(d) | frozenset(x for v in d.values() for x in v)
    return _STREETS


def _candidates(word: str) -> set:
    w = word.lower()
    out = {w} | {i[2][1].split(":")[0].lower() for i in _morf().analyse(word[:1].upper() + word[1:].lower())}
    for suf, rep in _SUFFIX:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            out.add(w[: len(w) - len(suf)] + rep)
    return out


def match(word: str):
    """'month' | liczba osób (największa z pasujących nazwisk) | None (nie ze słownika albo biała lista)."""
    surn, white = _data()
    hits = {c: surn[c] for c in _candidates(word) if c in surn and c not in white}
    if not hits:
        return None
    if all(c in _MONTHS for c in hits):
        return "month"
    return max(v for c, v in hits.items() if c not in _MONTHS)


def decision(text: str, start: int, end: int):
    """Wołane PO sprawdzeniu mocnych dowodów (tytuł, etykieta, imię/token obok) — tu kotwicy już nie ma.
    'mask' | 'none' dla słowa ze słownika nazwisk; None — słowo spoza słownika (dotychczasowa ścieżka)."""
    from guard_residue import _sentence_start
    from layers.address import _CITY_FORMS
    from osoba_not_person import first_names
    word = text[start:end]
    m = match(word)
    if m is None:
        return None
    if m == "month" or _ROLE_WORD_RE.match(word):
        return "none"
    rare = m < _COMMON_SURNAME
    before = text[max(0, start - 12):start]
    if word in _CITY_FORMS and (rare or _LOC_PREP_RE.search(before)):
        return "none"   # miejscowość („w Rybniku”, „Siedlce”) — samo miasto jawne (polityka Pawła)
    if word.lower() in _streets() and (rare or _NUM_AFTER_RE.match(text, end)):
        return "none"   # ulica („Nowogrodzka”, „Żeromskiego 5”)
    names = first_names()
    b = _NB_BEFORE_RE.search(text[max(0, start - 40):start])
    if b and _sentence_start(text, start - len(b.group(0)) + b.group(0).find(b.group(1))):
        b = None
    a = _NB_AFTER_RE.match(text, end)
    if any(x and x.group(1).lower() not in names for x in (b, a)):
        return "none"   # człon nazwy własnej („Urzędu Wojewódzkiego”, „Dzienniku Urzędowym”)
    if _sentence_start(text, start):
        nxt = re.match(r"[ \t]+([a-ząćęłńóśźż]+)", text[end:end + 30])
        if not nxt:
            return "none"
        an = _morf().analyse(nxt.group(1))
        if any(i[2][1].split(":")[0] == "być" for i in an):
            return "none"   # „Konieczne jest…”
        return "mask" if any(i[2][2].startswith(("fin:sg", "praet:sg")) for i in an) else "none"
    return "mask"
