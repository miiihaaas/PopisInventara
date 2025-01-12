from flask import Blueprint, request
from flask import  render_template, flash, redirect, url_for, jsonify
from flask_login import current_user
from popisinventara import db
from popisinventara.models import Inventory, SingleItem, Building, Room
from datetime import datetime

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    route_name = request.endpoint
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    virtual_warehouse = SingleItem.query.filter_by(room_id=1).count()
    print(f'{virtual_warehouse=}')
    # weather_data = get_weather_forecast("Gornji Milanovac", "Srbija")
    # print(f'{weather_data=}')
    return render_template('home.html', title='Početna strana',
                            route_name=route_name,
                            active_inventory_list=active_inventory_list,
                            virtual_warehouse=virtual_warehouse)


@main.route("/about")
def about():
    route_name = request.endpoint
    return render_template('about.html', 
                            route_name=route_name,
                            title='About')


#! ove rute su za import podataka iz excela i koriste se na serveru


@main.route("/check_buildings_count", methods=['GET'])
def check_buildings_count():
    try:
        buildings_count = Building.query.count()
        return jsonify({'count': buildings_count})
    except Exception as e:
        print(f"Greška pri brojanju zgrada: {str(e)}")  # Za lakši debug na serveru
        return jsonify({'error': str(e)}), 500


@main.route("/import_building", methods=['POST'])
def import_building():
    try:
        # Dobavljanje podataka iz forme
        school_id = int(request.form.get('school_id'))
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        
        # Provera da li su svi potrebni podaci prisutni
        if not all([school_id, name, address, city]):
            return jsonify({'error': 'Nedostaju obavezni podaci'}), 400
            
        # Kreiranje nove zgrade
        new_building = Building(
            school_id=school_id,
            name=name,
            address=address,
            city=city
        )
        
        # Dodavanje u bazu
        db.session.add(new_building)
        db.session.commit()
        
        return jsonify({'message': f'Uspešno dodata zgrada: {name}'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@main.route("/check_rooms_count", methods=['GET'])
def check_rooms_count():
    rooms_count = Room.query.count()
    return jsonify(count=rooms_count)


@main.route("/import_room", methods=['POST'])
def import_room():
    try:
        # Dobavljanje podataka iz forme
        id = int(request.form.get('id'))
        building_id = int(request.form.get('building_id'))
        name = request.form.get('name')
        dynamic_name = request.form.get('dynamic_name')
        
        # Provera da li su svi potrebni podaci prisutni
        if not all([id, building_id, name, dynamic_name]):
            return jsonify({'error': 'Nedostaju obavezni podaci'}), 400
            
        # Kreiranje nove serije
        new_room = Room(
            id=id,
            building_id=building_id,
            name=name,
            dynamic_name=dynamic_name
        )
        
        # Dodavanje u bazu
        db.session.add(new_room)
        db.session.commit()
        
        return jsonify({'message': f'Uspešno dodata soba: {name}'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@main.route("/check_items_count", methods=['GET'])
def check_items_count():
    items_count = SingleItem.query.count()
    return jsonify(count=items_count)


@main.route("/import_item", methods=['POST'])
def import_item():
    try:
        # Dobavljanje podataka iz forme
        serial = int(request.form.get('serial'))
        room_id = int(request.form.get('room_id'))
        name = request.form.get('name')
        quantity = int(request.form.get('quantity'))
        purchase_date = request.form.get('purchase_date')
        initial_price = float(request.form.get('initial_price'))
        input_in_app_date = request.form.get('input_in_app_date')
        deprecation_value = float(request.form.get('deprecation_value'))
        supplier = request.form.get('supplier', '')
        invoice_number = request.form.get('invoice_number', '')
        category_id = int(request.form.get('category_id'))
        depreciation_rate_id = int(request.form.get('depreciation_rate_id'))
        
        # Provera da li su svi potrebni podaci prisutni
        required_fields = {
            'serial': serial,
            'room_id': room_id,
            'name': name,
            'quantity': quantity,
            'purchase_date': purchase_date,
            'initial_price': initial_price,
            'deprecation_value': deprecation_value,
            # 'supplier': supplier,
            # 'invoice_number': invoice_number,
            'category_id': category_id,
            'depreciation_rate_id': depreciation_rate_id
        }
        # Debug ispis vrednosti
        print("\nDebug - vrednosti pre provere:")
        print(f"serial: {serial} ({type(serial)})")
        print(f"room_id: {room_id} ({type(room_id)})")
        print(f"name: {name} ({type(name)})")
        print(f"quantity: {quantity} ({type(quantity)})")
        print(f"purchase_date: {purchase_date} ({type(purchase_date)})")
        print(f"initial_price: {initial_price} ({type(initial_price)})")
        print(f"category_id: {category_id} ({type(category_id)})")
        print(f"depreciation_rate_id: {depreciation_rate_id} ({type(depreciation_rate_id)})")
        print("-" * 50)
        # Provera da li su svi potrebni podaci prisutni
        required_fields = {
            'serial': bool(serial),
            'room_id': bool(room_id),
            'name': bool(name and name.strip()),
            'quantity': bool(quantity),
            'purchase_date': bool(purchase_date),
            'initial_price': initial_price is not None,
            'category_id': bool(category_id),
            'depreciation_rate_id': bool(depreciation_rate_id)
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            return jsonify({'error': f'Nedostaju obavezni podaci: {", ".join(missing_fields)}'}), 400
            
        # Kreiranje nove serije predmeta
        items_created = 0
        for i in range(quantity):
            inventory_number = f'{serial:05d}-{i+1:04d}'
            new_item = SingleItem(
                serial=serial,
                inventory_number=inventory_number,
                name=name,
                supplier=supplier,
                invoice_number=invoice_number,
                initial_price=initial_price,
                current_price=deprecation_value, #! zato što je vrednost na kaju godine ona vrednost koju je škola dala
                input_in_app_date=datetime.strptime(input_in_app_date, '%Y-%m-%d').date(),
                deprecation_value=deprecation_value,
                purchase_date=datetime.strptime(purchase_date, '%Y-%m-%d').date(),
                room_id=room_id,
                category_id=category_id,
                depreciation_rate_id=depreciation_rate_id
            )
            if new_item.serial in [item.serial for item in SingleItem.query.all()]:
                return jsonify({'message': f'Predmet sa serijom {serial} vec postoji u bazi i nije dodat'}), 202
            db.session.add(new_item)
            items_created += 1
        
        db.session.commit()
        return jsonify({'message': f'Uspešno dodato {items_created} predmeta za seriju {serial}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500