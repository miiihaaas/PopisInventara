import time
from datetime import date, datetime
from flask import Blueprint, flash, json
from flask import request, render_template, redirect, url_for
from flask_login import current_user
from popisinventara import db
from popisinventara.single_items.functions import current_price_calculation
from popisinventara.models import SingleItem, Item, Room, Inventory
from sqlalchemy import and_


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


@single_items.route('/api/singleitems')
def api_single_items():
    single_items_query = SingleItem.query
    
    # search filter
    search = request.args.get('search[value]')
    room_select = request.args.get('room_select')
    current_year_procurement = request.args.get('current_year_procurement')
    print(f'{current_year_procurement=}')
    if search and not room_select:
        print('imamo pretragu')
        print(f'{search=}')
        single_items_query = single_items_query.filter(db.or_(
            SingleItem.name.like(f'%{search}%'),
            SingleItem.inventory_number.like(f'%{search}%'),
            SingleItem.item_id.like(f'%{search}%'),
        ))
    elif search and room_select:
        print('selektovana je prostorija i imamo pretragu')
        print(f'{search=}')
        print(f'{room_select=}')
        single_items_query = single_items_query.filter(db.or_(
            SingleItem.name.like(f'%{search}%'),
            SingleItem.inventory_number.like(f'%{search}%'),
            SingleItem.room_id.like(f'{int(room_select)}'),
            SingleItem.item_id.like(f'%{search}%'),
        ))
    elif room_select:
        print('samo je selektovana prostorija')
        print(f'{room_select=}')
        single_items_query = single_items_query.filter(db.or_(
            SingleItem.room_id.like(f'{int(room_select)}'),
        ))
    # Proverite da li je vrednost "on" prisutna za current_year_procurement
    if current_year_procurement == 'true':
        current_year_procurement = True
        # Prvo, dohvatite trenutnu godinu
        current_year = datetime.now().year
            
        # Zatim postavite početni i krajnji datum za trenutnu godinu
        start_date = date(current_year, 1, 1)
        end_date = date(current_year, 12, 31)
        single_items_query = single_items_query.filter(and_(SingleItem.purchase_date >= start_date, SingleItem.purchase_date <= end_date))
    else:
        current_year_procurement = False
    total_filtered = single_items_query.count()
    
    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        if col_name not in ['id', 'inventory_number', 'name', 'initial_price', 'current_price', 'room_id', 'purchase_date']:
            col_name = 'name'
        descending = request.args.get(f'order[{i}][dir]') == 'desc'
        col = getattr(SingleItem, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        single_items_query = single_items_query.order_by(*order)
    
    # pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    single_items_query = single_items_query.offset(start).limit(length)
    
    single_items_list = []
    for single_item in single_items_query:
        new_dict = {
            'id': single_item.id,
            'inventory_number': single_item.inventory_number,
            'name': single_item.name,
            'initial_price': single_item.initial_price,
            'current_price': single_item.current_price,
            'room_id': single_item.room_id,
            'purchase_date': single_item.purchase_date,
            'button_name': single_item.single_item_room.room_building.name + " > " +  single_item.single_item_room.dynamic_name
        }
        single_items_list.append(new_dict)
    return {
        'data': single_items_list,
        'recordsFiltered': total_filtered,
        'recordsTotal': total_filtered,
        'draw': request.args.get('draw', type=int),
    }


@single_items.route('/move_single_item__to_room', methods=['GET', 'POST'])
def move_single_item__to_room():
    single_item_id = request.form.get('single_item_id')
    room_id = request.form.get('edit_single_item_room')
    print(f'{single_item_id=} {room_id=}')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    single_item.room_id = room_id
    db.session.commit()
    flash(f'Uspesno ste premestili predmet {single_item.name} u prostoriju {single_item.single_item_room.name}.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/add_single_item', methods=['GET', 'POST'])
def add_single_item():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
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
    quantity = request.form.get('add_single_item_quantity')
    initial_price = float(request.form.get('add_single_item_initial_price')) / float(quantity)
    purchase_date = datetime.strptime(request.form.get('add_single_item_date'), '%Y-%m-%d').date()
    current_price = current_price_calculation(initial_price, rate, purchase_date)
    print(f'{item_id=} {item_name=} {item_room=} {initial_price=} {purchase_date=} {quantity=}')
    new_single_items = []
    for i in range(1, int(quantity) + 1):
        print(f'{type(item_id)=}, {type(max_serial_number)=}, {type(i)=}')
        inventory_number = f'{int(item_id):04d}-{max_serial_number:05d}-{i:04d}'
        new_single_item = SingleItem(item_id=item_id,
                                        serial=max_serial_number,
                                        name=item_name,
                                        room_id=item_room,
                                        initial_price=initial_price,
                                        current_price=current_price,
                                        purchase_date=purchase_date,
                                        inventory_number=inventory_number)
        new_single_items.append(new_single_item)
    db.session.add_all(new_single_items)
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
        if 'submit_to' in request.form:
            item_id = request.form.get('item_id_to_move_to')
            room_id = request.form.get('room_id_to_move_to')
            return redirect(url_for('single_items.move_to', item_id=item_id, room_id=room_id))
        elif 'submit_from' in request.form:
            item_id = request.form.get('item_id_to_move_from')
            room_id = request.form.get('room_id_to_move_from')
            return redirect(url_for('single_items.move_from', item_id=item_id, room_id=room_id))

    
    item_list = Item.query.all()
    room_list_to = Room.query.all() 
    room_list_from = Room.query.all() #! ne treba listati prostorije koje nemaju ovaj predmet za tip kretnje iz prostorije u druge prostorije
    print(f'{item_list=}')
    return render_template('move_select.html', title='Izbor predmeta za premeštanje',
                            item_list=item_list,
                            room_list_to=room_list_to,
                            room_list_from=room_list_from)


@single_items.route("/move_from/<int:item_id>/<int:room_id>", methods=['GET', 'POST'])
def move_from(item_id, room_id):
    item = Item.query.filter_by(id=item_id).first()
    room_from = Room.query.filter_by(id=room_id).first()
    room_list = Room.query.all()
    single_item_in_room_list = SingleItem.query.filter_by(item_id=item_id, room_id=room_id).all()
    print(f'{single_item_in_room_list=}')
    data_list = [] #! svi predmeti izabranog tipa u svim prostorijama
    
    for room in room_list:
        single_item_list = SingleItem.query.filter_by(item_id=item_id, room_id=room.id).all()
        total_quantity = len(single_item_list)

        if single_item_list:
            single_item = single_item_list[0]  # Uzmemo prvi predmet za osnovne podatke
            new_dict = {
                'building': single_item.single_item_room.room_building.name,
                'room_id': room.id,
                'item_id': item_id,
                'room': f'({room.name}) {room.dynamic_name}',
                'serial': single_item.inventory_number.split('-')[1],
                'quantity': total_quantity,
                'single_item_name': f'{single_item.name}',
                'initial_price': single_item.initial_price,
                'current_price': single_item.current_price,
                'purchase_date': single_item.purchase_date,
            }
        else:
            new_dict = {
                'building': room.room_building.name,
                'room_id': room.id,
                'item_id': item_id,
                'room': f'({room.name}) {room.dynamic_name}',
                'serial': '',
                'quantity': 0,
                'single_item_name': '',
                'initial_price': 0,
                'current_price': 0,
                'purchase_date': '',
            }
        data_list.append(new_dict)
            
    print(f'{data_list=}')


    
    quantity_of_single_items_in_room = 0
    for data in data_list:
        if data['room_id'] == room_id and data['item_id'] == item_id:
            quantity_of_single_items_in_room += data['quantity']
            print(f'{quantity_of_single_items_in_room=}')
    
    if request.method == 'POST':
        print(f'{request.form=}')
        get_move_list = json.loads(request.form['data_to_move_from'])
        move_list = [data for data in get_move_list if data['quantity_to_move_from'] != '']
        print(f'{move_list=}')
        
        if not db.session.is_active:
            db.session.begin()
        for data in move_list:
            room_id_to_move = int(data['room_id'])
            quantity_to_move = int(data['quantity_to_move_from'])
            print(f'{room_id=} {quantity_to_move=}')
            for i in range(quantity_to_move):
                if not single_item_in_room_list:
                    flash(f'Premešteni su svi predmeti iz izabrane prostorije, nema predmeta koji mogu da se premeste u prostoriju: {room_id_to_move}.', 'danger')
                    break #! Ako su svi predmeti iz te prostorije već premješteni, izađite iz petlje
                
                single_item_to_move_from = single_item_in_room_list[0]
                single_item_to_move_from.room_id = room_id_to_move
                single_item_in_room_list.remove(single_item_to_move_from)
        db.session.commit()
        return redirect(url_for('single_items.single_item_rooms', item_id=item_id))
    
    return render_template('move_from.html', title='Premeštanje predmeta iz izabrane prostorije',
                            item=item,
                            room_from=room_from,
                            single_item_list=single_item_list,
                            data_list=data_list,
                            quantity_of_single_items_in_room=quantity_of_single_items_in_room)


@single_items.route("/move_to/<int:item_id>/<int:room_id>", methods=['GET', 'POST'])
def move_to(item_id, room_id):
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
        get_move_list = json.loads(request.form['data_to_move_to'])
        move_list = [data for data in get_move_list if data['quantity_to_move_to'] != '']
        print(f'{move_list=}')
        try:
            if not db.session.is_active:
                db.session.begin()
            for data in move_list:
                for i in range(int(data['quantity_to_move_to'])):
                    single_item = SingleItem.query.filter_by(room_id=data['room_id']).filter_by(serial=int(data['serial'])).first()
                    single_item.room_id = room_id #!iz atributa funkcije
            db.session.commit()
        except Exception as e:
            print(f'Greška pri čuvanju promena u bazi: {e}')
            db.session.rollback() # U slučaju greške, poništite transakciju
        return redirect(url_for('single_items.single_item_rooms', item_id=item_id))
    return render_template('move_to.html', title='Premeštanje predmeta u izabranu prostoriju',
                            item=item,
                            room=room,
                            single_item_list=single_item_list,
                            data_list=data_list)


@single_items.route('/update_price', methods=['GET', 'POST'])
def update_price():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
    single_items = SingleItem.query.all()
    for sigle_item in single_items:
        sigle_item.current_price = current_price_calculation(sigle_item.initial_price, sigle_item.single_item_item.item_depreciation_rate.rate, sigle_item.purchase_date)
        print(f'{sigle_item.id=}')
        
    db.session.commit()
    return redirect(url_for('single_items.single_item_list'))