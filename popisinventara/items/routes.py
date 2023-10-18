from flask import Blueprint
from flask import render_template, redirect, url_for
from popisinventara import db
from popisinventara.models import Item, Category, DepreciationRate
from flask import url_for
from flask import request
from flask import flash




item = Blueprint('items', __name__)


@item.route('/items', methods=['GET'])
def items():
    items = Item.query.all()
    rates = DepreciationRate.query.all()
    categories = Category.query.all()
    return render_template('items.html', title="Tipovi predmeta",
                            items=items, 
                            rates=rates, 
                            categories=categories)


@item.route('/add_item', methods=['GET', 'POST'])
def add_item():
    name = request.form.get('add_item_name')
    category = request.form.get('add_item_category')
    depreciation_rate = request.form.get('add_item_rate')
    print(f'{name=} {category=} {depreciation_rate=}')
    new_item = Item(name=name, category_id=category, depreciation_rate_id=depreciation_rate)
    db.session.add(new_item)
    db.session.commit()
    flash(f'Dodat je predmet "{name}".', 'success')
    return redirect(url_for('items.items'))


@item.route('/edit_item', methods=['GET', 'POST'])
def edit_item():
    item_id = request.form.get('edit_item_id')
    name = request.form.get('edit_item_name')
    category = request.form.get('edit_item_category')
    depreciation_rate = request.form.get('edit_item_rate')
    print(f'{item_id=} {name=} {category=} {depreciation_rate=}')
    
    item = Item.query.get(item_id)
    item.name = name
    item.category_id = category
    item.depreciation_rate_id = depreciation_rate
    db.session.commit()
    flash(f'Uspesno ste izmenili predmet "{name}".', 'success')
    return redirect(url_for('items.items'))


@item.route('/category')
def category():
    categories = Category.query.all()
    return render_template('category.html', title="Konta", categories=categories)


@item.route('/add_category' , methods=['GET', 'POST'])
def add_category():
    category_number = request.form.get('add_category_number')
    category_name = request.form.get('add_category_name')
    print(f'{category_number=} {category_name=}')
    new_category = Category(category_number=category_number, name=category_name)
    db.session.add(new_category)
    db.session.commit()
    flash(f'Dodat je konto "{category_name}".', 'success')
    return redirect(url_for('items.category'))


@item.route('/edit_category', methods=['GET', 'POST'])
def edit_category():
    print('dodaj kod za editovanje kategorije')
    category_id = request.form.get('edit_category_id')
    category_number = request.form.get('edit_category_number')
    category_name = request.form.get('edit_category_name')
    print(f'{category_id=} {category_number=} {category_name=}')
    
    category = Category.query.get(category_id)
    category.category_number = category_number
    category.name = category_name
    db.session.commit()
    flash(f'Uspesno ste izmenili konto "{category_name}".', 'success')
    return redirect(url_for('items.category'))


@item.route('/depreciation_rates')
def depreciation_rates():
    depreciation_rates = DepreciationRate.query.all()
    return render_template('depreciation_rates.html', title="Stope amortizacije", depreciation_rates=depreciation_rates)

@item.route('/add_depreciation_rate', methods=['GET', 'POST'])
def add_depreciation_rate():
    name = request.form.get('add_depreciation_rate_name')
    rate = request.form.get('add_depreciation_rate_rate')
    print(f'{rate=} {name=}')
    new_depreciation_rate = DepreciationRate(name=name, rate=rate)
    db.session.add(new_depreciation_rate)
    db.session.commit()
    flash(f'Dodata je stopa amortizacije "{name}".', 'success')
    return redirect(url_for('items.depreciation_rates'))


@item.route('/edit_depreciation_rate', methods=['GET', 'POST'])
def edit_depreciation_rate():
    depreciation_rate_id = request.form.get('edit_depreciation_rate_id')
    name = request.form.get('edit_depreciation_rate_name')
    rate = request.form.get('edit_depreciation_rate_rate')
    print(f'{depreciation_rate_id=} {rate=} {name=}')
    
    depreciation_rate = DepreciationRate.query.get(depreciation_rate_id)
    depreciation_rate.name = name
    depreciation_rate.rate = rate
    db.session.commit()
    flash(f'Ažurirana je stopa amortizacije "{name}".', 'success')
    return redirect(url_for('items.depreciation_rates'))