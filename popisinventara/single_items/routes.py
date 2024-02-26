import time
from datetime import date, datetime
from flask import Blueprint, flash, json, render_template_string, Markup
from flask import request, render_template, redirect, url_for
from flask_login import current_user
from popisinventara import db
from popisinventara.reports.functions import write_off_until_current_year
from popisinventara.single_items.functions import create_reverse_document, current_price_calculation
from popisinventara.models import School, SingleItem, Item, Room, Inventory
from sqlalchemy import and_, or_, extract


single_items = Blueprint('single_items', __name__)


def single_item_list_without_expeditured_items():
    '''
    This function returns a query of all single items that have not been expeditured yet or expeditured year is equal to current year.
    It does this by filtering out all single items that have an expediture date set.
    The list is then returned.
    '''
    current_month = datetime.now().month #! ako se u januaru i februaru radi popis od prošle godine
    if current_month in (1, 2):
        current_year = datetime.now().year - 1
    else:
        current_year = datetime.now().year

    single_item_list = SingleItem.query.filter(
        or_(
            SingleItem.expediture_date.is_(None),
            extract('year', SingleItem.expediture_date) == current_year
        )
    )

    return single_item_list

@single_items.route('/single_item_list')
def single_item_list():
    inventory_years = [inventory.date for inventory in Inventory.query.all()]
    print(f'{inventory_years=}')
    
    correction = 0
    if date((date.today().year -1), 12, 31) not in inventory_years:
        print(f'NIJE urađen je popis na kraju prošle godine')
        correction = 1
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    single_item_list = single_item_list_without_expeditured_items().all()
    item_list = Item.query.all()
    all_room_list = Room.query.all()
    room_list = [room for room in all_room_list if room.id not in [2]] #! sve sobe osim magacina za rashod (id=2), magacina za revers (id=3) i magacina za manjkove (id=4)
    
    cumulatively_per_series = []
    for item in single_item_list:
        print(f'debug: {type(item.initial_price)=}')
        series = item.inventory_number.split('-')[1]
        
        new_dict = {
            'item_id': item.item_id,
            'series': series,
            'name': item.single_item_item.name,
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
            'name': item.single_item_item.name,
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
                            correction=correction,
                            active_inventory_list=active_inventory_list,
                            single_item_list=single_item_list,
                            item_list=item_list,
                            room_list=room_list,
                            cumulatively_per_series=cumulatively_per_series,
                            cumulatively_per_item=cumulatively_per_item,
                            cumulatively_per_room=cumulatively_per_room)


@single_items.route('/api/item')
def api_item(): #! kupulativno po tipu predmeta
    single_item_list = single_item_list_without_expeditured_items().all()
    # search filter
    search = request.args.get('search[value]')
    room_select = request.args.get('room_select')
    current_year_procurement = request.args.get('current_year_procurement')
    # Proverite da li je vrednost "on" prisutna za current_year_procurement
    if current_year_procurement == 'true':
        current_year_procurement = True
        # Prvo, dohvatite trenutnu godinu
        current_year = datetime.now().year
        # Zatim postavite početni i krajnji datum za trenutnu godinu
        start_date = date(current_year, 1, 1)
        end_date = date(current_year, 12, 31)
    else: 
        current_year_procurement = False
    
    cumulatively_per_item = []
    if room_select and not current_year_procurement:
        print('dodaj kod za filter: soba')
        for item in single_item_list:
            write_off, _, __ = write_off_until_current_year(item)
            if item.room_id == int(room_select):
                new_dict = {
                    'item_id': item.item_id,
                    'name': item.single_item_item.name,
                    'quantity': 1,
                    'initial_price': item.initial_price,
                    'write_off': write_off,
                    'current_price': item.current_price,
                    'purchase_date': item.purchase_date,
                }
                item_found = False
                for existing_dict in cumulatively_per_item:
                    if existing_dict['item_id'] == item.item_id:
                        existing_dict['quantity'] += 1
                        existing_dict['initial_price'] += item.initial_price
                        existing_dict['current_price'] += item.current_price
                        existing_dict['write_off'] += write_off
                        item_found = True
                        break
                
                if not item_found:
                    cumulatively_per_item.append(new_dict)
    elif room_select and current_year_procurement:
        print('dodaj kod za filter: soba i ova godina')
        for item in single_item_list:
            write_off, _, __ = write_off_until_current_year(item)
            if item.room_id == int(room_select) and item.purchase_date >= start_date and item.purchase_date <= end_date:
                new_dict = {
                    'item_id': item.item_id,
                    'name': item.single_item_item.name,
                    'quantity': 1,
                    'initial_price': item.initial_price,
                    'write_off': write_off,
                    'current_price': item.current_price,
                    'purchase_date': item.purchase_date,
                }
                item_found = False
                for existing_dict in cumulatively_per_item :
                    if existing_dict['item_id'] == item.item_id:
                        existing_dict['quantity'] += 1
                        existing_dict['initial_price'] += item.initial_price
                        existing_dict['current_price'] += item.current_price
                        existing_dict['write_off'] += write_off
                        item_found = True
                        break
                
                if not item_found:
                    cumulatively_per_item.append(new_dict)
    elif not room_select and current_year_procurement:
        print('dodaj kod za filter: ova godina')
        for item in single_item_list:
            write_off, _, __ = write_off_until_current_year(item)
            if item.purchase_date >= start_date and item.purchase_date <= end_date:
                new_dict = {
                    'item_id': item.item_id,
                    'name': item.single_item_item.name,
                    'quantity': 1,
                    'initial_price': item.initial_price,
                    'write_off': write_off,
                    'current_price': item.current_price,
                    'purchase_date': item.purchase_date,
                }
                item_found = False
                for existing_dict in cumulatively_per_item:
                    if existing_dict['item_id'] == item.item_id:
                        existing_dict['quantity'] += 1
                        existing_dict['initial_price'] += item.initial_price
                        existing_dict['current_price'] += item.current_price
                        existing_dict['write_off'] += write_off
                        item_found = True
                        break
                
                if not item_found:
                    cumulatively_per_item.append(new_dict)
    else:
        for item in single_item_list:
            write_off, _, __ = write_off_until_current_year(item)
            new_dict = {
                'item_id': item.item_id,
                'name': item.single_item_item.name,
                'quantity': 1,
                'initial_price': item.initial_price,
                'write_off': write_off,
                'current_price': item.current_price,
                'purchase_date': item.purchase_date,
            }
            
            item_found = False
            for existing_dict in cumulatively_per_item:
                if existing_dict['item_id'] == item.item_id:
                    existing_dict['quantity'] += 1
                    existing_dict['initial_price'] += item.initial_price
                    existing_dict['current_price'] += item.current_price
                    existing_dict['write_off'] += write_off
                    item_found = True
                    break
                
            if not item_found:
                cumulatively_per_item.append(new_dict)
    if search:
        cumulatively_per_item = [record for record in cumulatively_per_item if
                                str(search).lower() in str(record['name']).lower() or
                                str(search).lower() in str(record['item_id']).lower()]
    
    print(f'iz api_item: {current_year_procurement=} {search=} {room_select=}')
    total_filtered = len(cumulatively_per_item)
    
    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        if col_name not in ['item_id', 'name', 'quantity', 'initial_price', 'current_price', 'purchase_date']:
            col_name = 'name'
        descending = request.args.get(f'order[{i}][dir]') == 'desc'
        # Korišćenje lambda funkcija za pristupanje odgovarajućim vrednostima u zapisima
        if col_name == 'item_id':
            col = lambda x: x['item_id']
        elif col_name == 'name':
            col = lambda x: x['name']
        elif col_name == 'quantity':
            col = lambda x: x['quantity']
        elif col_name == 'initial_price':
            col = lambda x: x['initial_price']
        elif col_name == 'current_price':
            col = lambda x: x['current_price']
        elif col_name == 'purchase_date':
            col = lambda x: x['purchase_date']
        order.append(col)
        i += 1
    if order:
        # Ovde primenjujete sortiranje na listu cumulatively_per_series
        cumulatively_per_item.sort(key=lambda x: [col(x) for col in order], reverse=descending)
    # pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    cumulatively_per_item = cumulatively_per_item[start:start + length]
    return {
        'data': cumulatively_per_item,
        'recordsFiltered': total_filtered,
        'recordsTotal': total_filtered,
        'draw': request.args.get('draw', type=int),
    }


@single_items.route('/api/serial')
def api_serial(): #! kumulativno po seriji
    single_item_list = single_item_list_without_expeditured_items().all()
    # room_select = request.args.get('room_select')
    cumulatively_per_series = []
    for item in single_item_list:
        write_off, _, __ = write_off_until_current_year(item)
        series = item.inventory_number.split('-')[1]
        new_dict = {
            'item_id': item.item_id,
            'series': series,
            'name': item.name,
            'quantity': 1,
            'initial_price': item.initial_price,
            'write_off': write_off,
            'current_price': item.current_price,
            'purchase_date': item.purchase_date,
            'supplier': item.supplier,
            'invoice_number': item.invoice_number,
            'room_id': item.room_id,
        }
        series_found = False
        for existing_dict in cumulatively_per_series:
            if existing_dict['series'] == series:
                existing_dict['quantity'] += 1
                existing_dict['write_off'] += write_off
                existing_dict['initial_price'] += item.initial_price
                existing_dict['current_price'] += item.current_price
                series_found = True
                break
        
        if not series_found:
            cumulatively_per_series.append(new_dict)
    print(f'{cumulatively_per_series=}')
    # search filter
    search = request.args.get('search[value]')
    room_select = request.args.get('room_select')
    current_year_procurement = request.args.get('current_year_procurement')
    print(f'iz api_serial: {current_year_procurement=} {search=} {room_select=}')
    
    if room_select:
        # cumulatively_per_series = [record for record in cumulatively_per_series if
        #                         str(room_select).lower() in str(record['room_id']).lower()]
        room_select = request.args.get('room_select')

        cumulatively_per_series = []

        for item in single_item_list:
            write_off, _, __ = write_off_until_current_year(item)
            if item.room_id == int(room_select):
                series = item.inventory_number.split('-')[1]
                new_dict = {
                    'item_id': item.item_id,
                    'series': series,
                    'name': item.name,
                    'quantity': 1,
                    'initial_price': item.initial_price,
                    'write_off': write_off,
                    'current_price': item.current_price,
                    'purchase_date': item.purchase_date,
                    'supplier': item.supplier,
                    'invoice_number': item.invoice_number,
                    'room_id': item.room_id,
                }
                series_found = False
                for existing_dict in cumulatively_per_series:
                    if existing_dict['series'] == series:
                        existing_dict['quantity'] += 1
                        existing_dict['initial_price'] += item.initial_price
                        existing_dict['current_price'] += item.current_price
                        existing_dict['write_off'] += write_off
                        series_found = True
                        break
                
                if not series_found:
                    cumulatively_per_series.append(new_dict)


    # Proverite da li je vrednost "on" prisutna za current_year_procurement
    if current_year_procurement == 'true':
        current_year_procurement = True
        # Prvo, dohvatite trenutnu godinu
        current_year = datetime.now().year

        # Zatim postavite početni i krajnji datum za trenutnu godinu
        start_date = date(current_year, 1, 1)
        end_date = date(current_year, 12, 31)
        cumulatively_per_series = [record for record in cumulatively_per_series if record['purchase_date'] >= start_date and record['purchase_date'] <= end_date]
    else:
        current_year_procurement = False
    if search:
        cumulatively_per_series = [record for record in cumulatively_per_series if
                                str(search).lower() in str(record['name']).lower() or
                                str(search).lower() in str(record['item_id']).lower() or
                                str(search).lower() in str(record['series']).lower() or 
                                str(search).lower() in str(record['supplier']).lower() or 
                                str(search).lower() in str(record['invoice_number']).lower()]
    total_filtered = len(cumulatively_per_series)
    
    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        if col_name not in ['item_id', 'series', 'name', 'quantity', 'initial_price', 'current_price', 'purchase_date']:
            col_name = 'name'
        descending = request.args.get(f'order[{i}][dir]') == 'desc'

        # Korišćenje lambda funkcija za pristupanje odgovarajućim vrednostima u zapisima
        if col_name == 'item_id':
            col = lambda x: x['item_id']
        elif col_name == 'series':
            col = lambda x: x['series']
        elif col_name == 'name':
            col = lambda x: x['name']
        elif col_name == 'quantity':
            col = lambda x: x['quantity']
        elif col_name == 'initial_price':
            col = lambda x: x['initial_price']
        elif col_name == 'current_price':
            col = lambda x: x['current_price']
        elif col_name == 'purchase_date':
            col = lambda x: x['purchase_date']

        order.append(col)
        i += 1

    if order:
        # Ovde primenjujete sortiranje na listu cumulatively_per_series
        cumulatively_per_series.sort(key=lambda x: [col(x) for col in order], reverse=descending)
    # pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    cumulatively_per_series = cumulatively_per_series[start:start + length]
    
    # update_price()
    
    return {
        'data': cumulatively_per_series,
        'recordsFiltered': total_filtered,
        'recordsTotal': total_filtered,
        'draw': request.args.get('draw', type=int),
    }


@single_items.route('/api/singleitems')
def api_single_items():
    single_items_query = single_item_list_without_expeditured_items()
    
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
            SingleItem.supplier.like(f'%{search}%'),
            SingleItem.invoice_number.like(f'%{search}%'),
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
            SingleItem.supplier.like(f'%{search}%'),
            SingleItem.invoice_number.like(f'%{search}%'),
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
        write_off, _, __ = write_off_until_current_year(single_item)
        new_dict = {
            'id': single_item.id,
            'inventory_number': single_item.inventory_number,
            'name': single_item.name,
            'initial_price': single_item.initial_price,
            'write_off': write_off,
            'current_price': single_item.current_price,
            'item_id': single_item.item_id,
            'room_id': single_item.room_id,
            'purchase_date': single_item.purchase_date,
            'supplier': single_item.supplier,
            'invoice_number': single_item.invoice_number,
            'reverse_date': single_item.reverse_date,
            'reverse_person': single_item.reverse_person,
            'button_name': single_item.single_item_room.room_building.name + " > " +  single_item.single_item_room.dynamic_name,
        }
        single_items_list.append(new_dict)
    return {
        'data': single_items_list,
        'recordsFiltered': total_filtered,
        'recordsTotal': total_filtered,
        'draw': request.args.get('draw', type=int),
    }


@single_items.route('/move_single_item_to_room', methods=['GET', 'POST'])
def move_single_item_to_room():
    single_item_id = request.form.get('single_item_id')
    room_id = request.form.get('edit_single_item_room')
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće premeštati predmete dok je aktivan popis.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    if not room_id or not room_id.strip():
        flash('Da bi ste premestili predmet, morate izabrati prostoriju u koju treba premestiti predmet.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    print(f'{single_item_id=} {room_id=}')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    single_item.room_id = room_id
    db.session.commit()
    flash(f'Uspešno ste premestili predmet {single_item.name} u prostoriju {single_item.single_item_room.name}.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/open_file', methods=['GET', 'POST'])
def open_file():
    # Ovde dodajte kod koji će otvoriti fajl u novom tabu
    print('ušao sam u funkciju open_file')
    file_path = './static/reverses/revers.pdf'  # Promenite putanju prema vašem fajlu
    return render_template_string("""
        <script>
            window.open("{{ url_for('single_items.single_item_list') }}", "_blank");
            window.location.href = "{{ url_for('single_items.open_file') }}";
        </script>
    """)
    


@single_items.route('/reverse_single_item', methods=['GET', 'POST'])
def reverse_single_item():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće izdavati predmet na revers dok je aktivan popis.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    school = School.query.get_or_404(1)
    single_item_id = request.form.get('single_item_id_reverse')
    reverse_date_input = request.form.get('single_item_reverse_date_reverse')
    if not reverse_date_input or not reverse_date_input.strip():
        flash('Da bi ste izdali predmet na revers, morate uneti validan datum reversa.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    else:
        reverse_date = datetime.strptime(reverse_date_input, '%Y-%m-%d').date()
    reverse_person = request.form.get('single_item_reverse_person_reverse')
    if not reverse_person or not reverse_person.strip():
        flash('Da bi ste izdali predmet na revers, morate uneti ime osobe kojoj se izdaje revers.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    print(f'{single_item_id=} {reverse_date=} {reverse_person}')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    print(f'revers za ovaj predmet: {single_item=}')
    single_item.reverse_date = reverse_date
    single_item.reverse_person = reverse_person
    single_item.room_id = 3 #! room_id = 3 je magacin reversa
    db.session.commit()
    create_reverse_document(school, single_item)
    file_path = './static/reverses/revers.pdf'
    pdf_link = Markup(f'<a class="alert-success-link" href="{file_path}" target="_blank">Odštampajte revers</a>')
    flash(f'Predmet: {single_item.name} je izdat na revers {single_item.reverse_person}. {pdf_link}', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/return_reverse_single_item', methods=['GET', 'POST'])
def return_reverse_single_item():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    print(f'{request.form=}')
    action = request.form.get('action')
    print('povraćaj reversa')
    single_item_id = request.form.get('single_item_id_reverse_return')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    if action == 'print_reverse':
        school = School.query.get_or_404(1)
        create_reverse_document(school, single_item)
        file_path = './static/reverses/revers.pdf'
        pdf_link = Markup(f'<a class="alert-success-link" href="{file_path}" target="_blank">Odštampajte revers</a>')
        flash(f'Štampa reversa za predmet: {single_item.name} koji je izdat na korišćenje {single_item.reverse_person}. {pdf_link}', 'success')
    elif action == 'return_reverse':
        if active_inventory_list:
            flash(f'Nije moguće vršiti povraćaj reversa dok je aktivan popis.', 'danger')
            return redirect(url_for('single_items.single_item_list'))
        print(f'povraćaj reversa za ovaj predmet: {single_item=}')
        single_item.room_id = 1 #! room_id = 1 je virtuelni magacin
        single_item.reverse_date = None
        single_item.reverse_person = None
        db.session.commit()
        flash(f'Predmet: {single_item.name} je premešten u virtuelni magacin.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/expediture_single_item', methods=['GET', 'POST'])
def expediture_single_item():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće rashodovati predmete dok je aktivan popis.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    single_item_id = request.form.get('single_item_id_expediture')
    expediture_date = request.form.get('single_item_expediture_date_expediture')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    if not expediture_date or not expediture_date.strip():
        flash('Da bi ste rashodovali predmet, morate uneti validan datum rashoda.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    elif expediture_date > date.today().strftime('%Y-%m-%d'):
        flash('Odabrani datum rashoda je u budućnosti. Da bi ste rashodovali predmet, morate uneti validan datum rashoda.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    elif expediture_date < single_item.purchase_date.strftime('%Y-%m-%d'):
        flash('Odabrani datum rashoda je pre kupovine predmeta. Da bi ste rashodovali predmet, morate uneti datum rashoda koji je nakon kupovine predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    elif False:
        print('dodati uslov da je datum rashoda obavezan da bude u tekućoj godini // ispravi False u potrebni uslov')
    else:
        expediture_date = datetime.strptime(request.form.get('single_item_expediture_date_expediture'), '%Y-%m-%d').date()
    print(f'{single_item_id=} {expediture_date=}')
    print(f'rashodovao bih ovaj predmet: {single_item=}')
    initial_price = single_item.initial_price
    rate = single_item.single_item_item.item_depreciation_rate.rate
    purchase_date = single_item.purchase_date
    input_in_app_date = single_item.input_in_app_date 
    deprecation_value = single_item.deprecation_value
    
    single_item.current_price, single_item.expediture_price = current_price_calculation(initial_price, rate, purchase_date, expediture_date, None, input_in_app_date, deprecation_value)
    single_item.expediture_date = expediture_date
    single_item.room_id = 2 #! room_id = 2 je magacin rashoda
    db.session.commit()
    flash(f'Uspešno ste rashodovali predmet: {single_item.name}.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/undo_expediture_single_item', methods=['GET', 'POST'])
def undo_expediture_single_item():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće stornirati rashodovani predmet dok je aktivan popis.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    single_item_id = request.form.get('single_item_id_expediture_undo')
    single_item = SingleItem.query.filter_by(id=single_item_id).first()
    print(f'poništavam rashod za ovaj predmet: {single_item=}')
    single_item.expediture_date = None
    single_item.expediture_price = None
    single_item.room_id = 1 #! room_id = 1 je virtuelni magacin
    db.session.commit()
    flash(f'Predmet: {single_item.name} je storniran iz rashoda.', 'success')
    update_price()
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/add_single_items_to_app', methods=['GET', 'POST'])
def add_single_items_to_app():
    single_items_list = SingleItem.query.all()
    if len(single_items_list) == 0:
        max_serial_number = 1
    else:
        max_serial_number = max([int(single_item.inventory_number.split('-')[1]) for single_item in single_items_list])+1
    
    item_id = request.form.get('add_single_item_item_id')
    rate = Item.query.filter_by(id=item_id).first().item_depreciation_rate.rate
    item_name = request.form.get('add_single_item_name')
    # if not item_name or not item_name.strip():
    #     flash('Da bi ste dodali novi predmet, morate uneti naziv predmeta.', 'danger')
    #     return redirect(url_for('single_items.single_item_list'))
    item_room = request.form.get('add_single_item_room')
    if not item_room or not item_room.strip():
        item_room = 1 #! ako nije selektovana nijedna soba onda je room_id = 1 je virtuelni magacin
    quantity = request.form.get('add_single_item_quantity')
    # if not quantity or not quantity.strip():
    #     flash('Da bi ste dodali novi predmet, morate uneti količinu predmeta.', 'danger')
    #     return redirect(url_for('single_items.single_item_list'))
    # Pokušaj konvertovati quantity u cijeli broj
    try:
        quantity = int(quantity)
    except ValueError:
        # Ako nije moguće konvertovati u cijeli broj
        print(f'{type(quantity)=}')
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je quantity sada cijeli broj
    if not isinstance(quantity, int):
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    if int(quantity) < 1:
        flash('Količina predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    #! nastaviti (initial_price, quantity, purchase_date)
    initial_price = float(request.form.get('add_single_item_initial_price')) / float(quantity)
    if initial_price < 0:
        flash('Cena predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    purchase_date_str = request.form.get('add_single_item_date')
    
    input_in_app_date = request.form.get('input_in_app_date')
    deprecatin_value = float(request.form.get('deprecation_value')) / float(quantity)

    # Provjeri da li je purchase_date_str prazan ili sastoji se samo od praznina
    if not purchase_date_str or not purchase_date_str.strip():
        flash('Da bi ste dodali novi predmet, morate uneti datum kupovine predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Pokušaj parsirati purchase_date_str u datetime.date
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Neispravan format datuma. Molimo unesite datum u formatu YYYY-MM-DD.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je purchase_date u prošlosti
    if purchase_date > datetime.now().date():
        flash('Datum kupovine ne može biti u budućnosti.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    supplier = request.form.get('add_single_item_supplier')
    invoice_number = request.form.get('add_single_item_invoice_number')
    current_price, _ = current_price_calculation(initial_price, rate, purchase_date)
    print(f'{item_id=} {item_name=} {item_room=} {initial_price=} {purchase_date=} {quantity=} {input_in_app_date=} {deprecatin_value=}')
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
                                        inventory_number=inventory_number,
                                        supplier=supplier,
                                        invoice_number=invoice_number,
                                        input_in_app_date=input_in_app_date,
                                        deprecation_value=deprecatin_value)
        new_single_items.append(new_single_item)
    db.session.add_all(new_single_items)
    db.session.commit()
    return redirect(url_for('single_items.single_item_list'))

@single_items.route('/add_single_item', methods=['GET', 'POST'])
def add_single_item():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Da bi ste dodali novi predmet, morate prvo završiti aktivnu popisnu listu koja je započeta: {active_inventory_list.date}.', 'danger')
        return redirect(url_for('main.home'))
    single_items_list = SingleItem.query.all()
    if len(single_items_list) == 0:
        max_serial_number = 1
    else:
        max_serial_number = max([int(single_item.inventory_number.split('-')[1]) for single_item in single_items_list])+1
    item_id = request.form.get('add_single_item_item_id')
    rate = Item.query.filter_by(id=item_id).first().item_depreciation_rate.rate
    print(f'{rate=}')
    item_name = request.form.get('add_single_item_name')
    if not item_name or not item_name.strip():
        flash('Da bi ste dodali novi predmet, morate uneti naziv predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    item_room = request.form.get('add_single_item_room')
    if not item_room or not item_room.strip():
        item_room = 1 #! ako nije selektovana nijedna soba onda je room_id = 1 je virtuelni magacin
    quantity = request.form.get('add_single_item_quantity')
    if not quantity or not quantity.strip():
        flash('Da bi ste dodali novi predmet, morate uneti količinu predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    # Pokušaj konvertovati quantity u cijeli broj
    try:
        quantity = int(quantity)
    except ValueError:
        # Ako nije moguće konvertovati u cijeli broj
        print(f'{type(quantity)=}')
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je quantity sada cijeli broj
    if not isinstance(quantity, int):
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    if int(quantity) < 1:
        flash('Količina predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    #! nastaviti (initial_price, quantity, purchase_date)
    initial_price = float(request.form.get('add_single_item_initial_price')) / float(quantity)
    if initial_price < 0:
        flash('Cena predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    purchase_date_str = request.form.get('add_single_item_date')

    # Provjeri da li je purchase_date_str prazan ili sastoji se samo od praznina
    if not purchase_date_str or not purchase_date_str.strip():
        flash('Da bi ste dodali novi predmet, morate uneti datum kupovine predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Pokušaj parsirati purchase_date_str u datetime.date
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Neispravan format datuma. Molimo unesite datum u formatu YYYY-MM-DD.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je purchase_date u prošlosti
    if purchase_date > datetime.now().date():
        flash('Datum kupovine ne može biti u budućnosti.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    supplier = request.form.get('add_single_item_supplier')
    invoice_number = request.form.get('add_single_item_invoice_number')
    current_price, _ = current_price_calculation(initial_price, rate, purchase_date)
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
                                        inventory_number=inventory_number,
                                        supplier=supplier,
                                        invoice_number=invoice_number)
        new_single_items.append(new_single_item)
    db.session.add_all(new_single_items)
    db.session.commit()
    if quantity == 1:
        flash(f'Novi predmet je uspešno dodat.', 'success')
    else:
        flash(f'Uspešno je dodato {quantity} novih predmeta.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/edit_single_item', methods=['GET', 'POST'])
def edit_single_item():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće vršiti izmene podataka predmeta dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    inventory_years = [inventory.date for inventory in Inventory.query.all()]
    print(f'{inventory_years=}')
    
    correction = 0
    if date((date.today().year -1), 12, 31) not in inventory_years:
        print(f'NIJE urađen je popis na kraju prošle godine')
        correction = 1

    purchase_date = datetime.strptime(request.form.get('edit_single_item_date'), '%Y-%m-%d').date()
    if purchase_date.year + correction < date.today().year:
        flash('Ne može se menjati serija predmeta iz predhodnih godina.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    serial = int(request.form.get('edit_single_item_serial'))
    item_id = request.form.get('edit_single_item_item_id')
    name = request.form.get('edit_single_item_name')
    if not name or not name.strip():
        flash('Da bi ste izmenili predmet, morate uneti naziv predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    quantity = request.form.get('edit_single_item_quantity')
    if not quantity or not quantity.strip():
        flash('Da bi ste dodali novi predmet, morate uneti količinu predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    # Pokušaj konvertovati quantity u cijeli broj
    try:
        quantity = int(quantity)
    except ValueError:
        # Ako nije moguće konvertovati u cijeli broj
        print(f'{type(quantity)=}')
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je quantity sada cijeli broj
    if not isinstance(quantity, int):
        flash('Količina predmeta mora biti ceo broj.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    if int(quantity) < 1:
        flash('Količina predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    initial_price = float(request.form.get('edit_single_item_initial_price')) / float(quantity)
    if initial_price < 0:
        flash('Cena predmeta mora biti veća od 0.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    purchase_date_str = request.form.get('edit_single_item_date')

    # Provjeri da li je purchase_date_str prazan ili sastoji se samo od praznina
    if not purchase_date_str or not purchase_date_str.strip():
        flash('Da bi ste izmenili predmet, morate uneti datum kupovine predmeta.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Pokušaj parsirati purchase_date_str u datetime.date
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Neispravan format datuma. Molimo unesite datum u formatu YYYY-MM-DD.', 'danger')
        return redirect(url_for('single_items.single_item_list'))

    # Provjeri da li je purchase_date u prošlosti
    if purchase_date > datetime.now().date():
        flash('Datum kupovine ne može biti u budućnosti.', 'danger')
        return redirect(url_for('single_items.single_item_list'))
    current_price, _ = current_price_calculation(initial_price, Item.query.filter_by(id=item_id).first().item_depreciation_rate.rate, datetime.now().date())
    supplier = request.form.get('edit_single_item_supplier')
    invoice_number = request.form.get('edit_single_item_invoice_number')
    print(f'{serial=}, {initial_price=}')
    single_items = SingleItem.query.filter_by(serial=serial).all()
    print(f'{single_items=}')
    for single_item in single_items:
        inventory_number = single_item.inventory_number
        i = int(inventory_number.split('-')[2])
        single_item.item_id = item_id
        single_item.name = name
        single_item.initial_price = initial_price
        single_item.current_price = current_price
        single_item.purchase_date = purchase_date
        single_item.inventory_number = f'{int(item_id):04d}-{int(serial):05d}-{i:04d}'
        single_item.supplier = supplier
        single_item.invoice_number = invoice_number
    db.session.commit()
    for i in range(1, (len(single_items) - quantity + 1)):
        print(f'{quantity=}, {len(single_items)=}')
        db.session.delete(single_items[-i])
    if quantity > len(single_items):
        for i in range(len(single_items), quantity):
            i += 1 #! da bi bio veći za jedan od maximalnog broja len(single_items)
            inventory_number = f'{int(item_id):04d}-{serial}-{i:04d}'
            new_single_item = SingleItem(item_id=item_id,
                                            serial=serial,
                                            name=name,
                                            initial_price=initial_price,
                                            current_price=current_price,
                                            purchase_date=purchase_date,
                                            inventory_number=inventory_number,
                                            room_id=1, #! virtuelni magacin
                                            supplier=supplier,
                                            invoice_number=invoice_number)
            db.session.add(new_single_item)
    db.session.commit()
    update_price()
    flash(f'Uspešno ste izmenili predmete sa serijom: {str(serial).zfill(5)}.', 'success')
    return redirect(url_for('single_items.single_item_list'))


@single_items.route('/single_item_rooms/<int:item_id>', methods=['GET', 'POST'])
def single_item_rooms(item_id):
    item = Item.query.filter_by(id=item_id).first()
    inventory = Inventory.query.filter_by(status='active').first()
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
            if existing_item['building'] == new_dict['building'] and existing_item['room'] == new_dict['room'] and existing_item['serial'] == new_dict['serial']:
                existing_item['quantity'] += 1
                found = True
                break
        
        if not found:
            data_list.append(new_dict)
        
    print(f'{data_list=}')
    
    return render_template('single_item_rooms.html', title="Pregled predmeta po prostorijama",
                            single_item_list=single_item_list,
                            item=item,
                            inventory=inventory,
                            data_list=data_list)


@single_items.route('/room_single_items/<int:room_id>', methods=['GET', 'POST'])
def room_single_items(room_id):
    room = Room.query.filter_by(id=room_id).first()
    single_item_list = SingleItem.query.filter_by(room_id=room_id).all()
    active_inventory_list=Inventory.query.filter_by(status='active').first()
    print(f'{single_item_list=}')
    data_list = []
    for single_item in single_item_list:
        new_dict = {
            'id': single_item.single_item_item.id,
            'item_name': f'{single_item.single_item_item.name}',
            'single_item_name': single_item.name,
            'serial': single_item.inventory_number.split('-')[1],
            'quantity': 1,
            'initial_price': single_item.initial_price,
            'current_price': single_item.current_price,
            'purchase_date': single_item.purchase_date,
        }
        print(f'{new_dict=}')
        found = False
        for existing_item in data_list:
            if existing_item['serial'] == new_dict['serial']:
                existing_item['quantity'] += 1
                found = True
                break
        if not found:
            data_list.append(new_dict)
    print(f'{data_list=}')
    return render_template('room_single_items.html', title="Pregled predmeta u prostoriji",
                                room=room,
                                single_item_list=single_item_list,
                                data_list=data_list,
                                active_inventory_list=active_inventory_list)


@single_items.route('/move_select', methods=['GET', 'POST'])
def move_select_item():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće premeštati predmete dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        if 'submit_to' in request.form:
            item_id = request.form.get('item_id_to_move_to')
            room_id = request.form.get('room_id_to_move_to')
            return redirect(url_for('single_items.move_to', item_id=item_id, room_id=room_id))
        elif 'submit_from' in request.form:
            item_id = request.form.get('item_id_to_move_from')
            room_id = request.form.get('room_id_to_move_from')
            return redirect(url_for('single_items.move_from', serial=item_id, room_id=room_id))
    item_list = Item.query.all()
    from sqlalchemy import distinct

    single_item_list = SingleItem.query.all()
    unique_series = set()  # Set za praćenje jedinstvenih serija
    single_item_list_from = []

    for single_item in sorted(single_item_list, key=lambda x: x.item_id):
        if single_item.serial not in unique_series:
            unique_series.add(single_item.serial)
            single_item_list_from.append(single_item)

    print(f'{single_item_list_from=}')
    all_room_list = Room.query.all()
    room_list_to = [room for room in all_room_list if room.id not in [2, 3, 4]] #! 2 - magacin rashoda, 3 - magacin reversa, 4 magacin manjkova -> ne može se na ovaj način premestiti u taj magacin
    room_list_from = [room for room in all_room_list if room.id not in [2, 3, 4]] #! 2 - magacin rashoda, 3 - magacin reversa, 4 magacin manjkova -> ne može se na ovaj način premestiti u taj magacinv !!!! ne treba listati prostorije koje nemaju ovaj predmet za tip kretnje iz prostorije u druge prostorije
    print(f'{item_list=}')
    return render_template('move_select.html', title='Izbor predmeta za premeštanje',
                            item_list=item_list,
                            single_item_list_from=single_item_list_from,
                            room_list_to=room_list_to,
                            room_list_from=room_list_from)


# @single_items.route("/move_from/<int:item_id>/<int:room_id>", methods=['GET', 'POST'])
@single_items.route("/move_from/<int:serial>/<int:room_id>", methods=['GET', 'POST'])
# def move_from(item_id, room_id):
def move_from(serial, room_id):
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće premeštati predmete dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    single_item_ = SingleItem.query.filter_by(serial=serial).first() #!
    room_from = Room.query.filter_by(id=room_id).first()
    room_list = Room.query.all()
    single_item_in_room_list = SingleItem.query.filter_by(serial=serial, room_id=room_id).all()
    print(f'{single_item_in_room_list=}')
    data_list = [] #! svi predmeti izabranog tipa u svim prostorijama
    
    for room in room_list:
        if room.id not in [2, 3, 4]:
            single_item_list = SingleItem.query.filter_by(serial=serial, room_id=room.id).all()

            if not single_item_list:
                new_dict = {
                    'building': room.room_building.name,
                    'room_id': room.id,
                    'item_id': single_item_.item_id,
                    'room': f'({room.name}) {room.dynamic_name}',
                    'serial': '',
                    'quantity': 0,
                    'single_item_name': '',
                    'initial_price': 0,
                    'current_price': 0,
                    'purchase_date': '',
                }
                data_list.append(new_dict)
            else:
                for single_item in single_item_list:
                    new_dict = {
                        'building': single_item.single_item_room.room_building.name,
                        'room_id': room.id,
                        'item_id': single_item.item_id,
                        'room': f'({room.name}) {room.dynamic_name}',
                        'serial': single_item.inventory_number.split('-')[1],
                        'quantity': 1,
                        'single_item_name': f'{single_item.name}',
                        'initial_price': single_item.initial_price,
                        'current_price': single_item.current_price,
                        'purchase_date': single_item.purchase_date,
                    }
                    found = False
                    for existing_item in data_list:
                        if existing_item['serial'] == new_dict['serial'] and existing_item['room_id'] == new_dict['room_id'] and existing_item['building'] == new_dict['building']:
                            existing_item['quantity'] += 1
                            found = True
                            break
                    if not found:
                        data_list.append(new_dict)
    print(f'{data_list=}')


    
    quantity_of_single_items_in_room = 0
    for data in data_list:
        if data['room_id'] == room_id and data['serial'] == str(serial).zfill(5):
            quantity_of_single_items_in_room += data['quantity']
            print(f'{quantity_of_single_items_in_room=}')
    
    if request.method == 'POST':
        print(f'{request.form=}')
        get_move_list = json.loads(request.form['data_to_move_from'])
        move_list = [data for data in get_move_list if data['quantity_to_move_from'] != '']
        print(f'{move_list=}')
        if len(move_list) == 0:
            flash('Niste izabrali nijedan predmet za premeštanje.', 'danger')
            return redirect(url_for('single_items.move_from', serial=serial, room_id=room_id))
        
        if not db.session.is_active:
            db.session.begin()
        for data in move_list:
            room_id_to_move = int(data['room_id'])
            quantity_to_move = int(data['quantity_to_move_from'])
            print(f'{room_id=} {quantity_to_move=}')
            for i in range(quantity_to_move):
                if not single_item_in_room_list:
                    flash(f'Premešteni su svi predmeti iz izabrane prostorije, nema predmeta koji mogu da se premeste u prostoriju: {room_id_to_move}.', 'danger')
                    break #! Ako su svi predmeti iz te prostorije već premešteni, izađite iz petlje
                single_item_to_move_from = single_item_in_room_list[0]
                single_item_to_move_from.room_id = room_id_to_move
                single_item_in_room_list.remove(single_item_to_move_from)
        db.session.commit()
        # room_to_move = Room.query.get_or_404(room_id_to_move)
        flash(f'Premešteni su predmeti iz izabrane prostorije:  ({room_from.name}) {room_from.dynamic_name}.', 'success')
        return redirect(url_for('single_items.single_item_rooms', item_id=single_item_.item_id))
    
    return render_template('move_from.html', title='Premeštanje predmeta iz izabrane prostorije u više različitih prostorija',
                            item=single_item_,
                            room_from=room_from,
                            single_item_list=single_item_list,
                            data_list=data_list,
                            quantity_of_single_items_in_room=quantity_of_single_items_in_room)


@single_items.route("/move_to/<int:item_id>/<int:room_id>", methods=['GET', 'POST'])
def move_to(item_id, room_id):
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće premeštati predmete dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
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
        if len(move_list) == 0:
            flash('Niste izabrali nijedan predmet za premeštanje.', 'danger')
            return redirect(url_for('single_items.move_to', item_id=item_id, room_id=room_id))
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
        flash(f'Predmeti su premešteni u prostoriju: ({room.name}) {room.dynamic_name}.', 'success')
        return redirect(url_for('single_items.single_item_rooms', item_id=item_id))
    return render_template('move_to.html', title='Premeštanje predmeta u izabranu prostoriju',
                            item=item,
                            room=room,
                            single_item_list=single_item_list,
                            data_list=data_list)


@single_items.route('/update_price', methods=['GET', 'POST'])
def update_price():
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće preračunavanje vrednosti predmeta dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
    single_items = SingleItem.query.all()
    for single_item in single_items:
        if single_item.expediture_date is None:
            single_item.current_price, _ = current_price_calculation(single_item.initial_price, single_item.single_item_item.item_depreciation_rate.rate, single_item.purchase_date, None, None, single_item.input_in_app_date, single_item.deprecation_value)
            print(f'{single_item.inventory_number=}; {single_item.input_in_app_date=}: {single_item.current_price=}')
    flash('Cena na kraju tekuće godine kod svih nerashodovanih predmeta je izmenjena.', 'success')
    db.session.commit()
    return redirect(url_for('single_items.single_item_list'))