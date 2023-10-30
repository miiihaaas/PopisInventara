from datetime import datetime, date
from popisinventara.models import SingleItem
from popisinventara import db


def current_price_calculation(initial_price, rate, purchase_date, expediture_date=None):
    if expediture_date:
        print(f'{expediture_date=}')
        today = expediture_date
    else:
        today = date.today()
    #! koliko je meseci ostalo u godini u kojoj je kupljen predmet
    first_year_months_remaining = 12 - purchase_date.month + 1
    last_year_months_passed = today.month
    #! postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = float(initial_price) * (first_year_months_remaining / 12) * rate / 100
    last_year_depreciation = float(initial_price) * (last_year_months_passed / 12) * rate / 100
    depreciation_per_year = float(initial_price) * rate / 100
    
    item_age_in_years = today.year - purchase_date.year
    
    price_at_end_of_current_year = float(initial_price) - first_year_depreciation - item_age_in_years * depreciation_per_year
    if price_at_end_of_current_year < 0:
        price_at_end_of_current_year = 0
    current_price = float(initial_price) - first_year_depreciation - ((item_age_in_years - 1) * depreciation_per_year) - last_year_depreciation
    if current_price < 0:
        current_price = 0
    
    if expediture_date:
        price_at_end_of_current_year = 0
    return price_at_end_of_current_year, current_price
