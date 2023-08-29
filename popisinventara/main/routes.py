from flask import Blueprint
from flask import  render_template, flash, redirect, url_for
from flask_login import current_user
from popisinventara.models import Inventory, SingleItem

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    if not current_user.is_authenticated:
        flash('Da biste pristupili ovoj stranici treba da budete ulogovani.', 'danger')
        return redirect(url_for('users.login'))
    active_inventory_list = Inventory.query.filter_by(status='active').first()
    virtual_warehouse = SingleItem.query.filter_by(room_id=1).count()
    print(f'{virtual_warehouse=}')
    return render_template('home.html', title='Početna strana',
                            active_inventory_list=active_inventory_list,
                            virtual_warehouse=virtual_warehouse)


@main.route("/about")
def about():
    return render_template('about.html', title='About')

