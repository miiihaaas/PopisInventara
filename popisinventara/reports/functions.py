
from decimal import Decimal
from datetime import date


def write_off_until_current_year(single_item, year=None):
    ''' funkcija otpis do tekuće godine '''
    if not year:
        current_year = date.today().year
    else:
        current_year = int(year)
    purchase_date = single_item.purchase_date
    input_in_app_date = single_item.input_in_app_date
    initial_price = Decimal(str(single_item.initial_price))
    current_price = Decimal(str(single_item.current_price))
    rate = Decimal(str(single_item.single_item_item.item_depreciation_rate.rate))
    
    # koliko je meseci ostalo u godini u kojoj je kupljen predmet
    first_year_months_remaining = 12 - purchase_date.month + 1
    
    # postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = initial_price * Decimal(first_year_months_remaining) / Decimal(12) * rate / Decimal(100)
    depreciation_per_year = initial_price * rate / Decimal(100)
    
    if input_in_app_date:
        first_year_depreciation = single_item.deprecation_value
        item_age_in_years = current_year - input_in_app_date.year
    else:
        item_age_in_years = current_year - purchase_date.year
    
    write_off = first_year_depreciation + depreciation_per_year * Decimal(item_age_in_years - 1)
    price_at_end_of_year = initial_price - (first_year_depreciation + depreciation_per_year * Decimal(item_age_in_years))
    
    if write_off > initial_price:
        write_off = initial_price
    elif write_off < 0:
        write_off = Decimal(0)
        
    if current_year == purchase_date.year:
        depreciation_per_year = first_year_depreciation
    elif depreciation_per_year > current_price:
        depreciation_per_year = current_price
    
    if price_at_end_of_year < 0:
        price_at_end_of_year = Decimal(0)
        
    return write_off, price_at_end_of_year, depreciation_per_year