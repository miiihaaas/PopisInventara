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
print(f'Response status: {response.status_code}')
print(f'Response text: {response.text}')

input('pritisni ENTER dugme da bi nastavio')

try:
    if response.status_code != 200:
        print(f'Greška pri proveri broja zgrada: {response.text}')
        exit()
    if response.text:  # Proveravamo da li ima sadržaja
        response_json = response.json()
        print(f'Response JSON: {response_json}')
    else:
        print('Server je vratio prazan odgovor')
        response_json = {}
except requests.exceptions.JSONDecodeError as e:
    print(f'Greška pri parsiranju JSON odgovora: {str(e)}')
    print(f'Sadržaj odgovora: {response.text}')
    response_json = {}

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
print(f'Response status: {response.status_code}')
print(f'Response text: {response.text}')
input('pritisni ENTER dugme da bi nastavio')

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
print(f'Response status: {response.status_code}')
print(f'Response text: {response.text}')
input('pritisni ENTER dugme da bi nastavio')

items_count = 0

if response.status_code == 200:
    items_count = int(response.json().get('count', 0))

print("Nema predmeta u bazi. Započinjem unos predmeta...")
# Učitajte podatke iz Excel fajla (Pojedinačni predmeti po SERIJI) u DataFrame
df_pps = pd.read_excel(file_path, sheet_name='Pojedinačni predmeti po SERIJI')

# Pronađi kolonu koja počinje sa "Vrednost na kraju"
value_column = next(col for col in df_pps.columns if col.startswith('Vrednost na kraju'))
# Izvuci godinu iz naziva kolone
year = int(''.join(filter(str.isdigit, value_column)))
# Kreiraj datum za poslednji dan te godine
last_day_of_year = f'{year}-12-31'

# Funkcija za bezbedno konvertovanje vrednosti
def safe_value(value, default='', data_type=str):
    if pd.isna(value):
        return default
    if data_type == int:
        # Ako je float, prvo zaokružimo pa konvertujemo u int
        return int(float(value)) if isinstance(value, (float, str)) else int(value)
    if data_type == float:
        return float(value)
    return str(value)

# Ako nema predmeta na serveru, prvo unesite predmete
if items_count != 0:
    print(f'U bazi ima {items_count} predmeta. Ako ima potrebe, ručno dodajte ostale predmeta.')
else:
    print("Nema predmeta u bazi. Započinjem unos predmeta...")

items_success = 0
for index, row in df_pps.iterrows():
    item_payload = {
        'serial': safe_value(row['Serija'], default=None, data_type=int),
        'room_id': safe_value(row.get('room_id'), default=1, data_type=int),
        'name': safe_value(row['Naziv']),
        'quantity': safe_value(row['Količina'], default=None, data_type=int),
        'purchase_date': safe_value(row['Datum nabavke']).split()[0],
        'initial_price': safe_value(row['Nabavna vrednost'], default=None, data_type=float),
        'input_in_app_date': last_day_of_year,
        'deprecation_value': safe_value(row.get(value_column, 0), default=None, data_type=float),
        'supplier': safe_value(row.get('Dobavljač'), ''),
        'invoice_number': safe_value(row.get('Faktura'), ''),
        'category_id': safe_value(row['id konta'], default=None, data_type=int),
        'depreciation_rate_id': safe_value(row['id amortizacije'], default=None, data_type=int)
    }

    
    # Slanje POST zahteva za kreiranje predmeta
    item_url = f'{base_url}/import_item'
    response = requests.post(item_url, data=item_payload)
    
    if response.status_code == 200:
        items_success += 1
        # Debug ispis
        print(f'Uspešno dodat predmet: {row["Naziv"]}')
    elif response.status_code == 202:
        print(f'Predmet {row["Naziv"]} vec postoji u bazi. Uspesno dodat: {response.text}')
    else:
        print("\nDebug - item_payload:")
        for key, value in item_payload.items():
            print(f"{key}: {value} | {type(value)}")
        print("-" * 50)
        print(f'Greška pri dodavanju predmeta {row["Naziv"]}: {response.text}')
if items_count > 0:
    print(f'U bazi je imalo {items_count} predmeta. \nUspešno dodato {items_success} od {len(df_pps)} predmeta. \nNeuspešno dodato {items_count - items_success} predmeta.')
else:
    print(f'Uspešno dodato {items_success} od {len(df_pps)} predmeta.')