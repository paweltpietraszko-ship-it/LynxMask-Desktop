"""
firma_context.py — [LYNX-FIRMA-FILTER-FIX] forma prawna nigdy nie jest samotną encją.

SpaCy potrafi zwrócić jako encję samą formę prawną („z o.o.” jako FIRMA, „A.” z „S.A.” jako OSOBA), a nazwa firmy przed nią
zostaje jawna („ALFA Sp. FIRMA_001”) albo encja ginie jako zbyt krótka. Tu taki kandydat jest rozszerzany w lewo o nazwę w tej samej
linii i staje się jedną FIRMA („ALFA Sp. z o.o.” — jedna wartość mapy, Przywróć 1:1). Bez nazwy — kandydat znika (bez samotnego tokenu).
Dowód formy prawnej (Codex C1): wieloliterowe formy same w sobie; pojedyncza litera („A.”, „k.”, „j.”, „p.”) tylko z bezpośrednio
poprzedzającym „S.”/„Sp.” — inaczej to inicjał osoby („Jan A.”) i encja zostaje bez zmian.
"""
from __future__ import annotations

import dataclasses
import re

_MULTI_FORM_RE = re.compile(r"(?:z\s?o\.\s?o|s\.\s?k\.\s?a|p\.\s?s\.\s?a|s\.\s?c)\.?", re.IGNORECASE)
_LETTER_FORM_RE = re.compile(r"[akjp]\.?", re.IGNORECASE)
_FULL_FORM_RE = re.compile(r"(?:Sp\.?\s?(?:z\s?o\.\s?o|[kjp])|S\.\s?A|S\.\s?K\.\s?A|P\.\s?S\.\s?A)\.?", re.IGNORECASE)
_SP_BEFORE_RE = re.compile(r"(?:\bSp\.?|\bS\.)\s?$", re.IGNORECASE)
_WORD_RE = re.compile(r"[\w&-]+\.?")
# [SILENT-PACK1] Forma zdublowana („z o.o. sp. z o.o.”, „Sp. z o.o. Sp. z o.o.”) — łańcuch form to nadal sama forma prawna.
_FORM_CHAIN_RE = re.compile(rf"(?:{_FULL_FORM_RE.pattern}|{_MULTI_FORM_RE.pattern})(?:\s*{_FULL_FORM_RE.pattern})+", re.IGNORECASE)


def _form_start(text: str, start: int, value: str) -> int | None:
    """Początek pełnej formy prawnej (z „Sp.”/„S.” przed nią) albo None, gdy kandydat nie jest formą prawną."""
    head = _SP_BEFORE_RE.search(text[max(0, start - 6):start])
    if _FULL_FORM_RE.fullmatch(value):   # cała forma jako kandydat: „Sp. z o.o.”, „S.A.”, „Sp. k.” (F1 Codexa r3)
        return start
    if _MULTI_FORM_RE.fullmatch(value) or _FORM_CHAIN_RE.fullmatch(value):
        return start - len(head.group(0)) if head else start
    if _LETTER_FORM_RE.fullmatch(value) and head:
        return start - len(head.group(0))
    return None


def _name_start(text: str, form_start: int) -> int | None:
    """Początek nazwy firmy przed formą prawną w tej samej linii: słowa z wielkiej litery / WIELKIE / z cyfrą oraz „i”, „&”,
    łącznik; stop na początku linii, dwukropku i słowie z małej litery. None — brak nazwy."""
    line_start = text.rfind("\n", 0, form_start) + 1
    segment = re.split(r"[:,;]", text[line_start:form_start])[-1]   # dwukropek, przecinek, średnik kończą nazwę
    offset = form_start - len(segment)
    start = None
    for m in reversed(list(_WORD_RE.finditer(segment))):
        word = m.group(0)
        if word.lower().startswith("spółk"):   # „Spółka z o.o.” — część formy prawnej, nie nazwa
            continue
        if word[0].isupper() or any(c.isdigit() for c in word):
            start = offset + m.start()
        elif word.lower() not in ("i", "&", "-"):
            break
    return start


# [LYNX-FORMATS-PACK2] Forma prawna z kropką po „sp” (także bez spacji: „sp.j.”, „Sp.k.”, „sp.z o.o.”) — FIRMA bez encji spaCy
# (Mobile NameEngine FIRMA_LEGAL_REGEX). „spj” bez kropki i S.A. poza skanem (spaCy łapie S.A.).
# [LYNX-FIRMA-SILENT2] „s.c.” w skanie — tylko po nazwie z wyrazem ≥2 liter (nie po samych inicjałach „J. S.C.”).
_FORM_SCAN_RE = re.compile(r"(?<![\w.])(?:sp\.[ \t]*z[ \t]*o\.?[ \t]*o|sp\.[ \t]*k\.?[ \t]*a|sp\.[ \t]*[jkp]|p\.[ \t]*s\.[ \t]*a|s\.[ \t]*c)\.?(?!\w)",
                           re.IGNORECASE)  # odstępy dowolne w linii (Codex F1: „sp.z  o.o.”)


def scan_legal_forms(text: str, ner_results: list) -> list:
    """Kandydaci FIRMA „nazwa + forma prawna” nienakładający się na encje spaCy; nazwa jak w `_name_start`, bez nazwy — nic."""
    from spacy_ner import NERResult
    out = []
    for m in _FORM_SCAN_RE.finditer(text):
        # [SILENT-PACK1] OSOBA zaczęta przed formą, która połknęła jej „sp.” („Jurzerznka sp.”), nie blokuje FIRMA (nazwa+forma).
        if any(r.start < m.end() and m.start() < r.end and not (r.label == "OSOBA" and r.start < m.start()) for r in ner_results):
            continue
        name = _name_start(text, m.start())
        if name is not None and m.group(0)[:1] in "sS" and not re.search(r"[^\W\d_]{2,}[\"”]?[ \t]*$", text[name:m.start()]):
            continue   # „s.c.” tuż po inicjale („J. S.C.”) — nie firma; wyraz przed formą musi mieć ≥2 litery
        if name is not None:
            out.append(NERResult(text[name:m.end()], "FIRMA", 0.8, name, m.end()))
    return out


# [LYNX-FIRMA-SILENT2] Nazwa jednoosobowej działalności: rzeczownik działalności + słowa z wielkiej litery + imię i nazwisko na końcu
# („Usługi Konserwatorskie Cezary Jeż”) — jedna FIRMA (wybór Pawła 23.10: opis działalności zakryty razem z osobą).
_JDG_HEAD_RE = re.compile(r"(?<![\w-])(?:Usługi|Biuro|Zakład|Pracownia|Studio|Kancelaria|Gabinet|Warsztat|Firma|Przedsiębiorstwo|Sklep"
                          r"|Hurtownia|Serwis|Salon|Atelier|Agencja)(?![\w-])")
_CAP_WORD_RE = re.compile(r"[ \t]+([A-ZĄĆĘŁŃÓŚŹŻ][\w]*(?:-[A-ZĄĆĘŁŃÓŚŹŻ][\w]*)?)(?![\w-])")


def is_jdg(value: str) -> bool:
    """Cała wartość to nazwa JDG (rzeczownik działalności … imię nazwisko) — nie dział wewnętrzny („Biuro Organizacji Pracy Jan Kos”)."""
    return any(e.start == 0 and e.end == len(value.strip()) for e in jdg_entities(value.strip()))


def jdg_entities(text: str) -> list:
    """FIRMA dla każdego wystąpienia „rzeczownik działalności + słowa z wielkiej litery + imię + nazwisko”; bez imienia — nic."""
    from osoba_not_person import first_names
    from spacy_ner import NERResult
    names, out = first_names(), []
    for m in _JDG_HEAD_RE.finditer(text):
        words, pos = [], m.end()
        while (w := _CAP_WORD_RE.match(text, pos)) and len(words) < 8:
            words.append(w)
            pos = w.end()
        for i in range(len(words) - 1, 0, -1):   # ostatnia para imię + nazwisko (nazwisko bywa też imieniem: „Cezary Marek”)
            if words[i - 1].group(1).lower() in names:
                out.append(NERResult(text[m.start():words[i].end()], "FIRMA", 0.8, m.start(), words[i].end()))
                break
    return out


_CONNECTOR_HEAD_RE = re.compile(r"(?:[A-ZĄĆĘŁŃÓŚŹŻ0-9][\w-]*\.?\s+)+(?:i|&)\s+$")
_HAS_FORM_RE = re.compile(r"\b(?:Sp\.|S\.\s?A\.?|z\s?o\.\s?o)", re.IGNORECASE)


def legal_form_entities(text: str, ner_results: list) -> list:
    """Kandydaci-formy prawne → FIRMA z nazwą przed nimi (albo usunięci); FIRMA z formą prawną dołącza nazwę przed spójnikiem
    („Kowalski i Wspólnicy Sp. k.”); encje zawarte w nowej FIRMA odrzucane."""
    out, firms = [], []
    for ner in ner_results:
        value = text[ner.start:ner.end].strip()
        form = _form_start(text, ner.start, value) if value else None
        if form is None:
            head = _CONNECTOR_HEAD_RE.search(text[text.rfind("\n", 0, ner.start) + 1:ner.start])
            if ner.label == "FIRMA" and head and _HAS_FORM_RE.search(value):
                firms.append(dataclasses.replace(ner, start=ner.start - len(head.group(0)),
                                                 text=text[ner.start - len(head.group(0)):ner.end]))
            else:
                out.append(ner)
            continue
        name = _name_start(text, form)
        if name is not None:
            firm = dataclasses.replace(ner, start=name, end=ner.end, text=text[name:ner.end], label="FIRMA")
            if (firm.start, firm.end) not in [(f.start, f.end) for f in firms]:
                firms.append(firm)
    # Usuwamy tylko fragmenty firm zawarte w nowej FIRMA; OSOBA zostaje (inny zapis tej firmy, np. „Sp.z”, może nie trafić
    # w wartość mapy — wtedy nazwisko musi mieć własny token, a nie alias innej osoby; Przywróć 1:1).
    kept = [r for r in out if r.label == "OSOBA" or not any(f.start <= r.start and r.end <= f.end for f in firms)]
    return sorted(kept + firms, key=lambda r: r.start)


# [SILENT-PACK1 / LYNX-FIRMA-BARE-REPEAT] Rdzeń firmy (nazwa bez formy prawnej) powtórzony w dokumencie dostaje token tej firmy.
_TAIL_FORM_RE = re.compile(r"[\s,]*(?:sp\.?\s?z\s?o\.?\s?o|sp\.?\s?k\.?\s?a|sp\.?\s?[jkp]|s\.\s?a|s\.\s?c|p\.\s?s\.\s?a|spółka\s+(?:z\s+ograniczoną\s+"
                           r"odpowiedzialnością|akcyjna|jawna|komandytowa|partnerska|cywilna))\.?$", re.IGNORECASE)


def _firma_core(value: str) -> str | None:
    """Nazwa firmy bez (także zdublowanej) formy prawnej; None, gdy brak formy albo rdzeń za słaby: ≥2 słowa z wielkiej litery
    (spójniki „i”, „&” dozwolone) albo jedno słowo ≥4 litery z wielkiej litery — dopasowanie i tak tylko z wielkiej litery."""
    core = value
    while (m := _TAIL_FORM_RE.search(core)) and m.start() > 0:
        core = core[:m.start()]
    core = core.strip(" \"„”“,")
    words = core.split()
    if core == value.strip(" \"„”“,") or not words or not all(w[0].isupper() or w[0].isdigit() or w in ("i", "&") for w in words):
        return None
    # [LYNX-FIRMA-PROOF] jedno słowo z łącznikiem („AG-COMPLEX”) też jest rdzeniem
    return core if len(words) >= 2 or (len(core) >= 4 and core.replace("-", "").isalpha() and not _common_word(core)) else None


def _common_word(word: str) -> bool:
    """Jednowyrazowy rdzeń ze znaczeniem pospolitym („Punkt”, „Most”, „Jutrzenka” = świt) albo błąd Morfeusza — nie podmieniamy (B3)."""
    from osoba_not_person import _common_or_person
    common, _person, _geo = _common_or_person(word)
    return common is not False


def firma_core_variants(text: str, reverse_map: dict, all_variants: dict, is_person_word) -> tuple[dict, dict]:
    """Rdzeń firmy powtórzony bez formy dostaje token tej firmy (Przywróć: pełna nazwa); OSOBA o wartości równej rdzeniowi
    (spaCy tak nazywa powtórzenie) przechodzi na ten token. Dwie różne firmy z tym samym rdzeniem → rdzeń dostaje własny
    token FIRMA z wartością rdzenia (B2). Rdzeń z samych imion/nazwisk albo nieobecny w tekście — bez zmian."""
    by_core: dict[str, list[str]] = {}
    for tok, value in reverse_map.items():
        core = _firma_core(value) if tok.startswith("FIRMA") else None
        if core and not all(is_person_word(w) for w in core.split()) and re.search(rf"(?<!\w){re.escape(core)}(?!\w)", text):
            by_core.setdefault(core, []).append(tok)
    for core, toks in by_core.items():
        old = all_variants.get(core)
        if old and old not in toks and not (old.startswith("OSOBA") and reverse_map.get(old) == core):
            continue
        if len({reverse_map[t] for t in toks}) == 1:
            tok = toks[0]
        else:
            tok = f"FIRMA_{max(int(t.rsplit('_', 1)[1]) for t in reverse_map if t.startswith('FIRMA_')) + 1:03d}"
            reverse_map[tok] = core
        if old and old not in toks:   # OSOBA = rdzeń firmy: jej warianty przechodzą na token rdzenia, wpis OSOBA znika
            for var, t in list(all_variants.items()):
                if t == old:
                    all_variants[var] = tok
            del reverse_map[old]
        all_variants[core] = tok
    return reverse_map, all_variants
