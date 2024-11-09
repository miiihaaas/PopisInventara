from datetime import datetime
from decimal import Decimal
import json
from flask import Blueprint
from popisinventara.models import Inventory, Room, SingleItem
from popisinventara.reports.functions import write_off_until_current_year, category_reports_past_pdf, category_reports_expediture_pdf, category_reports_item_pdf, category_reports_new_purchases_pdf, serial_reports_pdf
from flask import render_template


reports = Blueprint('reports', __name__)


@reports.route('/category_reports')
def category_reports():
    """
    Generise izveštaj po kategorijama (kontima) za sve aktivne predmete.
    Predmeti su grupisani po kategorijama i prikazuju sumarnu vrednost za svaku kategoriju.
    """
    # Dobavljamo sve predmete koji nisu rashodovani
    single_items = SingleItem.query.filter(SingleItem.expediture_date.is_(None)).all()
    
    data = []
    category_list = []
    
    for single_item in single_items:
        # Dobavljamo kategoriju na osnovu effective_category_id property-ja
        # koji će vratiti odgovarajuću kategoriju u zavisnosti od sistema (legacy/new)
        category_id = single_item.effective_category_id
        if not category_id:
            continue
            
        category = single_item.category
        category_number = category.category_number if category else None
        
        if not category_number:
            continue
            
        # Računamo vrednosti otpisa
        write_off_til_current_year, price_at_end_of_year, depreciation_per_year = write_off_until_current_year(single_item)
        
        if category_number not in category_list:
            # Ako kategorija nije u listi, dodajemo novi zapis
            category_list.append(category_number)
            new_record = {
                'category': category_number,
                'initial_price': single_item.initial_price,
                'current_price': single_item.current_price,
                'write_off_until_current_year': write_off_til_current_year,
                'depreciation_per_year': depreciation_per_year,
                'price_at_end_of_year': price_at_end_of_year if price_at_end_of_year > 0 else 0,
                'quantity': 1  # Dodajemo brojač količine
            }
            data.append(new_record)
        else:
            # Ako kategorija postoji, ažuriramo postojeći zapis
            for record in data:
                if record['category'] == category_number:
                    record['initial_price'] += single_item.initial_price
                    record['current_price'] += single_item.current_price
                    record['write_off_until_current_year'] += write_off_til_current_year
                    record['depreciation_per_year'] += depreciation_per_year
                    record['price_at_end_of_year'] += (price_at_end_of_year if price_at_end_of_year > 0 else 0)
                    record['quantity'] += 1
                    break
    
    # Sortiramo podatke po broju kategorije
    data.sort(key=lambda x: x['category'])
    
    return render_template('category_reports.html', 
                            data=data,
                            title='Izveštaj po kontima',
                            legend='Izveštaj po kontima')


@reports.route('/category_reports_past/<int:inventory_id>', methods=['GET', 'POST'])
def category_reports_past(inventory_id):
    """
    Generiše izveštaj po kontima za određeni inventar.
    Prikazuje stanje predmeta grupisano po kategorijama za datum kada je inventar napravljen.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_list = []
    
    # Debug ispis
    print(f"Loaded inventory data with {len(single_items)} items")
    
    for single_item in single_items:
        # Preskačemo rashodovane predmete
        if single_item.get('expediture_date') is not None:
            continue
            
        # U working_data, category_number je već sačuvan
        category_number = single_item.get('category_number')
        if not category_number:
            print(f"Missing category for item {single_item.get('name')}")
            continue

        if category_number not in category_list:
            category_list.append(category_number)
            new_record = {
                'category': category_number,
                'initial_price': Decimal(str(single_item['initial_price'])),
                'current_price': Decimal(str(single_item['current_price'])),
                'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                'quantity': 1
            }
            data.append(new_record)
        else:
            for record in data:
                if record['category'] == category_number:
                    record['initial_price'] += Decimal(str(single_item['initial_price']))
                    record['current_price'] += Decimal(str(single_item['current_price']))
                    record['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                    record['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                    record['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                    record['quantity'] += 1
                    break
    
    # Debug ispis
    print(f"Processed data for {len(category_list)} categories")
    print("Category list:", category_list)
    print("Data:", data)

    # Sortiramo podatke po broju kategorije
    data.sort(key=lambda x: x['category'])
    
    # Računamo totale
    totals = {
        'initial_price': sum(record['initial_price'] for record in data),
        'current_price': sum(record['current_price'] for record in data),
        'write_off_until_current_year': sum(record['write_off_until_current_year'] for record in data),
        'depreciation_per_year': sum(record['depreciation_per_year'] for record in data),
        'price_at_end_of_year': sum(record['price_at_end_of_year'] for record in data),
        'quantity': sum(record['quantity'] for record in data),
    }

    # Generišemo PDF izveštaj
    category_reports_past_pdf(data, inventory)

    return render_template('category_reports.html', 
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            title='Izveštaj po kontima',
                            legend=f'Izveštaj po kontima - popis {inventory.date}')

@reports.route('/category_reports_expediture/<int:inventory_id>')
def category_reports_expediture(inventory_id):
    """
    Generiše izveštaj o rashodovanim predmetima grupisano po kategorijama (kontima).
    Prikazuje samo predmete koji su rashodovani u godini popisa.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_list = []
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    for single_item in single_items:
        # Provera da li predmet ima datum rashoda
        expediture_date_str = single_item.get('expediture_date')
        if not expediture_date_str:
            continue
            
        try:
            expediture_date = datetime.strptime(expediture_date_str, '%Y-%m-%d')
            expediture_year = expediture_date.year
            
            # Proveravamo da li je rashod izvršen u godini popisa
            if expediture_year != inventory_year:
                continue
                
            category_number = single_item.get('category_number')
            if not category_number:
                print(f"Missing category for item {single_item.get('name')}")
                continue
                
            print(f"Processing expediture item with category {category_number}")
            
            if category_number not in category_list:
                category_list.append(category_number)
                new_record = {
                    'category': category_number,
                    'initial_price': Decimal(str(single_item['initial_price'])),
                    'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                    'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                    'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                    'current_price': Decimal(str(single_item['current_price'])),
                    'quantity': 1
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category_number:
                        record['initial_price'] += Decimal(str(single_item['initial_price']))
                        record['current_price'] += Decimal(str(single_item['current_price']))
                        record['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                        record['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                        record['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                        record['quantity'] += 1
                        break
                        
        except (ValueError, TypeError) as e:
            print(f"Error processing date {expediture_date_str}: {e}")
            continue
    
    # Debug ispis
    print(f"Found {len(category_list)} categories with expediture items")
    print("Category list:", category_list)
    print("Data:", data)
    
    # Sortiramo podatke po broju kategorije
    data.sort(key=lambda x: x['category'])
    
    # Računamo totale
    totals = {
        'initial_price': sum(record['initial_price'] for record in data),
        'current_price': sum(record['current_price'] for record in data),
        'write_off_until_current_year': sum(record['write_off_until_current_year'] for record in data),
        'depreciation_per_year': sum(record['depreciation_per_year'] for record in data),
        'price_at_end_of_year': sum(record['price_at_end_of_year'] for record in data),
        'quantity': sum(record['quantity'] for record in data)
    }

    # Generišemo PDF izveštaj
    category_reports_expediture_pdf(data, inventory)

    return render_template('category_reports_expediture.html',
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            title=f'Rekapitulacija rashoda po kontima - datum popisa: {inventory.date}',
                            legend=f'Rekapitulacija rashoda po kontima')


@reports.route('/category_reports_expediture_item/<int:inventory_id>')
def category_reports_expediture_item(inventory_id):
    """
    Generiše izveštaj o rashodovanim predmetima grupisano po kategorijama i nazivima predmeta.
    Prikazuje samo predmete koji su rashodovani u godini popisa.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_serial_list = []  # Koristimo seriju umesto item_id
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    for single_item in single_items:
        # Provera da li predmet ima datum rashoda
        expediture_date_str = single_item.get('expediture_date')
        if not expediture_date_str:
            continue
            
        try:
            expediture_date = datetime.strptime(expediture_date_str, '%Y-%m-%d')
            expediture_year = expediture_date.year
            
            # Proveravamo da li je rashod izvršen u godini popisa
            if expediture_year != inventory_year:
                continue
                
            category_number = single_item.get('category_number')
            serial = single_item.get('serial')
            
            if not category_number or not serial:
                print(f"Missing category or serial for item {single_item.get('name')}")
                continue
                
            print(f"Processing expediture item with category {category_number} and serial {serial}")
            
            found = False
            for cat, ser in category_serial_list:
                if cat == category_number and ser == serial:
                    found = True
                    # Ažuriramo postojeći zapis
                    for record in data:
                        if record['category'] == category_number and record['serial'] == serial:
                            record['quantity'] += 1
                            record['initial_price'] += Decimal(str(single_item['initial_price']))
                            record['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                            record['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                            record['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                            break
                    break

            if not found:
                # Dodajemo novi zapis
                category_serial_list.append((category_number, serial))
                new_record = {
                    'category': category_number,
                    'serial': serial,
                    'item': single_item['name'],
                    'quantity': 1,
                    'initial_price': Decimal(str(single_item['initial_price'])),
                    'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                    'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                    'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                }
                data.append(new_record)
                
        except (ValueError, TypeError) as e:
            print(f"Error processing item: {e}")
            continue
    
    # Debug ispis
    print(f"Found {len(category_serial_list)} unique category-serial combinations")
    print("Category-Serial list:", category_serial_list)
    
    # Sortiramo podatke po kategoriji i nazivu
    data.sort(key=lambda x: (x['category'], x['item']))
    
    # Računamo totale
    totals = {
        'quantity': sum(record['quantity'] for record in data),
        'initial_price': sum(record['initial_price'] for record in data),
        'write_off_until_current_year': sum(record['write_off_until_current_year'] for record in data),
        'depreciation_per_year': sum(record['depreciation_per_year'] for record in data),
        'price_at_end_of_year': sum(record['price_at_end_of_year'] for record in data),
    }

    # Generišemo PDF izveštaj
    report_type = 'expediture_item'
    category_reports_item_pdf(data, inventory, report_type)

    return render_template('category_reports_item.html',
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            report_type=report_type,
                            title=f'Rekapitulacija rashodovanih predmeta po kontima',
                            legend=f'Rekapitulacija rashodovanih predmeta po kontima - datum popisa: {inventory.date}')

@reports.route('/category_reports_new_purchases_past/<int:inventory_id>')
def category_reports_new_purchases_past(inventory_id):
    """
    Generiše izveštaj o novim nabavkama grupisano po kategorijama (kontima).
    Prikazuje samo predmete koji su nabavljeni u godini popisa.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_list = []
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    for single_item in single_items:
        try:
            # Provera godine nabavke
            purchase_date_str = single_item.get('purchase_date')
            if not purchase_date_str:
                print(f"Missing purchase date for item {single_item.get('name')}")
                continue
                
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
            if purchase_date.year != inventory_year:
                continue
            
            print(f"Found item purchased in inventory year: {purchase_date_str}")
            
            # Dobavljanje kategorije
            category_number = single_item.get('category_number')
            if not category_number:
                print(f"Missing category for item {single_item.get('name')}")
                continue
                
            if category_number not in category_list:
                category_list.append(category_number)
                new_record = {
                    'category': category_number,
                    'initial_price': Decimal(str(single_item['initial_price'])),
                    'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                    'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                    'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                    'current_price': Decimal(str(single_item['current_price'])),
                    'quantity': 1  # Dodajemo brojač količine
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category_number:
                        record['initial_price'] += Decimal(str(single_item['initial_price']))
                        record['current_price'] += Decimal(str(single_item['current_price']))
                        record['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                        record['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                        record['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                        record['quantity'] += 1
                        break
                        
        except (ValueError, TypeError) as e:
            print(f"Error processing item: {e}")
            continue
    
    # Debug ispis
    print(f"Found {len(category_list)} categories with new purchases")
    print("Category list:", category_list)
    print("Data:", data)
    
    # Sortiramo podatke po broju kategorije
    data.sort(key=lambda x: x['category'])
    
    # Računamo totale
    totals = {
        'initial_price': sum(record['initial_price'] for record in data),
        'current_price': sum(record['current_price'] for record in data),
        'write_off_until_current_year': sum(record['write_off_until_current_year'] for record in data),
        'depreciation_per_year': sum(record['depreciation_per_year'] for record in data),
        'price_at_end_of_year': sum(record['price_at_end_of_year'] for record in data),
        'quantity': sum(record.get('quantity', 0) for record in data)
    }

    # Generišemo PDF izveštaj
    category_reports_new_purchases_pdf(data, inventory)

    return render_template('category_reports_new_purchases.html',
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            title=f'Rekapitulacija novih nabavki po kontima',
                            legend=f'Rekapitulacija novih nabavki po kontima - datum popisa: {inventory.date}')


@reports.route('/category_reports_new_purchases_item/<int:inventory_id>')
def category_reports_new_purchases_item(inventory_id):
    """
    Generiše izveštaj o novim nabavkama grupisano po kategorijama i predmetima.
    Prikazuje samo predmete koji su nabavljeni u godini popisa.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_serial_list = []  # Koristimo (category_number, serial) umesto (category, item_id)
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    for single_item in single_items:
        try:
            # Provera godine nabavke
            purchase_date_str = single_item.get('purchase_date')
            if not purchase_date_str:
                print(f"Missing purchase date for item {single_item.get('name')}")
                continue
                
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
            if purchase_date.year != inventory_year:
                continue
            
            print(f"Found item purchased in inventory year: {purchase_date_str}")
            
            # Dobavljanje kategorije i serijskog broja
            category_number = single_item.get('category_number')
            serial = single_item.get('serial')
            
            if not category_number or not serial:
                print(f"Missing category or serial for item {single_item.get('name')}")
                continue
            
            # Proveravamo da li već imamo ovu kombinaciju kategorije i serije
            if (category_number, serial) not in category_serial_list:
                category_serial_list.append((category_number, serial))
                new_record = {
                    'category': category_number,
                    'serial': serial,
                    'item': single_item['name'],
                    'quantity': 1,
                    'initial_price': Decimal(str(single_item['initial_price'])),
                    'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                    'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                    'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                    'current_price': Decimal(str(single_item['current_price']))
                }
                data.append(new_record)
            else:
                # Ažuriramo postojeći zapis
                for record in data:
                    if record['category'] == category_number and record['serial'] == serial:
                        record['quantity'] += 1
                        record['initial_price'] += Decimal(str(single_item['initial_price']))
                        record['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                        record['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                        record['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                        record['current_price'] += Decimal(str(single_item['current_price']))
                        break
                        
        except (ValueError, TypeError) as e:
            print(f"Error processing item: {e}")
            continue
    
    # Debug ispis
    print(f"Found {len(category_serial_list)} unique category-serial combinations")
    print("Category-Serial list:", category_serial_list)
    
    # Sortiramo podatke po kategoriji i nazivu predmeta
    data.sort(key=lambda x: (x['category'], x['item']))
    
    # Računamo totale
    totals = {
        'quantity': sum(record['quantity'] for record in data),
        'initial_price': sum(record['initial_price'] for record in data),
        'current_price': sum(record['current_price'] for record in data),
        'write_off_until_current_year': sum(record['write_off_until_current_year'] for record in data),
        'depreciation_per_year': sum(record['depreciation_per_year'] for record in data),
        'price_at_end_of_year': sum(record['price_at_end_of_year'] for record in data)
    }

    # Generišemo PDF izveštaj
    report_type = 'new_purchases_item'
    category_reports_item_pdf(data, inventory, report_type)

    return render_template('category_reports_item.html',
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            report_type=report_type,
                            title=f'Rekapitulacija nabavljenih predmeta po kontima',
                            legend=f'Rekapitulacija nabavljenih predmeta po kontima - datum popisa: {inventory.date}')


@reports.route('/single_item_working/<int:inventory_id>', methods=['GET', 'POST'])
def single_item_working(inventory_id):
    """
    Prikazuje stanje inventara grupisano po serijama i kategorijama.
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_data = json.loads(inventory.working_data)
    inventory_single_items_working = inventory_data.get('single_items', [])
    
    # Debug ispis
    print(f"Processing {len(inventory_single_items_working)} items from inventory")
    
    # Filtriraj prostorije (isključi magacin rashodovanih predmeta)
    all_room_list = Room.query.all()
    room_list = [room for room in all_room_list if room.id not in [2]]

    # Grupisanje po serijama
    inventory_cumulatively_per_series_working = []
    
    for single_item in inventory_single_items_working:
        serial = single_item.get('serial')
        if not serial:
            print(f"Missing serial for item {single_item.get('name')}")
            continue
            
        found = False
        for item in inventory_cumulatively_per_series_working:
            if item['serial'] == serial:
                # Ažuriramo postojeći zapis
                item['quantity'] += 1
                item['initial_price'] += Decimal(str(single_item['initial_price']))
                item['current_price'] += Decimal(str(single_item['current_price']))
                item['depreciation_per_year'] += Decimal(str(single_item['depreciation_per_year']))
                item['write_off_until_current_year'] += Decimal(str(single_item['write_off_until_current_year']))
                item['price_at_end_of_year'] += Decimal(str(single_item['price_at_end_of_year']))
                found = True
                break

        if not found:
            # Dodajemo novi zapis
            new_item = {
                'serial': serial,
                'name': single_item['name'],
                'category_number': single_item.get('category_number', ''),
                'category_name': single_item.get('category_name', ''),
                'quantity': 1,
                'initial_price': Decimal(str(single_item['initial_price'])),
                'current_price': Decimal(str(single_item['current_price'])),
                'depreciation_per_year': Decimal(str(single_item['depreciation_per_year'])),
                'write_off_until_current_year': Decimal(str(single_item['write_off_until_current_year'])),
                'price_at_end_of_year': Decimal(str(single_item['price_at_end_of_year'])),
                'depreciation_rate': single_item.get('depreciation_rate', 0)
            }
            inventory_cumulatively_per_series_working.append(new_item)

    # Sortiranje po kategoriji i serijskom broju
    inventory_cumulatively_per_series_working.sort(key=lambda x: (x['category_number'], x['serial']))
    
    # Debug ispis
    print(f"Created {len(inventory_cumulatively_per_series_working)} grouped records by serial")

    # Generišemo PDF izveštaj
    serial_reports_pdf(inventory_cumulatively_per_series_working, inventory)

    # Grupisanje po kategorijama
    inventory_cumulatively_per_category_working = []
    
    for single_item in inventory_single_items_working:
        category_number = single_item.get('category_number')
        if not category_number:
            continue
            
        found = False
        for item in inventory_cumulatively_per_category_working:
            if item['category_number'] == category_number:
                # Ažuriramo postojeći zapis
                item['quantity'] += 1
                item['initial_price'] += Decimal(str(single_item['initial_price']))
                item['current_price'] += Decimal(str(single_item['current_price']))
                found = True
                break

        if not found:
            # Dodajemo novi zapis
            new_item = {
                'category_number': category_number,
                'category_name': single_item.get('category_name', ''),
                'quantity': 1,
                'initial_price': Decimal(str(single_item['initial_price'])),
                'current_price': Decimal(str(single_item['current_price']))
            }
            inventory_cumulatively_per_category_working.append(new_item)

    # Sortiranje po kategoriji
    inventory_cumulatively_per_category_working.sort(key=lambda x: x['category_number'])

    # Debug ispis
    print(f"Created {len(inventory_cumulatively_per_category_working)} grouped records by category")

    return render_template('single_items_working.html', 
                            title=f"Stanje inventara na datum: {inventory.date}",
                            room_list=room_list,
                            inventory_single_items_working=inventory_single_items_working,
                            inventory_cumulatively_per_series_working=inventory_cumulatively_per_series_working,
                            inventory_cumulatively_per_category_working=inventory_cumulatively_per_category_working,
                            inventory_id=inventory_id)