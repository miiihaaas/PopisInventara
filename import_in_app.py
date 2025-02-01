import requests
import os
import pandas as pd


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

print("\n" + "="*50)
print("IMPORT PODATAKA U APLIKACIJU")
print("="*50)

# Dobijanje apsolutne putanje do trenutnog direktorijuma skripte
current_directory = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(current_directory)
directory_name = os.path.basename(parent_directory)
file_path = os.path.join(current_directory, f'{directory_name}_input_data.xlsx')

print("\n📂 INFORMACIJE O RADNOM OKRUŽENJU:")
print("-"*30)
print(f"🏢 Naziv aplikacije: {directory_name}")
print(f"📁 Radni direktorijum: {current_directory}")
print(f"📊 Excel fajl: {file_path}")

# Provera da li Excel fajl postoji
if not os.path.exists(file_path):
    print("\n❌ GREŠKA: Excel fajl nije pronađen!")
    print(f"   Fajl koji se traži: {file_path}")
    print("   Molimo proverite da li je fajl na pravom mestu i da li ima ispravan naziv.")
    exit()
else:
    print("\n✅ Excel fajl je uspešno pronađen")

print("\n" + "-"*50)
print("❓ Da li želite da započnete import podataka?")
print("   - Pritisnite 'Y' za početak")
print("   - Pritisnite bilo koji drugi taster za izlaz")
odgovor = input("   Vaš izbor (Y/N): ").lower()

if odgovor != 'y':
    print("\n🛑 Import podataka je prekinut na zahtev korisnika.")
    exit()

print("\n✨ Započinjem proces importa podataka...")
print("-"*50 + "\n")

# Postavite URL na koji želite slati zahteve
base_url = f'https://popis.online/{directory_name}'
url = f'{base_url}/import_in_app'  # URL za unos podataka

#! 1. Provera broja zgrada u bazi
print("\n" + "="*50)
print("PROVERA BROJA ZGRADA U BAZI")
print("="*50)

# Prvo proverite broj zgrada na serveru
check_buildings_url = f'{base_url}/check_buildings_count'
response = requests.get(check_buildings_url)
print(f'Response status: {response.status_code}')
print(f'Response text: {response.text}')

#? input('pritisni ENTER dugme da bi nastavio')

try:
    if response.status_code != 200:
        print("\n❌ GREŠKA: Neuspešna provera broja zgrada")
        print(f"Status kod: {response.status_code}")
        print(f"Poruka: {response.text}")
        exit()
    if response.text:
        response_json = response.json()
        buildings_count = int(response_json.get('count', 0))
        print(f"\n✅ Uspešna provera broja zgrada")
        print(f"📊 Trenutni broj zgrada u bazi: {buildings_count}")
    else:
        print("\n⚠️ Upozorenje: Server je vratio prazan odgovor")
        buildings_count = 0
        response_json = {}
except requests.exceptions.JSONDecodeError as e:
    print("\n❌ GREŠKA: Problem sa parsiranjem odgovora servera")
    print(f"Detalji greške: {str(e)}")
    print(f"Sadržaj odgovora: {response.text}")
    response_json = {}
    exit()

print("\n" + "-"*50)
input('📌 Pritisnite ENTER za nastavak...')
print("-"*50 + "\n")

# Ako nema zgrada na serveru, prvo unesite zgrade
if buildings_count == 0:
    print("🏗️  ZAPOČINJEM UNOS ZGRADA")
    print("-"*30)
    
    # Učitajte podatke iz Excel fajla (Zgrade) u DataFrame
    try:
        df_zgrade = pd.read_excel(file_path, sheet_name='Zgrade')
        print(f"📑 Učitano {len(df_zgrade)} zgrada iz Excel fajla")
    except Exception as e:
        print("\n❌ GREŠKA: Problem pri učitavanju Excel fajla")
        print(f"Detalji greške: {str(e)}")
        exit()
    
    buildings_success = 0
    print("\nPočinjem unos zgrada u bazu...")
    
    for index, row in df_zgrade.iterrows():
        current_building = str(row['Naziv zgrade'])
        print(f"\nObrada zgrade ({index + 1}/{len(df_zgrade)}): {current_building}")
        
        building_payload = {
            'school_id': '1',
            'name': str(row['Naziv zgrade']),
            'address': str(row['Adresa']),
            'city': str(row['Mesto'])
        }
        
        # Slanje POST zahteva za kreiranje zgrade
        building_url = f'{base_url}/import_building'
        response = requests.post(building_url, data=building_payload)
        
        if response.status_code == 200:
            buildings_success += 1
            print(f"✅ Uspešno dodata zgrada: {current_building}")
        else:
            print(f"❌ Greška pri dodavanju zgrade {current_building}")
            print(f"   Status kod: {response.status_code}")
            print(f"   Poruka: {response.text}")
    
    print("\n" + "="*50)
    print(f"📊 REZULTAT UNOSA ZGRADA:")
    print(f"✅ Uspešno dodato: {buildings_success}")
    print(f"❌ Neuspešno: {len(df_zgrade) - buildings_success}")
    print(f"📑 Ukupno za obradu: {len(df_zgrade)}")
    print("="*50 + "\n")
else:
    print("\n📊 TRENUTNO STANJE ZGRADA")
    print(f"🏢 U bazi postoji {buildings_count} zgrada")
    print("ℹ️  Ako je potrebno, možete ručno dodati dodatne zgrade kroz aplikaciju\n")


#! 2. Provera broja prostorija u bazi
print("\n" + "="*50)
print("PROVERA BROJA PROSTORIJA U BAZI")
print("="*50)

check_rooms_url = f'{base_url}/check_rooms_count'
response = requests.get(check_rooms_url)
try:
    if response.status_code != 200:
        print("\n❌ GREŠKA: Neuspešna provera broja prostorija")
        print(f"Status kod: {response.status_code}")
        print(f"Poruka: {response.text}")
        exit()
    
    if response.text:
        response_json = response.json()
        rooms_count = int(response_json.get('count', 0))
        print(f"\n✅ Uspešna provera broja prostorija")
        print(f"📊 Trenutni broj prostorija u bazi: {rooms_count}")
    else:
        print("\n⚠️ Upozorenje: Server je vratio prazan odgovor")
        rooms_count = 0
        response_json = {}
except requests.exceptions.JSONDecodeError as e:
    print("\n❌ GREŠKA: Problem sa parsiranjem odgovora servera")
    print(f"Detalji greške: {str(e)}")
    print(f"Sadržaj odgovora: {response.text}")
    response_json = {}
    exit()

print("\n" + "-"*50)
input('📌 Pritisnite ENTER za nastavak...')
print("-"*50 + "\n")

# Ako nema prostorija na serveru, prvo unesite prostorije
if rooms_count == 0:
    print("🚪 ZAPOČINJEM UNOS PROSTORIJA")
    print("-"*30)
    
    # Učitajte podatke iz Excel fajla (Prostorije) u DataFrame
    try:
        df_prostorije = pd.read_excel(file_path, sheet_name='Prostorije')
        print(f"📑 Učitano {len(df_prostorije)} prostorija iz Excel fajla")
    except Exception as e:
        print("\n❌ GREŠKA: Problem pri učitavanju Excel fajla")
        print(f"Detalji greške: {str(e)}")
        exit()
    
    rooms_success = 0
    print("\nPočinjem unos prostorija u bazu...")
    
    for index, row in df_prostorije.iterrows():
        current_room = str(row['Naziv prostorije (dinamički)'])
        print(f"\nObrada prostorije ({index + 1}/{len(df_prostorije)}): {current_room}")
        
        try:
            room_payload = {
                'id': str(row['id_prostorije']),
                'building_id': str(row['id_zgrade']),
                'name': str(row['Naziv prostorije (numerički)']),
                'dynamic_name': str(row['Naziv prostorije (dinamički)'])
            }
            
            # Slanje POST zahteva za kreiranje prostorije
            room_url = f'{base_url}/import_room'
            response = requests.post(room_url, data=room_payload)
            
            if response.status_code == 200:
                rooms_success += 1
                print(f"✅ Uspešno dodata prostorija: {current_room}")
            else:
                print(f"❌ Greška pri dodavanju prostorije {current_room}")
                print(f"   Status kod: {response.status_code}")
                print(f"   Poruka: {response.text}")
        except Exception as e:
            print(f"❌ Greška pri obradi prostorije {current_room}")
            print(f"   Detalji greške: {str(e)}")
    
    print("\n" + "="*50)
    print(f"📊 REZULTAT UNOSA PROSTORIJA:")
    print(f"✅ Uspešno dodato: {rooms_success}")
    print(f"❌ Neuspešno: {len(df_prostorije) - rooms_success}")
    print(f"📑 Ukupno za obradu: {len(df_prostorije)}")
    print("="*50 + "\n")
else:
    print("\n📊 TRENUTNO STANJE PROSTORIJA")
    print(f"🚪 U bazi postoji {rooms_count} prostorija")
    print("ℹ️  Ako je potrebno, možete ručno dodati dodatne prostorije kroz aplikaciju\n")


#! 3. Provera broja predmeta u bazi
print("\n" + "="*50)
print("PROVERA BROJA PREDMETA U BAZI")
print("="*50)


check_items_url = f'{base_url}/check_items_count'
response = requests.get(check_items_url)

try:
    if response.status_code != 200:
        print("\n❌ GREŠKA: Neuspešna provera broja predmeta")
        print(f"Status kod: {response.status_code}")
        print(f"Poruka: {response.text}")
        exit()
    
    if response.text:
        response_json = response.json()
        items_count = int(response_json.get('count', 0))
        print(f"\n✅ Uspešna provera broja predmeta")
        print(f"📊 Trenutni broj predmeta u bazi: {items_count}")
    else:
        print("\n⚠️ Upozorenje: Server je vratio prazan odgovor")
        items_count = 0
        response_json = {}
except requests.exceptions.JSONDecodeError as e:
    print("\n❌ GREŠKA: Problem sa parsiranjem odgovora servera")
    print(f"Detalji greške: {str(e)}")
    print(f"Sadržaj odgovora: {response.text}")
    response_json = {}
    exit()

print("\n" + "-"*50)
input('📌 Pritisnite ENTER za nastavak...')
print("-"*50 + "\n")

# Ako nema predmeta na serveru, prvo unesite predmete
if items_count == 0:
    print("📦 ZAPOČINJEM UNOS PREDMETA")
    print("-"*30)
    
    # Učitajte podatke iz Excel fajla (Pojedinačni predmeti) u DataFrame
    try:
        df_predmeti = pd.read_excel(file_path, sheet_name='Pojedinačni predmeti po SERIJI')
        print(f"📑 Učitano {len(df_predmeti)} predmeta iz Excel fajla")
        
        # Pronađi kolonu koja počinje sa "Vrednost na kraju"
        value_column = next(col for col in df_predmeti.columns if col.startswith('Vrednost na kraju'))
        # Izvuci godinu iz naziva kolone
        year = int(''.join(filter(str.isdigit, value_column)))
        # Kreiraj datum za poslednji dan te godine
        last_day_of_year = f'{year}-12-31'
    except Exception as e:
        print("\n❌ GREŠKA: Problem pri učitavanju Excel fajla")
        print(f"Detalji greške: {str(e)}")
        exit()
    
    items_success = 0
    print("\nPočinjem unos predmeta u bazu...")
    
    for index, row in df_predmeti.iterrows():
        current_item = f"{safe_value(row['Naziv'])} (Serija: {safe_value(row['Serija'])})"
        print(f"\nObrada predmeta ({index + 1}/{len(df_predmeti)}): {current_item}")
        
        try:
            item_payload = {
                'serial': safe_value(row['Serija'], default=None, data_type=int),
                'room_id': safe_value(row.get('room_id'), default=1, data_type=int),
                'name': safe_value(row['Naziv']),
                'quantity': safe_value(row['Količina'], default=None, data_type=int),
                'purchase_date': safe_value(row['Datum nabavke']).split()[0],
                'initial_price': safe_value(row['Nabavna vrednost'], default=None, data_type=float),
                'input_in_app_date': last_day_of_year,
                'deprecation_value': safe_value(row.get(value_column, 0), default=None, data_type=float), #! ovo je ukupna vrednost svih predmeta iz serije na kraju godine
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
                print(f"✅ Uspešno dodat predmet: {current_item}")
                print(f"   Poruka: {response.json().get('message', '')}")
            elif response.status_code == 202:
                print(f"ℹ️  Predmet već postoji: {current_item}")
                print(f"   Poruka: {response.json().get('message', '')}")
            else:
                print(f"❌ Greška pri dodavanju predmeta {current_item}")
                print(f"   Status kod: {response.status_code}")
                print(f"   Poruka: {response.text}")
        except Exception as e:
            print(f"❌ Greška pri obradi predmeta {current_item}")
            print(f"   Detalji greške: {str(e)}")
    
    print("\n" + "="*50)
    print(f"📊 REZULTAT UNOSA PREDMETA:")
    print(f"✅ Uspešno dodato: {items_success}")
    print(f"❌ Neuspešno: {len(df_predmeti) - items_success}")
    print(f"📑 Ukupno za obradu: {len(df_predmeti)}")
    print("="*50 + "\n")
else:
    print("\n📊 TRENUTNO STANJE PREDMETA")
    print(f"📦 U bazi postoji {items_count} predmeta")
    print("ℹ️  Ako je potrebno, možete ručno dodati dodatne predmete kroz aplikaciju\n")
