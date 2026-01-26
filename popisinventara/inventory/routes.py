import json
from decimal import Decimal
from datetime import date, datetime
from flask import Blueprint
from flask import  render_template, flash, redirect, url_for
from flask_login import current_user
from flask import request
from popisinventara import db
from popisinventara.models import Inventory, Room, School, SingleItem, Item, User
from popisinventara.inventory.functions import popisna_lista_gen, popisne_liste_gen
from popisinventara.reports.functions import write_off_until_current_year
from popisinventara.single_items.functions import current_price_calculation
from sqlalchemy.orm import joinedload


inventory = Blueprint('inventory', __name__)


def serialize_data(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")



@inventory.route('/create_inventory_list', methods=['GET', 'POST'])
def create_inventory_list():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za da pristupite ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    
    virtual_warehouse = SingleItem.query.filter_by(room_id=1).count()
    if virtual_warehouse:
        flash('Pre kreiranja popisnih listi treba premestiti sve predmete iz virtuelnog magacina.', 'danger')
        return redirect(url_for('main.home'))
        
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Da bi ste kreirali novu popisnu listu, morate prvo završiti aktivnu popisnu listu koja je započeta: {active_inventory_list.date}.', 'danger')
        return redirect(url_for('main.home'))
    
    route_name = request.endpoint
    
    # all_room_list = Room.query.all()
    # rooms = [room for room in all_room_list if room.id not in [1, 2, 4]]
    # Kompletnija query sa filtriranjem u samom upitu
    rooms = db.session.query(Room).options(
        joinedload(Room.building)
    ).filter(
        Room.id.notin_([1, 2, 4])
    ).order_by(
        Room.building_id,
        Room.name
    ).all()
    # Debug ispis
    print("\n=== DEBUG BEFORE TEMPLATE ===")
    print(f"Number of rooms: {len(rooms)}")
    print("Room IDs:", [r.id for r in rooms])
    print("Room Names:", [r.name for r in rooms])
    print("Building IDs:", [r.building_id for r in rooms])
    print("Building Names:", [r.building.name if r.building else 'None' for r in rooms])
    print("========================\n")
    
    users = User.query.filter_by(authorization='user').all()
    
    this_year = date.today().year
    years = [this_year - 1, this_year]
    
    inventory_years = [inventory.date for inventory in Inventory.query.all()]
    inventory_at_the_end_of_current_year = date(this_year, 12, 31) in inventory_years
    inventory_at_the_end_of_last_year = date(this_year - 1, 12, 31) in inventory_years

    if request.method == 'POST':
        description = request.form.get('description')
        single_items = SingleItem.query.all()
        
        year = request.form.get('inventry_types')
        if year != '':
            datum = date(int(year), 12, 31)
        else:
            year = None
            datum = date.today()
        
        # Kalkulacija trenutne cene sa novim modelom
        for single_item in single_items:
            if single_item.expediture_date is None:
                single_item.current_price, _ = current_price_calculation(
                    single_item.initial_price,
                    single_item.depreciation_rate.rate,
                    single_item.purchase_date,
                    single_item.expediture_date,
                    year,
                    single_item.input_in_app_date,
                    single_item.deprecation_value
                )
        db.session.commit()
        
        room_ids = request.form.getlist('room_id[]')
        user_ids = request.form.getlist('user_id[]')
        if any(item == '' for item in user_ids):
            flash('Morate dodeliti predsednika popisne komisije za svaku prostoriju.', 'danger')
            return redirect(url_for('inventory.create_inventory_list'))
        room_user_ids = list(zip(room_ids, user_ids))
        
        # Kreiranje inventory_initial_data sa novom strukturom
        inventory_initial_data = []
        for room in rooms:
            room_id = room.id
            user_id = [int(u_id) for (r_id, u_id) in room_user_ids if r_id == str(room_id)][0]
            single_items_in_room = SingleItem.query.filter_by(room_id=room_id).all()
            items = []
            
            for single_item in single_items_in_room:
                item = {
                    'serial': single_item.serial,
                    'name': single_item.name,
                    'category_number': single_item.category.category_number,
                    'category_name': single_item.category.name,
                    'depreciation_rate': single_item.depreciation_rate.rate,
                    'quantity': 1,
                    'quantity_input': 0,
                    'current_price': single_item.current_price,
                    'total_value': single_item.current_price,
                    'comment': ''
                }
                if not items:
                    items.append(item)
                else:
                    found = False
                    for existing_item in items:
                        if existing_item['serial'] == item['serial']:
                            existing_item['quantity'] += 1
                            existing_item['total_value'] += item['current_price']
                            found = True
                            break
                    if not found:
                        items.append(item)
            
            inventory_initial_data.append({
                'room_id': room_id,
                'user_id': user_id,
                'items': items
            })
        
        # Kreiranje inventory_working_data 
        inventory_working_data = []
        for room in inventory_initial_data:
            new_room = {'room_id': room['room_id'], 'user_id': room['user_id'], 'items': []}
            for item in room['items']:
                new_item = item.copy()  # Kopiramo sve podatke
                new_item['quantity_input'] = 0
                new_item['total_value'] = 0
                new_room['items'].append(new_item)
            inventory_working_data.append(new_room)
        
        # Kreiranje single_items_list
        single_items_list = []
        for single_item in single_items:
            # Provera da li predmet ima datum rashodovanja i da li je godina rashodovanja manja od godine popisa
            if single_item.expediture_date is None or (
                year is not None and single_item.expediture_date.year == int(year)
            ):
                write_off_til_current_year, price_at_end_of_year, depreciation_per_year = write_off_until_current_year(single_item, year)
                    
                new_single_item = {
                    'id': single_item.id,
                    'serial': single_item.serial,
                    'name': single_item.name,
                    'category_number': single_item.category.category_number,
                    'category_name': single_item.category.name,
                    'depreciation_rate': single_item.depreciation_rate.rate,
                    'initial_price': single_item.initial_price,
                    'current_price': single_item.current_price,
                    'purchase_date': single_item.purchase_date,
                    'expediture_date': single_item.expediture_date,
                    'room_id': single_item.room_id,
                    'depreciation_per_year': depreciation_per_year,
                    'write_off_until_current_year': write_off_til_current_year,
                    'price_at_end_of_year': price_at_end_of_year if price_at_end_of_year > 0 else 0,
                }
                single_items_list.append(new_single_item)
        
        # Kreiranje i čuvanje popisne liste
        initial_data = {
            'inventory': inventory_initial_data,
            'single_items': single_items_list,
        }
        
        working_data = {
            'inventory': inventory_working_data,
            'single_items': single_items_list,
        }
        
        new_inventory_list = Inventory(
            description=description,
            date=datum,
            initial_data=json.dumps(initial_data, default=serialize_data),
            working_data=json.dumps(working_data, default=serialize_data),
            status='active'
        )
        
        db.session.add(new_inventory_list)
        db.session.commit()
        
        flash('Popis inventara je uspešno kreiran.', 'success')
        return redirect(url_for('main.home'))
    print(f'last debug on GET: {[type(room) for room in rooms]=}')
    # return render_template('create_inventory_list.html',
    #                         title="Kreiranje popisne liste",
    #                         route_name=route_name,
    #                         rooms=rooms,
    #                         users=users,
    #                         years=years,
    #                         inventory_at_the_end_of_last_year=inventory_at_the_end_of_last_year,
    #                         inventory_at_the_end_of_current_year=inventory_at_the_end_of_current_year)
    # Dodajte provjeru da li rooms lista ostaje ista
    original_rooms = rooms.copy()
    
    result = render_template('create_inventory_list.html',
                         title="Kreiranje popisne liste",
                         route_name=route_name,
                         rooms=rooms,
                         users=users,
                         years=years,
                         inventory_at_the_end_of_last_year=inventory_at_the_end_of_last_year,
                         inventory_at_the_end_of_current_year=inventory_at_the_end_of_current_year)
                         
    # Provjera nakon renderovanja
    print("\n=== DEBUG AFTER TEMPLATE ===")
    print(f"Original rooms count: {len(original_rooms)}")
    print(f"Current rooms count: {len(rooms)}")
    print("========================\n")
    
    return result

@inventory.route('/edit_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def edit_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
        
    inventory = Inventory.query.get_or_404(inventory_id)
    
    try:
        inventory_data = json.loads(inventory.working_data)
        initial_data = json.loads(inventory.initial_data)
    except json.JSONDecodeError:
        flash('Greška pri učitavanju podataka popisa.', 'danger')
        return redirect(url_for('main.home'))

    all_rooms = Room.query.filter(
        ~Room.id.in_([1, 2, 4])
    ).order_by(
        Room.building_id,
        Room.name
    ).all()

    # Kreiranje mape user_id -> room_ids
    user_room_map = {}
    for room_data in inventory_data['inventory']:
        user_id = room_data['user_id']
        if user_id not in user_room_map:
            user_room_map[user_id] = []
        user_room_map[user_id].append(room_data['room_id'])

    def calculate_room_summary(room_id, inventory_data):
        """Izračunava rezime za sobu."""
        room_items = next((room['items'] for room in inventory_data['inventory'] 
                          if room['room_id'] == room_id), [])
        
        return {
            'total_items': len(room_items),
            'counted_items': sum(1 for item in room_items if item['quantity_input'] > 0),
            'total_quantity': sum(item['quantity'] for item in room_items),
            'counted_quantity': sum(item['quantity_input'] for item in room_items),
            'categories': len(set(item.get('category_number') for item in room_items)),
            'items_with_comments': sum(1 for item in room_items if item.get('comment')),
        }

    def get_room_inventory_status(room_id, inventory_data):
        """Određuje detaljni status popisa za prostoriju."""
        summary = calculate_room_summary(room_id, inventory_data)
        
        if summary['total_items'] == 0:
            return {
                'status': 'empty',
                'label': 'Prazna prostorija',
                'color': 'secondary',
                'summary': summary
            }
        
        if summary['counted_items'] == 0:
            return {
                'status': 'not_started',
                'label': 'Nije započeto',
                'color': 'danger',
                'summary': summary
            }
            
        if summary['counted_items'] < summary['total_items']:
            progress = (summary['counted_items'] / summary['total_items']) * 100
            return {
                'status': 'in_progress',
                'label': f'U toku ({progress:.1f}%)',
                'color': 'warning',
                'summary': summary
            }
            
        differences = summary['counted_quantity'] != summary['total_quantity']
        if differences:
            return {
                'status': 'differences',
                'label': 'Završeno (razlike)',
                'color': 'info',
                'summary': summary
            }
            
        return {
            'status': 'completed',
            'label': 'Završeno',
            'color': 'success',
            'summary': summary
        }

    # Priprema room_buttons liste
    room_buttons = []
    if current_user.authorization == 'admin':
        for room in all_rooms:
            assigned_user = User.query.get(
                next((rd['user_id'] for rd in inventory_data['inventory'] 
                      if rd['room_id'] == room.id), None)
            )

            status = get_room_inventory_status(room.id, inventory_data)
            
            new_room = {
                'room_id': room.id,
                'name': room.name,
                'dynamic_name': room.dynamic_name,
                'building_name': room.building.name,
                'building_id': room.building_id,
                'assigned_user': assigned_user.name if assigned_user else None,
                'assigned_user_id': assigned_user.id if assigned_user else None,
                'status': status,
            }
            room_buttons.append(new_room)
    else:
        assigned_room_ids = user_room_map.get(current_user.id, [])
        for room in all_rooms:
            if room.id in assigned_room_ids:
                status = get_room_inventory_status(room.id, inventory_data)
                
                new_room = {
                    'room_id': room.id,
                    'name': room.name,
                    'dynamic_name': room.dynamic_name,
                    'building_name': room.building.name,
                    'building_id': room.building_id,
                    'assigned_user': current_user.name,
                    'assigned_user_id': current_user.id,
                    'status': status,
                }
                room_buttons.append(new_room)

    # Sortiranje i grupisanje
    room_buttons.sort(key=lambda x: (x['building_name'], x['name']))
    unique_building_names = sorted({room['building_name'] for room in room_buttons})

    # Ukupna statistika
    def calculate_inventory_stats(inventory_data, room_buttons):
        total_stats = {
            'total_rooms': len(room_buttons),
            'completed_rooms': 0,
            'in_progress_rooms': 0,
            'not_started_rooms': 0,
            'empty_rooms': 0,
            'rooms_with_differences': 0,
            'total_items': 0,
            'counted_items': 0,
            'total_quantity': 0,
            'counted_quantity': 0,
            'total_categories': set(),
            'items_with_comments': 0
        }
        
        for room in room_buttons:
            status = room['status']
            summary = status['summary']
            
            if status['status'] == 'completed':
                total_stats['completed_rooms'] += 1
            elif status['status'] == 'in_progress':
                total_stats['in_progress_rooms'] += 1
            elif status['status'] == 'not_started':
                total_stats['not_started_rooms'] += 1
            elif status['status'] == 'empty':
                total_stats['empty_rooms'] += 1
            elif status['status'] == 'differences':
                total_stats['rooms_with_differences'] += 1
                
            total_stats['total_items'] += summary['total_items']
            total_stats['counted_items'] += summary['counted_items']
            total_stats['total_quantity'] += summary['total_quantity']
            total_stats['counted_quantity'] += summary['counted_quantity']
            total_stats['items_with_comments'] += summary['items_with_comments']
            
            # Dodajemo kategorije u set
            room_items = next((r['items'] for r in inventory_data['inventory'] 
                             if r['room_id'] == room['room_id']), [])
            categories = {item.get('category_number') for item in room_items}
            total_stats['total_categories'].update(categories)
            
        total_stats['total_categories'] = len(total_stats['total_categories'])
        total_stats['completion_percentage'] = (
            (total_stats['counted_items'] / total_stats['total_items'] * 100) 
            if total_stats['total_items'] > 0 else 0
        )
        
        return total_stats

    inventory_stats = calculate_inventory_stats(inventory_data, room_buttons)

    return render_template(
        'edit_inventory_list.html',
        title="Izmena popisnih listi",
        inventory_id=inventory_id,
        room_buttons=room_buttons,
        unique_building_names=unique_building_names,
        inventory_stats=inventory_stats,
        inventory=inventory
    )

# def _get_room_inventory_status(room_id, inventory_data):
#     """
#     Određuje status popisa za datu prostoriju.
#     """
#     for room_data in inventory_data['inventory']:
#         if room_data['room_id'] == room_id:
#             total_items = len(room_data['items'])
#             items_counted = sum(1 for item in room_data['items'] if item['quantity_input'] > 0)
            
#             if total_items == 0:
#                 return {
#                     'status': 'empty',
#                     'label': 'Prazna prostorija',
#                     'color': 'secondary'
#                 }
#             elif items_counted == 0:
#                 return {
#                     'status': 'not_started',
#                     'label': 'Nije započeto',
#                     'color': 'danger'
#                 }
#             elif items_counted < total_items:
#                 return {
#                     'status': 'in_progress',
#                     'label': f'U toku ({items_counted}/{total_items})',
#                     'color': 'warning'
#                 }
#             else:
#                 return {
#                     'status': 'completed',
#                     'label': 'Završeno',
#                     'color': 'success'
#                 }
#     return {
#         'status': 'error',
#         'label': 'Greška',
#         'color': 'danger'
#     }

# def _calculate_inventory_stats(inventory_data, room_buttons):
#     """
#     Izračunava statistiku popisa.
#     """
#     total_rooms = len(room_buttons)
#     completed_rooms = sum(1 for room in room_buttons 
#                          if room['status']['status'] == 'completed')
#     in_progress_rooms = sum(1 for room in room_buttons 
#                            if room['status']['status'] == 'in_progress')
#     not_started_rooms = sum(1 for room in room_buttons 
#                            if room['status']['status'] == 'not_started')
#     empty_rooms = sum(1 for room in room_buttons 
#                      if room['status']['status'] == 'empty')

#     return {
#         'total_rooms': total_rooms,
#         'completed_rooms': completed_rooms,
#         'in_progress_rooms': in_progress_rooms,
#         'not_started_rooms': not_started_rooms,
#         'empty_rooms': empty_rooms,
#         'completion_percentage': (completed_rooms / total_rooms * 100) if total_rooms > 0 else 0
#     }


@inventory.route('/edit_inventory_list/<int:inventory_id>/<int:room_id>', methods=['GET', 'POST'])
def edit_inventory_room_list(inventory_id, room_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
        
    # Učitavanje osnovnih podataka
    inventory = Inventory.query.get_or_404(inventory_id)
    school = School.query.get_or_404(1)
    room = Room.query.get_or_404(room_id)
    
    try:
        working_data = json.loads(inventory.working_data)
        initial_data = json.loads(inventory.initial_data)
        inventory_list_data = working_data['inventory']
    except json.JSONDecodeError:
        flash('Greška pri učitavanju podataka popisa.', 'danger')
        return redirect(url_for('inventory.edit_inventory_list', inventory_id=inventory_id))

    # Provera autorizacije
    user_id = next((entry['user_id'] for entry in inventory_list_data 
                   if entry['room_id'] == room_id), None)
                   
    if current_user.authorization != 'admin' and current_user.id != user_id:
        flash('Nemate dozvolu za da pristupite ovoj stranici.', 'danger')
        return redirect(url_for('inventory.edit_inventory_list', inventory_id=inventory_id))

    if request.method == 'POST':
        # Dobavljanje postojećih podataka za sobu
        items_in_room = next((room['items'] for room in inventory_list_data 
                            if room['room_id'] == room_id), [])

        # Kreiranje rečnika za grupisane stavke
        grouped_items = {}
        
        # Obrada POST zahteva
        for field_name, value in request.form.items():
            if field_name.startswith('quantity_input_'):
                serial = int(field_name.split("_")[-1])
                quantity_input = int(value)
                comment = request.form.get(f'comment_{serial}')
                
                single_item = SingleItem.query.filter_by(serial=serial).first()
                if not single_item:
                    continue

                # Tražimo originalnu količinu iz initial_data
                initial_room_data = next((room for room in initial_data['inventory'] 
                                    if room['room_id'] == room_id), {})
                initial_items = initial_room_data.get('items', [])
                original_quantity = sum(item.get('quantity', 0) 
                                    for item in initial_items 
                                    if item['serial'] == serial)

                grouped_items[serial] = {
                    'serial': serial,
                    'name': single_item.name,
                    'category_number': single_item.category.category_number,
                    'category_name': single_item.category.name,
                    'depreciation_rate': single_item.depreciation_rate.rate,
                    'quantity': original_quantity,
                    'quantity_input': quantity_input,
                    'comment': comment,
                    'current_price': single_item.current_price
                }

        # Ažuriranje inventory podataka
        for room_data in inventory_list_data:
            if room_data['room_id'] == room_id:
                room_data['items'] = list(grouped_items.values())
                break

        # Čuvanje promena
        working_data['inventory'] = inventory_list_data
        inventory.working_data = json.dumps(working_data, default=serialize_data)
        db.session.commit()

        flash(f'Popisna lista za prostoriju {room.name} je sačuvana!', 'success')
        return redirect(url_for('inventory.edit_inventory_list', inventory_id=inventory_id))

    # GET zahtev
    if request.method == 'GET':
        inventory_item_list_data = []
        serials_in_room = set()
        
        # Dobavljanje stavki trenutne sobe iz working_data i initial_data
        current_room_data = next((room for room in inventory_list_data 
                                if room['room_id'] == room_id), None)
        
        # Dobavljanje originalnih podataka iz initial_data
        initial_room_data = next((room for room in initial_data['inventory'] 
                                if room['room_id'] == room_id), None)
        
        print("DEBUG - Initial Room Data:", json.dumps(initial_room_data, default=serialize_data))
        
        if current_room_data and current_room_data.get('items'):
            # Prvo kreiramo mapu originalnih količina iz initial_data
            original_quantities = {}
            if initial_room_data and initial_room_data.get('items'):
                for item in initial_room_data['items']:
                    serial = str(item['serial'])  # Konvertujemo u string za konzistentnost
                    if serial not in original_quantities:
                        original_quantities[serial] = item['quantity']
                    else:
                        original_quantities[serial] += item['quantity']
            
            print("DEBUG - Original Quantities:", original_quantities)

            # Grupišemo po serijama
            grouped_items = {}
            
            for item in current_room_data['items']:
                serial = item['serial']
                single_item = SingleItem.query.filter_by(serial=serial).first()
                
                if not single_item:
                    continue
                    
                serial_str = str(serial)  # Konvertujemo u string za konzistentnost
                
                if serial_str not in grouped_items:
                    grouped_item = {
                        'serial': serial,
                        'name': single_item.name,
                        'category_number': single_item.category.category_number,
                        'category_name': single_item.category.name,
                        'depreciation_rate': single_item.depreciation_rate.rate,
                        'quantity': original_quantities.get(serial_str, 0),  # Koristimo string ključ
                        'quantity_input': item.get('quantity_input', 0),
                        'comment': item.get('comment', ''),
                        'current_price': str(single_item.current_price)  # Konvertujemo Decimal u string
                    }
                    grouped_items[serial_str] = grouped_item
                else:
                    if item.get('quantity_input', 0) > 0:
                        grouped_items[serial_str]['quantity_input'] = item.get('quantity_input', 0)
                    if item.get('comment'):
                        grouped_items[serial_str]['comment'] = item.get('comment')

                serials_in_room.add(serial)

            # Pretvaramo grupisane podatke u listu
            inventory_item_list_data = list(grouped_items.values())

        # Priprema liste svih dostupnih serija
        all_items = SingleItem.query.all()
        # Kreiranje privremenog rečnika za grupisanje po serijama
        unique_items_dict = {}
        for single_item in all_items:
            if single_item.serial not in serials_in_room:
                serial = str(single_item.serial)  # Konvertujemo u string za konzistentnost
                if serial not in unique_items_dict:
                    unique_items_dict[serial] = (
                        single_item.serial,
                        single_item.name,
                        f"{single_item.category.category_number} - {single_item.category.name}",
                        single_item.depreciation_rate.rate
                    )

        # Konvertovanje rečnika u listu
        all_serials_items_list = list(unique_items_dict.values())

        # Sortiranje lista
        all_serials_items_list.sort(key=lambda x: (x[2], int(str(x[0]))))
        inventory_item_list_data.sort(key=lambda x: (x['category_number'], int(str(x['serial']))))

        # Generisanje imena sobe i dokumenta
        room_name = f'{room.building.name} - ({room.name}) {room.dynamic_name}'
        popisna_lista_gen(inventory_item_list_data, room, inventory_id, school, inventory)

        # Debug ispis
        print("Final Data:", json.dumps(inventory_item_list_data, default=serialize_data))

        # Određivanje naslova stranice
        title = f"Pregled popisne liste: {room.name}" if inventory.status == 'finished' else f"Izmena popisne liste: {room.name}"

        return render_template('edit_inventory_room_list.html',
                            school=school,
                            title=title,
                            inventory_item_list_data=inventory_item_list_data,
                            inventory=inventory,
                            room_name=room_name,
                            all_serials_items_list=all_serials_items_list,
                            inventory_id=inventory_id,
                            room_id=room_id)

@inventory.route('/compare_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def compare_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
        
    inventory = Inventory.query.get_or_404(inventory_id)
    
    if request.method == 'POST':
        try:
            # Učitavanje podataka iz inventara
            single_items_from_inventory = json.loads(inventory.initial_data)['single_items']
            working_inventory_list_data = json.loads(inventory.working_data)['inventory']
            
            # Prebacivanje svih predmeta u magacin viškova (room_id=4)
            SingleItem.query.filter(SingleItem.room_id > 2).update({SingleItem.room_id: 4}, synchronize_session=False)
            db.session.commit()
            
            # Priprema podataka za efikasno procesiranje
            items_to_move = {}  # {(serial, room_id): quantity}
            
            # Formiramo mapu koja sadrži potreban broj predmeta za svaku prostoriju
            for room in working_inventory_list_data:
                room_id = int(room['room_id'])
                for item in room['items']:
                    serial = int(item['serial'])
                    quantity_input = int(item['quantity_input'])
                    
                    if quantity_input > 0:
                        items_to_move[(serial, room_id)] = quantity_input
            # Procesiramo predmete u manjim grupama od po 100 predmeta
            batch_size = 100
            keys = list(items_to_move.keys())
            
            for i in range(0, len(keys), batch_size):
                batch_keys = keys[i:i+batch_size]
                
                for serial, room_id in batch_keys:
                    quantity_needed = items_to_move[(serial, room_id)]
                    
                    if room_id == 3:
                        # Za prostoriju 3 tražimo samo predmete koji su na reversu
                        single_items = SingleItem.query.filter_by(
                            room_id=4, serial=serial
                        ).filter(
                            SingleItem.reverse_date.isnot(None)
                        ).limit(quantity_needed).all()
                    else:
                        # Za sve ostale prostorije tražimo SAMO predmete koji NISU na reversu
                        single_items = SingleItem.query.filter_by(
                            room_id=4, serial=serial, reverse_date=None
                        ).limit(quantity_needed).all()
                    
                    # Ažuriramo prostoriju za sve pronađene predmete
                    for single_item in single_items:
                        single_item.room_id = room_id
                
                # Commit radimo samo jednom po batch-u, a ne za svaki predmet
                db.session.commit()
            
            # Završavanje popisa
            inventory.status = 'finished'
            db.session.commit()
            
            # Ažuriranje trenutnih cena u batch-u
            single_items = SingleItem.query.filter(SingleItem.room_id > 2).all()
            batch_size = 200
            
            for i in range(0, len(single_items), batch_size):
                batch_items = single_items[i:i+batch_size]
                
                for single_item in batch_items:
                    single_item.current_price, _ = current_price_calculation(
                        single_item.initial_price,
                        single_item.depreciation_rate.rate,
                        single_item.purchase_date,
                        single_item.expediture_date,
                        None,
                        single_item.input_in_app_date,
                        single_item.deprecation_value
                    )
                
                # Commit radimo samo jednom po batch-u
                db.session.commit()
            
            # Obrada predmeta koji su ostali u magacinu viškova (manjak)
            items_in_surplus = SingleItem.query.filter_by(room_id=4).all()
            # Koristimo datum iz tekućeg popisa umesto današnjeg datuma
            inventory_date = inventory.date
            
            # Obrađujemo ih u batch-u
            batch_size = 200
            for i in range(0, len(items_in_surplus), batch_size):
                batch_items = items_in_surplus[i:i+batch_size]
                
                for item in batch_items:
                    item.expediture_price = item.current_price
                    item.expediture_date = inventory_date
                    item.current_price = 0
                    item.room_id = 2
                
                # Commit radimo samo jednom po batch-u
                db.session.commit()
            
            flash(f'Popis "{inventory.description}" je završen.', 'success')
            return redirect(url_for('main.home'))
        
        except Exception as e:
            db.session.rollback()
            # Dodati logging ovde
            flash(f'Došlo je do greške prilikom završavanja popisa: {str(e)}', 'danger')
            return redirect(url_for('inventory.compare_inventory_list', inventory_id=inventory_id))
        
        # single_items = SingleItem.query.filter(SingleItem.room_id > 2).all()
        
        # for single_item in single_items:
        #     single_item.room_id = 4
        #     db.session.commit()
            
        # Prolazak kroz popisane prostorije i predmete
        # for room in working_inventory_list_data:
        #     room_id = int(room['room_id'])
        #     for item in room['items']:
        #         serial = int(item['serial'])
        #         quantity_input = int(item['quantity_input'])
        #         print(f"\n--- Obrada: Serija {serial} u prostoriji {room_id}, potrebna količina: {quantity_input} ---")
        #         # Premeštanje predmeta prema popisanim količinama
        #         for i in range(quantity_input):
        #             if room_id == 3:
        #                 # Za prostoriju 3 tražimo samo predmete koji su na reversu
        #                 single_item = SingleItem.query.filter_by(room_id=4, serial=serial).filter(SingleItem.reverse_date.isnot(None)).first()
        #                 print(f"Prostorija 3 - Tražim predmet sa reversom: {'Pronađen' if single_item else 'Nije pronađen'}")
        #                 if single_item:
        #                     print(f"Predmet ID: {single_item.id}, Serija: {single_item.serial}, Reverse date: {single_item.reverse_date}")
        #                     single_item.room_id = room_id
        #                     db.session.commit()
        #                     print(f"Premešten u prostoriju {room_id}")
        #             else:
        #                 # Za sve ostale prostorije tražimo SAMO predmete koji NISU na reversu
        #                 single_item = SingleItem.query.filter_by(room_id=4, serial=serial, reverse_date=None).first()
        #                 print(f"Ostale prostorije - Tražim predmet bez reversa: {'Pronađen' if single_item else 'Nije pronađen'}")
        #                 if single_item:
        #                     print(f"Predmet ID: {single_item.id}, Serija: {single_item.serial}, Reverse date: {single_item.reverse_date}")
        #                     single_item.room_id = room_id
        #                     db.session.commit()
        #                     print(f"Premešten u prostoriju {room_id}")

        
        # inventory.status = 'finished'
        # db.session.commit()
        
        # # Ažuriranje trenutnih cena
        # for single_item in single_items:
        #     single_item.current_price, _ = current_price_calculation(
        #         single_item.initial_price,
        #         single_item.depreciation_rate.rate,  # Korišćenje depreciation_rate direktno iz SingleItem
        #         single_item.purchase_date,
        #         single_item.expediture_date,
        #         None,
        #         single_item.input_in_app_date,
        #         single_item.deprecation_value
        #     )
        #     db.session.commit()
        # # Obrada predmeta koji su ostali u magacinu viškova (manjak)
        # items_in_surplus = SingleItem.query.filter_by(room_id=4).all()
        # today = date.today()
        
        # for item in items_in_surplus:
        #     # Čuvamo trenutnu cenu pre nego što je postavimo na 0
        #     item.expediture_price = item.current_price
        #     # Postavljamo datum isknjiženja na danas
        #     item.expediture_date = today
        #     # Postavljamo trenutnu cenu na 0
        #     item.current_price = 0
        #     # Prebacujemo u magacin isknjiženja
        #     item.room_id = 2
            
        # db.session.commit()
        # flash(f'Popis "{inventory.description}" je završen.', 'success')
        # return redirect(url_for('main.home'))

    # GET request - priprema podataka za poređenje
    def serialize_data(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    initial_inventory_list_data = json.loads(inventory.initial_data)
    initial_inventory_list_data_rooms = initial_inventory_list_data['inventory']
    
    # Kreiranje mape za grupisanje po serijama
    compare_items_dict = {}
    
    # Obrada inicijalnih podataka
    for room in initial_inventory_list_data_rooms:
        for item in room['items']:
            serial = str(item['serial'])  # Konvertujemo u string za konzistentnost
            single_item = SingleItem.query.filter_by(serial=serial).first()
            
            if not single_item:
                continue
                
            if serial not in compare_items_dict:
                compare_items_dict[serial] = {
                    'serial': serial,
                    'name': single_item.name,
                    'category_number': single_item.category.category_number,
                    'category_name': single_item.category.name,
                    'depreciation_rate': single_item.depreciation_rate.rate,
                    'quantity': item['quantity'],
                    'value': float(single_item.current_price) * item['quantity'],
                    'quantity_input': 0,
                    'value_input': 0,
                }
            else:
                compare_items_dict[serial]['quantity'] += item['quantity']
                compare_items_dict[serial]['value'] += float(single_item.current_price) * item['quantity']

    # Obrada popisanih podataka
    working_inventory_list_data = json.loads(inventory.working_data)['inventory']
    
    for room in working_inventory_list_data:
        for item in room['items']:
            serial = str(item['serial'])
            single_item = SingleItem.query.filter_by(serial=serial).first()
            
            if not single_item:
                continue
                
            quantity_input = int(item['quantity_input'])
            value_input = float(single_item.current_price) * quantity_input
            
            if serial in compare_items_dict:
                compare_items_dict[serial]['quantity_input'] += quantity_input
                compare_items_dict[serial]['value_input'] += value_input
            else:
                compare_items_dict[serial] = {
                    'serial': serial,
                    'name': single_item.name,
                    'category_number': single_item.category.category_number,
                    'category_name': single_item.category.name,
                    'depreciation_rate': single_item.depreciation_rate.rate,
                    'quantity': 0,
                    'value': 0,
                    'quantity_input': quantity_input,
                    'value_input': value_input,
                }

    # Konvertovanje rečnika u listu i sortiranje
    compare_items_list = list(compare_items_dict.values())
    compare_items_list.sort(key=lambda x: (x['category_number'], int(x['serial'])))

    return render_template('compare_inventory_list.html', 
                            title="Poređenje popisnih rezultata sa stanjem u sistemu",
                            compare_items_list=compare_items_list,
                            inventory=inventory)

@inventory.route('/read_inventory_list', methods=['GET', 'POST'])
def read_inventory_list():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory_lists = Inventory.query.all()
    return render_template('read_inventory_list.html', title="Pregled popisnih listi",
                            inventory_lists=inventory_lists)


@inventory.route('/add_single_item_to_room', methods=['GET', 'POST'])
def add_single_item_to_room():
    room_id = int(request.form.get('add_single_item_room_id'))
    inventory_id = int(request.form.get('add_single_item_inventory_id'))
    single_item_serial = int(request.form.get('add_single_item_data'))
    single_item_quantity = int(request.form.get('add_single_item_quantity'))
    signle_item_comment = request.form.get('add_single_item_comment')
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_list_data = json.loads(inventory.working_data)['inventory']
    working_data = json.loads(inventory.working_data)
    initial_data = json.loads(inventory.initial_data)
    # print(f'{working_data=}')
    
    
    # proverava da li predmet sa istom serijom već postoji u popisnoj listi
    desired_room_data = None
    for room_data in inventory_list_data:
        if room_data['room_id'] == room_id:
            desired_room_data = room_data
            break
    if desired_room_data is None:
        desired_room_data = {
            "room_id": room_id,
            "user_id": current_user.id, #! ovo može da bude problem, treba da se dodeli id predsednika komisije
            "items": []
        }
    for item in desired_room_data['items']:
        if item['serial'] == single_item_serial:
            flash('Izabrana serija već postoji stavka u popisnoj listi.', 'danger')
            return redirect(url_for('inventory.edit_inventory_room_list', inventory_id = inventory_id, room_id = room_id))
        
    print(f'{inventory_list_data=}')
    print(f'{desired_room_data=}')
    single_item = SingleItem.query.filter_by(serial=single_item_serial).first() #! treba uzimati podatak iz istance pre popisa: initial_data['single_items'] a ne iz db jer db menja current price
    print(f'debug total_value: {single_item.current_price=} * {single_item_quantity=}')
    item_working_data = {
                'serial': single_item_serial,
                'quantity': 0,
                'quantity_input': single_item_quantity,
                'current_price': single_item.current_price, 
                'total_value': single_item.current_price * single_item_quantity,
                'comment': signle_item_comment
            }
    item_initial_data = {
                'serial': single_item_serial,
                'quantity': 0,
                'quantity_input': single_item_quantity,
                'total_value': 0, #! zato što je dodat red u listu i inicijalna vrednost je 0
                'comment': signle_item_comment
            }
    
    print(f'{item_working_data=}')
    # if room_id not in [room_dict['room_id'] for room_dict in working_data['inventory']]:
    #     flash('Izabrana prostorija ne postoji u inicijalnoj popisnoj listi. dodaj kod za to', 'danger')
    #     new_room_dict = desired_room_data['items'].append(item_initial_data)
    #     working_data['inventory'].append(new_room_dict)
    # else:
    for room_dict in working_data['inventory']:
        if room_dict['room_id'] == room_id:
            room_dict['items'].append(item_working_data)
            break
    print(f'posle dodatka nosvog reda: {working_data["inventory"]=}')
    
    # if room_id not in [room_dict['room_id'] for room_dict in initial_data['inventory']]:
    #     flash('Izabrana prostorija ne postoji u inicijalnoj popisnoj listi. dodaj kod za to', 'danger')
    #     new_room_dict = desired_room_data['items'].append(item_initial_data)
    #     initial_data['inventory'].append(new_room_dict)
    # else:
    for room_dict in initial_data['inventory']:
        if room_dict['room_id'] == room_id:
            room_dict['items'].append(item_initial_data)
            break
    inventory.initial_data = json.dumps(initial_data, default=serialize_data)
    inventory.working_data = json.dumps(working_data, default=serialize_data)
    db.session.commit()
    
    flash('Dodata je nova stavka u popisnu listu.', 'success')
    return redirect(url_for('inventory.edit_inventory_room_list', inventory_id = inventory_id, room_id = room_id))