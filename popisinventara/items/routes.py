from flask import Blueprint
from flask import render_template, redirect, url_for
from flask_login import current_user
from popisinventara import db
from popisinventara.models import Inventory, Item, Category, DepreciationRate
from flask import url_for
from flask import request
from flask import flash




item = Blueprint('items', __name__)


@item.route('/items', methods=['GET'])
def items():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati tipovima predmeta dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    items = Item.query.all()
    rates = DepreciationRate.query.all()
    categories = Category.query.all()
    return render_template('items.html', title="Tipovi predmeta",
                            items=items, 
                            rates=rates, 
                            categories=categories)


@item.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati tipovima predmeta dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    name = request.form.get('add_item_name')
    if not name or not name.strip():
        flash('Niste uneli validan naziv tipa predmeta.', 'danger')
        return redirect(url_for('items.items'))
    category = request.form.get('add_item_category')
    if not category or not category.strip():
        flash('Niste odabrali konto za tip predmeta.', 'danger')
        return redirect(url_for('items.items'))
    depreciation_rate = request.form.get('add_item_rate')
    if not depreciation_rate or not depreciation_rate.strip():
        flash('Niste odabrali procenat amortizacije za tip predmeta.', 'danger')
        return redirect(url_for('items.items'))
    print(f'{name=} {category=} {depreciation_rate=}')
    new_item = Item(name=name, category_id=category, depreciation_rate_id=depreciation_rate)
    db.session.add(new_item)
    db.session.commit()
    flash(f'Dodat je tip predmeta "{name}".', 'success')
    return redirect(url_for('items.items'))


@item.route('/edit_item', methods=['GET', 'POST'])
def edit_item():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati tipovima predmeta dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    item_id = request.form.get('edit_item_id')
    name = request.form.get('edit_item_name')
    if not name or not name.strip():
        flash('Niste uneli validan naziv tipa predmeta.', 'danger')
        return redirect(url_for('items.items'))
    category = request.form.get('edit_item_category')
    if not category or not category.strip():
        flash('Niste odabrali konto za tip predmeta.', 'danger')
        return redirect(url_for('items.items'))
    depreciation_rate = request.form.get('edit_item_rate')
    if not depreciation_rate or not depreciation_rate.strip():
        flash('Niste odabrali procenat amortizacije za tip predmeta.', 'danger')
        return redirect(url_for('items.items'))
    print(f'{item_id=} {name=} {category=} {depreciation_rate=}')
    
    item = Item.query.get(item_id)
    item.name = name
    item.category_id = category
    item.depreciation_rate_id = depreciation_rate
    db.session.commit()
    flash(f'Uspešno ste izmenili tip predmeta "{name}".', 'success')
    return redirect(url_for('items.items'))


@item.route('/category')
def category():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati kontima dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    categories = Category.query.all()
    return render_template('category.html', title="Konta", categories=categories)


def category_validation(category_number, category_name):
    if not category_number or not category_number.strip():
        flash('Niste uneli validan broj konta.', 'danger')
        return False
    elif len(category_number) != 6:
        flash('Broj konta mora da ima 6 cifara.', 'danger')
        return False
    elif not category_number.isdigit():
        flash('Broj konta mora da sadrzi samo cifre.', 'danger')
        return False
    if not category_name or not category_name.strip():
        flash('Niste uneli validan opis konta.', 'danger')
        return False
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati kontima dok je aktivan popis.', 'danger')
        return False
    return True
    


@item.route('/add_category' , methods=['GET', 'POST'])
def add_category():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    category_number = request.form.get('add_category_number')
    category_name = request.form.get('add_category_name')
    if category_validation(category_number, category_name) == False:
        return redirect(url_for('items.category'))
    print(f'{category_number=} {category_name=}')
    new_category = Category(category_number=category_number, name=category_name)
    db.session.add(new_category)
    db.session.commit()
    flash(f'Dodat je konto "{category_name}".', 'success')
    return redirect(url_for('items.category'))


@item.route('/edit_category', methods=['GET', 'POST'])
def edit_category():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    print('dodaj kod za editovanje kategorije')
    category_id = request.form.get('edit_category_id')
    category_number = request.form.get('edit_category_number')
    category_name = request.form.get('edit_category_name')
    if category_validation(category_number, category_name) == False:
        return redirect(url_for('items.category'))
    print(f'{category_id=} {category_number=} {category_name=}')
    
    category = Category.query.get(category_id)
    category.category_number = category_number
    category.name = category_name
    db.session.commit()
    flash(f'Uspešno ste izmenili konto "{category_name}".', 'success')
    return redirect(url_for('items.category'))


@item.route('/depreciation_rates')
def depreciation_rates():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati stopama amortizacije dok je aktivan popis.', 'danger')
        return redirect(url_for('main.home'))
    depreciation_rates = DepreciationRate.query.all()
    return render_template('depreciation_rates.html', title="Stope amortizacije", depreciation_rates=depreciation_rates)


def depreciation_rate_validation(name, rate):
    if not name or not name.strip():
        flash('Niste uneli validan naziv stope amortizacije.', 'danger')
        return False
    if not rate or not rate.strip():
        flash('Niste uneli validan procenat stope amortizacije.', 'danger')
        return False
    try:
        float_rate = float(rate)
    except ValueError:
        flash('Procenat stope amortizacije mora sadržati samo cifre.', 'danger')
        return False
    if not (0 <= float(rate) <= 100):
        flash('Procenat stope amortizacije mora biti u rasponu od 0 do 100 procenata.', 'danger')
        return False
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    if active_inventory_list:
        flash(f'Nije moguće upravljati stopama amortizacije dok je aktivan popis.', 'danger')
        return False
    return True
    
@item.route('/add_depreciation_rate', methods=['GET', 'POST'])
def add_depreciation_rate():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    name = request.form.get('add_depreciation_rate_name')
    rate = request.form.get('add_depreciation_rate_rate')
    if depreciation_rate_validation(name, rate) == False:
        return redirect(url_for('items.depreciation_rates'))    
    print(f'{rate=} {name=}')
    new_depreciation_rate = DepreciationRate(name=name, rate=rate)
    db.session.add(new_depreciation_rate)
    db.session.commit()
    flash(f'Dodata je stopa amortizacije: "{name}".', 'success')
    return redirect(url_for('items.depreciation_rates'))


@item.route('/edit_depreciation_rate', methods=['GET', 'POST'])
def edit_depreciation_rate():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    if current_user.authorization != 'admin':
        flash('Nemate dozvolu za pristup ovoj stranici.', 'danger')
        return redirect(url_for('main.home'))
    depreciation_rate_id = request.form.get('edit_depreciation_rate_id')
    name = request.form.get('edit_depreciation_rate_name')
    rate = request.form.get('edit_depreciation_rate_rate')
    if depreciation_rate_validation(name, rate) == False:
        return redirect(url_for('items.depreciation_rates'))
    print(f'{depreciation_rate_id=} {rate=} {name=}')
    
    depreciation_rate = DepreciationRate.query.get_or_404(depreciation_rate_id)
    depreciation_rate.name = name
    depreciation_rate.rate = rate
    db.session.commit()
    flash(f'Ažurirana je stopa amortizacije "{name}".', 'success')
    return redirect(url_for('items.depreciation_rates'))