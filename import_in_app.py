import requests
import os
import pandas as pd


# Dobijanje apsolutne putanje do trenutnog direktorijuma skripte
current_directory = os.path.dirname(os.path.abspath(__file__))
# Uzimamo pretposlednji direktorijum iz putanje
parent_directory = os.path.dirname(current_directory)
directory_name = os.path.basename(parent_directory)
file_path = os.path.join(current_directory, f'{directory_name}_input_data.xlsx')

print(f'Radni direktorijum: {file_path=}.')
print(f'Naziv direktorijuma: {directory_name=}.')
print(f'Trenutni direktorijum: {current_directory=}.')

input(f'Da li želiš da nastaviš? (Y/N) ')
if input().lower() != 'y':
    print(f'Prekinut unos podataka.')
    exit()

# Postavite URL na koji želite slati zahteve
base_url = f'https://popis.online/{directory_name}'
url = f'{base_url}/import_in_app'  # URL za unos podataka

# Prvo proverite broj zgrada na serveru
check_buildings_url = f'{base_url}/check_buildings_count'
response = requests.get(check_buildings_url)
buildings_count = 0

if response.status_code == 200:
    buildings_count = int(response.json().get('count', 0))

# Ako nema zgrada na serveru, prvo unesite zgrade
if buildings_count == 0:
    print("Nema zgrada u bazi. Započinjem unos zgrada...")
    # Učitajte podatke iz Excel fajla (Zgrade) u DataFrame
    df_zgrade = pd.read_excel(file_path, sheet_name='Zgrade')
    buildings_success = 0
    for index, row in df_zgrade.iterrows():
        building_payload = {
            'school_id': '1',  # Fiksan school_id
            'name': str(row['Naziv zgrade']),
            'address': str(row['Adresa']),
            'city': str(row['Mesto'])
        }
        
        # Slanje POST zahteva za kreiranje zgrade
        building_url = f'{base_url}/import_building'
        response = requests.post(building_url, data=building_payload)
        
        if response.status_code == 200:
            buildings_success += 1
            print(f'Uspešno dodata zgrada: {row["Naziv zgrade"]}')
        else:
            print(f'Greška pri dodavanju zgrade {row["Naziv zgrade"]}: {response.text}')
    
    print(f'Uspešno dodato {buildings_success} od {len(df_zgrade)} zgrada')
else:
    print(f'U bazi ima {buildings_count} zgrada. Ako ima potrebe, ručno dodajte ostale zgrade.')


#Drugo proverite broj prostorija na serveru
check_rooms_url = f'{base_url}/check_rooms_count'
response = requests.get(check_rooms_url)
rooms_count = 0

if response.status_code == 200:
    rooms_count = int(response.json().get('count', 0))

# Ako nema prostorija na serveru, prvo unesite prostorije
if rooms_count == 0:
    print("Nema prostorija u bazi. Započinjem unos prostorija...")
    # Učitajte podatke iz Excel fajla (Prostorije) u DataFrame
    df_prostorije = pd.read_excel(file_path, sheet_name='Prostorije')
    rooms_success = 0
    for index, row in df_prostorije.iterrows():
        room_payload = {
            'id': str(row['id_prostorije']),  # Zadržavamo originalni ID iz excela
            'building_id': str(row['id_zgrade']),
            'name': str(row['Naziv prostorije (numerički)']),
            'dynamic_name': str(row['Naziv prostorije (dinamički)'])
        }
        # Slanje POST zahteva za kreiranje prostorije
        room_url = f'{base_url}/import_room'
        response = requests.post(room_url, data=room_payload)
        
        if response.status_code == 200:
            rooms_success += 1
            print(f'Uspešno dodata prostorija: {row["Naziv prostorije"]}')
        else:
            print(f'Greška pri dodavanju prostorije {row["Naziv prostorije"]}: {response.text}')
    
    print(f'Uspešno dodato {rooms_success} od {len(df_prostorije)} prostorija')
else:
    print(f'U bazi ima {rooms_count} prostorija. Ako ima potrebe, ručno dodajte ostale prostorije.')


# Treće proveriti broj predmeta na serveru
check_items_url = f'{base_url}/check_items_count'
response = requests.get(check_items_url)
items_count = 0

if response.status_code == 200:
    items_count = int(response.json().get('count', 0))

# Ako nema predmeta na serveru, prvo unesite predmete
if items_count == 0:
    print("Nema predmeta u bazi. Započinjem unos predmeta...")
    # Učitajte podatke iz Excel fajla (Pojedinačni predmeti po SERIJI) u DataFrame
    df_pps = pd.read_excel(file_path, sheet_name='Pojedinačni predmeti po SERIJI')
    
    # Pronađi kolonu koja počinje sa "Vrednost na kraju"
    value_column = next(col for col in df_pps.columns if col.startswith('Vrednost na kraju'))
    # Izvuci godinu iz naziva kolone
    year = int(''.join(filter(str.isdigit, value_column)))
    # Kreiraj datum za poslednji dan te godine
    last_day_of_year = f'{year}-12-31'
    
    items_success = 0
    for index, row in df_pps.iterrows():
        # Funkcija za bezbedno konvertovanje vrednosti
        def safe_value(value, default=''):
            return str(default if pd.isna(value) else value)
        item_payload = {
            'serial': safe_value(row['Serija']),
            'room_id': safe_value(row.get('room_id'), 1),  # Default 1 ako je nan
            'name': safe_value(row['Naziv']),
            'quantity': safe_value(row['Količina'], 1),
            'purchase_date': safe_value(row['Datum nabavke']).split()[0],
            'initial_price': safe_value(row['Nabavna vrednost'], 0),
            'input_in_app_date': last_day_of_year,
            'deprecation_value': safe_value(row.get(value_column, 0), 0),
            'supplier': safe_value(row.get('Dobavljač'), ''),  # Prazan string ako je nan
            'invoice_number': safe_value(row.get('Faktura'), ''),  # Prazan string ako je nan
            'category_id': safe_value(row['id konta']),
            'depreciation_rate_id': safe_value(row['id amortizacije'])
        }
        # Debug ispis
        print("\nDebug - item_payload:")
        for key, value in item_payload.items():
            print(f"{key}: {value}")
        print("-" * 50)
        
        # Slanje POST zahteva za kreiranje predmeta
        item_url = f'{base_url}/import_item'
        response = requests.post(item_url, data=item_payload)
        
        if response.status_code == 200:
            items_success += 1
            print(f'Uspešno dodat predmet: {row["Naziv"]}')
        else:
            print(f'Greška pri dodavanju predmeta {row["Naziv"]}: {response.text}')
    
    print(f'Uspešno dodato {items_success} od {len(df_pps)} predmeta')
else:
    print(f'U bazi ima {items_count} predmeta. Ako ima potrebe, ručno dodajte ostale predmeta.')