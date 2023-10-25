import json
from datetime import date
from flask import Blueprint
from flask import  render_template, flash, redirect, url_for
from flask_login import current_user
from flask import request
from popisinventara import db
from popisinventara.models import Inventory, Room, SingleItem, Item
from popisinventara.inventory.functions import popisna_lista_gen, popisne_liste_gen


inventory = Blueprint('inventory', __name__)


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
        flash('Pre kreiranja popisnih sliti treba rasporediti sve predmete i virtuelnog magacina!', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    print(f'{active_inventory_list=}')
    if active_inventory_list:
        flash(f'Morate završiti aktivnu popisnu listu {active_inventory_list} da bi ste kreirali novu', 'danger')
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        description = request.form.get('description')
        single_items = SingleItem.query.all()
        data = []
        for single_item in single_items:
            new_data = {
                'room_id': single_item.room_id,
                'items': [
                    {
                        # 'item_id': single_item.item_id,
                        'serial': single_item.inventory_number.split('-')[1],
                        'quantity': 1, 
                    }
                ]
            }
            if not data:
                data.append(new_data)
            else:
                found = False
                for existing_data in data:
                    if existing_data['room_id'] == new_data['room_id']:
                        for item in existing_data['items']:
                            if item['serial'] == new_data['items'][0]['serial']:
                                item['quantity'] += 1
                                found = True
                                break
                        if not found:
                            existing_data['items'].append(new_data['items'][0])
                            found = True
                        break
                if not found:
                    data.append(new_data)
        print(f'{data=}')
        working_data = []

        for room in data:
            new_room = {'room_id': room['room_id'], 'items': []}
            for item in room['items']:
                new_item = {'serial': item['serial'], 'quantity_input': 0, 'comment': ''}
                new_room['items'].append(new_item)
            working_data.append(new_room)

        print(working_data)
        new_inventory_list = Inventory(description=description,
                                        date=date.today(),
                                        initial_data=json.dumps(data),
                                        working_data=json.dumps(working_data),
                                        status='active')
        db.session.add(new_inventory_list)
        db.session.commit()
        return redirect(url_for('main.home'))
    return render_template('create_inventory_list.html', title="Kreiranje popisne liste")


@inventory.route('/edit_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def edit_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory = Inventory.query.get_or_404(inventory_id)
    inventory_list_data = json.loads(inventory.initial_data)
    print(f'{inventory_list_data=}')
    room_buttons = []
    for room_data in inventory_list_data:
        room = Room.query.get_or_404(room_data['room_id'])
        new_room = {
            'room_id': room_data['room_id'],
            'name': room.name,
            'dynamic_name': room.dynamic_name,
            'building_name': room.room_building.name,
        }
        room_buttons.append(new_room)
    # Sortiranje po 'building_name'
    sorted_room_buttons = sorted(room_buttons, key=lambda x: (x['building_name'], x['dynamic_name']))
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
    if request.method == 'POST':
        print(f'save dugme iz sobe... nastavi kod')
        inventory = Inventory.query.get_or_404(inventory_id)
        working_inventory_list_data = json.loads(inventory.working_data)
        print(f'{working_inventory_list_data=}')
        data = []
        print(f'{request.form=}')
        for item_id in request.form:
            print(f'{item_id=}')
            if item_id.startswith('quantity_input_'):
                serial = item_id.split("_")[-1]
                quantity_input = int(request.form.get(item_id))
                comment = request.form.get(f'comment_{item_id.split("_")[-1]}')

                data.append({
                    'serial': serial,
                    'quantity_input': quantity_input,
                    'comment': comment
                })
        print(f'{data=}')
        for room in working_inventory_list_data:
            if room['room_id'] == room_id:
                room['items'] = data
                break
        inventory.working_data = json.dumps(working_inventory_list_data)
        db.session.commit()
        return redirect(url_for('inventory.compare_inventory_list', inventory_id=inventory_id))
    if request.method == 'GET':
        inventory = Inventory.query.get_or_404(inventory_id)
        initial_inventory_list_data = json.loads(inventory.initial_data)
        working_inventory_list_data = json.loads(inventory.working_data)
        print(f'{working_inventory_list_data=}')
        for room in initial_inventory_list_data:
            print(f'{room=}')
            if room['room_id'] == room_id:
                inventory_item_list_data = room['items']
                for item_data in inventory_item_list_data:
                    print(f'{item_data=}')
                    print(f'{item_data["serial"]=}')
                    single_item = SingleItem.query.filter(SingleItem.inventory_number.like(f'%-{item_data["serial"]}-%')).first()
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
        sorted_inventory = sorted(inventory_item_list_data, key=lambda x: (x['item_id'], x['serial']))
        inventory_item_list_data = sorted_inventory
        print(f'test: {inventory_item_list_data=}')
        room_name = f'{Room.query.get_or_404(room_id).room_building.name} - ({Room.query.get_or_404(room_id).name}) {Room.query.get_or_404(room_id).dynamic_name}'
        popisna_lista_gen(inventory_item_list_data, room_name, inventory_id)
    return render_template('edit_inventory_room_list.html', 
                            title=f"Izmena popisne liste: {room_id}",
                            inventory_item_list_data=inventory_item_list_data,
                            inventory=inventory,
                            room_name=room_name)


@inventory.route('/compare_inventory_list/<int:inventory_id>', methods=['GET', 'POST'])
def compare_inventory_list(inventory_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'success')
        return redirect(url_for('users.login'))
    inventory = Inventory.query.get_or_404(inventory_id)
    if request.method == 'POST':
        inventory.status = 'finished'
        db.session.commit()
        flash(f'Popis "{inventory.description}" je završen.', 'success')
        return redirect(url_for('main.home'))
    initial_inventory_list_data = json.loads(inventory.initial_data)
    compare_items_list = [] #! ideja je da se prvo napravi lista initial, pa da se njoj dodaju quantity_input iz working_inventory_list_data
    for room in initial_inventory_list_data:
        print(f'{room=}')
        for item in room['items']:
            print(f'{item=}')
            single_item = SingleItem.query.filter(SingleItem.inventory_number.like(f'%-{item["serial"]}-%')).first()
            initial_item = {
                'item_id': single_item.item_id,
                'serial': item['serial'],
                'item_name': single_item.single_item_item.name,
                'name': single_item.name,
                'quantity': item['quantity'],
                'quantity_input': 0
            }
            if not compare_items_list:
                compare_items_list.append(initial_item)
            else:
                found = False
                for existing_item in compare_items_list:
                    if existing_item['serial'] == initial_item['serial']:
                        existing_item['quantity'] += initial_item['quantity']
                        found = True
                        break
                if not found:
                    compare_items_list.append(initial_item)
                
            print(f'{compare_items_list=}')
    working_inventory_list_data = json.loads(inventory.working_data)
    #! ovdenastavi: ideja je da se prvo napravi lista initial, pa da se njoj dodaju quantity_input iz working_inventory_list_data
    for room in working_inventory_list_data:
        for item in room['items']:
            single_item = SingleItem.query.filter(SingleItem.inventory_number.like(f'%-{item["serial"]}-%')).first()
            input_item = {
                'item_id': single_item.item_id,
                'serial': item['serial'],
                'item_name': single_item.single_item_item.name,
                'name': single_item.name,
                'quantity': 0,
                'quantity_input': item['quantity_input']
            }
            serial = item['serial']
            quantity_input = item['quantity_input']
            print(f'{quantity_input=}')
            found = False
            for existing_item in compare_items_list:
                if existing_item['serial'] == serial:
                    existing_item['quantity_input'] += quantity_input
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