import requests
import os
import pandas as pd
import sys
import time


# ════════════════════════════════════════════════════════════════════
# KONFIGURACIJA
# ════════════════════════════════════════════════════════════════════

# Funkcija za bezbedno konvertovanje vrednosti
def safe_value(value, default='', data_type=str):
    if pd.isna(value):
        return default
    if data_type == int:
        return int(float(value)) if isinstance(value, (float, str)) else int(value)
    if data_type == float:
        return float(value)
    return str(value)


def print_header(title, icon="📌"):
    """Štampa stilizovani header za sekciju"""
    width = 60
    print()
    print(f"  ╔{'═' * width}╗")
    print(f"  ║  {icon} {title.upper():<{width - 5}}║")
    print(f"  ╚{'═' * width}╝")


def print_subheader(title, icon="▸"):
    """Štampa manji podnaslov"""
    print(f"\n  {icon} {title}")
    print(f"  {'─' * 50}")


def print_success(msg):
    print(f"  ✅ {msg}")


def print_error(msg):
    print(f"  ❌ {msg}")


def print_warning(msg):
    print(f"  ⚠️  {msg}")


def print_info(msg):
    print(f"  ℹ️  {msg}")


def print_item(msg):
    print(f"     ├─ {msg}")


def print_progress(current, total, name, status_icon="⏳"):
    """Štampa progres bar sa informacijama"""
    bar_width = 25
    progress = current / total if total > 0 else 0
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    pct = progress * 100
    print(f"\r  {status_icon} [{bar}] {pct:5.1f}% ({current}/{total}) {name[:30]:<30}", end="", flush=True)


def print_results(success, failed, total, entity_name):
    """Štampa rezultate importa"""
    print(f"\n\n  ┌{'─' * 45}┐")
    print(f"  │  📊 REZULTAT: {entity_name.upper():<28}│")
    print(f"  ├{'─' * 45}┤")
    print(f"  │  ✅ Uspešno:    {success:>6}                      │")
    print(f"  │  ❌ Neuspešno:  {failed:>6}                      │")
    print(f"  │  📑 Ukupno:     {total:>6}                      │")
    print(f"  └{'─' * 45}┘")


def check_count(base_url, endpoint, entity_name):
    """Proverava broj entiteta u bazi"""
    url = f'{base_url}/{endpoint}'
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print_error(f"Neuspešna provera ({response.status_code})")
            return -1
        if response.text:
            data = response.json()
            count = int(data.get('count', 0))
            print_info(f"Trenutno u bazi: {count} {entity_name}")
            return count
        return 0
    except Exception as e:
        print_error(f"Greška pri proveri: {str(e)}")
        return -1


def pause():
    """Pauza za korisnika"""
    print()
    input("  📌 Pritisnite ENTER za nastavak...")
    print()


# ════════════════════════════════════════════════════════════════════
# GLAVNI PROGRAM
# ════════════════════════════════════════════════════════════════════

print("\n")
print("  ╔════════════════════════════════════════════════════════════╗")
print("  ║                                                            ║")
print("  ║        🔄  IMPORT PODATAKA U APLIKACIJU  🔄               ║")
print("  ║                                                            ║")
print("  ╚════════════════════════════════════════════════════════════╝")

# Dobijanje putanja
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)
directory_name = os.path.basename(parent_directory)
file_path = os.path.join(current_directory, f'{directory_name}_input_data.xlsx')

print_subheader("Radno okruženje", "📂")
print_item(f"Aplikacija:  {directory_name}")
print_item(f"Direktorijum: {current_directory}")
print_item(f"Excel fajl:  {os.path.basename(file_path)}")

# Provera Excel fajla
if not os.path.exists(file_path):
    print_error(f"Excel fajl nije pronađen: {file_path}")
    print_info("Proverite da li je fajl na pravom mestu i da li ima ispravan naziv.")
    sys.exit(1)
else:
    print_success("Excel fajl pronađen")

print(f"\n  ❓ Da li želite da započnete import? (Y/N)")
odgovor = input("     Vaš izbor: ").strip().lower()

if odgovor != 'y':
    print_warning("Import prekinut na zahtev korisnika.")
    sys.exit(0)

base_url = f'https://popis.online/{directory_name}'


# ─────────────────────────────────────────────────────────────────
# 1. ZGRADE
# ─────────────────────────────────────────────────────────────────
print_header("1/5  Zgrade", "🏢")

buildings_count = check_count(base_url, 'check_buildings_count', 'zgrada')
if buildings_count < 0:
    sys.exit(1)

if buildings_count == 0:
    try:
        df_zgrade = pd.read_excel(file_path, sheet_name='Zgrade')
        # Filtriraj prazne redove
        df_zgrade = df_zgrade.dropna(subset=['Naziv zgrade'])
        print_info(f"Učitano {len(df_zgrade)} zgrada iz Excel fajla")
    except Exception as e:
        print_error(f"Problem pri učitavanju: {str(e)}")
        sys.exit(1)

    success = 0
    errors = []

    for index, row in df_zgrade.iterrows():
        name = safe_value(row['Naziv zgrade'])
        print_progress(index + 1, len(df_zgrade), name)

        payload = {
            'school_id': '1',
            'name': name,
            'address': safe_value(row['Adresa']),
            'city': safe_value(row['Mesto'])
        }

        response = requests.post(f'{base_url}/import_building', data=payload)
        if response.status_code == 200:
            success += 1
        else:
            errors.append(f"{name}: {response.status_code} - {response.text[:80]}")

    print_results(success, len(df_zgrade) - success, len(df_zgrade), "Zgrade")
    for err in errors:
        print_error(err)
else:
    print_success(f"Zgrade već postoje u bazi ({buildings_count}). Preskačem.")

pause()


# ─────────────────────────────────────────────────────────────────
# 2. PROSTORIJE
# ─────────────────────────────────────────────────────────────────
print_header("2/5  Prostorije", "🚪")

rooms_count = check_count(base_url, 'check_rooms_count', 'prostorija')
if rooms_count < 0:
    sys.exit(1)

if rooms_count == 0:
    try:
        df_prostorije = pd.read_excel(file_path, sheet_name='Prostorije')
        df_prostorije = df_prostorije.dropna(subset=['Naziv prostorije (dinamički)'])
        print_info(f"Učitano {len(df_prostorije)} prostorija iz Excel fajla")
    except Exception as e:
        print_error(f"Problem pri učitavanju: {str(e)}")
        sys.exit(1)

    success = 0
    errors = []

    for index, row in df_prostorije.iterrows():
        name = safe_value(row['Naziv prostorije (dinamički)'])
        print_progress(index + 1, len(df_prostorije), name)

        payload = {
            'id': safe_value(row['id_prostorije'], data_type=int),
            'building_id': safe_value(row['id_zgrade'], data_type=int),
            'name': safe_value(row['Naziv prostorije (numerički)']),
            'dynamic_name': name
        }

        response = requests.post(f'{base_url}/import_room', data=payload)
        if response.status_code == 200:
            success += 1
        else:
            errors.append(f"{name}: {response.status_code} - {response.text[:80]}")

    print_results(success, len(df_prostorije) - success, len(df_prostorije), "Prostorije")
    for err in errors:
        print_error(err)
else:
    print_success(f"Prostorije već postoje u bazi ({rooms_count}). Preskačem.")

pause()


# ─────────────────────────────────────────────────────────────────
# 3. STOPE AMORTIZACIJE (sheet: Amortizacija → tabela: depreciation_rate)
# ─────────────────────────────────────────────────────────────────
print_header("3/5  Stope amortizacije", "📉")

dep_rate_count = check_count(base_url, 'check_depreciation_rates_count', 'stopa amortizacije')

if dep_rate_count == 0 or dep_rate_count < 0:
    try:
        df_amortizacija = pd.read_excel(file_path, sheet_name='Amortizacija')
        df_amortizacija = df_amortizacija.dropna(subset=['id'])
        # Ukloni redove gde rate nije numerička vrednost
        df_amortizacija = df_amortizacija[pd.to_numeric(df_amortizacija['rate'], errors='coerce').notna()]
        print_info(f"Učitano {len(df_amortizacija)} stopa amortizacije iz Excel fajla")
    except Exception as e:
        print_error(f"Problem pri učitavanju: {str(e)}")
        sys.exit(1)

    success = 0
    errors = []

    for index, row in df_amortizacija.iterrows():
        name = safe_value(row['name'])
        print_progress(success + len(errors) + 1, len(df_amortizacija), name)

        payload = {
            'id': safe_value(row['id'], data_type=int),
            'name': name,
            'rate': safe_value(row['rate'], data_type=float)
        }

        response = requests.post(f'{base_url}/import_depreciation_rate', data=payload)
        if response.status_code == 200:
            success += 1
        elif response.status_code == 202:
            success += 1  # Već postoji, računamo kao uspeh
        else:
            errors.append(f"ID={payload['id']} {name[:40]}: {response.status_code} - {response.text[:80]}")

    print_results(success, len(errors), len(df_amortizacija), "Stope amortizacije")
    for err in errors:
        print_error(err)
else:
    print_success(f"Stope amortizacije već postoje u bazi ({dep_rate_count}). Preskačem.")

pause()


# ─────────────────────────────────────────────────────────────────
# 4. KATEGORIJE / KONTA (sheet: Konta → tabela: category)
# ─────────────────────────────────────────────────────────────────
print_header("4/5  Kategorije (Konta)", "📂")

cat_count = check_count(base_url, 'check_categories_count', 'kategorija')

if cat_count == 0 or cat_count < 0:
    try:
        df_konta = pd.read_excel(file_path, sheet_name='Konta')
        df_konta = df_konta.dropna(subset=['id'])
        print_info(f"Učitano {len(df_konta)} kategorija iz Excel fajla")
    except Exception as e:
        print_error(f"Problem pri učitavanju: {str(e)}")
        sys.exit(1)

    success = 0
    errors = []

    for index, row in df_konta.iterrows():
        name = safe_value(row['name'])
        print_progress(success + len(errors) + 1, len(df_konta), name)

        payload = {
            'id': safe_value(row['id'], data_type=int),
            'category_number': safe_value(row['category_number']),
            'name': name
        }

        response = requests.post(f'{base_url}/import_category', data=payload)
        if response.status_code == 200:
            success += 1
        elif response.status_code == 202:
            success += 1
        else:
            errors.append(f"ID={payload['id']} {name[:40]}: {response.status_code} - {response.text[:80]}")

    print_results(success, len(errors), len(df_konta), "Kategorije (Konta)")
    for err in errors:
        print_error(err)
else:
    print_success(f"Kategorije već postoje u bazi ({cat_count}). Preskačem.")

pause()


# ─────────────────────────────────────────────────────────────────
# 5. PREDMETI (sheet: Pojedinačni predmeti po SERIJI → tabela: single_item)
# ─────────────────────────────────────────────────────────────────
print_header("5/5  Predmeti", "📦")

items_count = check_count(base_url, 'check_items_count', 'predmeta')
if items_count < 0:
    sys.exit(1)

if items_count == 0:
    try:
        df_predmeti = pd.read_excel(file_path, sheet_name='Pojedinačni predmeti po SERIJI')
        # Filtriraj prazne redove
        df_predmeti = df_predmeti.dropna(subset=['Serija', 'Naziv'])

        # Pronađi kolonu "Vrednost na kraju XXXX" i izvuci godinu
        value_column = next(col for col in df_predmeti.columns if str(col).startswith('Vrednost na kraju'))
        year = int(''.join(filter(str.isdigit, str(value_column))))
        last_day_of_year = f'{year}-12-31'

        print_info(f"Učitano {len(df_predmeti)} predmeta iz Excel fajla")
        print_info(f"Referentna godina: {year} (datum unosa: {last_day_of_year})")
    except Exception as e:
        print_error(f"Problem pri učitavanju: {str(e)}")
        sys.exit(1)

    success = 0
    skipped = 0
    errors = []

    for index, row in df_predmeti.iterrows():
        name = safe_value(row['Naziv'])
        serial = safe_value(row['Serija'], default='?', data_type=int)
        label = f"{name} (S:{serial})"
        print_progress(success + skipped + len(errors) + 1, len(df_predmeti), label)

        try:
            purchase_date_raw = safe_value(row['Datum nabavke'])
            purchase_date = purchase_date_raw.split()[0] if purchase_date_raw else ''

            payload = {
                'serial': safe_value(row['Serija'], default=None, data_type=int),
                'room_id': safe_value(row.get('room_id'), default=1, data_type=int),
                'name': name,
                'quantity': safe_value(row['Količina'], default=None, data_type=int),
                'purchase_date': purchase_date,
                'initial_price': safe_value(row['Nabavna vrednost'], default=None, data_type=float),
                'input_in_app_date': last_day_of_year,
                'deprecation_value': safe_value(row.get(value_column, 0), default=None, data_type=float),
                'supplier': safe_value(row.get('Dobavljač'), ''),
                'invoice_number': safe_value(row.get('Faktura'), ''),
                'category_id': safe_value(row['id konta'], default=None, data_type=int),
                'depreciation_rate_id': safe_value(row['id amortizacije'], default=None, data_type=int)
            }

            response = requests.post(f'{base_url}/import_item', data=payload)

            if response.status_code == 200:
                success += 1
            elif response.status_code == 202:
                skipped += 1
            else:
                errors.append(f"S:{serial} {name[:35]}: {response.status_code} - {response.text[:80]}")
        except Exception as e:
            errors.append(f"S:{serial} {name[:35]}: {str(e)[:80]}")

    failed = len(df_predmeti) - success - skipped
    print(f"\n")
    print(f"  ┌{'─' * 45}┐")
    print(f"  │  📊 REZULTAT: PREDMETI                      │")
    print(f"  ├{'─' * 45}┤")
    print(f"  │  ✅ Uspešno:    {success:>6}                      │")
    print(f"  │  ⏭️  Preskočeno: {skipped:>6}  (već postoji)        │")
    print(f"  │  ❌ Neuspešno:  {len(errors):>6}                      │")
    print(f"  │  📑 Ukupno:     {len(df_predmeti):>6}                      │")
    print(f"  └{'─' * 45}┘")
    for err in errors:
        print_error(err)
else:
    print_success(f"Predmeti već postoje u bazi ({items_count}). Preskačem.")


# ─────────────────────────────────────────────────────────────────
# ZAVRŠETAK
# ─────────────────────────────────────────────────────────────────
print("\n")
print("  ╔════════════════════════════════════════════════════════════╗")
print("  ║                                                            ║")
print("  ║        ✨  IMPORT PODATAKA JE ZAVRŠEN  ✨                 ║")
print("  ║                                                            ║")
print("  ╚════════════════════════════════════════════════════════════╝")
print()