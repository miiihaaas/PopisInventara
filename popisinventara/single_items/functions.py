from datetime import datetime, date
from decimal import Decimal
import os

from fpdf import FPDF
from popisinventara.models import SingleItem
from popisinventara import db
from popisinventara.reports.functions import BaseReportPDF


def distribute_prices(total_price: float, quantity: int) -> list:
    """
    Raspoređuje ukupnu cenu na quantity predmeta tako da:
    - Većina predmeta ima istu osnovnu cenu zaokruženu na 2 decimale
    - Poslednjih nekoliko predmeta dele razliku da bi se postigla tačna ukupna cena
    
    Args:
        total_price (float): Ukupna cena svih predmeta
        quantity (int): Broj predmeta
    
    Returns:
        list: Lista cena za sve predmete
    """
    # Prvo proverimo da li je cena deljiva sa količinom bez ostatka nakon zaokruživanja
    base_price = round(total_price / quantity, 2)
    if round(base_price * quantity, 2) == total_price:
        # Ako jeste, sve cene su iste
        return [base_price] * quantity
    
    # Ako nije deljivo, nastavljamo sa originalnom logikom
    if quantity <= 4:
        num_items_to_adjust = quantity
    else:
        num_items_to_adjust = min(max(3, round(quantity * 0.1)), 8)
    
    total_base = base_price * quantity
    diff = round(total_price - total_base, 2)
    
    prices = [base_price] * quantity
    
    if diff != 0:
        adjustment_base = round(diff / num_items_to_adjust, 2)
        remaining_diff = diff
        
        for i in range(num_items_to_adjust):
            if i == num_items_to_adjust - 1:
                adjustment = round(remaining_diff, 2)
            else:
                adjustment = adjustment_base
                remaining_diff = round(remaining_diff - adjustment, 2)
            
            prices[-(i+1)] = round(base_price + adjustment, 2)
    
    return prices


def current_price_calculation(initial_price, rate, purchase_date, expediture_date=None, year=None, input_in_app_date=None, deprecation_value=None, date_in_use=None, room_id=None):
    # Ako je predmet u magacinu novih (room_id=6), amortizacija = 0
    if room_id == 6:
        return Decimal(str(initial_price)), Decimal(str(initial_price))
    
    # Ako predmet nikada nije bio pušten u upotrebu (date_in_use=None) i nije u specijalnom magacinu
    # Vraćamo punu vrednost jer amortizacija još nije počela
    if date_in_use is None and room_id is not None:
        return Decimal(str(initial_price)), Decimal(str(initial_price))
    
    # Određivanje datuma od kojeg počinje amortizacija
    # Ako postoji date_in_use, koristimo ga; inače koristimo purchase_date (backward compatibility)
    depreciation_start_date = date_in_use if date_in_use else purchase_date
    
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
    
    #! Koliko meseci je ostalo u godini u kojoj je predmet pušten u upotrebu
    #! ############################################################################## !#
    first_year_months_remaining = 12 - depreciation_start_date.month + 1 #? ovde treba modifikovati da se ne računa +1? 
    #! primer. predmet je pušten u upotrebu 17.feb.2021.                              !#
    #! preostali broj meseci je (mart-decembar) što je 10 meseci                      !#
    #! a trenutno računa first_year_months_remaining = 12 - 2 + 1 = 11 što nije tačno !#
    #! ############################################################################## !#
    last_year_months_passed = today.month
    
    #! Postavljanje vrednosti amortizacije za prvu i ostale godine
    first_year_depreciation = Decimal(initial_price) * (Decimal(first_year_months_remaining) / Decimal('12')) * Decimal(rate) / Decimal('100')
    last_year_depreciation = Decimal(initial_price) * (Decimal(last_year_months_passed) / Decimal('12')) * Decimal(rate) / Decimal('100')
    depreciation_per_year = Decimal(initial_price) * Decimal(rate) / Decimal('100')
    
    # Starost predmeta se računa od datuma puštanja u upotrebu
    item_age_in_years = today.year - depreciation_start_date.year
    
    # Poseban slučaj ako postoji datum unosa u aplikaciju I ako je unos posle ili u istoj godini kao puštanje u upotrebu
    # (predmet je već imao neki otpis pre unosa u sistem)
    if input_in_app_date and depreciation_start_date.year <= input_in_app_date.year:
        item_age_in_years = today.year - input_in_app_date.year
        first_year_depreciation = Decimal(deprecation_value) if deprecation_value else Decimal(0)
    
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