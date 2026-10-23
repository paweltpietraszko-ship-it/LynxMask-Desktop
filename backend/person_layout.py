"""
person_layout.py — [LYNX-OSOBA-LAYOUT] osoba z układu pisma: decyzja silnika (nie pytanie Guarda).

Wołane w `ner_adapter.apply_ner_layer` po słownikowych imionach, na tekście z tokenami. Każda reguła to ogólna zasada:
1) wiersz z samych 2–3 słów z wielkiej litery po etykiecie osoby („Imię i nazwisko:”, „NABYWCA:”) albo nad wierszem
   „PESEL”/„zamieszkały”/„data urodzenia”; także ta sama etykieta z nazwą w jednym wierszu;
2) znane imię + słowo z wielkiej litery tuż obok (C3), poza nazwą ulicy/patrona i miejscowością („Tomaszów Mazowiecki”);
3) słowo tuż za tokenem osoby w tym samym wierszu („OSOBA_001 Kiljanek”) — gdy Morfeusz zna je jako nazwisko, albo gdy token
   zakrył samo imię, a słowo zamyka nazwę („Sheila Osoba”); słowo nieznane zostaje — o nie pyta Guard;
4) „Pan/Pani/P./dr/mgr/mec. + słowo z wielkiej litery” — poza funkcją (także w odmianie: „Panie Ministrze”) i czasownikiem.
"""
from __future__ import annotations

import re

_W = r"[^\W\d_](?:[^\W\d_]|̇|['’-])+"
_NAME_LINE_RE = re.compile(r"^[ \t]*(?:\d{1,2}[.)][ \t]*)?(" + _W + r"(?:[ \t]+" + _W + r"){1,2})[ \t]*,?[ \t]*$", re.MULTILINE)
_LABEL_RE = re.compile(r"(?i)(?:imi[eę] i nazwisko|nazwisko i imi[eę]|nabywca|sprzedawca|wnioskodawca|zleceniobiorca|zleceniodawca"
                       r"|osoba|wniosku|dłużnik|wierzyciel|pomiędzy|skarżąc\w*|pozwan\w*|powód(?:ka)?|najemca|wynajmujący)[ \t]*:?[ \t]*$")
_NEXT_RE = re.compile(r"(?i)[ \t]*(?:\d{1,2}[.)][ \t]*)?(?:pesel|zamieszka|data urodzenia|urodzon)")
_SAME_LINE_RE = re.compile(r"(?i:imi[eę] i nazwisko|nabywca|sprzedawca|wnioskodawca)[ \t]*:[ \t]*(" + _W + r"(?:[ \t]+" + _W + r"){1,2})"
                           r"[ \t]*$", re.MULTILINE)
_PAIR_RE = re.compile(r"(?<![\w.])(" + _W + r")(?=[ \t]+(" + _W + r")(?![\w-]))")  # pary zachodzące („Wczoraj Lucyna Osoba”)
_AFTER_TOKEN_RE = re.compile(r"(OSOBA_\d+)([ \t]*\n[ \t]*|[ \t]+)(" + _W + r")(?![\w-])")  # także przez złamanie wiersza PDF
_INITIAL_RE = re.compile(r"(?<![\w.])[A-ZĄĆĘŁŃÓŚŹŻ]\.[ \t]?([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})(?![\w-])")  # „P.Kapusta”, „J. Nowak”
_TITLED_RE = re.compile(r"(?:^|[\s(])(?:[Pp]an(?:a|u|em|ie|i|ią|owie)?|P\.|[Dd]r\.?|mgr|mec\.)[ \t]+"
                        r"([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}(?:-[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})?)(?![\w-])")
# nazwa funkcji (rdzeń, także w odmianie: minist-er/-ra/-rze, radn-y/-ej, prezyden-t/-cie)
_ROLE_WORD_RE = re.compile(r"(?i)(?:protokolant|przewodnicząc|sędzi|prezes|dyrektor|kierownik|mecenas|prokurator|komornik|notariusz"
                           r"|radc|radn|adwokat|minist|wojewod|marszał|burmistrz|wójt|starost|posł|poseł|senator|rzecznik|inspektor|referent"
                           r"|ławnik|biegł|świad|kurator|doktor|profesor|inżynier|kanclerz|premier|prezyden|członk|zastęp|sekretar|skarbnik)")
_VERB_ADJ = ("fin", "praet", "inf", "impt", "adj")


def _readings(word: str) -> list:
    """(lemat, tag, kwalifikatory) z Morfeusza; [] przy błędzie (reguła wtedy nie zakrywa — zostaje Guard)."""
    from guard_residue import _morf_interps
    return [(i[2][1], i[2][2], i[2][3]) for i in _morf_interps(word) or []]


def _cap(w: str) -> bool:
    return w[:1].isupper() and not w.isupper()


def _ok(words: list) -> bool:
    return all(_cap(w) and not _ROLE_WORD_RE.match(w) for w in words)


def _layout_lines(text: str) -> list:
    out = []
    for m in _NAME_LINE_RE.finditer(text):
        if not _ok(m.group(1).split()):
            continue
        prev = text[:m.start()].rstrip("\n \t").rsplit("\n", 1)[-1]
        nxt = text[m.end():].lstrip("\n \t").split("\n", 1)[0]
        if _LABEL_RE.search(prev) or _NEXT_RE.match(nxt):
            out.append(m.group(1))
    return out + [m.group(1) for m in _SAME_LINE_RE.finditer(text) if _ok(m.group(1).split())]


def _name_pairs(text: str) -> list:
    from osoba_not_person import _variants, first_names, in_city_name, inside_street_name
    names, out = first_names(), []
    for m in _PAIR_RE.finditer(text):
        a, b = m.group(1), m.group(2)
        if not (_cap(a) and _ok([b])) or inside_street_name(text, m.start()) or in_city_name(text, m.start(1), m.end(1)) \
                or text[max(0, m.start() - 4):m.start()].strip().endswith("im."):
            continue
        if not (a.lower() in names or any(v.lower() in names for v in _variants(a)[:8])):
            continue
        rd = _readings(a)  # „Rady Miejskiej”, „Danych Osobowych”, „Tomaszów Mazowiecki” — pierwsze słowo nie jest tu imieniem
        geo = any("nazwa_geograficzna" in q for _l, _t, q in rd)
        b_person = any("nazwisko" in q or t == "ign" for _l, t, q in _readings(b))
        if any(lem[:1].islower() and "nazwa_pospolita" in q for lem, _t, q in rd) \
                or (geo and (not any("imię" in q for _l, _t, q in rd) or not b_person)):
            continue
        out.append(f"{a} {b}")
    return out


def _after_token(text: str, values: dict) -> list:
    from osoba_not_person import first_names
    names, out = first_names(), []
    for m in _AFTER_TOKEN_RE.finditer(text):
        w = m.group(3)
        if not _ok([w]):
            continue
        surname = any("nazwisko" in q for _l, _t, q in _readings(w))
        only_first = values.get(m.group(1), "").strip().lower() in names
        if "\n" in m.group(2):  # przez złamanie wiersza tylko nazwisko za samym imieniem („OSOBA_010 ⏎ Zająca”), nie etykieta
            if only_first and surname and ":" not in text[m.end():].split("\n", 1)[0]:
                out.append(m.span(3))
            continue
        closes = re.match(r"[ \t]*(?:$|\n|[,.;:)])", text[m.end():m.end() + 3])
        if surname or (only_first and closes):
            out.append(m.span(3))
    return out


def _initial_surname(text: str) -> list:
    """Inicjał + nazwisko wg Morfeusza („P.Kapusta”, „J. Nowak”) — poza ulicą („ul. A. Mickiewicza”) i funkcją."""
    from osoba_not_person import inside_street_name
    return [m.span(1) for m in _INITIAL_RE.finditer(text)
            if _ok([m.group(1)]) and not inside_street_name(text, m.start())
            and any("nazwisko" in q for _l, _t, q in _readings(m.group(1)))]


def _titled(text: str) -> list:
    out = []
    for m in _TITLED_RE.finditer(text):
        w = m.group(1)
        rd = _readings(w)
        if _ROLE_WORD_RE.match(w) or any(_ROLE_WORD_RE.match(lem) for lem, _t, _q in rd) \
                or (rd and all(t.split(":")[0] in _VERB_ADJ for _l, t, _q in rd)):
            continue
        out.append(m.span(1))
    return out


def _sentence_initial(text: str, start: int) -> bool:
    before = text[:start].rstrip(" \t„\"(")
    return not before or before[-1] in "\n.!?:;•–-"


def _mask_spans(text: str, spans: list, allocator, sub_whole) -> str:
    """Słowo ze zwykłym znaczeniem („Termin”, „Osoba”): wystąpienia z kotwicą + wystąpienia z wielkiej litery w środku zdania
    (nazwa własna); na początku zdania/wiersza zostaje („Termin wykonania…” — decyzja per wystąpienie, C3).
    Nazwisko bez zwykłego znaczenia — każde wystąpienie w tekście (jak dotąd)."""
    common = {}
    for s, e in spans:
        w = text[s:e]
        if w not in common:
            common[w] = any(lem[:1].islower() for lem, _t, q in _readings(w) if "nazwa_pospolita" in q)
    tokens = {w: allocator.assign("OSOBA", w) for w in dict.fromkeys(text[s:e] for s, e in spans)}
    spans = set(spans) | {m.span() for w, c in common.items() if c
                          for m in re.finditer(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", text)
                          if not _sentence_initial(text, m.start())}
    for s, e in sorted(spans, reverse=True):
        if common[text[s:e]]:
            text = text[:s] + tokens[text[s:e]] + text[e:]
    for w, tok in tokens.items():
        if not common[w]:
            text = sub_whole(text, w, tok)
    return text


def apply_person_layout(text: str, allocator, sub_whole) -> str:
    """Zakrywa osoby z reguł 1–4 (jeden token na wartość)."""
    for p in dict.fromkeys(_layout_lines(text) + _name_pairs(text)):
        text = sub_whole(text, p, allocator.assign("OSOBA", p))
    text = _mask_spans(text, _after_token(text, allocator.reverse_map) + _initial_surname(text), allocator, sub_whole)
    return _mask_spans(text, _titled(text), allocator, sub_whole)
