from flask import Blueprint
from flask_login import current_user
from popisinventara.models import School, Room, Building
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
    school = School.query.get_or_404(school_id)
    buildings = Building.query.filter_by(school_id=school_id).all()
    rooms = Room.query.all()
    print(f'{rooms=}')
    form = EditSchoolForm()
    building_form = AddNewBuildingForm()
    room_form = AddNewRoomForm()
    room_form.building_id.choices = [(building.id, building.name) for building in buildings]
    if form.validate_on_submit():
        school.schoolname = form.schoolname.data
        school.address = form.address.data
        school.zip_code = form.zip_code.data
        school.city = form.city.data
        school.municipality = form.municipality.data
        school.country = form.country.data
        school.mb = form.mb.data
        school.jbkjs = form.jbkjs.data
        db.session.commit()
        flash('Uspesno ste izmenili podatke škole.', 'success')
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
                            form=form)


@schools.route('/add_building', methods=['POST'])
def add_building():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
    print('dodavanje nove zgrade. nastavi kod')
    building = Building(school_id=1, 
                        name=request.form.get('name'),
                        address = request.form.get('address'))
    db.session.add(building)
    db.session.commit()
    flash('Nova zgrada je uspešno dodata.', 'success')
    return redirect(url_for('schools.school', school_id=1))


@schools.route('/edit_building', methods=['GET', 'POST'])
def edit_building():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
    building_id = request.form.get('edit_building_id')
    building_name = request.form.get('edit_building_name')
    building_address = request.form.get('edit_building_address')
        
    building = Building.query.get_or_404(building_id)
    building.name = building_name
    building.address = building_address
    db.session.commit()
    return redirect(url_for('schools.school', school_id=1))


@schools.route('/add_room', methods=['POST'])
def add_room():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
    print('dodavanje nove Prostorije. nastavi kod')
    room = Room(name=request.form.get('name'),
                dynamic_name=request.form.get('dynamic_name'),
                building_id=request.form.get('building_id'))
    db.session.add(room)
    db.session.commit()
    flash('Nova prostorija je uspešno dodata.', 'success')
    return redirect(url_for('schools.school', school_id=1))

@schools.route('/edit_room', methods=['GET', 'POST'])
def edit_room():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristum ovoj stranici.', 'danger')
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
    return redirect(url_for('schools.school', school_id=1))

@schools.route('/rooms', methods=['GET', 'POST'])
def rooms():
    rooms = Room.query.all()
    pass