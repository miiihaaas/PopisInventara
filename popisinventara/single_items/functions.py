from datetime import datetime, date
from decimal import Decimal
import os

from fpdf import FPDF
from popisinventara.models import SingleItem
from popisinventara import db
from popisinventara.reports.functions import BaseReportPDF


def distribute_prices(total_price: float, quantity: int) -> tuple:
    """
    Raspoređuje ukupnu cenu na quantity predmeta tako da:
    - Svi predmeti osim poslednjeg imaju istu cenu zaokruženu na 2 decimale
    - Poslednji predmet ima cenu koja osigurava da je zbir svih cena jednak total_price
    
    Args:
        total_price (float): Ukupna cena svih predmeta
        quantity (int): Broj predmeta
    
    Returns:
        tuple: (base_price, last_item_price) gde je:
            - base_price: cena za sve predmete osim poslednjeg
            - last_item_price: cena poslednjeg predmeta
    """
    # Izračunavanje prosečne cene
    exact_price = total_price / quantity
    
    # Zaokruživanje na 2 decimale (na gore i na dole)
    price_floor = float(format(exact_price, '.2f'))
    price_ceil = float(format(exact_price + 0.01, '.2f'))
    
    # Provera koja kombinacija daje tačnu ukupnu cenu
    # Pokušavamo prvo sa zaokruživanjem na dole
    total_with_floor = price_floor * (quantity - 1)
    last_price_with_floor = float(format(total_price - total_with_floor, '.2f'))
    
    # Pokušavamo sa zaokruživanjem na gore
    total_with_ceil = price_ceil * (quantity - 1)
    last_price_with_ceil = float(format(total_price - total_with_ceil, '.2f'))
    
    # Biramo kombinaciju koja daje manju razliku između cena
    diff_with_floor = abs(last_price_with_floor - price_floor)
    diff_with_ceil = abs(last_price_with_ceil - price_ceil)
    
    if diff_with_floor <= diff_with_ceil:
        return price_floor, last_price_with_floor
    else:
        return price_ceil, last_price_with_ceil


def current_price_calculation(initial_price, rate, purchase_date, expediture_date=None, year=None, input_in_app_date=None, deprecation_value=None):
    if expediture_date:
        today = expediture_date
    elif year:
        today = date(int(year), 12, 31)
    else:
        today = date.today()
        
    if rate == 100:
        #! (sitan inventar) ako je stopa 100%, cena kupljenog predmeta na kraju godine i trenutna cena su jednake 0
        price_at_end_of_current_year = Decimal('0')
        current_price = Decimal('0')
        return price_at_end_of_current_year, current_price
    
    #! Koliko meseci je ostalo u godini u kojoj je kupljen predmet
    first_year_months_remaining = 12 - purchase_date.month + 1
    last_year_months_passed = today.month
    
    #! Postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = Decimal(initial_price) * (Decimal(first_year_months_remaining) / Decimal('12')) * Decimal(rate) / Decimal('100')
    last_year_depreciation = Decimal(initial_price) * (Decimal(last_year_months_passed) / Decimal('12')) * Decimal(rate) / Decimal('100')
    depreciation_per_year = Decimal(initial_price) * Decimal(rate) / Decimal('100')
    
    if input_in_app_date:
        item_age_in_years = today.year - input_in_app_date.year
        first_year_depreciation = Decimal(deprecation_value) #! stavljam vrednost otpisa koju smo dobili kao input koji su škole dostavile
    else:
        item_age_in_years = today.year - purchase_date.year
    
    price_at_end_of_current_year = Decimal(initial_price) - first_year_depreciation - item_age_in_years * depreciation_per_year
    if price_at_end_of_current_year < Decimal('0'):
        price_at_end_of_current_year = Decimal('0')
    
    current_price = Decimal(initial_price) - first_year_depreciation - ((item_age_in_years - 1) * depreciation_per_year) - last_year_depreciation
    if current_price < Decimal('0'):
        current_price = Decimal('0')
    
    if expediture_date:
        price_at_end_of_current_year = Decimal('0')
    
    return price_at_end_of_current_year, current_price


current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')


# def create_reverse_document(school, single_item):
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(190/2, 10, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 10, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 10, school.address, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 10, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 10, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#     pdf = PDF()
#     pdf.add_page()
#     pdf.set_font('DejaVuSansCondensed', 'B', 14)
#     pdf.cell(0, 10, f'Reversni račun', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#     pdf.set_font('DejaVuSansCondensed', '', 12)
#     pdf.cell(0, 10, f'Datum izdavanja reversa: {single_item.reverse_date}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#     pdf.cell(0, 10, f'Ovim putem potvrđujem da sam od {school.schoolname} dobio/la na korišćenje: ', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#     pdf.cell(60, 10, f'Naziv', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'Inventarski broj', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'Količina', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
#     pdf.cell(60, 10, f'{single_item.name}', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'{single_item.inventory_number}', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'1 kom', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    
#     pdf.cell(100, 10, f'Opremu preuzeo', new_y='LAST', align='C', border=0)
#     pdf.cell(100, 10, f'Opremu izdao', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#     pdf.cell(100, 10, f'{single_item.reverse_person}', new_y='LAST', align='C', border=0)
#     pdf.cell(100, 10, f'____________________', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    
#     pdf.cell(0, 10, f'Datum povratka reversa: __________________', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#     pdf.cell(0, 10, f'Ovim putem potvrđujem da sam vratio/la predmet koji sam dobio/la od {school.schoolname} na korišćenje: ', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#     pdf.cell(60, 10, f'Naziv', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'Inventarski broj', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'Količina', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
#     pdf.cell(60, 10, f'{single_item.name}', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'{single_item.inventory_number}', new_y='LAST', align='L', border=1)
#     pdf.cell(60, 10, f'1 kom', new_x='LMARGIN', new_y='NEXT', align='L', border=1)
    
#     pdf.cell(100, 10, f'Opremu vratio', new_y='LAST', align='C', border=0)
#     pdf.cell(100, 10, f'Opremu primio', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#     pdf.cell(100, 10, f'{single_item.reverse_person}', new_y='LAST', align='C', border=0)
#     pdf.cell(100, 10, f'____________________', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
    
    
#     # Proverite postojanje foldera, ako ne postoji, kreirajte ga
#     path = os.path.join(project_folder, 'static', 'reverses')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     file_name = f'revers.pdf'
#     pdf.output(os.path.join(path, file_name))


class ReverseDocumentPDF(BaseReportPDF):
    """
    Klasa za generisanje reversnog dokumenta.
    Kreira PDF dokument za evidenciju izdavanja i vraćanja opreme.
    """
    def __init__(self, school, single_item, **kwargs):
        title = 'Reversni račun'
        super().__init__(school, None, title, **kwargs)  # inventory je None jer nije potreban
        self.single_item = single_item
        
    def header(self):
        """Generisanje prilagođenog zaglavlja za reversni dokument."""
        self.set_font('DejaVuSansCondensed', '', 12)
        
        # Leva strana zaglavlja
        self.cell(120, 10, self.school.schoolname, 0, 0, 'L')
        # Desna strana zaglavlja - više prostora za matični broj
        self.cell(70, 10, f'Matični broj: {self.school.mb}', 0, 1, 'R')
        
        self.cell(120, 10, self.school.address, 0, 0, 'L')
        # Više prostora za JBKJS
        self.cell(70, 10, f'JBKJS: {self.school.jbkjs}', 0, 1, 'R')
        
        self.cell(0, 10, 
                 f'{self.school.zip_code} {self.school.city}, {self.school.municipality}',
                 0, 1, 'L')

        # Naslov dokumenta
        self.ln(5)
        self.set_font('DejaVuSansCondensed', 'B', 14)
        self.cell(0, 10, self.title, 0, 1, 'C')

    def _add_item_table(self):
        """Dodaje tabelu sa informacijama o predmetu."""
        # Podešavanje boja
        self.set_fill_color(*self.colors['table_header'])
        self.set_text_color(255, 255, 255)
        
        # Zaglavlje tabele
        self.set_font('DejaVuSansCondensed', 'B', 10)
        headers = ['Naziv', 'Inventarski broj', 'Količina']
        widths = [60, 60, 60]
        
        for width, header in zip(widths, headers):
            self.cell(width, 10, header, 1, 0, 'L', True)
        self.ln()
        
        # Podaci
        self.set_text_color(0, 0, 0)
        self.set_font('DejaVuSansCondensed', '', 10)
        self.cell(60, 10, self.single_item.name, 1, 0, 'L')
        self.cell(60, 10, self.single_item.inventory_number, 1, 0, 'L')
        self.cell(60, 10, '1 kom', 1, 1, 'L')

    def _add_signature_section(self, izdavanje=True):
        """Dodaje sekciju za potpise."""
        self.ln(10)
        if izdavanje:
            left_text = 'Opremu preuzeo'
            right_text = 'Opremu izdao'
        else:
            left_text = 'Opremu vratio'
            right_text = 'Opremu primio'
            
        # Nazivi polja
        self.cell(self.w/2, 10, left_text, 0, 0, 'C')
        self.cell(self.w/2, 10, right_text, 0, 1, 'C')
        
        # Linije za potpis
        self.cell(self.w/2, 10, self.single_item.reverse_person, 0, 0, 'C')
        self.cell(self.w/2, 10, '____________________', 0, 1, 'C')

    def create_document(self):
        """Kreira kompletan reversni dokument."""
        self.add_page()
        
        # Datum izdavanja
        self.set_font('DejaVuSansCondensed', '', 12)
        self.cell(0, 10, 
                 f'Datum izdavanja reversa: {self.single_item.reverse_date}',
                 0, 1, 'R')
        
        # Tekst izdavanja
        self.cell(0, 10, 
                 f'Ovim putem potvrđujem da sam od {self.school.schoolname} dobio/la na korišćenje:',
                 0, 1, 'L')
        
        # Tabela izdavanja
        self._add_item_table()
        
        # Potpisi izdavanja
        self._add_signature_section(izdavanje=True)
        
        # Sekcija za povratak
        self.ln(10)
        self.cell(0, 10, 'Datum povratka reversa: __________________', 0, 1, 'R')
        
        self.cell(0, 10,
                 f'Ovim putem potvrđujem da sam vratio/la predmet koji sam dobio/la od {self.school.schoolname} na korišćenje:',
                 0, 1, 'L')
        
        # Tabela povratka
        self._add_item_table()
        
        # Potpisi povratka
        self._add_signature_section(izdavanje=False)
        
        # Čuvanje dokumenta
        self.save_document()
        
    def save_document(self):
        """Čuva PDF fajl u odgovarajućem direktorijumu."""
        path = os.path.join(project_folder, 'static', 'reverses')
        os.makedirs(path, exist_ok=True)
        filename = 'revers.pdf'
        self.output(os.path.join(path, filename))

def create_reverse_document(school, single_item):
    """Pomoćna funkcija za kreiranje reversnog dokumenta."""
    pdf = ReverseDocumentPDF(school, single_item)
    pdf.create_document()