"""
generate_lookups_v3.py
Fix: GUS serwuje XLSX (ZIP) zamiast CSV — parser przez stdlib zipfile + xml.
"""

import json, csv, io, zipfile, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FIRST_NAMES = [
    "Jan","Marek","Tomasz","Piotr","Paweł","Krzysztof","Andrzej","Michał",
    "Marcin","Łukasz","Adam","Grzegorz","Maciej","Bartosz","Jacek","Zbigniew",
    "Tadeusz","Stanisław","Dariusz","Mariusz","Wojciech","Ryszard","Henryk",
    "Arkadiusz","Radosław","Robert","Przemysław","Sebastian","Mateusz","Jakub",
    "Kamil","Dawid","Karol","Rafał","Damian","Mirosław","Sławomir","Leszek",
    "Cezary","Wiesław","Zenon","Jerzy","Waldemar","Zygmunt","Władysław",
    "Kazimierz","Edward","Józef","Aleksander","Artur","Filip","Oskar","Igor",
    "Dominik","Patryk","Kacper","Hubert","Wiktor","Adrian","Konrad","Norbert",
    "Ireneusz","Bogdan","Bogusław","Wacław","Czesław","Mieczysław","Roman",
    "Stefan","Franciszek","Leon","Witold","Juliusz","Sylwester","Tobiasz",
    "Benedykt","Cyprian","Klemens","Feliks","Teodor","Bernard",
    "Anna","Maria","Katarzyna","Małgorzata","Agnieszka","Barbara","Ewa",
    "Zofia","Krystyna","Joanna","Monika","Magdalena","Elżbieta","Teresa",
    "Jadwiga","Beata","Iwona","Halina","Grażyna","Danuta","Irena","Wanda",
    "Urszula","Renata","Bożena","Zuzanna","Alicja","Dorota","Helena","Janina",
    "Julita","Klaudia","Lidia","Natalia","Patrycja","Sandra","Sylwia",
    "Wioletta","Karolina","Paulina","Aleksandra","Marta","Justyna","Ewelina",
    "Aneta","Dominika","Edyta","Kinga","Sabina","Mariola","Jolanta","Daria",
    "Emilia","Gabriela","Hanna","Laura","Michalina","Nina","Oliwia","Roksana",
    "Weronika","Amelia","Izabela","Julia","Kamila","Milena","Olga","Wiktoria",
    "Żaneta","Agata","Angelika","Blanka","Celina","Elwira","Faustyna",
    "Honorata","Jagoda","Kalina","Malwina","Rozalia","Tatiana","Walentyna",
    "Ksenia","Anastazja","Władysława","Stanisława","Cecylia","Łucja","Regina",
    "Genowefa","Leokadia","Mirosława","Aldona",
    # --- ZDROBNIENIA I FORMY POTOCZNE ---
    "Ania", "Kasia", "Magda", "Zosia", "Basia", "Gosia",
    "Ola", "Asia", "Iza", "Ela", "Monia", "Aga",
    "Piotrek", "Tomek", "Janek", "Jaś", "Jasiu", "Kuba", "Wojtek",
    "Krzysiek", "Darek", "Tadek", "Staszek", "Zbyszek", "Romek", "Leszek",
]

SURNAMES_FALLBACK = [
    "Nowak","Kowalski","Kowalska","Wiśniewski","Wiśniewska","Wójcik",
    "Kowalczyk","Kamiński","Kamińska","Lewandowski","Lewandowska",
    "Zieliński","Zielińska","Szymański","Szymańska","Woźniak",
    "Dąbrowski","Dąbrowska","Kozłowski","Kozłowska","Jankowski","Jankowska",
    "Mazur","Kwiatkowski","Kwiatkowska","Krawczyk","Piotrowski","Piotrowska",
    "Grabowski","Grabowska","Nowakowski","Nowakowska","Pawłowski","Pawłowska",
    "Michalski","Michalska","Nowicki","Nowicka","Adamczyk","Dudek",
    "Zając","Wieczorek","Jabłoński","Jabłońska","Malinowski","Malinowska",
    "Sadowski","Sadowska","Baran","Wróbel","Szewczyk","Tomaszewski","Tomaszewska",
    "Pietrzak","Walczak","Sikora","Głowacki","Głowacka","Olejnik",
    "Borkowski","Borkowska","Wróblewski","Wróblewska","Jaworski","Jaworska",
    "Tkaczyk","Majewski","Majewska","Janik","Witkowski","Witkowska",
    "Nawrocki","Nawrocka","Bąk","Chmielewski","Chmielewska","Górski","Górska",
    "Kaczmarek","Czajkowski","Czajkowska","Stępień","Marciniak","Kołodziej",
    "Zawadzki","Zawadzka","Kubiak","Mazurek","Rutkowski","Rutkowska",
    "Polak","Kucharski","Kucharska","Wasilewski","Wasilewska",
    "Wysocki","Wysocka","Olszewski","Olszewska","Urbański","Urbańska",
    "Brzeziński","Brzezińska","Wilk","Sokołowski","Sokołowska",
    "Błaszczyk","Wojciechowski","Wojciechowska","Lis","Wierzbicki","Wierzbicka",
    "Duda","Markowski","Markowska","Zalewski","Zalewska",
    "Szczepański","Szczepańska","Jakubowski","Jakubowska",
    "Krupa","Szulc","Piątkowski","Piątkowska","Orzechowski","Orzechowska",
    "Jasiński","Jasińska","Kalinowski","Kalinowska","Maciejewski","Maciejewska",
    "Andrzejewski","Andrzejewska","Czerwiński","Czerwińska",
    "Dobrowolski","Dobrowolska","Wolski","Wolska","Bielski","Bielska",
    "Rybak","Kozak","Różański","Różańska","Zagórski","Zagórska",
    "Sobczak","Sobczyk","Przybylski","Przybylska","Witek","Pawlak",
    "Kędzierski","Kędzierska","Stasiak","Ziółkowski","Ziółkowska",
    "Śliwka","Filipiak","Kasprzak","Klimek","Klimczak","Grzelak",
    "Wawrzyniak","Bednarek","Bednarz","Bednarczyk","Bednarski","Bednarska",
    "Skrzypek","Skrzypczak","Siwek","Siwiński","Siwińska",
    "Stankiewicz","Głębocki","Głębocka","Zaremba","Wojtas","Wojtasik",
    "Gajewski","Gajewska","Łapiński","Łapińska","Kubicki","Kubicka",
    "Sobieraj","Nowaczyński","Nowaczyńska","Michalczyk","Michalik",
    "Niedziela","Niedzielski","Sobota","Dąbek","Łukasik",
    "Nowacki","Nowacka","Grzybowski","Grzybowska",
    "Zaborski","Zaborska","Gruszka","Gruszecki","Gruszecka",
    "Kurowski","Kurowska","Przybyszewski","Przybyszewska",
    "Brzozowski","Brzozowska","Pająk","Okoń","Okońska",
    "Janowiak","Lewicki","Lewicka","Pisarski","Pisarska",
    "Sobieski","Sobieska","Kowalewski","Kowalewska",
    "Wierzbowski","Wierzbowska","Jóźwiak","Jóźwik",
    "Wieruszewski","Wieruszewska","Zaremba","Zarembski","Zarembska",
    "Kasprzyk","Oleksy","Oleksiak","Łączny","Łączna",
    "Grobelny","Grobelna","Krakowski","Krakowska",
    "Szczepanik","Szczepaniak","Filipek","Grzelka",
    "Paluch","Paluszek","Niemczyk","Niemczak",
    "Stachowiak","Stachowska","Stachowski",
    "Wiśniak","Wiśnicki","Wiśnicka","Lisowski","Lisowska",
    "Kwiecień","Kwiecińska","Kwieciński",
    "Czarnecki","Czarnecka","Czarny","Czarna",
    "Kwaśniewski","Kwaśniewska","Kwaśny",
    "Dróżdż","Drożdż","Drożdżewski","Drożdżewska",
    "Olszak","Olszak","Ostrowska","Ostrowski","Ostrowiec",
    "Wójcicki","Wójcicka","Szczygieł","Szczygielski",
    "Hołda","Hołyst","Holendro","Adamski","Adamska",
    "Bartosik","Bartoszewicz","Bartoszewski","Bartoszewska",
    "Bogacki","Bogacka","Bochenek","Bocheński","Bocheńska",
    "Broda","Brodowski","Brodowska","Bróg","Broż",
    "Buczek","Buczkowski","Buczkowska","Budziński","Budzińska",
    "Bylica","Bylicka","Byrski","Bystrzycki","Bystrzycka",
    "Chojnacki","Chojnacka","Chojnowski","Chojnowska",
    "Cichocki","Cichocka","Cichy","Cicha","Cichoń",
    "Dębski","Dębska","Długosz","Długoszewski",
    "Godlewski","Godlewska","Golec","Golecki","Golecka",
    "Grad","Gradowski","Gralak","Grala","Gramowski",
    "Jakimowicz","Jakimowski","Janas","Janasz","Janiec",
    "Jurczak","Jurczyk","Jurek","Jurkiewicz","Jurkiewcz",
    "Kałuża","Kałużny","Kałużna","Karwowski","Karwowska",
    "Kasperek","Kasperczyk","Kasperczak","Kasperkiewicz",
    "Kobus","Kobyłecki","Kobylański","Kobylańska",
    "Komorowski","Komorowska","Konopka","Kopczyński","Kopczyńska",
    "Kraśnicki","Kraśnicka","Kraśnik","Krawczewski","Krawczewska",
    "Krzemiński","Krzemińska","Krzyżanowski","Krzyżanowska",
    "Lewicki","Lewicka","Lipski","Lipska","Lipiec",
    "Łukasiewicz","Łukasik","Maciąg","Maciągowski","Maciągowska",
    "Mądry","Mądra","Mądrowski","Miotk","Miotke",
    "Mróz","Mrozek","Mrozowski","Mrozowska",
    "Muszyński","Muszyńska","Musiał","Musiałek",
    "Napierała","Napieralski","Napieralska",
    "Olczak","Olczyk","Olejniczak","Olejniczyk",
    "Pałka","Pałkowski","Pałkowska","Paprocki","Paprocka",
    "Podgórski","Podgórska","Podolski","Podolska",
    "Sałata","Sałatka","Sałkowski","Sałkowska",
    "Skibicki","Skibicka","Skibiński","Skibińska",
    "Słomka","Słomkowski","Słomkowska","Słomczyński","Słomczyńska",
    "Smolak","Smolański","Smolańska","Smolarski","Smolarska",
    "Staniek","Staniewicz","Stanisławski","Stanisławska",
    "Szafrański","Szafrańska","Szałas","Szymczak","Szymczyk",
    "Świderski","Świderska","Świtała","Świtała","Tarnowski","Tarnowska",
    "Trojanowski","Trojanowska","Twardowski","Twardowska",
    "Urbaniak","Urbanek","Urbańczyk","Urbańczykowa",
    "Wesołowski","Wesołowska","Wierzbicki","Wierzbicka",
    "Więcławski","Więcławska","Włodarski","Włodarska",
    "Woźnicki","Woźnicka","Wróblewski","Wróblewska",
    "Wysocka","Wysocki","Zając","Zaleska","Zaleski",
    "Zarzycki","Zarzyckia","Zawisza","Zawiszewski",
    "Zieliński","Zielińska","Ziółek","Ziółkowski","Ziółkowska",
    "Żółtowski","Żółtowska","Żuk","Żukowski","Żukowska",
]


def get_inflections(morf, word):
    forms = set()
    for candidate in {word, word.capitalize()}:
        try:
            for interp in morf.analyse(candidate):
                f = interp[2][0].lower()
                if len(f) >= 2:
                    forms.add(f)
            for gen in morf.generate(candidate):
                f = gen[0].lower()
                if len(f) >= 2:
                    forms.add(f)
        except Exception:
            pass
    forms.add(word.lower())
    return sorted(forms)


NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def parse_xlsx_bytes(raw_bytes):
    """
    Parsuje XLSX (ZIP+XML) przez stdlib. Zero zewnętrznych zależności.
    Zwraca listę wartości z pierwszej kolumny (z pominięciem nagłówka).
    """
    results = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            names_in_zip = z.namelist()

            # 1. Wczytaj shared strings
            shared = []
            if "xl/sharedStrings.xml" in names_in_zip:
                with z.open("xl/sharedStrings.xml") as f:
                    tree = ET.parse(f)
                for si in tree.findall(f".//{{{NS}}}si"):
                    text = "".join(
                        t.text or ""
                        for t in si.findall(f".//{{{NS}}}t")
                    )
                    shared.append(text)

            # 2. Znajdź arkusz (sheet1 lub pierwszy dostępny)
            sheet_path = next(
                (n for n in names_in_zip if "worksheets/sheet" in n),
                None
            )
            if not sheet_path:
                print("  Brak arkusza w XLSX")
                return results

            with z.open(sheet_path) as f:
                tree = ET.parse(f)

            header_skipped = False
            for row in tree.findall(f".//{{{NS}}}row"):
                cells = row.findall(f"{{{NS}}}c")
                if not cells:
                    continue
                if not header_skipped:
                    header_skipped = True
                    continue

                # Pierwsza komórka
                cell = cells[0]
                cell_type = cell.get("t", "")
                v_el = cell.find(f"{{{NS}}}v")
                if v_el is None or not v_el.text:
                    continue

                if cell_type == "s":
                    idx = int(v_el.text)
                    value = shared[idx] if idx < len(shared) else ""
                else:
                    value = v_el.text

                value = value.strip()
                if value and len(value) >= 2:
                    results.append(value)

    except Exception as e:
        print(f"  Błąd parsowania XLSX: {e}")

    return results


def fetch_gus_surnames(max_count=1000):
    print("  Pobieram listę nazwisk z GUS API...")
    surnames = []
    seen = set()

    for resource_id in ["44647", "44646"]:
        try:
            meta_url = f"https://api.dane.gov.pl/1.4/resources/{resource_id}"
            req = urllib.request.Request(
                meta_url,
                headers={"Accept": "application/json", "User-Agent": "LynxMask/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                meta = json.loads(resp.read().decode("utf-8"))

            attrs = meta.get("data", {}).get("attributes", {})
            download_url = (
                attrs.get("download_url") or
                attrs.get("csv_download_url") or
                meta.get("attributes", {}).get("download_url", "")
            )

            if not download_url:
                print(f"  Brak download_url dla resource {resource_id}")
                continue

            print(f"  Pobieram: ...{download_url[-50:]}")
            with urllib.request.urlopen(download_url, timeout=30) as resp:
                raw = resp.read()

            # Sprawdź czy to XLSX (sygnatura ZIP: PK = 0x50 0x4B)
            if raw[:2] == b"PK":
                print(f"  Format: XLSX — parsowanie przez zipfile")
                names_from_file = parse_xlsx_bytes(raw)
            else:
                print(f"  Format: CSV — parsowanie przez csv")
                for enc in ["utf-8-sig", "utf-8", "cp1250", "iso-8859-2"]:
                    try:
                        content = raw.decode(enc)
                        break
                    except Exception:
                        continue
                first_line = content.split("\n")[0]
                sep = ";" if ";" in first_line else ","
                reader = csv.reader(io.StringIO(content), delimiter=sep)
                names_from_file = []
                header_skipped = False
                for row in reader:
                    if not header_skipped:
                        header_skipped = True
                        continue
                    if row and row[0].strip():
                        names_from_file.append(row[0].strip())

            count = 0
            for name in names_from_file:
                name_lower = name.lower()
                if name_lower not in seen and len(name) >= 2:
                    if all(c.isalpha() or c in "-– " for c in name):
                        seen.add(name_lower)
                        surnames.append(
                            name if (name and name[0].isupper()) else name.capitalize()
                        )
                        count += 1
            print(f"  Resource {resource_id}: {count} nazwisk")

        except Exception as e:
            print(f"  Błąd dla resource {resource_id}: {e}")
            continue

        if len(surnames) >= max_count:
            break

    print(f"  Łącznie z GUS: {len(surnames)} nazwisk")
    return surnames[:max_count]


def main():
    import morfeusz2

    print("=" * 55)
    print("  LynxMask — Generator lookup tables v3")
    print("=" * 55)

    print("\nŁaduję Morfeusz2...")
    morf = morfeusz2.Morfeusz()
    print("OK")

    # ── [1/2] IMIONA ──────────────────────────────────────
    print(f"\n[1/2] Generuję formy dla {len(FIRST_NAMES)} imion...")
    names_result = {}
    for i, name in enumerate(FIRST_NAMES):
        names_result[name.lower()] = get_inflections(morf, name)
        if (i + 1) % 30 == 0:
            print(f"      {i+1}/{len(FIRST_NAMES)}")

    single_names = sum(1 for v in names_result.values() if len(v) == 1)
    print(f"  Imiona z 1 formą: {single_names}")
    out_names = Path("names_inflected.json")
    out_names.write_text(
        json.dumps(names_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(len(v) for v in names_result.values())
    print(f"  ✓ {out_names}  ({len(names_result)} imion, {total} form)")

    # ── [2/2] NAZWISKA ─────────────────────────────────────
    print(f"\n[2/2] Pobieranie i generacja form nazwisk...")
    surnames = fetch_gus_surnames(max_count=1000)

    if len(surnames) < 100:
        print(f"  Pobrano za mało ({len(surnames)}) — używam listy awaryjnej.")
        seen = set()
        surnames = []
        for s in SURNAMES_FALLBACK:
            if s.lower() not in seen:
                seen.add(s.lower())
                surnames.append(s)
        print(f"  Lista awaryjna: {len(surnames)} nazwisk")

    print(f"  Generuję formy Morfeusz2...")
    surnames_result = {}
    for i, surname in enumerate(surnames):
        surnames_result[surname.lower()] = get_inflections(morf, surname)
        if (i + 1) % 100 == 0:
            print(f"      {i+1}/{len(surnames)}")

    single_s = sum(1 for v in surnames_result.values() if len(v) == 1)
    print(f"  Nazwiska z 1 formą: {single_s}")
    out_surnames = Path("surnames_top1000.json")
    out_surnames.write_text(
        json.dumps(surnames_result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(len(v) for v in surnames_result.values())
    print(f"  ✓ {out_surnames}  ({len(surnames_result)} nazwisk, {total} form)")

    print("\n✅ Gotowe!")
    print(f"   names_inflected.json  →  {out_names.stat().st_size // 1024} KB")
    print(f"   surnames_top1000.json →  {out_surnames.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
