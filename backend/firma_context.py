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


def _form_start(text: str, start: int, value: str) -> int | None:
    """Początek pełnej formy prawnej (z „Sp.”/„S.” przed nią) albo None, gdy kandydat nie jest formą prawną."""
    head = _SP_BEFORE_RE.search(text[max(0, start - 6):start])
    if _FULL_FORM_RE.fullmatch(value):   # cała forma jako kandydat: „Sp. z o.o.”, „S.A.”, „Sp. k.” (F1 Codexa r3)
        return start
    if _MULTI_FORM_RE.fullmatch(value):
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
# (Mobile NameEngine FIRMA_LEGAL_REGEX). „spj” bez kropki, S.A. i s.c. świadomie poza skanem (inicjały, spaCy łapie S.A.).
_FORM_SCAN_RE = re.compile(r"(?<![\w.])(?:sp\.[ \t]*z[ \t]*o\.?[ \t]*o|sp\.[ \t]*k\.?[ \t]*a|sp\.[ \t]*[jkp]|p\.[ \t]*s\.[ \t]*a)\.?(?!\w)",
                           re.IGNORECASE)  # odstępy dowolne w linii (Codex F1: „sp.z  o.o.”)


def scan_legal_forms(text: str, ner_results: list) -> list:
    """Kandydaci FIRMA „nazwa + forma prawna” nienakładający się na encje spaCy; nazwa jak w `_name_start`, bez nazwy — nic."""
    from spacy_ner import NERResult
    out = []
    for m in _FORM_SCAN_RE.finditer(text):
        if any(r.start < m.end() and m.start() < r.end for r in ner_results):
            continue
        name = _name_start(text, m.start())
        if name is not None:
            out.append(NERResult(text[name:m.end()], "FIRMA", 0.8, name, m.end()))
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
