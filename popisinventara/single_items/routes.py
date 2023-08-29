import time
from datetime import datetime
from flask import Blueprint, json
from flask import request, render_template, redirect, url_for
from popisinventara import db
from popisinventara.single_items.functions import current_price_calculation
from popisinventara.models import SingleItem, Item, Room, Inventory


single_items = Blueprint('single_items', __name__)


@single_items.route('/single_item_list')
def single_item_list():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    single_item_list = SingleItem.query.all()
    item_list = Item.query.all()
    room_list = Room.query.all()
    
    cumulatively_per_series = []
    for item in single_item_list:
        series = item.inventory_number.split('-')[1]
        
        new_dict = {
            'item_id': item.item_id,
            'series': series,
            'name': item.name,
            'quantity': 1,
            'initial_price': item.initial_price,
            'current_price': item.current_price,
            'purchase_date': item.purchase_date,
        }
        
        series_found = False
        for existing_dict in cumulatively_per_series:
            if existing_dict['series'] == series:
                existing_dict['quantity'] += 1
                existing_dict['initial_price'] += item.initial_price
                existing_dict['current_price'] += item.current_price
                series_found = True
                break
        
        if not series_found:
            cumulatively_per_series.append(new_dict)

    cumulatively_per_item = []
    for item in single_item_list:
        new_dict = {
            'item_id': item.item_id,
            'name': item.name,
            'quantity': 1,
            'initial_price': item.initial_price,
            'current_price': item.current_price,
            'purchase_date': item.purchase_date,
        }
        
        item_found = False
        for existing_dict in cumulatively_per_item:
            if existing_dict['item_id'] == item.item_id:
                existing_dict['quantity'] += 1
                existing_dict['initial_price'] += item.initial_price
                existing_dict['current_price'] += item.current_price
                item_found = True
                break
            
        if not item_found:
            cumulatively_per_item.append(new_dict)
    cumulatively_per_room = []
    for item in single_item_list:
        new_dict = {
            'room_id': item.room_id,
            'room_name': item.single_item_room.name,
            'item_id': item.item_id,
            'item_name': item.single_item_item.name,
            'serial': item.serial,
            'quantity': 1,
            'initial_price': item.initial_price,
            'current_price': item.current_price,
            'purchase_date': item.purchase_date,
        }
        item_found = False
        for existing_dict in cumulatively_per_room:
            if existing_dict['room_id'] == item.room_id:
                existing_dict['quantity'] += 1
                existing_dict['initial_price'] += item.initial_price
                existing_dict['current_price'] += item.current_price
                item_found = True
                break
        if not item_found:
            cumulatively_per_room.append(new_dict)
    
    
    return render_template('single_items.html', title="Pregled predmeta",
                            active_inventory_list=active_inventory_list,
                            single_item_list=single_item_list,
                            item_list=item_list,
                            room_list=room_list,
                            cumulatively_per_series=cumulatively_per_series,
                            cumulatively_per_item=cumulatively_per_item,
                            cumulatively_per_room=cumulatively_per_room)


@single_items.route('/add_single_item', methods=['GET', 'POST'])
def add_single_item():
    single_items_list = SingleItem.query.all()
    if len(single_items_list) == 0:
        max_serial_number = 1
    else:
        max_serial_number = max([int(single_item.inventory_number.split('-')[1]) for single_item in single_items_list])+1
    item_id = request.form.get('add_single_item_item_id')
    rate = Item.query.filter_by(id=item_id).first().item_depreciation_rate.rate
    print(f'{rate=}')
    item_name = request.form.get('add_single_item_name')
    item_room = request.form.get('add_single_item_room')
    initial_price = request.form.get('add_single_item_initial_price')
    purchase_date = datetime.strptime(request.form.get('add_single_item_date'), '%Y-%m-%d').date()
    quantity = request.form.get('add_single_item_quantity')
    current_price = current_price_calculation(initial_price, rate, purchase_date)
    print(f'{item_id=} {item_name=} {item_room=} {initial_price=} {purchase_date=} {quantity=}')
    for i in range(1, int(quantity)+1):
        inventory_number = f'{item_id}-{max_serial_number}-{i}'
        new_single_item = SingleItem(item_id=item_id,
                                        serial=max_serial_number,
                                        name=item_name,
                                        room_id=item_room,
                                        initial_price=initial_price,
                                        current_price=current_price,
                                        purchase_date=purchase_date,
                                        inventory_number=inventory_number)
        db.session.add(new_single_item)
        db.session.commit()
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/single_item_rooms/<int:item_id>', methods=['GET', 'POST'])
def single_item_rooms(item_id):
    item = Item.query.filter_by(id=item_id).first()
    single_item_list = SingleItem.query.filter_by(item_id=item_id).all()
    data_list = []
    for single_item in single_item_list:
        new_dict = {
            'building': single_item.single_item_room.room_building.name,
            'room_id': single_item.single_item_room.id,
            'room': f'({single_item.single_item_room.name}) {single_item.single_item_room.dynamic_name}',
            'serial': single_item.inventory_number.split('-')[1],
            'quantity': 1,
            'initial_price': single_item.initial_price,
            'current_price': single_item.current_price,
            'purchase_date': single_item.purchase_date,
        }
        found = False
        for existing_item in data_list:
            if existing_item['building'] == new_dict['building'] and existing_item['room'] == new_dict['room']:
                existing_item['quantity'] += 1
                found = True
                break
        
        if not found:
            data_list.append(new_dict)
        
    print(f'{data_list=}')
    
    return render_template('single_item_rooms.html', title="Pregled predmeta po prostorijama",
                            single_item_list=single_item_list,
                            item=item,
                            data_list=data_list)


@single_items.route('/room_single_items/<int:room_id>', methods=['GET', 'POST'])
def room_single_items(room_id):
    room = Room.query.filter_by(id=room_id).first()
    single_item_list = SingleItem.query.filter_by(room_id=room_id).all()
    print(f'{single_item_list=}')
    data_list = []
    for single_item in single_item_list:
        new_dict = {
            'id': single_item.single_item_item.id,
            'name': f'{single_item.single_item_item.name}',
            'serial': single_item.inventory_number.split('-')[1],
            'quantity': 1,
            'initial_price': single_item.initial_price,
            'current_price': single_item.current_price,
            'purchase_date': single_item.purchase_date,
        }
        print(f'{new_dict=}')
        found = False
        for existing_item in data_list:
            if existing_item['id'] == new_dict['id']:
                existing_item['quantity'] += 1
                found = True
                break
        if not found:
            data_list.append(new_dict)
    print(f'{data_list=}')
    return render_template('room_single_items.html', title="Pregled predmeta u prostoriji",
                                room=room,
                                single_item_list=single_item_list,
                                data_list=data_list)


@single_items.route('/move_select', methods=['GET', 'POST'])
def move_select_item():
    if request.method == 'POST':
        item_id = request.form.get('item_id_to_move')
        room_id = request.form.get('room_id_to_move')
        return redirect(url_for('single_items.move', item_id=item_id, room_id=room_id))
    
    item_list = Item.query.all()
    room_list = Room.query.all()
    print(f'{item_list=}')
    return render_template('move_select.html', title='Izbor predmeta za premeštanje',
                            item_list=item_list,
                            room_list=room_list)


@single_items.route("/move/<int:item_id>/<int:room_id>", methods=['GET', 'POST'])
def move(item_id, room_id):
    item = Item.query.filter_by(id=item_id).first()
    room = Room.query.filter_by(id=room_id).first()
    single_item_list = SingleItem.query.filter_by(item_id=item_id).all()
    data_list = []
    for single_item in single_item_list:
        new_dict = {
            'building': single_item.single_item_room.room_building.name,
            'room_id': single_item.single_item_room.id,
            'room': f'({single_item.single_item_room.name}) {single_item.single_item_room.dynamic_name}',
            'serial': single_item.inventory_number.split('-')[1],
            'quantity': 1,
            'single_item_name': f'{single_item.name}',
            'initial_price': single_item.initial_price,
            'current_price': single_item.current_price,
            'purchase_date': single_item.purchase_date,
        }
        found = False
        for existing_item in data_list:
            if existing_item['building'] == new_dict['building'] and existing_item['room'] == new_dict['room'] and existing_item['serial'] == new_dict['serial']:
                existing_item['quantity'] += 1
                found = True
                break
        
        if not found:
            data_list.append(new_dict)
    print(f'{data_list=}')
    if request.method == 'POST':
        print(f'{request.form=}')
        get_move_list = json.loads(request.form['data_to_move'])
        
        move_list = [data for data in get_move_list if data['quantity_to_move'] != '']
        print(f'{move_list=}')
        for data in move_list:
            for i in range(int(data['quantity_to_move'])):
                single_item = SingleItem.query.filter_by(room_id=data['room_id']).filter_by(serial=data['serial']).first()
                single_item.room_id = room_id #!iz atributa funkcije
                db.session.commit()
        return redirect(url_for('single_items.single_item_rooms', item_id=item_id))
    return render_template('move.html', title='Premeštanje predmeta',
                            item=item,
                            room=room,
                            single_item_list=single_item_list,
                            data_list=data_list)
    
@single_items.route('/update_price', methods=['GET', 'POST'])
def update_price():
    single_items = SingleItem.query.all()
    print(f'{single_items=}')
    for sigle_item in single_items:
        sigle_item.current_price = current_price_calculation(sigle_item.initial_price, sigle_item.single_item_item.item_depreciation_rate.rate, sigle_item.purchase_date)
        print(f'{sigle_item.id=}')
        db.session.commit()
    return redirect(url_for('single_items.single_item_list'))