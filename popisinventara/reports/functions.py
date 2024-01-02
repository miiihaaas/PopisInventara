
from datetime import date


def write_off_until_current_year(single_item, year=None):
    ''' funkcija otpis do tekuće godine '''
    if not year:
        current_year = date.today().year
    else:
        current_year = int(year)
    purchase_date = single_item.purchase_date
    initial_price = single_item.initial_price
    current_price = single_item.current_price
    rate = single_item.single_item_item.item_depreciation_rate.rate
    
    
    #! koliko je meseci ostalo u godini u kojoj je kupljen predmet
    months_remaining = 12 - purchase_date.month + 1
    
    
    #! postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = float(initial_price) * (months_remaining / 12) * rate / 100
    depreciation_per_year = float(initial_price) * rate / 100
    
    write_off = first_year_depreciation + depreciation_per_year * (current_year - purchase_date.year - 1)
    price_at_end_of_year = initial_price - (first_year_depreciation + depreciation_per_year * (current_year - purchase_date.year))
    if write_off > initial_price:
        write_off = initial_price
    elif write_off < 0:
        write_off = 0
    # print(f'{depreciation_per_year=}')
    if current_year == purchase_date.year:
        depreciation_per_year = first_year_depreciation
    elif depreciation_per_year > current_price:
        depreciation_per_year = current_price
    if price_at_end_of_year < 0:
        price_at_end_of_year = 0
    return write_off, price_at_end_of_year, depreciation_per_year