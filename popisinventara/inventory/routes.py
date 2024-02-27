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
        flash('Pre kreiranja popisnih listi treba prestiti sve predmete iz virtuelnog magacina.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    print(f'{active_inventory_list=}')
    if active_inventory_list:
        flash(f'Da bi ste kreirali novu popisnu listu, morate prvo završiti aktivnu popisnu listu koja je započeta: {active_inventory_list.date}.', 'danger')
        return redirect(url_for('main.home'))
    all_room_list = Room.query.all()
    rooms = [room for room in all_room_list if room.id not in [1, 2, 4]] #! 1 - virtuelni magacin se ne popisuje; 2 - magacin rashodovanih predmeta se ne popisuje; 4 - magacin manjkova se ne popisuje
    # debug_room_ids = [room.id for room in rooms]
    # # return f"{debug_room_ids=}"
    users = User.query.filter_by(authorization='user').all()
    this_year = date.today().year
    years = [this_year - 1, this_year]
    
    inventory_years = [inventory.date for inventory in Inventory.query.all()]
    print(f'{inventory_years=}')
    inventory_at_the_end_of_current_year = False
    inventory_at_the_end_of_last_year = False
    if date((date.today().year -1), 12, 31) in inventory_years:
        inventory_at_the_end_of_last_year = True
    if date((date.today().year), 12, 31) in inventory_years:
        inventory_at_the_end_of_current_year = True
    
    if request.method == 'POST':
        description = request.form.get('description')
        single_items = SingleItem.query.all()
        
        
        year = request.form.get('inventry_types')
        if year != '':
            datum = date(int(year), 12, 31)
        else:
            year = None #! zato što mi ne treba godina koja je opcioni input u funkciji write_off_until_current_year()
            datum = date.today()
        
        for single_item in single_items:
            if single_item.expediture_date is None:
                print(f'start -- pre izmene: {single_item.current_price=}')
                single_item.current_price, _ = current_price_calculation(single_item.initial_price, single_item.single_item_item.item_depreciation_rate.rate, single_item.purchase_date, single_item.expediture_date, year, single_item.input_in_app_date, single_item.deprecation_value)
                print(f'posle izmene: {single_item.current_price=}')
                print('------------------------------------------------------')
        db.session.commit()
        
        room_ids = request.form.getlist('room_id[]')
        user_ids = request.form.getlist('user_id[]')
        if any(item == '' for item in user_ids):
            flash('Morate dodeliti predsednika popisne komisije za svaku prostoriju. Kliknite na dugme NAZAD da povratite podatke', 'danger')
            return redirect(url_for('inventory.create_inventory_list'))
        room_user_ids = list(zip(room_ids, user_ids))
        print(f'{room_ids=}; {user_ids=}')
        print(f'{room_user_ids=}')
        inventory_initial_data = []
        
        for room in rooms:
            room_id = room.id
            user_id = [int(u_id) for (r_id, u_id) in room_user_ids if r_id == str(room_id)][0]
            single_items_in_room = SingleItem.query.filter_by(room_id=room_id).all()
            items = []
            for single_item in single_items_in_room:
                item = {
                        'serial': int(single_item.inventory_number.split('-')[1]),
                        'quantity': 1,
                        'quantity_input': 0,
                        'current_price': single_item.current_price,
                        'total_value': single_item.current_price,
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
                        found = True
            new_data = {
                'room_id': room_id,
                'user_id': user_id,
                'items': items
            }
            inventory_initial_data.append(new_data)
        
        # for single_item in single_items:
        #     if str(single_item.room_id) not in room_ids:
        #         continue
        #     new_data = {
        #         'room_id': single_item.room_id,
        #         'user_id': [int(user_id) for (room_id, user_id) in room_user_ids if room_id == str(single_item.room_id)][0],
        #         'items': [
        #             {
        #                 # 'item_id': single_item.item_id,
        #                 'serial': int(single_item.inventory_number.split('-')[1]),
        #                 'quantity': 1, 
        #                 'quantity_input': 0,
        #                 'current_price': single_item.current_price,
        #                 'total_value': single_item.current_price,
        #             }
        #         ]
        #     }
        #     if not inventory_initial_data:
        #         inventory_initial_data.append(new_data)
        #     else:
        #         found = False
        #         for existing_data in inventory_initial_data:
        #             if existing_data['room_id'] == new_data['room_id']:
        #                 for item in existing_data['items']:
        #                     if item['serial'] == new_data['items'][0]['serial']:
        #                         item['quantity'] += 1
        #                         item['total_value'] += new_data['items'][0]['current_price']
        #                         found = True
        #                         break
        #                 if not found:
        #                     existing_data['items'].append(new_data['items'][0])
        #                     found = True
        #                 break
        #         if not found:
        #             inventory_initial_data.append(new_data)
        # # print(f'{inventory_initial_data=}')
        inventory_working_data = []

        for room in inventory_initial_data:
            new_room = {'room_id': room['room_id'], 'user_id': room['user_id'], 'items': []}
            for item in room['items']:
                new_item = {'serial': item['serial'], 'quantity': item['quantity'], 'quantity_input': 0, 'current_price': item['current_price'] , 'total_value': 0, 'comment': ''}
                new_room['items'].append(new_item)
            inventory_working_data.append(new_room)

        # print(f'{inventory_working_data=}')
        

        
        
        single_items_list = []
        for single_item in single_items:
            write_off_til_current_year, price_at_end_of_year, depreciation_per_year = write_off_until_current_year(single_item, year) #! proveri ovu funkcionalnost (year)
            new_single_item = {
                'id': single_item.id,
                'serial': single_item.serial,
                'inventory_number': single_item.inventory_number,
                'name': single_item.name,
                'supplier': single_item.supplier,
                'invoice_number': single_item.invoice_number,
                'initial_price': single_item.initial_price,
                'current_price': single_item.current_price,
                'expediture_price': single_item.expediture_price,
                'purchase_date': single_item.purchase_date,
                'expediture_date': single_item.expediture_date,
                'reverse_person': single_item.reverse_person,
                'reverse_date': single_item.reverse_date,
                'room_id': single_item.room_id,
                'item_id': single_item.item_id,
                'category': single_item.single_item_item.item_category.category_number,
                'depreciation_rate': single_item.single_item_item.item_depreciation_rate.rate,
                'depreciation_per_year': depreciation_per_year if depreciation_per_year < single_item.current_price else single_item.current_price, #!!!!!!
                'write_off_until_current_year': write_off_til_current_year,
                'price_at_end_of_year': price_at_end_of_year if price_at_end_of_year > 0 else 0,
            }
            print(f'new_single_item: {new_single_item["current_price"]=}')
            single_items_list.append(new_single_item)
        
        
        initial_data = {
            'inventory': inventory_initial_data,
            'single_items': single_items_list,
        }
        
        working_data = {
            'inventory': inventory_working_data,
            'single_items': single_items_list,
        }
        # print(f'{initial_data=}')
        # print(f'{working_data=}')
        new_inventory_list = Inventory(description=description,
                                        date=datum,
                                        initial_data=json.dumps(initial_data, default=serialize_data),
                                        working_data=json.dumps(working_data, default=serialize_data),
                                        status='active')
        db.session.add(new_inventory_list)
        db.session.commit()
        flash('Popis inventara je uspešno kreiran.', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_inventory_list.html', 
                            title="Kreiranje popisne liste",
                            rooms=rooms,
                            users=users,
                            years=years,
                            inventory_at_the_end_of_last_year=inventory_at_the_end_of_last_year,
                            inventory_at_the_end_of_current_year=inventory_at_the_end_of_current_year,)


@inventory.route('/edit_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def edit_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_list_data = json.loads(inventory.initial_data)
    # print(f'{inventory_list_data=}')
    #! generiši filtrirane popisne liste za prostorije korisnika, tj sve popisne liste za admina
    room_buttons = []
    # if current_user.authorization == 'admin':
    #     for room_data in inventory_list_data['inventory']:
    #         room = Room.query.get_or_404(room_data['room_id'])
    #         new_room = {
    #             'room_id': room_data['room_id'],
    #             'name': room.name,
    #             'dynamic_name': room.dynamic_name,
    #             'building_name': room.room_building.name,
    #         }
    #         room_buttons.append(new_room)
    # else:
    #     for room_data in inventory_list_data['inventory']:
    #         if room_data['user_id'] == current_user.id:
    #             room = Room.query.get_or_404(room_data['room_id'])
    #             new_room = {
    #                 'room_id': room_data['room_id'],
    #                 'name': room.name,
    #                 'dynamic_name': room.dynamic_name,
    #                 'building_name': room.room_building.name,
    #             }
    #             room_buttons.append(new_room)
    all_rooms = Room.query.filter(~Room.id.in_([1, 2, 4])).all() #! ~Room.id.in_([1, 2, 4]) znači da nije u listi
    if current_user.authorization == 'admin':
        for room in all_rooms:
            new_room = {
                'room_id': room.id,
                'name': room.name,
                'dynamic_name': room.dynamic_name,
                'building_name': room.room_building.name,
            }
            room_buttons.append(new_room)
    else:
        for room_data in inventory_list_data['inventory']:
            if room_data['user_id'] == current_user.id:
                room = Room.query.get_or_404(room_data['room_id'])
                new_room = {
                    'room_id': room_data['room_id'],
                    'name': room.name,
                    'dynamic_name': room.dynamic_name,
                    'building_name': room.room_building.name,
                }
                room_buttons.append(new_room)
    # Sortiranje po 'building_name'
    sorted_room_buttons = sorted(room_buttons, key=lambda x: (x['building_name'], x['name']))
    room_buttons = sorted_room_buttons
    print(f'{room_buttons=}')
    unique_building_names = sorted({room['building_name'] for room in room_buttons})
    print(f'{unique_building_names}')
    
    #! generiši popisne liste
    popisne_liste_gen()
    return render_template('edit_inventory_list.html', title="Izmena popisnih listi",
                            inventory_id=inventory_id,
                            room_buttons=room_buttons,
                            unique_building_names=unique_building_names)


@inventory.route('/edit_inventory_list/<int:inventory_id>/<int:room_id>', methods=['GET', 'POST'])
def edit_inventory_room_list(inventory_id, room_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory = Inventory.query.get_or_404(inventory_id)
    school = School.query.get_or_404(1)
    # print(f'ovo tražim: {json.loads(inventory.working_data)=}')
    inventory_list_data = json.loads(inventory.working_data)['inventory']
    for entry in inventory_list_data:
        if entry['room_id'] == room_id:
            user_id = entry['user_id']
            break
        else:
            user_id = None
    print(f'test user_id za selektovani room_id: {room_id=}; {user_id=}')
    if current_user.authorization != 'admin' and current_user.id != int(user_id):
        flash('Nemate dozvolu za da pristupite ovoj stranici.', 'danger')
        return redirect(url_for('inventory.edit_inventory_list', inventory_id=inventory_id))
    if request.method == 'POST':
        print(f'save dugme iz sobe... nastavi kod')
        inventory = Inventory.query.get_or_404(inventory_id)
        working_inventory_list_data = json.loads(inventory.working_data)['inventory']
        print(f'{working_inventory_list_data=}')
        #! izvlači podakte o items u prostoriji koja se edituje
        items_in_room = []
        for room in working_inventory_list_data:
            if room['room_id'] == room_id:
                items_in_room = room['items']
                break
        print(f'debug items_in_room: {items_in_room=}')

        print(f'{request.form=}')
        for item_id in request.form:
            print(f'{item_id=}')
            if item_id.startswith('quantity_input_'):
                serial = int(item_id.split("_")[-1])
                quantity_input = int(request.form.get(item_id))
                comment = request.form.get(f'comment_{item_id.split("_")[-1]}')
                single_item = SingleItem.query.filter_by(serial=serial).first()
                if serial in [int(item['serial']) for item in items_in_room]:
                    for item in items_in_room:
                        if item['serial'] == serial:
                            item['quantity_input'] = quantity_input
                            item['total_value'] = quantity_input * single_item.current_price
                            item['comment'] = comment
                            break
                else:
                    items_in_room.append({
                                            'serial': serial,
                                            'quantity': 0, #! 
                                            'quantity_input': quantity_input,
                                            'current_price': single_item.current_price,
                                            'total_value': quantity_input * single_item.current_price,
                                            'comment': comment
                                        })
                
        print(f'{items_in_room=}')
        for room in working_inventory_list_data:
            if room['room_id'] == room_id:
                room['items'] = items_in_room
                break
        working_data = {
            'inventory': working_inventory_list_data,
            'single_items': json.loads(inventory.working_data)['single_items'],
        }
        inventory.working_data = json.dumps(working_data, default=serialize_data)
        db.session.commit()
        flash(f'Popisna lista {room_id} je sačuvana!', 'success')
        return redirect(url_for('inventory.edit_inventory_list', inventory_id=inventory_id))
    if request.method == 'GET':
        inventory = Inventory.query.get_or_404(inventory_id)
        initial_inventory_list_data = json.loads(inventory.initial_data)['inventory']
        working_inventory_list_data = json.loads(inventory.working_data)['inventory']
        single_items = SingleItem.query.all()
        serials_in_room = []
        for room in working_inventory_list_data:
            if room['room_id'] == room_id:
                serials_in_room = [int(serial['serial']) for serial in room['items']]
                break
        print(f'{serials_in_room=}')
        
        
        all_serials_items_list = list(set((int(single_item.item_id), int(single_item.serial), single_item.single_item_item.name, single_item.name) for single_item in single_items if int(single_item.serial) not in serials_in_room)) #! izbaciti serije koje se već nalaze u ovoj prostoriji
        sorted_list = sorted(all_serials_items_list, key=lambda x: (x[0], x[1]))
        print(f'sorted list: {sorted_list}')
        all_serials_items_list = sorted_list
        print(f'list: {all_serials_items_list=}')
        print(f'{working_inventory_list_data=}')
        inventory_item_list_data = []
        for room in working_inventory_list_data:
            print(f'{room=}')
            if room['room_id'] == room_id:
                inventory_item_list_data = room['items']
                for item_data in inventory_item_list_data:
                    print(f'{item_data=}')
                    print(f'{item_data["serial"]=}')
                    single_item = SingleItem.query.filter_by(serial = item_data["serial"]).first()
                    print(f'{single_item.id=} {single_item.name=}')
                    item_data['item_id'] = single_item.item_id
                    item_data['item_name'] = single_item.single_item_item.name
                    item_data['name'] = single_item.name
                    for room in working_inventory_list_data:
                        if room['room_id'] == room_id:
                            for item in room['items']:
                                if item['serial'] == item_data["serial"]:
                                    item_data['quantity_input'] = item['quantity_input']
                                    item_data['comment'] = item['comment']
                                    break  # Ovdje prekidamo petlju jer smo pronašli traženi element
                            break  # Ovdje prekidamo petlju jer smo pronašli traženu sobu
        if len(inventory_item_list_data) == 0:
            inventory_item_list_data = []
        else:
            sorted_inventory = sorted(inventory_item_list_data, key=lambda x: (x['item_id'], x['serial']))
            inventory_item_list_data = sorted_inventory
        print(f'test: {inventory_item_list_data=}')
        room = Room.query.get_or_404(room_id)
        room_name = f'{Room.query.get_or_404(room.id).room_building.name} - ({Room.query.get_or_404(room.id).name}) {Room.query.get_or_404(room.id).dynamic_name}'
        popisna_lista_gen(inventory_item_list_data, room, inventory_id)
    if inventory.status == 'finished':
        title = f"Pregled popisne liste: {room_id}"
    else:
        title = f"Izmena popisne liste: {room_id}"
    return render_template('edit_inventory_room_list.html',
                            school=school,
                            title=title,
                            inventory_item_list_data=inventory_item_list_data,
                            inventory=inventory,
                            room_name=room_name,
                            all_serials_items_list=all_serials_items_list,
                            inventory_id=inventory_id,
                            room_id=room_id,)


@inventory.route('/compare_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def compare_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory = Inventory.query.get_or_404(inventory_id)
    if request.method == 'POST':
        single_items = SingleItem.query.all()
        single_items_from_inventory = json.loads(inventory.initial_data)['single_items']
        working_inventory_list_data = json.loads(inventory.working_data)['inventory']
        #! prebaci sve predmete u magacin viškova (room_id=4)
        for single_item in single_items:
            single_item.room_id = 4
            db.session.commit()
        #! izlista sve prostorije, definiše room_id
        for room in working_inventory_list_data:
            room_id = int(room['room_id'])
            #! za svaki predmet u prostoriji
            for item in room['items']:
                serial = int(item['serial'])
                quantity_input = int(item['quantity_input'])
                #! premesti onoliko predmeta koliki je quantity_input (iz magacina manjka u određenu prostoriju)
                for i in range(quantity_input):
                    single_item = SingleItem.query.filter_by(room_id=4).filter_by(serial=serial).first()
                    if single_item:
                        single_item.room_id = room_id
                        db.session.commit()
                    else: 
                        print(f'Nema predmeta sa serijom {serial} u magacinu manjkova.')
        # print(f'{single_items_from_inventory=}')
        # print(f'{single_items=}')
        inventory.status = 'finished'
        db.session.commit()
        for single_item in single_items:
            single_item.current_price, _ = current_price_calculation(single_item.initial_price, single_item.single_item_item.item_depreciation_rate.rate, single_item.purchase_date, single_item.expediture_date, None, single_item.input_in_app_date, single_item.deprecation_value)
            db.session.commit()
        flash(f'Popis "{inventory.description}" je završen.', 'success')
        return redirect(url_for('main.home'))
    initial_inventory_list_data = json.loads(inventory.initial_data)
    initial_inventory_list_data_rooms = initial_inventory_list_data['inventory']
    print(f'{initial_inventory_list_data_rooms=}')
    compare_items_list = [] #! ideja je da se prvo napravi lista initial, pa da se njoj dodaju quantity_input iz working_inventory_list_data
    for room in initial_inventory_list_data_rooms:
        print(f'{room=}')
        for item in room['items']:
            print(f'{item=}')
            single_item = SingleItem.query.filter_by(serial=item['serial']).first()
            initial_item = {
                'item_id': single_item.item_id,
                'serial': item['serial'],
                'item_name': single_item.single_item_item.name,
                'name': single_item.name,
                'quantity': item['quantity'],
                'value': single_item.current_price,
                'quantity_input': 0,
                'value_input': 0, #! vrednost je 0 jele je input 0
            }
            if not compare_items_list:
                compare_items_list.append(initial_item)
            else:
                found = False
                for existing_item in compare_items_list:
                    if existing_item['serial'] == initial_item['serial']:
                        existing_item['quantity'] += initial_item['quantity']
                        existing_item['value'] += initial_item['value']
                        found = True
                        break
                if not found:
                    compare_items_list.append(initial_item)
                
            print(f'{compare_items_list=}')
    working_inventory_list_data = json.loads(inventory.working_data)
    working_inventory_list_data_rooms = working_inventory_list_data['inventory'] 
    #! ovde nastavi: ideja je da se prvo napravi lista initial, pa da se njoj dodaju quantity_input iz working_inventory_list_data
    for room in working_inventory_list_data_rooms:
        for item in room['items']:
            single_item = SingleItem.query.filter_by(serial=item['serial']).first()
            input_item = {
                'item_id': single_item.item_id,
                'serial': item['serial'],
                'item_name': single_item.single_item_item.name,
                'name': single_item.name,
                'quantity': 0,
                'value': 0,
                'quantity_input': item['quantity_input'],
                'value_input': single_item.current_price, #!
            }
            print(f'{room["items"]=}')
            serial = item['serial']
            quantity_input = item['quantity_input']
            print(f'{quantity_input=}; {item=}; {single_item.current_price=}')
            value_input = float(item['current_price']) * quantity_input #! mora da se isravi dict room da ima kay value...
            print(f'{quantity_input=}')
            found = False
            for existing_item in compare_items_list:
                if existing_item['serial'] == serial:
                    existing_item['quantity_input'] += quantity_input
                    existing_item['value_input'] += value_input
                    found = True
                    break
            if not found:
                compare_items_list.append(input_item)
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