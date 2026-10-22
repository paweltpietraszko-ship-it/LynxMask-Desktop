"""[LYNX-GUARD-A] Ostrzeżenia Guarda R1–R5 (brief v2 `tasks/LYNX-GUARD-RESIDUE/brief.md`, S4 22.10) — teksty syntetyczne."""
import pytest

from guard_residue import collect_warnings, shift_warnings


def _frags(text, **kw):
    return {w["fragment"]: w["rules"] for w in collect_warnings(text, **kw)}


@pytest.mark.parametrize("text,fragment,rule", [
    ("Świadek Śludkowskiego nie stawił się na rozprawę.", "Śludkowskiego", "R1"),
    ("Wczoraj Kawa zlecił wysłanie paczki.", "Kawa", "R1"),
    ("Przyszedł Pan Rogalik z wnioskiem.", "Rogalik", "R1"),
    ("Protokół podpisał Marcin S. w obecności świadków.", "Marcin S.", "R2"),
    ("Protokół podpisał OSOBA_001 S. w obecności świadków.", "S.", "R2"),
    ("NIP: 7 NUMER_021", "7", "R3"),
    ("zamieszkały: ADRES_003, 32-5 00 Chrzanow", "32-5 00 Chrzanow", "R3"),
    ("Nr działki 128/7 w obrębie.", "128/7", "R4"),
    ("Klient urodzony 12.03.1985 r. w szpitalu.", "12.03.1985", "R4"),
    ("Sprzedawca: Biuro Rachunkowe RACHMISTRZ", "Biuro Rachunkowe RACHMISTRZ", "R5"),
    ("Nabywca: ALFA sp. z o.o.", "ALFA sp. z o.o.", "R5"),
    ("Umowę zawarto z BETA S.A. w dniu podpisania.", "BETA S.A.", "R5"),
    # Codex F1 r1: słowa z szerokiej listy instytucji R1 nie wyłączają firmy z formą prawną ani z roli kontrahenta
    ("Kontrahent: Centrum Projektowe MODRZEW sp. z o.o.", "Centrum Projektowe MODRZEW sp. z o.o.", "R5"),
    ("Kontrahent: Instytut Projektowy MODRZEW sp. z o.o.", "Instytut Projektowy MODRZEW sp. z o.o.", "R5"),
    ("Kontrahent: MODRZEW sp. z o.o.", "MODRZEW sp. z o.o.", "R5"),
    ("Zleceniodawca: Fundusz Inwestycyjny ORZEŁ", "Fundusz Inwestycyjny ORZEŁ", "R5"),
    # [LYNX-GUARD-B ROZSZERZENIE CC] nazwa z roli kończy się na końcu zdania
    ("Sprzedawca: Biuro Rachunkowe RACHMISTRZ. Wczoraj przyszła faktura.", "Biuro Rachunkowe RACHMISTRZ", "R5"),
    ("Nabywca: GAMMA S.A. Termin płatności 14 dni.", "GAMMA S.A.", "R5"),
    # [LYNX-GUARD-FIX1] kolumny: nazwa z lewej kolumny bez prawej, bez znaku końca linii
    ("Sprzedawca: Biuro Rachunkowe RACHMISTRZ          Nabywca: OSOBA_001\r\n", "Biuro Rachunkowe RACHMISTRZ", "R5"),
])
def test_wskazuje_jawna_pozostalosc(text, fragment, rule):
    found = _frags(text)
    assert fragment in found and rule in found[fragment], found


@pytest.mark.parametrize("text", [
    "Pozew wniesiono do Sąd Rejonowy w Poznaniu.",
    "FIRMA_001, NUMER_021",
    "Warszawa, dnia 21.10.2026",
    "Zamawiający zleca, a Wykonawca przyjmuje. Strony ustalają, że Umowa wchodzi w życie.",
    "Spotkanie odbyło się w Kaliszu oraz w Warszawie.",
    "Zgodnie z art. 5 ust. 2 Dz.U. nr 12 poz. 45 Strony postanawiają.",
    "Nabywca: Gmina Kraków",
    "Odbiorca: Urząd Skarbowy w Radomiu",
    "Płatnik: ZUS Oddział w Warszawie",
    # [LYNX-GUARD-FIX1] OWNER 22.10, `Pliki testowe/doc_stresstest_silnik_guard_lvl0_3.txt` l. 112–113: dwie kolumny, CRLF
    "Sprzedawca:                              Nabywca:\r\nFIRMA_001              Przychodnia Rejonowa „Zdrowie”\r\n",
    "Odbiorca:\r\nPrzychodnia Rejonowa w Krakowie przyjmuje pacjentów.",
    "Dostawca: FIRMA_002 ul. Długa",
    "Sygn. akt I C 123/24. Rozprawa odbędzie się w Sądzie.",
    # pomiar 22.10 (150 dok. OCR): największe źródła fałszywych R1
    "Organ: Urząd Marszałkowski Województwa Mazowieckiego, Wydział Ochrony Środowiska.",
    "Wydał Urząd Gminy Warszawa-Wola w sprawie.",
    "Niniejszym wzywa Panią/Pana do zapłaty.",
    "Umowa z OSOBA_001, zwanym dalej „Zleceniobiorcą”, na okres próbny.",
    "Siedziba w dzielnicy Kraków-Śródmieście od roku.",
    "Odpis wydano dnia 2 NUMER_005 w sekretariacie.",
    "Marek OSOBA_001\n4 ADRES_001",
])
def test_brak_alarmu(text):
    assert _frags(text) == {}


def test_jedno_wystapienie_z_wielu_powodow_to_jedna_pozycja():
    ws = collect_warnings("Sprzedawca: ALFA sp. z o.o.")
    assert len(ws) == 1 and ws[0]["rules"] == ["R5"] and ws[0]["id"] == "W001"


def test_map_leak_bez_wielkosci_liter_i_poziom_red():
    ws = collect_warnings("Pismo od OSOBA_001, w stopce KOWALSKI.", map_values=["Kowalski"])
    assert [(w["fragment"], w["level"]) for w in ws] == [("KOWALSKI", "RED")]


def test_nic_wewnatrz_tokenow():
    ws = collect_warnings("Kontakt: NUMER_123 oraz FIRMA_001.")
    assert ws == []


def test_allowlista_wycisza_fragment():
    assert _frags("Wczoraj Kawa zlecił wysłanie paczki.", allowlist=["kawa"]) == {}


def test_przesuniecie_o_naglowek_pse():
    text = "Świadek Śludkowskiego nie stawił się."
    w = shift_warnings(collect_warnings(text), 10)[0]
    assert ("x" * 10 + text)[w["start"]:w["end"]] == "Śludkowskiego"
