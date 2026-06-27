"""
test_pipeline.py — Testy pipeline'u Pseudominizera
Wysyła prawdziwe żądania do http://127.0.0.1:8765/preview

Zmiany 13.06.2026:
  Poprawiona ścieżka do api_token.txt — os.path.abspath(__file__) zamiast
  __file__, żeby działała niezależnie od katalogu uruchomienia.
  T22: info("Nr dowodu nie znaleziony...") → warn(...) — usunięto
  wewnętrznie sprzeczny komunikat (zakryty + nie zakryty jednocześnie).

Uruchomienie:
  python test_pipeline.py

Wymagania:
  pip install requests
  Backend musi być uruchomiony (uruchom_tauri_dev.vbs lub ręcznie)
"""

import io
import re
import sys
import json
import base64
import textwrap
import requests

BASE_URL    = "http://127.0.0.1:8765"
PREVIEW_URL = f"{BASE_URL}/preview"
HEALTH_URL  = f"{BASE_URL}/health"

# [SECURITY-TOKEN] Odczyt tokenu API z api_token.txt generowanego przez backend.
# Plik tworzony przy starcie pseudominizer_api.py w tym samym folderze.
def _load_api_token() -> str:
    import os
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api_token.txt")
    try:
        with open(token_path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

_API_TOKEN = _load_api_token()
_AUTH_HEADERS = {"x-api-token": _API_TOKEN} if _API_TOKEN else {}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}[OK]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}⚠{RESET} {msg}")
def info(msg): print(f"  {CYAN}→{RESET} {msg}")

_current_test_failed = False

def fail(msg):
    global _current_test_failed
    _current_test_failed = True
    print(f"  {RED}[FAIL]{RESET} {msg}")

# ── Pomocnicze ────────────────────────────────────────────────────────────────

def send_preview(text: str, filename: str = "test.txt") -> dict:
    payload = io.BytesIO(text.encode("utf-8"))
    r = requests.post(PREVIEW_URL, files={"file": (filename, payload, "text/plain")}, headers=_AUTH_HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()

def tokens_of_type(result: dict, token_type: str) -> list[dict]:
    return [t for t in result.get("tokens", []) if t["type"] == token_type]

def original_masked(result: dict, original_value: str) -> bool:
    return original_value.lower() not in result.get("anonymized_preview", "").lower()

def token_covers(result: dict, original_value: str) -> bool:
    return any(original_value.lower() in t.get("original", "").lower() for t in result.get("tokens", []))

def assert_masked(r, value, label):
    if original_masked(r, value):
        ok(f"{label} zakryty")
    else:
        fail(f"{label} WIDOCZNY w wyjściu")

def assert_masked_with_preview(r, value, label):
    if original_masked(r, value):
        ok(f"{label} zakryty")
    else:
        fail(f"{label} WIDOCZNY w wyjściu")
        fail(f"  Wyjście: {r.get('anonymized_preview', '')[:120]}")

def save_to_archive(pse_code: str, tokens: list, anon_text: str) -> bool:
    blob = json.dumps({"tokens": tokens, "anonymized_preview": anon_text})
    enc_blob = base64.b64encode(blob.encode("utf-8")).decode("ascii")
    desc = base64.b64encode(b"test").decode("ascii")
    res = requests.post(
        f"{BASE_URL}/archive",
        headers=_AUTH_HEADERS,
        json={"pse": pse_code, "token_count": len(tokens), "enc_blob": enc_blob, "description": desc},
        timeout=10,
    )
    return res.json().get("ok", False)

def depseudo_python(text: str, tokens: list) -> str:
    """Odpowiednik restoreText z Depseudonimizuj.tsx."""
    token_map = {t["token"]: t["original"] for t in tokens}
    return re.sub(r"\b[A-Z][A-Z_]+_\d{3}\b", lambda m: token_map.get(m.group(0), m.group(0)), text)

def delete_archive(pse_code: str):
    try:
        requests.delete(f"{BASE_URL}/archive/{pse_code}", headers=_AUTH_HEADERS, timeout=5)
    except Exception:
        pass

# ── Dekorator ─────────────────────────────────────────────────────────────────

TESTS = []

def test(name):
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator

# ── Testy ─────────────────────────────────────────────────────────────────────

@test("T01 — PESEL (11 cyfr)")
def t01():
    r = send_preview("Dane pacjenta: Jan Nowak, PESEL 92081512345, ur. 15.08.1992.")
    pesel = "92081512345"
    assert_masked_with_preview(r, pesel, f"PESEL {pesel}")
    if token_covers(r, pesel):
        ok("Token NUMER w reverse_map")
    else:
        warn("PESEL nie ma tokenu w reverse_map (może go wchłonął inny wzorzec)")
    return r

@test("T02 — NIP (format z myślnikami)")
def t02():
    r = send_preview("Firma ABC Sp. z o.o., NIP: 527-285-30-52, ul. Marszałkowska 1, Warszawa.")
    assert_masked(r, "527-285-30-52", "NIP 527-285-30-52")
    return r

@test("T03 — IBAN PL (format ze spacjami)")
def t03():
    r = send_preview("Przelej na konto: PL 61 1090 1014 0000 0712 1981 2874.")
    assert_masked_with_preview(r, "1090 1014", "IBAN (fragment środkowy)")
    return r

@test("T04 — Email")
def t04():
    r = send_preview("Kontakt: jan.kowalski@kancelaria-nowak.pl lub biuro@firma.com.pl")
    for email in ["jan.kowalski@kancelaria-nowak.pl", "biuro@firma.com.pl"]:
        assert_masked(r, email, f"Email {email}")
    return r

@test("T05 — Telefon (format +48 i bez prefiksu)")
def t05():
    r = send_preview("Zadzwoń: +48 512 345 678 lub 22 123 45 67.")
    for tel in ["512 345 678", "22 123 45 67"]:
        assert_masked(r, tel, f"Telefon '{tel}'")
    return r

@test("T06 — Adres z prefiksem ul. (pipeline ADDR_RE)")
def t06():
    r = send_preview("Siedziba: ul. Zielona 15A/3, 65-510 Zielona Góra.")
    fragments = ["Zielona 15A", "65-510"]
    masked_count = sum(1 for f in fragments if original_masked(r, f))
    if masked_count == len(fragments):
        ok("Adres z prefiksem zakryty w całości")
    elif masked_count > 0:
        warn(f"Adres częściowo zakryty ({masked_count}/{len(fragments)} fragmentów)")
    else:
        fail("Adres z prefiksem NIE zakryty")
    info(f"Tokeny ADRES: {len(tokens_of_type(r, 'ADRES'))}")
    return r

@test("T07 — Kwota z walutą (PLN/EUR)")
def t07():
    r = send_preview("Wartość faktury: 12 345,67 PLN. Zaliczka: 500,00 EUR.")
    kwoty = tokens_of_type(r, "KWOTA")
    if len(kwoty) >= 2:
        ok(f"Znaleziono {len(kwoty)} tokeny KWOTA")
    elif len(kwoty) == 1:
        warn("Znaleziono tylko 1 token KWOTA — jedna kwota mogła umknąć")
    else:
        fail("Brak tokenów KWOTA — obie kwoty pominięte")
    assert_masked(r, "12 345,67 PLN", "Kwota PLN")
    return r

@test("T08 — Imię i nazwisko (SpaCy NER)")
def t08():
    r = send_preview("Umowę podpisali: Marek Wiśniewski oraz Anna Kowalczyk-Nowak w dniu 03.06.2026.")
    osoba_tokens = tokens_of_type(r, "OSOBA")
    if len(osoba_tokens) >= 2:
        ok(f"Znaleziono {len(osoba_tokens)} tokeny OSOBA")
    elif len(osoba_tokens) == 1:
        warn("Znaleziono tylko 1 token OSOBA — jedna osoba mogła umknąć")
        warn(f"  Znaleziony: {osoba_tokens[0].get('original', '?')}")
    else:
        fail("Brak tokenów OSOBA — SpaCy nie wykryło osób")
    for name in ["Marek Wiśniewski", "Anna Kowalczyk-Nowak"]:
        assert_masked(r, name, f"'{name}'")
    return r

@test("T09 — Nazwa firmy (SpaCy NER)")
def t09():
    r = send_preview("Zamawiający: Kancelaria Prawna Nowak & Partnerzy Sp. k. z siedzibą w Krakowie.")
    firma_tokens = tokens_of_type(r, "FIRMA")
    if firma_tokens:
        ok(f"Znaleziono {len(firma_tokens)} tokeny FIRMA")
    else:
        fail("Brak tokenów FIRMA — SpaCy nie wykryło firmy")
    return r

@test("T10 — Adres patronimiczny (ul. Jana Kowalskiego — kolejność warstw)")
def t10():
    """ADDR_RE musi złapać adres przed NER, inaczej adres staje się 'ul. OSOBA_001'."""
    r = send_preview("Zamieszkały: ul. Jana Kowalskiego 5/2, 30-001 Kraków.")
    anon = r.get("anonymized_preview", "")
    if "ul. OSOBA_" in anon or "ul. Jana" in anon:
        fail("Kolejność warstw BŁĘDNA — adres patronimiczny rozbity")
        fail(f"  Wyjście: {anon[:120]}")
    else:
        ok("Adres patronimiczny przetworzony poprawnie")
    if original_masked(r, "Jana Kowalskiego 5"):
        ok("Adres zakryty w wyjściu")
    else:
        warn("Fragment adresu może być widoczny")
    return r

@test("T11 — REGON (9 cyfr)")
def t11():
    r = send_preview("REGON spółki: 123456785. Numer KRS: 0000123456.")
    assert_masked(r, "123456785", "REGON")
    assert_masked(r, "0000123456", "KRS")
    return r

@test("T12 — Tekst bez PII (brak fałszywych pozytywów)")
def t12():
    text = textwrap.dedent("""
        Sąd Rejonowy w Poznaniu wydał wyrok w dniu 1 marca 2026 roku.
        Sprawa dotyczyła naruszenia prawa autorskiego.
        Wartość przedmiotu sporu wynosiła sto tysięcy złotych.
        Strony zawarły ugodę na sali sądowej.
    """).strip()
    r = send_preview(text)
    tokens = r.get("tokens", [])
    numery = tokens_of_type(r, "NUMER")
    osoby  = tokens_of_type(r, "OSOBA")
    kwoty  = tokens_of_type(r, "KWOTA")
    if not numery:
        ok("Brak fałszywych NUMER")
    else:
        warn(f"Potencjalne false positives NUMER: {[t['original'] for t in numery]}")
    if not osoby:
        ok("Brak fałszywych OSOBA")
    else:
        warn(f"Potencjalne false positives OSOBA: {[t['original'] for t in osoby]}")
    if not kwoty:
        ok("Brak fałszywych KWOTA (kwota słowna — sprawdź verbal_amounts)")
    else:
        warn(f"Tokeny KWOTA (mogą być poprawne): {[t['original'] for t in kwoty]}")
    info(f"Łącznie tokenów: {len(tokens)}")
    return r

@test("T13 — Output guard (PII przemycone jako ALLCAPS — czy guard widzi?)")
def t13():
    """PESEL osadzony w ciągu alfanumerycznym REF...XYZ — test aktywności output_guard."""
    r = send_preview("Numer referencyjny zlecenia: REF92081512345XYZ — proszę podać przy kontakcie.")
    if original_masked(r, "92081512345"):
        ok("PESEL w ciągu alfanumerycznym złapany")
    else:
        warn("PESEL w ciągu REF...XYZ pominięty (word boundary blokuje — znana raf)")
    info(f"guard_blocked: {r.get('blocked', False)}")
    info(f"guard_reasons: {r.get('guard_reasons', [])}")
    return r

@test("T14 — Adres wieloliniowy (newline między ulicą a kodem)")
def t14():
    r = send_preview("Adresat:\nul. Słowackiego 22\n30-004 Kraków\nPolska")
    fragments = ["Słowackiego 22", "30-004"]
    masked = sum(1 for f in fragments if original_masked(r, f))
    if masked == len(fragments):
        ok("Adres wieloliniowy zakryty w całości")
    elif masked > 0:
        warn(f"Adres wieloliniowy zakryty częściowo ({masked}/{len(fragments)})")
    else:
        fail("Adres wieloliniowy NIE zakryty")
    return r

@test("T15 — Tekst bliski limitu 15000 znaków (stabilność pipeline'u)")
def t15():
    base = "Jan Kowalski, PESEL 92081512345, mieszka przy ul. Zielona 1, 65-001 Zielona Góra. "
    text = (base * (14000 // len(base) + 1))[:14000]
    r = send_preview(text)
    if r.get("error"):
        fail(f"Błąd przy dużym tekście: {r['error']}")
    else:
        ok(f"Duży tekst przetworzony — {r.get('total', 0)} tokenów łącznie")
    return r

@test("T16 — Pełny obieg: pseudonimizacja → archiwum → depseudonimizacja")
def t16():
    """Test end-to-end: sprawdza czy tekst po pełnym obiegu wraca do oryginału."""
    original = "Jan Kowalski, PESEL 92081512345, ul. Zielona 1, 65-001 Zielona Góra."
    r = send_preview(original)
    pse    = r.get("pse_code", "")
    tokens = r.get("tokens", [])
    anon   = r.get("anonymized_preview", "")
    if not pse:
        fail("Brak pse_code w odpowiedzi /preview")
        return r
    saved = save_to_archive(pse, tokens, anon)
    if saved:
        ok(f"Zapisano do archiwum: {pse}")
    else:
        warn("Zapis do archiwum nieudany — depseudonimizacja niemożliwa")
        return r
    restored = depseudo_python(anon, tokens)
    for token in tokens:
        orig_val = token.get("original", "")
        if len(orig_val) < 4:
            continue
        if orig_val.lower() in restored.lower():
            ok(f"'{orig_val[:30]}' odtworzone poprawnie")
        else:
            fail(f"'{orig_val[:30]}' NIE odtworzone w wyniku depseudonimizacji")
    remaining = re.findall(r"\b[A-Z][A-Z_]+_\d{3}\b", restored)
    if not remaining:
        ok("Brak nieodtworzonych tokenów w wyniku")
    else:
        fail(f"Tokeny bez odtworzenia: {remaining}")
    delete_archive(pse)
    return r

@test("T17 — PSE kod w anonymized_preview (autodetekt depseudonimizacji)")
def t17():
    """PSE-RRRR-NNNN musi być w pierwszej linii wyjścia — Depseudonimizuj.tsx tego wymaga."""
    r = send_preview("Anna Nowak, tel. 512 345 678.")
    anon = r.get("anonymized_preview", "")
    pse  = r.get("pse_code", "")
    if not pse:
        fail("Brak pse_code w odpowiedzi")
        return r
    first_line = anon.split("\n")[0]
    if pse in first_line:
        ok(f"PSE kod '{pse}' w pierwszej linii wyjścia")
    else:
        fail(f"PSE kod NIE jest w pierwszej linii — autodetekt nie zadziała")
        fail(f"  Pierwsza linia: {first_line[:80]}")
    return r

@test("T18 — Depseudonimizacja z tokenem wielokrotnym (ten sam token kilka razy)")
def t18():
    """Token wielokrotny musi być zastąpiony we wszystkich wystąpieniach."""
    original = "Jan Kowalski podpisał umowę. Jan Kowalski jest stroną. Podpis: Jan Kowalski."
    r = send_preview(original)
    restored = depseudo_python(r.get("anonymized_preview", ""), r.get("tokens", []))
    count_original = original.lower().count("jan kowalski")
    count_restored = restored.lower().count("jan kowalski")
    if count_restored == count_original:
        ok(f"Token wielokrotny odtworzony {count_restored}x (oczekiwano {count_original}x)")
    else:
        fail(f"Token wielokrotny odtworzony {count_restored}x zamiast {count_original}x")
    return r

@test("T19 — Trie: encja dodana ręcznie nie wchłania tokenu z adresu")
def t19():
    """FIX-TRIE-TRIM: encja z /profile/add-entity powinna być przycinana do pierwszej nowej linii."""
    res = requests.post(
        f"{BASE_URL}/profile/add-entity",
        headers=_AUTH_HEADERS,
        json={"text": "Firma Testowa Sp. z o.o.\nADRES_001", "token_type": "FIRMA"},
        timeout=10,
    )
    data = res.json()
    if data.get("ok"):
        token_id = data.get("token_id", "")
        ok(f"Encja dodana jako {token_id}")
        if token_id.startswith("FIRMA"):
            ok("Typ tokenu poprawny — trim zadziałał")
        else:
            warn(f"Nieoczekiwany typ tokenu: {token_id}")
    else:
        fail(f"Błąd dodawania encji: {data.get('error', '?')}")
    return data

@test("T20 — Firmy w cudzysłowie typograficznym (normalizacja przed NER)")
def t20():
    """FIX-QUOTES: cudzysłów „" musi być znormalizowany przed NER."""
    r = send_preview('Zleceniodawca: „Wiśniewski Consulting" Sp. z o.o., ul. Lipowa 1, Kraków.')
    firma_origs = [t.get("original", "") for t in tokens_of_type(r, "FIRMA")]
    osoba_origs = [t.get("original", "") for t in tokens_of_type(r, "OSOBA")]
    if any("Wiśniewski Consulting" in o for o in firma_origs):
        ok("Firma w cudzysłowie wykryta jako FIRMA")
    elif any("Wiśniewski" in o for o in osoba_origs):
        fail("Firma rozbita — 'Wiśniewski' trafił jako OSOBA (normalizacja cudzysłowów nie działa)")
    else:
        warn("Firma nie wykryta ani jako FIRMA ani OSOBA — SpaCy pominął")
    assert_masked(r, "Wiśniewski Consulting", "Nazwa firmy")
    return r

@test("T21 — Adres z prefiksem os. (osiedle — bug: SpaCy bierze nazwę za OSOBA)")
def t21():
    """Prefix 'os.' nie obsługiwany przez _ADDR_RE — SpaCy wykrywa patronimik jako osobę."""
    r = send_preview("Zamieszkały: os. Bolesława Chrobrego 12/3, 61-550 Poznań.")
    anon = r.get("anonymized_preview", "")
    assert_masked(r, "Bolesława Chrobrego 12", "Adres z os.")
    osoba_origs = [t.get("original", "") for t in tokens_of_type(r, "OSOBA")]
    if any("Bolesława Chrobrego" in o or "Bolesław" in o for o in osoba_origs):
        fail("'Bolesława Chrobrego' wykryty jako OSOBA — patronimiczna nazwa osiedla")
        fail(f"  Tokeny OSOBA: {[o[:40] for o in osoba_origs]}")
    else:
        ok("Brak false positive OSOBA dla nazwy osiedla")
    info(f"Tokeny ADRES: {len(tokens_of_type(r, 'ADRES'))}")
    return r

@test("T22 — Nr dowodu osobistego (format ABC 123456 — bug: trafia jako ADRES)")
def t22():
    """Regex dla formatu ABC 123456 brakuje w anonymizer.py — powinien być NUMER nie ADRES."""
    r = send_preview("Tożsamość potwierdzona dowodem osobistym seria ABC nr 123456.")
    assert_masked(r, "ABC 123456", "Nr dowodu osobistego")
    numer_origs = [t.get("original", "") for t in tokens_of_type(r, "NUMER")]
    adres_origs = [t.get("original", "") for t in tokens_of_type(r, "ADRES")]
    if any("ABC" in o for o in numer_origs):
        ok("Nr dowodu jako NUMER — poprawna klasyfikacja")
    elif any("ABC" in o for o in adres_origs):
        fail("Nr dowodu trafił jako ADRES — błędna klasyfikacja")
    else:
        warn("Nr dowodu zakryty przez Guard (redakcja), nie przez pipeline (brak tokenu) — "
             "wartość nie wycieka ale typ PII niezarejestrowany w reverse_map")
    return r

@test("T23 — Data urodzenia (format ur. DD.MM.RRRR — bug: nie zakryta)")
def t23():
    """Regex 'ur. DD.MM.RRRR' brakuje w anonymizer.py."""
    r = send_preview(
        "Dane osobowe: Jan Kowalski, ur. 12.04.1990 w Gdańsku, "
        "zam. ul. Zielona 1, 80-001 Gdańsk."
    )
    assert_masked(r, "ur. 12.04.1990", "Data urodzenia")
    if original_masked(r, "Gdańsku"):
        ok("Miasto urodzenia zakryte")
    else:
        warn("Miasto urodzenia 'Gdańsku' widoczne (w połączeniu z datą to PII)")
    return r

@test("T24 — Instytucje publiczne (Sąd Rejonowy + Wydział — bug: niezamaskowane)")
def t24():
    """Brak typu INSTYTUCJA lub rozszerzenia FIRMA o instytucje publiczne."""
    r = send_preview(
        "Sprawa prowadzona przez Sąd Rejonowy dla Krakowa-Śródmieścia "
        "w Krakowie, Wydział I Cywilny, sygn. akt I C 123/2026."
    )
    assert_masked(r, "Sąd Rejonowy dla Krakowa-Śródmieścia", "Sąd Rejonowy")
    assert_masked(r, "Wydział I Cywilny", "Wydział")
    if original_masked(r, "I C 123/2026"):
        ok("Sygnatura akt zakryta")
    else:
        warn("Sygnatura akt widoczna (może być PII kontekstowe)")
    info(f"Tokeny FIRMA: {len(tokens_of_type(r, 'FIRMA'))}")
    return r

@test("T25 — Dokument prawny (kombinacja: osoba + firma + sąd + kwota + adres)")
def t25():
    """Realistyczny fragment umowy najmu — gęste PII różnych typów naraz."""
    text = (
        "UMOWA NAJMU zawarta w Krakowie dnia 15.05.2026 r. między:\n"
        "1. Janem Kowalskim, PESEL 85010112345, zam. ul. Długa 5/2, 31-001 Kraków\n"
        "   (dalej: Wynajmujący)\n"
        "2. ABC Development Sp. z o.o., NIP 527-285-30-52, KRS 0000123456,\n"
        "   ul. Marszałkowska 1, 00-001 Warszawa (dalej: Najemca)\n"
        "Czynsz najmu: 3 500,00 PLN miesięcznie.\n"
        "Kontakt: jan.kowalski@gmail.com, tel. +48 512 345 678"
    )
    r = send_preview(text)
    checks = [
        ("Jan Kowalski",           "OSOBA"),
        ("85010112345",            "PESEL"),
        ("ul. Długa 5",            "ADRES"),
        ("ABC Development",        "FIRMA"),
        ("527-285-30-52",          "NIP"),
        ("3 500,00 PLN",           "KWOTA"),
        ("jan.kowalski@gmail.com", "EMAIL"),
        ("512 345 678",            "TELEFON"),
    ]
    masked_count = 0
    for value, label in checks:
        if original_masked(r, value):
            ok(f"{label}: '{value[:30]}' zakryty")
            masked_count += 1
        else:
            fail(f"{label}: '{value[:30]}' WIDOCZNY")
    info(f"Łącznie zakrytych: {masked_count}/{len(checks)}")
    if masked_count < len(checks):
        fail(f"Nie wszystkie typy PII zakryte ({masked_count}/{len(checks)})")
    return r

# ── Runner ────────────────────────────────────────────────────────────────────

def check_health() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        data = r.json()
        print(f"\n{BOLD}=== Stan backendu ==={RESET}")
        print(f"  status:     {data.get('status')}")
        print(f"  anonymizer: {data.get('anonymizer')}")
        print(f"  spacy_ner:  {data.get('spacy_ner')}")
        print(f"  morfeusz:   {data.get('morfeusz')}")
        print(f"  crypto_ok:  {data.get('crypto_ok')}")
        if not data.get("anonymizer"):
            warn("Anonymizer NIEDOSTĘPNY — warstwy regex wyłączone")
        if not data.get("spacy_ner"):
            warn("SpaCy NER NIEDOSTĘPNY — detekcja osób/firm wyłączona")
        return True
    except requests.exceptions.ConnectionError:
        print(f"\n{RED}BŁĄD: Backend nie odpowiada na {BASE_URL}{RESET}")
        print("Uruchom backend przed testami (uruchom_tauri_dev.vbs lub python pseudominizer_api.py)")
        return False
    except Exception as e:
        print(f"\n{RED}BŁĄD health check: {e}{RESET}")
        return False


def run_all():
    if not check_health():
        sys.exit(1)

    print(f"\n{BOLD}=== Uruchamiam {len(TESTS)} testów ==={RESET}\n")

    passed = 0
    failed = 0
    errors = 0
    results_detail = []

    for name, fn in TESTS:
        print(f"{BOLD}{name}{RESET}")
        try:
            global _current_test_failed
            _current_test_failed = False
            result = fn()
            api_error = isinstance(result, dict) and result.get("error")
            if api_error or _current_test_failed:
                if api_error:
                    warn(f"API zwróciło error: {result['error']}")
                failed += 1
            else:
                passed += 1
        except requests.exceptions.ConnectionError:
            fail("Brak połączenia z backendem")
            errors += 1
        except requests.exceptions.HTTPError as e:
            fail(f"HTTP {e.response.status_code}: {e.response.text[:100]}")
            errors += 1
        except Exception as e:
            fail(f"Wyjątek: {type(e).__name__}: {e}")
            errors += 1
        print()

    print(f"{BOLD}=== Podsumowanie ==={RESET}")
    print(f"  {GREEN}Zakończone:{RESET} {passed}")
    print(f"  {RED}Nieudane:  {RESET} {failed}")
    print(f"  {YELLOW}Błędy:     {RESET} {errors}")
    print(f"  Łącznie:    {len(TESTS)}")

    if failed == 0 and errors == 0:
        print(f"\n{GREEN}{BOLD}Wszystkie testy przeszły.{RESET}")
    else:
        print(f"\n{YELLOW}{BOLD}Są nieprawidłowości — sprawdź wyniki powyżej.{RESET}")


if __name__ == "__main__":
    run_all()
