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
        df_predmeti = pd.read_excel(file_path, sheet_name='Pojedinačni predmeti')
        print(f"📑 Učitano {len(df_predmeti)} predmeta iz Excel fajla")
    except Exception as e:
        print("\n❌ GREŠKA: Problem pri učitavanju Excel fajla")
        print(f"Detalji greške: {str(e)}")
        exit()
    
    items_success = 0
    print("\nPočinjem unos predmeta u bazu...")
    
    for index, row in df_predmeti.iterrows():
        current_item = f"{row['Naziv predmeta']} (Serija: {row['Serijski broj']})"
        print(f"\nObrada predmeta ({index + 1}/{len(df_predmeti)}): {current_item}")
        
        try:
            item_payload = {
                'serial': str(row['Serijski broj']),
                'room_id': str(row['ID prostorije']),
                'name': str(row['Naziv predmeta']),
                'quantity': str(row['Količina']),
                'purchase_date': str(row['Datum kupovine']),
                'initial_price': str(row['Početna cena']),
                'input_in_app_date': str(row['Datum unosa']),
                'deprecation_value': str(row['Amortizovana vrednost']),
                'supplier': str(row['Dobavljač']),
                'invoice_number': str(row['Broj fakture']),
                'category_id': str(row['ID kategorije']),
                'depreciation_rate_id': str(row['ID stope amortizacije'])
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
