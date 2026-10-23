"""
firma_proof.py — [LYNX-FIRMA-PROOF] FIRMA tylko z dowodem (jak OSOBA: „udowodnij, że jesteś firmą”).

Kandydat FIRMA ze spaCy bywa urzędem („Krajowa Izba Odwoławcza”, „Rady Ministrów”), zwykłym słowem („Rejonu”, „Nadzoru”),
ustawą („Prawo Budowlane”) albo produktem („Microsoft Office”); każdy taki token rodzi potem w Guardzie lawinę MAP_LEAK
przy innych wystąpieniach słowa. Zamiast kolejnych filtrów-wyjątków: kandydat zostaje FIRMA tylko z dowodem —
  1. forma prawna w wartości (Sp. z o.o., S.A., s.c., spółka jawna…, GmbH, Ltd);
  2. rzeczownik rodzaju firmy („Przedsiębiorstwo”, „Zakład”, „Agencja”…) + słowo wyróżniające: WIELKIE, z cyfrą, w cudzysłowie
     albo nieznane słownikowi („Pracownia Projektowa Diapron”) — sam opis („Zakład Komunalny”) nie wystarcza;
  3. imię + nazwisko w nazwie albo nazwa JDG (rodzaj działalności + imię + nazwisko) — dane osobowe wg RODO, zakrywamy zawsze;
  4. początek nazwy firmy udowodnionej w tym samym dokumencie („AG-Complex”, „InPost” po „AG-COMPLEX Sp. z o.o.”).
Powtórzenie rdzenia bez formy, którego spaCy nie zwrócił, dalej obsługuje `firma_context.firma_core_variants`.
Słowo roli i numeracja na początku („Wykonawca POLSUPER Sp. z o.o.”, „3) A-ster s.c.”) nie należą do nazwy — zdejmowane.
Koszt (świadomy): firma bez formy prawnej i bez rzeczownika rodzaju, wspomniana tylko tak („Castorama Polska”), zostaje jawna —
nazwa osoby prawnej nie jest daną osobową (RODO motyw 14); słowa nieznane słownikowi pokazuje Guard (R1).
"""
from __future__ import annotations

import dataclasses
import re

_FORM_RE = re.compile(
    r"(?i:\bsp\.?\s*z\s*o\.?\s*o|\bsp\.?\s?[jkp]\b\.?|\bsp\.?$|\bspół(?:ka|ki|kę|ce|ką)[ \t]*$|\bs\.\s?[ac]\b\.?|\bs\.\s?k\.\s?a|\bp\.\s?s\.\s?a|\bsp\.?\s?k\.?\s?a"
    r"|\bspół\w*\s+(?:z\s+ograniczon\w*|akcyjn\w*|jawn\w*|komandytow\w*|cywiln\w*|partnersk\w*)|\bgmbh\b|\bltd\b\.?|\bllc\b|\binc\b\.)"
    r"|(?<![\w-])(?:SA|AG|OU|BV|NV)\.?[ \t]*$"
)
_HEAD_RE = re.compile(r"\b(?:Przedsiębiorstw|Zakład|Firm|Agencj|Biur|Hurtowni|Spółdzielni|Grup|Korporacj|Fabryk|Pracowni|Kancelari"
                      r"|Usług|Studi|Wydawnictw|Towarzystw|Centrum|Konsorcj|Salon|Serwis|Sklep|Warsztat)\w*", re.IGNORECASE)
_ROLE_HEAD_RE = re.compile(r"(?:(?:\d[\d/]*|[A-Z]\d)[.)][ \t]+|[A-Z]\)[ \t]+|(?:Wykonawc|Zamawiając|Odwołując|Przystępując|Konsorcj|Lider|Partner"
                           r"|Pełnomocni|Uczestni)\w*(?:[ \t]*[:–-])?[ \t]+)")
_WORD_RE = re.compile(r"[^\W_][\w-]*")
_ROMAN_RE = re.compile(r"[IVXLC]+")
# Forma prawna tuż za kandydatem (także w następnej linii: „Testopolia Systemy\nSp. z o.o.” po podziale linii)
_FORM_AFTER_RE = re.compile(r"[ \t\r\n,\"”]*(?:sp\.?\s*z\s*o|sp\.?\s?[jkp]\b|s\.\s?[ac]\b|spół\w*\s+(?:z\s+ogranicz|akcyj|jawn|komandyt|cywil|partner)"
                            r"|gmbh\b|ltd\b)", re.IGNORECASE)
# Nazwa w cudzysłowie zaczęta w kandydacie albo tuż za nim („Agencja Usługowa „Interserwis””)
_QUOTED_AFTER_RE = re.compile(r"[ \t]*[\"„“][^\"„“”\n]{2,60}[\"”“]")


def strip_role(text: str, ner):
    """Zdejmuje z początku FIRMA numerację i słowo roli (także kilka: „E1. Wykonawca …”) oraz otwierający cudzysłów po nich."""
    if ner.label != "FIRMA":
        return ner
    start = ner.start
    while (m := _ROLE_HEAD_RE.match(text, start, ner.end)) and m.end() < ner.end:
        start = m.end()
    if start != ner.start:
        start += len(text[start:ner.end]) - len(text[start:ner.end].lstrip("\"„“«"))
    return ner if start == ner.start else dataclasses.replace(ner, start=start, text=text[start:ner.end])


def _distinctive(word: str) -> bool:
    """Słowo wyróżniające nazwę: WIELKIE (nie liczba rzymska), z cyfrą albo nieznane słownikowi (nie pospolite, nie geo)."""
    from osoba_not_person import _common_or_person
    if any(c.isdigit() for c in word) or (len(word) >= 2 and word.isupper() and not _ROMAN_RE.fullmatch(word)):
        return True
    if not word[:1].isupper():
        return False
    common, person, geo = _common_or_person(word.split("-")[0])
    return common is False and not person and not geo


def has_proof(value: str) -> bool:
    """Czy wartość FIRMA ma dowód firmy (forma prawna / rodzaj + nazwa wyróżniająca / imię-nazwisko bez znaczenia pospolitego)."""
    from osoba_not_person import _common_or_person, _strong, first_names
    from firma_context import is_jdg
    if _FORM_RE.search(value) or is_jdg(value):   # JDG: rodzaj działalności + imię + nazwisko („Pracownia … Róża Kruk”)
        return True
    words = _WORD_RE.findall(value)
    names = first_names()
    if any(w[:1].isupper() and len(w) > 2 and w.lower() in names and nxt[:1].isupper() and len(nxt) > 1
           and _common_or_person(w)[0] is False for w, nxt in zip(words, words[1:])):  # imię + nazwisko („Jan Kos”), nie „Rady …”
        return True
    head = _HEAD_RE.search(value)
    if not head:
        return False
    rest = _WORD_RE.findall(value[:head.start()] + " " + value[head.end():])
    return bool(re.search(r"[\"„“].+[\"”“]", value)) or any(_distinctive(w) or w[:1].isupper() and _strong(w) for w in rest)


def _context_proof(text: str, r) -> bool:
    """Dowód z otoczenia: forma prawna tuż za kandydatem, nazwa w cudzysłowie (wokół kandydata, zaczęta w nim lub tuż za nim)
    albo nazwa własna spoza polskiego słownika („Testopolia Systemy”)."""
    if _FORM_AFTER_RE.match(text, r.end) or _foreign_name(r.text):
        return True
    if r.start and text[r.start - 1] in "\"„“" and text[r.end:r.end + 1] in ("\"", "”", "“"):
        return True
    quote = r.text.find("„")
    return bool(_QUOTED_AFTER_RE.match(text, r.start + quote if quote >= 0 else r.end))


def _foreign_name(value: str) -> bool:
    """Słowo z wielkiej litery nieznane polskiemu słownikowi, nie skrótowiec („Testopolia”, „Remondis”; nie „GDDKiA”, „MSWiA”)."""
    from osoba_not_person import _common_or_person
    for w in _WORD_RE.findall(value):
        if w[:1].isupper() and sum(c.isupper() for c in w) == 1 and len(w) >= 4 and not any(c.isdigit() for c in w):
            common, person, geo = _common_or_person(w.split("-")[0])
            if common is False and not person and not geo:
                return True
    return False


def _norm(value: str) -> str:
    """Słowa małymi literami; inicjały na końcu („ALTO Computers M.B.”) pominięte."""
    words = _WORD_RE.findall(value.lower().replace("-", " "))
    while len(words) > 1 and len(words[-1]) == 1:
        words.pop()
    return " ".join(words)


def firma_proof(text: str, ner_results: list) -> list:
    """FIRMA bez dowodu odpada (z mapy i z tekstu — zostaje jawna), chyba że jest początkiem nazwy firmy udowodnionej w tym
    dokumencie (dowód 4: „AG-Complex”, „InPost” po „AG-COMPLEX Sp. z o.o.”); z dowodem — bez słowa roli na początku."""
    # OSOBA z formą prawną i nazwą (wyraz ≥3 litery, nie same inicjały „J. S.C.”) = FIRMA, jak w _process_ner
    is_firm = [r.label == "FIRMA" or bool(_FORM_RE.search(r.text)) and any(len(w) >= 3 for w in _WORD_RE.findall(r.text))
               for r in ner_results]
    firms = [strip_role(text, dataclasses.replace(r, label="FIRMA")) for r, f in zip(ner_results, is_firm) if f]
    proven = {(r.start, r.end) for r in firms if has_proof(r.text) or _context_proof(text, r)}
    names = [_norm(r.text) + " " for r in firms if (r.start, r.end) in proven]
    out = [r for r, f in zip(ner_results, is_firm) if not f]
    for r in firms:
        key = _norm(r.text)
        if (r.start, r.end) in proven or len(key) >= 3 and any(n.startswith(key + " ") for n in names):
            out.append(r)
    return sorted(out, key=lambda r: r.start)
