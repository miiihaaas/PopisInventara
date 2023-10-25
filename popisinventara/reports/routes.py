from flask import Blueprint
from popisinventara.models import SingleItem
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