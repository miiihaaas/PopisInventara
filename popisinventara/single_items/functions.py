from datetime import datetime, date
import os

from fpdf import FPDF
from popisinventara.models import SingleItem
from popisinventara import db


def current_price_calculation(initial_price, rate, purchase_date, expediture_date=None, year=None):
    if expediture_date:
        print(f'{expediture_date=}')
        today = expediture_date
    elif year:
        today = date(int(year), 12, 31)
        print(f'{today=}')
        print(f'danas: {date.today()=}')
    else:
        today = date.today()
    if rate == 100:
        #! (sitan inventar) ako je rate 100% onda su cena kupljenog predmeta na kraju godine i trenutna cena jednaka 0
        price_at_end_of_current_year = 0
        current_price = 0
        return price_at_end_of_current_year, current_price
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


current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')


def create_reverse_document(school, single_item):
    class PDF(FPDF):
        def __init__(self, **kwargs):
            super(PDF, self).__init__(**kwargs)
            self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
            self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        def header(self):
            self.set_font('DejaVuSansCondensed', '', 12)
            self.cell(190/2, 10, school.schoolname, new_y='LAST', align='L', border=0)
            self.cell(190/2, 10, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 10, school.address, new_y='LAST', align='L', border=0)
            self.cell(190/2, 10, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 10, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('DejaVuSansCondensed', 'B', 14)
    pdf.cell(0, 10, f'Reversni račun', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    pdf.set_font('DejaVuSansCondensed', '', 12)
    pdf.cell(0, 10, f'Datum izdavanja reversa: {single_item.reverse_date}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
    pdf.cell(0, 10, f'Ovim putem potvrđujem da sam od {school.schoolname} dobio/la na korišćenje: ', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
    pdf.cell(60, 10, f'Naziv', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'Inventarski broj', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'Količina', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    pdf.cell(60, 10, f'{single_item.name}', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'{single_item.inventory_number}', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'1 kom', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    
    pdf.cell(100, 10, f'Opremu preuzeo', new_y='LAST', align='C', border=0)
    pdf.cell(100, 10, f'Opremu izdao', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    pdf.cell(100, 10, f'{single_item.reverse_person}', new_y='LAST', align='C', border=0)
    pdf.cell(100, 10, f'____________________', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    
    pdf.cell(0, 10, f'Datum povratka reversa: __________________', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
    pdf.cell(0, 10, f'Ovim putem potvrđujem da sam vratio/la predmet koji sam dobio/la od {school.schoolname} na korišćenje: ', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
    pdf.cell(60, 10, f'Naziv', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'Inventarski broj', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'Količina', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    pdf.cell(60, 10, f'{single_item.name}', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'{single_item.inventory_number}', new_y='LAST', align='L', border=1)
    pdf.cell(60, 10, f'1 kom', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    
    pdf.cell(100, 10, f'Opremu vratio', new_y='LAST', align='C', border=0)
    pdf.cell(100, 10, f'Opremu primio', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    pdf.cell(100, 10, f'{single_item.reverse_person}', new_y='LAST', align='C', border=0)
    pdf.cell(100, 10, f'____________________', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    
    
    # Proverite postojanje foldera, ako ne postoji, kreirajte ga
    path = os.path.join(project_folder, 'static', 'reverses')
    if not os.path.exists(path):
        os.makedirs(path)
    file_name = f'revers.pdf'
    pdf.output(os.path.join(path, file_name))
    