from flask import Blueprint
from flask_login import current_user
from popisinventara.models import School, Room, Building, Inventory
from popisinventara.schools.forms import EditSchoolForm, AddNewBuildingForm, AddNewRoomForm
from flask import url_for, redirect
from flask import render_template
from flask import request
from popisinventara import db
from flask import flash


schools = Blueprint('schools', __name__)


@schools.route('/school/<int:school_id>' , methods=['GET', 'POST'])
def school(school_id):
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    school = School.query.get_or_404(school_id)
    buildings = Building.query.filter_by(school_id=school_id).all()
    rooms = Room.query.all()
    print(f'{rooms=}')
    form = EditSchoolForm()
    building_form = AddNewBuildingForm()
    room_form = AddNewRoomForm()
    room_form.building_id.choices = [(building.id, building.name) for building in buildings]
    if form.validate_on_submit():
        if active_inventory_list:
            flash(f'Nije moguće menjati podatke škole dok je aktivan popis.', 'danger')
            return redirect(url_for('main.home'))
        school.schoolname = form.schoolname.data
        school.address = form.address.data
        school.zip_code = form.zip_code.data
        school.city = form.city.data
        school.municipality = form.municipality.data
        school.country = form.country.data
        school.mb = form.mb.data
        school.jbkjs = form.jbkjs.data
        db.session.commit()
        flash('Uspešno ste izmenili podatke škole.', 'success')
        return redirect(url_for('schools.school', school_id=school_id))
    elif request.method == 'GET':
        form.schoolname.data = school.schoolname
        form.address.data = school.address
        form.zip_code.data = school.zip_code
        form.city.data = school.city
        form.municipality.data = school.municipality
        form.country.data = school.country
        form.mb.data = school.mb
        form.jbkjs.data = school.jbkjs
    return render_template('school.html', 
                            school=school, 
                            buildings=buildings,
                            rooms=rooms,
                            building_form=building_form,
                            room_form=room_form,
                            form=form,
                            active_inventory_list=active_inventory_list)


@schools.route('/edit_settings', methods=['GET', 'POST'])
def edit_settings():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    school = School.query.get_or_404(1)
    settings_show_quantity = request.form.get('show_quantity')
    print(f'{settings_show_quantity=}')
    if settings_show_quantity == 'on':
        school.settings_show_quantity = True
    else:
        school.settings_show_quantity = False
    print(f'{school.settings_show_quantity=}')
    db.session.commit()
    flash('Uspešno ste izmenili podešavanja aplikacije.', 'success')
    return redirect(url_for('schools.school', school_id=1))


@schools.route('/buildings_rooms', methods=['GET', 'POST'])
def buildings_rooms():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    school = School.query.get_or_404(1)
    buildings = Building.query.filter_by(school_id=1).all()
    rooms = Room.query.all()
    print(f'{rooms=}')
    building_form = AddNewBuildingForm()
    room_form = AddNewRoomForm()
    room_form.building_id.choices = [(building.id, building.name) for building in buildings]
    return render_template('buildings_rooms.html',
                            title='Zgrade i prostorije',
                            legend='Zgrade i prostorije',
                            building_form=building_form,
                            room_form=room_form,
                            buildings=buildings,
                            rooms=rooms,
                            school=school,
                            active_inventory_list=active_inventory_list)


@schools.route('/add_building', methods=['POST'])
def add_building():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće dodavati nove zgrade dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    print('dodavanje nove zgrade. nastavi kod')
    building = Building(school_id=1, 
                        name=request.form.get('name'),
                        address = request.form.get('address'),
                        city=request.form.get('city'))
    db.session.add(building)
    db.session.commit()
    flash('Nova zgrada je uspešno dodata.', 'success')
    return redirect(url_for('schools.buildings_rooms', school_id=1))


@schools.route('/edit_building', methods=['GET', 'POST'])
def edit_building():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće vršiti izmene podataka zgrade dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    building_id = request.form.get('edit_building_id')
    building_name = request.form.get('edit_building_name')
    building_address = request.form.get('edit_building_address')
    building_city = request.form.get('edit_building_city')
        
    building = Building.query.get_or_404(building_id)
    building.name = building_name
    building.address = building_address
    building.city = building_city
    db.session.commit()
    return redirect(url_for('schools.buildings_rooms', school_id=1))


@schools.route('/add_room', methods=['POST'])
def add_room():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće dodavati nove prostrije dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    print('dodavanje nove Prostorije. nastavi kod')
    room = Room(name=request.form.get('name'),
                dynamic_name=request.form.get('dynamic_name'),
                building_id=request.form.get('building_id'))
    db.session.add(room)
    db.session.commit()
    flash('Nova prostorija je uspešno dodata.', 'success')
    return redirect(url_for('schools.buildings_rooms', school_id=1))

@schools.route('/edit_room', methods=['GET', 'POST'])
def edit_room():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće vršiti izmene podataka prostorije dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    room_id = request.form.get('edit_room_id')
    room_name = request.form.get('edit_room_name')
    room_dynamic_name = request.form.get('edit_room_dynamic_name')
    room_building_id = request.form.get('edit_room_building_id')
    print(f'{room_id=} {room_name=} {room_dynamic_name=} {room_building_id=}')
    room = Room.query.get_or_404(room_id)
    room.name = room_name
    room.dynamic_name = room_dynamic_name
    room.building_id = room_building_id
    db.session.commit()
    return redirect(url_for('schools.buildings_rooms', school_id=1))