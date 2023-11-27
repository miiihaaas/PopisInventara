from datetime import datetime
import json
from flask import Blueprint
from popisinventara.models import Inventory, Room, SingleItem
from popisinventara.reports.functions import write_off_until_current_year
from flask import render_template


reports = Blueprint('reports', __name__)


@reports.route('/category_reports')
def category_reports():
    single_items = SingleItem.query.all()
    
    data = []
    category_list = []
    for single_item in single_items:
        category = single_item.single_item_item.item_category.category_number
        write_off_til_current_year, price_at_end_of_year, depreciation_per_year = write_off_until_current_year(single_item)
        # print(f'inputi: {single_item.current_price=} - {depreciation_per_year=}')
        # print(f'cena na kraju godine: {price_at_end_of_year=}')
        if category not in category_list:
            category_list.append(category)
            new_record = {
                'category': category,
                'initial_price': single_item.initial_price,
                'current_price': single_item.current_price,
                'write_off_until_current_year': write_off_til_current_year,
                'depreciation_per_year': depreciation_per_year,
                'price_at_end_of_year': price_at_end_of_year if price_at_end_of_year > 0 else 0
            }
            data.append(new_record)
        else:
            for record in data:
                if record['category'] == category:
                    record['initial_price'] += single_item.initial_price
                    record['current_price'] += single_item.current_price
                    record['write_off_until_current_year'] += write_off_til_current_year
                    record['depreciation_per_year'] += depreciation_per_year
                    record['price_at_end_of_year'] += price_at_end_of_year if price_at_end_of_year > 0 else 0
                    break
    print(f'{category_list=}')
    print(f'{data=}')
    return render_template('category_reports.html', 
                            data=data, title='Izveštaj po kontima',
                            legend='Izveštaj po kontima')


@reports.route('/category_reports_past/<int:inventory_id>', methods=['GET', 'POST'])
def category_reports_past(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)
    single_items = json.loads(inventory.working_data)['single_items']
    print(f'{type(single_items)=}')
    data = []
    category_list = []
    for single_item in single_items:
        category = single_item['category']
        single_item_instance = SingleItem.query.get(single_item['item_id'])
        # print(f'{category=}')
        if category not in category_list:
            category_list.append(category)
            new_record = {
                'category': category,
                'initial_price': single_item['initial_price'],
                'current_price': single_item['current_price'],
                'write_off_until_current_year': single_item['write_off_until_current_year'],
                'depreciation_per_year': single_item['depreciation_per_year'],
                'price_at_end_of_year': single_item['price_at_end_of_year']
            }
            data.append(new_record)
        else:
            for record in data:
                if record['category'] == category:
                    record['initial_price'] += single_item['initial_price']
                    record['current_price'] += single_item['current_price']
                    record['write_off_until_current_year'] += single_item['write_off_until_current_year']
                    record['depreciation_per_year'] += single_item['depreciation_per_year']
                    record['price_at_end_of_year'] += single_item['price_at_end_of_year']
                    break
    print(f'{category_list=}')
    print(f'{data=}')
    # return f'single_items: {single_items}'
    return render_template('category_reports.html', 
                            data=data,
                            title=f'Izveštaj po kontima',
                            legend=f'Izveštaj po kontima - popis {inventory.date}')


@reports.route('/category_reports_expediture/<int:inventory_id>') #! izveštaj o rashodu // rekapitulacija po kontu - rashod
def category_reports_expediture(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)
    single_items = json.loads(inventory.working_data)['single_items']
    # print(f'{single_items=}')
    data = []
    category_list = []
    for single_item in single_items:
        if single_item['expediture_date']:
            print(f'{single_item["expediture_date"]=}')
            category = single_item['category']
            # print(f'{category=}')
            if category not in category_list:
                category_list.append(category)
                new_record = {
                    'category': category,
                    'initial_price': single_item['initial_price'],
                    'write_off_until_current_year': single_item['write_off_until_current_year'],
                    'depreciation_per_year': single_item['depreciation_per_year'],
                    'price_at_end_of_year': single_item['price_at_end_of_year'],
                    'current_price': single_item['current_price'],
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category:
                        record['initial_price'] += single_item['initial_price']
                        record['current_price'] += single_item['current_price']
                        record['write_off_until_current_year'] += single_item['write_off_until_current_year']
                        record['depreciation_per_year'] += single_item['depreciation_per_year']
                        record['price_at_end_of_year'] += single_item['price_at_end_of_year']
                        break
    print(f'{category_list=}')
    print(f'{data=}')
    return render_template('category_reports_expediture.html',
                            data=data,
                            title=f'Rekapitulacija po kontu - rashod: popis {inventory.date}',
                            legend=f'Rekapitulacija po kontu - rashod')


@reports.route('/category_reports_expediture_item/<int:inventory_id>') #! Izveštaj o rashodu (po kontima i predmetima) // Rashod za xxxx godinu
def category_reports_expediture_item(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)
    single_items = json.loads(inventory.working_data)['single_items']
    data = []
    category_item_list = []
    for single_item in single_items:
        if single_item['expediture_date']: #! verovatno treba dodati rashod samo za godinu u kojoj je rađen popis ( and expediture_date.year == inventory.date.year ) // trenutno lista sve predmete koji su rashodovani do popisa
            category = single_item['category']
            item = single_item["item_id"]
            if (category, item) not in category_item_list:
                category_item_list.append((category, item))
                new_record = {
                    'category': category,
                    'item': single_item['name'],
                    'quantity': 1,
                    'initial_price': single_item['initial_price'],
                    'write_off_until_current_year': single_item['write_off_until_current_year'],
                    'depreciation_per_year': single_item['depreciation_per_year'],
                    'price_at_end_of_year': single_item['price_at_end_of_year'],
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category and record['item'] == item:
                        record['quantity'] += 1
                        record['initial_price'] += single_item['initial_price']
                        record['write_off_until_current_year'] += single_item['write_off_until_current_year']
                        record['depreciation_per_year'] += single_item['depreciation_per_year']
                        record['price_at_end_of_year'] += single_item['price_at_end_of_year']
                        break
    return render_template('category_reports_item.html',
                            data=data,
                            inventory_id=inventory_id,
                            title=f'Rashod',
                            legend=f'Rashod: popis {inventory.date}')


@reports.route('/category_reports_new_purchases_past/<int:inventory_id>') #! izveštaji o novim nabavkama (po kontima zbirno) // rekapitulacija po kontima - nove nabavke 
def category_reports_new_purchases_past(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)
    single_items = json.loads(inventory.working_data)['single_items']
    # print(f'{single_items=}')
    data = []
    category_list = []
    inventory_year = inventory.date.year
    for single_item in single_items:
        if datetime.strptime(single_item['purchase_date'], '%Y-%m-%d').year == inventory_year:
            print(f'{single_item["purchase_date"]=} je siti kao {inventory_year}')
            category = single_item['category']
            # print(f'{category=}')
            if category not in category_list:
                category_list.append(category)
                new_record = {
                    'category': category,
                    'initial_price': single_item['initial_price'],
                    'write_off_until_current_year': single_item['write_off_until_current_year'],
                    'depreciation_per_year': single_item['depreciation_per_year'],
                    'price_at_end_of_year': single_item['price_at_end_of_year'],
                    'current_price': single_item['current_price'],
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category:
                        record['initial_price'] += single_item['initial_price']
                        record['current_price'] += single_item['current_price']
                        record['write_off_until_current_year'] += single_item['write_off_until_current_year']
                        record['depreciation_per_year'] += single_item['depreciation_per_year']
                        record['price_at_end_of_year'] += single_item['price_at_end_of_year']
                        break
    print(f'{category_list=}')
    print(f'{data=}')
    return render_template('category_reports_new_purchases.html',
                            data=data,
                            inventory_id=inventory_id,
                            title=f'Rekapitulacija po kontima - nove nabavke',
                            legend=f'Rekapitulacija po kontima - nove nabavke: popis {inventory.date}')


@reports.route('/category_reports_new_purchases_item/<int:inventory_id>') #! izveštaji o novim nabavkama (po kontima i predmetima) // nambavka u toku xxxx godine
def category_reports_new_purchases_item(inventory_id):
    inventory = Inventory.query.get_or_404(inventory_id)
    single_items = json.loads(inventory.working_data)['single_items']
    data = []
    category_item_list = []
    inventory_year = inventory.date.year
    for single_item in single_items:
        if datetime.strptime(single_item['purchase_date'], '%Y-%m-%d').year == inventory_year:
            category = single_item['category']
            item_id = single_item["item_id"]
            if (category, item_id) not in category_item_list:
                category_item_list.append((category, item_id))
                new_record = {
                    'category': category,
                    'item_id': item_id,
                    'item': single_item['name'],
                    'quantity': 1,
                    'initial_price': single_item['initial_price'],
                    'write_off_until_current_year': single_item['write_off_until_current_year'],
                    'depreciation_per_year': single_item['depreciation_per_year'],
                    'price_at_end_of_year': single_item['price_at_end_of_year'],
                }
                data.append(new_record)
            else:
                for record in data:
                    if record['category'] == category and record['item_id'] == item_id:
                        record['quantity'] += 1
                        record['initial_price'] += single_item['initial_price']
                        record['write_off_until_current_year'] += single_item['write_off_until_current_year']
                        record['depreciation_per_year'] += single_item['depreciation_per_year']
                        record['price_at_end_of_year'] += single_item['price_at_end_of_year']
                        break
    print(f'{category_item_list=}')
    print(f'{data=}')
    return render_template('category_reports_item.html',
                            data=data,
                            inventory_id=inventory_id,
                            title=f'Rekapitulacija po kontima - nove nabavke po predmetima',
                            legend=f'Rekapitulacija po kontima - nove nabavke po predmetima: popis {inventory.date}')