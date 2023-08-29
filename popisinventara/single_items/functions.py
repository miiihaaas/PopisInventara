from datetime import datetime, date
from popisinventara.models import SingleItem
from popisinventara import db


def current_price_calculation(initial_price, rate, purchase_date):
    today = date.today()
    #! koliko je meseci ostalo u godini u kojoj je kupljen predmet
    months_remaining = 12 - purchase_date.month + 1
    #! postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = float(initial_price) * (months_remaining / 12) * rate / 100
    depreciation_per_year = float(initial_price) * rate / 100
    
    item_age_in_years = today.year - purchase_date.year
    
    current_price = float(initial_price) - first_year_depreciation - item_age_in_years * depreciation_per_year
    if current_price < 0:
        current_price = 0
    return current_price
