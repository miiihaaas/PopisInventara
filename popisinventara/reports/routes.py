from datetime import datetime
from decimal import Decimal
import json
from flask import Blueprint, request
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
                            inventory_year=datetime.now().year,
                            title='Izveštaj po kontima',
                            legend='Izveštaj po kontima | Projekcija na kraju tekuće godine')


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
        # if single_item.get('expediture_date') is not None:
        #     continue
            
        # U working_data, category_number je već sačuvan
        category_number = single_item.get('category_number')
        if not category_number:
            print(f"Missing category for item {single_item.get('name')}")
            continue
        is_written_off = single_item.get('expediture_date') is not None

        if category_number not in category_list:
            category_list.append(category_number)
            new_record = {
                'category': category_number,
                'initial_price': Decimal(str(single_item['initial_price'])),
                'current_price': Decimal('0') if is_written_off else Decimal(str(single_item['current_price'])),
                'write_off_until_current_year': Decimal(str(single_item['initial_price'])) if is_written_off else Decimal(str(single_item['write_off_until_current_year'])),
                'depreciation_per_year': Decimal('0') if is_written_off else Decimal(str(single_item['depreciation_per_year'])),
                'price_at_end_of_year': Decimal('0') if is_written_off else Decimal(str(single_item['price_at_end_of_year'])),
                'quantity': 0 if is_written_off else 1
            }
            data.append(new_record)
        else:
            for record in data:
                if record['category'] == category_number:
                    record['initial_price'] += Decimal(str(single_item['initial_price']))
                    if is_written_off:
                        record['write_off_until_current_year'] += Decimal(str(single_item['initial_price']))
                    else:
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
                            inventory_year=inventory.date.year,
                            title='Izveštaj po kontima',
                            legend=f'Izveštaj po kontima - popis {inventory.date} | {inventory.description}')


@reports.route('/category_reports_expediture/<int:inventory_id>')
def category_reports_expediture(inventory_id):
    """
    Generiše izveštaj o rashodovanim predmetima grupisano po kategorijama (kontima).
    Prikazuje predmete koji su rashodovani u godini popisa, kao i predmete kod kojih
    je utvrđen manjak (razlika između stvarnog stanja i popisanog stanja).
    """
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    inventory_rooms = inventory_data.get('inventory', [])
    
    data = []
    category_list = []
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    # # Kreiramo mapu stvarnog stanja po serijskom broju
    # actual_quantities = {}
    # for single_item in single_items:
    #     serial = str(single_item.get('serial'))
    #     if serial not in actual_quantities:
    #         actual_quantities[serial] = {
    #             'quantity': 1,
    #             'item_data': single_item
    #         }
    #     else:
    #         actual_quantities[serial]['quantity'] += 1

    # # Kreiramo mapu popisanih količina po serijskom broju
    # counted_quantities = {}
    # for room in inventory_rooms:
    #     for item in room['items']:
    #         serial = str(item.get('serial'))
    #         quantity_input = int(item.get('quantity_input', 0))
    #         if serial not in counted_quantities:
    #             counted_quantities[serial] = quantity_input
    #         else:
    #             counted_quantities[serial] += quantity_input

    def process_item_for_report(single_item, category_list, data):
        """Pomoćna funkcija za obradu predmeta i dodavanje u izveštaj"""
        category_number = single_item.get('category_number')
        if not category_number:
            print(f"Missing category for item {single_item.get('name')}")
            return
            
        print(f"Processing item with category {category_number}")
        
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

    # Prvo obrađujemo već rashodovane predmete i pravimo set njihovih serijskih brojeva
    expedited_serials = set()
    for single_item in single_items:
        expediture_date_str = single_item.get('expediture_date')
        if expediture_date_str:
            try:
                expediture_date = datetime.strptime(expediture_date_str, '%Y-%m-%d')
                expediture_year = expediture_date.year
                
                if expediture_year != inventory_year:
                    continue
                    
                process_item_for_report(single_item, category_list, data)
                expedited_serials.add(str(single_item.get('serial')))
            except (ValueError, TypeError) as e:
                print(f"Error processing date {expediture_date_str}: {e}")
                continue

    # Kreiramo mapu stvarnog stanja po serijskom broju
    # ALI samo za predmete koji NISU rashodovani u tekućoj godini
    actual_quantities = {}
    for single_item in single_items:
        serial = str(single_item.get('serial'))
        # Preskačemo predmete koji su već obrađeni kao rashodovani
        if serial in expedited_serials:
            continue
            
        if serial not in actual_quantities:
            actual_quantities[serial] = {
                'quantity': 1,
                'item_data': single_item
            }
        else:
            actual_quantities[serial]['quantity'] += 1

    # Kreiramo mapu popisanih količina po serijskom broju
    counted_quantities = {}
    for room in inventory_rooms:
        for item in room['items']:
            serial = str(item.get('serial'))
            quantity_input = int(item.get('quantity_input', 0))
            if serial not in counted_quantities:
                counted_quantities[serial] = quantity_input
            else:
                counted_quantities[serial] += quantity_input

    # Zatim obrađujemo predmete koji imaju manjak
    for serial, actual_data in actual_quantities.items():
        actual_qty = actual_data['quantity']
        counted_qty = counted_quantities.get(serial, 0)
        
        if counted_qty < actual_qty:
            # Postoji manjak - razlika između stvarnog stanja i popisanog
            missing_qty = actual_qty - counted_qty
            item_data = actual_data['item_data']
            
            # # Preskačemo ako je predmet već rashodovan
            # if item_data.get('expediture_date'):
            #     continue
                
            # Dodajemo predmet u izveštaj onoliko puta koliki je manjak
            for _ in range(missing_qty):
                process_item_for_report(item_data, category_list, data)

    # Debug ispis
    print(f"Found {len(category_list)} categories with expediture and missing items")
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
                            inventory_year=inventory_year,
                            title=f'Izveštaj o isknjiženim stavkama po kontu - datum popisa: {inventory.date}',
                            legend=f'Izveštaj o isknjiženim stavkama po kontu')


@reports.route('/category_reports_expediture_item/<int:inventory_id>')
def category_reports_expediture_item(inventory_id):
    """
    Generiše izveštaj o rashodovanim predmetima grupisano po kategorijama i nazivima predmeta.
    Prikazuje predmete koji su rashodovani u godini popisa, kao i predmete kod kojih
    je utvrđen manjak (razlika između stvarnog stanja i popisanog stanja).
    """
    endpoint = request.endpoint
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    inventory_rooms = inventory_data.get('inventory', [])
    
    data = []
    category_serial_list = []  # Lista jedinstvenih kombinacija kategorija i serija
    
    # Debug ispis
    print(f"Processing {len(single_items)} items for inventory year {inventory_year}")
    
    def process_item_for_report(single_item, category_serial_list, data):
        """Pomoćna funkcija za obradu predmeta i dodavanje u izveštaj"""
        category_number = single_item.get('category_number')
        serial = single_item.get('serial')
        
        if not category_number or not serial:
            print(f"Missing category or serial for item {single_item.get('name')}")
            return
            
        print(f"Processing item with category {category_number} and serial {serial}")
        
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
    



    # Prvo obrađujemo već rashodovane predmete i pravimo set njihoivih serijskih brojeva
    expedited_serials = set()
    for single_item in single_items:
        expediture_date_str = single_item.get('expediture_date')
        if expediture_date_str:
            try:
                expediture_date = datetime.strptime(expediture_date_str, '%Y-%m-%d')
                expediture_year = expediture_date.year
                
                if expediture_year != inventory_year:
                    continue
                    
                process_item_for_report(single_item, category_serial_list, data)
                expedited_serials.add(str(single_item.get('serial')))
                
            except (ValueError, TypeError) as e:
                print(f"Error processing date {expediture_date_str}: {e}")
                continue
    # Kreiramo mapu stvarnog stanja po serijskom broju
    # ALI samo za predmete koji NISU rashodovani u tekućoj godini
    actual_quantities = {}
    for single_item in single_items:
        serial = str(single_item.get('serial'))
        # Preskačemo predmete koji su već obrađeni kao rashodovani
        if serial in expedited_serials:
            continue
            
        if serial not in actual_quantities:
            actual_quantities[serial] = {
                'quantity': 1,
                'item_data': single_item
            }
        else:
            actual_quantities[serial]['quantity'] += 1
    
    # Kreiramo mapu popisanih količina po serijskom broju
    counted_quantities = {}
    for room in inventory_rooms:
        for item in room['items']:
            serial = str(item.get('serial'))
            quantity_input = int(item.get('quantity_input', 0))
            if serial not in counted_quantities:
                counted_quantities[serial] = quantity_input
            else:
                counted_quantities[serial] += quantity_input

    # Zatim obrađujemo predmete koji imaju manjak
    for serial, actual_data in actual_quantities.items():
        actual_qty = actual_data['quantity']
        counted_qty = counted_quantities.get(serial, 0)
        
        if counted_qty < actual_qty:
            # Postoji manjak - razlika između stvarnog stanja i popisanog
            missing_qty = actual_qty - counted_qty
            item_data = actual_data['item_data']
            
            #! Preskačemo ako je predmet već rashodovan
            # if item_data.get('expediture_date'):
            #     continue
                
            # Dodajemo predmet u izveštaj onoliko puta koliki je manjak
            for _ in range(missing_qty):
                process_item_for_report(item_data, category_serial_list, data)
    
    # Debug ispis
    print(f"Found {len(category_serial_list)} unique category-serial combinations with expediture and missing items")
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
                            endpoint=endpoint,
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            inventory_year=inventory_year,
                            report_type=report_type,
                            title=f'Izveštaj o isknjiženim stavkama po kontu i predmetu',
                            legend=f'Izveštaj o isknjiženim stavkama po kontu i predmetu - datum popisa: {inventory.date} | {inventory.description}')


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
                            title=f'Izveštaj o novim nabavkama po kontu',
                            legend=f'Izveštaj o novim nabavkama po kontu - datum popisa: {inventory.date}')


@reports.route('/category_reports_new_purchases_item/<int:inventory_id>')
def category_reports_new_purchases_item(inventory_id):
    """
    Generiše izveštaj o novim nabavkama grupisano po kategorijama i predmetima.
    Prikazuje samo predmete koji su nabavljeni u godini popisa.
    """
    endpoint = request.endpoint
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_year = inventory.date.year
    inventory_data = json.loads(inventory.working_data)
    single_items = inventory_data.get('single_items', [])
    
    data = []
    category_serial_list = []  # Lista jedinstvenih kombinacija kategorija i serija
    
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
                            endpoint=endpoint,
                            data=data,
                            totals=totals,
                            inventory_id=inventory_id,
                            inventory_year=inventory_year,
                            report_type=report_type,
                            title=f'Izveštaj o novim nabavkama po kontu i predmetu po kontima',
                            legend=f'Izveštaj o novim nabavkama po kontu i predmetu po kontima - datum popisa: {inventory.date}')


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