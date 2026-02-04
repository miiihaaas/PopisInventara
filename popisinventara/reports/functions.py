from collections import defaultdict
from decimal import Decimal
from datetime import date
import os, locale
from fpdf import FPDF
from popisinventara.models import School


locale.setlocale(locale.LC_ALL, '')

def write_off_until_current_year(single_item, year=None):
    ''' Funkcija za obračun otpisa do tekuće godine '''
    if not year:
        current_year = date.today().year
    else:
        current_year = int(year)
    
    initial_price = Decimal(str(single_item.initial_price))
    
    # Ako je predmet u magacinu novih (room_id=6) ili nema datum puštanja u upotrebu
    # Amortizacija je 0, vraćamo punu vrednost
    if single_item.room_id == 6 or single_item.date_in_use is None:
        return Decimal(0), initial_price, Decimal(0)
    
    # Određivanje datuma od kojeg počinje amortizacija
    depreciation_start_date = single_item.date_in_use
    input_in_app_date = single_item.input_in_app_date
    
    if year and single_item.deprecation_value is not None:
        current_price = Decimal(str(single_item.initial_price)) - Decimal(str(single_item.deprecation_value))
    else:
        current_price = Decimal(str(single_item.current_price))
    
    # Pribavljanje stope amortizacije na osnovu postavki škole
    # if single_item.room.building.school.use_legacy_system:
    #     rate = Decimal(str(single_item.item.depreciation_rate.rate))
    # else:
    rate = Decimal(str(single_item.depreciation_rate.rate))
    
    # Izračunavanje preostalih meseci u godini puštanja u upotrebu
    first_year_months_remaining = 12 - depreciation_start_date.month + 1
    
    # Obračun amortizacije za prvu godinu i godišnje amortizacije
    first_year_depreciation = initial_price * Decimal(first_year_months_remaining) / Decimal(12) * rate / Decimal(100)
    depreciation_per_year = initial_price * rate / Decimal(100)
    
    # Starost predmeta se računa od datuma puštanja u upotrebu, ne od unosa u aplikaciju
    item_age_in_years = current_year - depreciation_start_date.year
    
    # Poseban slučaj ako postoji datum unosa u aplikaciju I ako je unos pre puštanja u upotrebu
    # (predmet je već imao neki otpis pre unosa u sistem)
    if input_in_app_date and input_in_app_date.year < depreciation_start_date.year:
        # Predmet je unet u sistem pre puštanja u upotrebu - deprecation_value se ignoriše
        pass
    elif input_in_app_date and depreciation_start_date.year <= input_in_app_date.year:
        # Predmet je pušten u upotrebu pre ili u istoj godini kad je unet u sistem
        # Koristimo deprecation_value kao početni otpis
        first_year_depreciation = Decimal(str(single_item.deprecation_value)) if single_item.deprecation_value else Decimal(0)
        item_age_in_years = current_year - input_in_app_date.year
    
    # Izračunavanje ukupnog otpisa i cene na kraju godine
    write_off = first_year_depreciation + depreciation_per_year * Decimal(item_age_in_years - 1)
    price_at_end_of_year = initial_price - (first_year_depreciation + depreciation_per_year * Decimal(item_age_in_years))
    
    # Korekcije vrednosti
    if write_off > initial_price:
        write_off = initial_price
    elif write_off < 0:
        write_off = Decimal(0)
        
    if current_year == depreciation_start_date.year:
        depreciation_per_year = first_year_depreciation
    elif depreciation_per_year > current_price:
        depreciation_per_year = current_price
    
    if price_at_end_of_year < 0:
        price_at_end_of_year = Decimal(0)
        
    return write_off, price_at_end_of_year, depreciation_per_year

current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')


# def category_reports_past_pdf(data, inventory):
#     school = School.query.get_or_404(1)
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#             self.set_font('DejaVuSansCondensed', 'B', 14)
#             self.cell(0, 10, f'Izveštaj po kontima - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             self.set_font('DejaVuSansCondensed', '', 8)
#             self.set_fill_color(211, 211, 211)
#             self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(33, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(33, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(33, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(33, 6, f'Ukupan otpis', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(33, 6, f'Vrednost na kraju godine', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(12, 6, f'Kol', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
#     pdf = PDF()
#     pdf.add_page()
#     totals = [Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0]
#     for row in data:
#         totals[0] += row["initial_price"]
#         totals[1] += row["write_off_until_current_year"]
#         totals[2] += row["depreciation_per_year"]
#         totals[3] += (row["write_off_until_current_year"] + row["depreciation_per_year"])
#         totals[4] += row["price_at_end_of_year"]
#         totals[5] += row["quantity"]
#         initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
#         write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
#         depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
#         price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
#         quantity = row["quantity"]
#         pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(33, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
#         pdf.cell(33, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(33, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(33, 6, f'{write_off_until_current_year + depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(33, 6, f'{price_at_end_of_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(12, 6, f'{quantity}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
#         print(f'{totals=}')
#     pdf.set_fill_color(211, 211, 211)
#     pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(33, 6, f'{locale.format_string("%.2f", totals[0].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(33, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(33, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(33, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(33, 6, f'{locale.format_string("%.2f", totals[4].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(12, 6, f'{totals[5]}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)
    
    
#     path = os.path.join(project_folder, 'static', 'reports')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     file_name = f'category_reports_past.pdf'
#     pdf.output(os.path.join(path, file_name))
    

# def category_reports_expediture_pdf(data, inventory):
#     school = School.query.get_or_404(1)
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#             self.set_font('DejaVuSansCondensed', 'B', 14)
#             self.cell(0, 10, f'Rekapitulacija rashoda po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             self.set_font('DejaVuSansCondensed', '', 8)
#             self.set_fill_color(211, 211, 211)
#             self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(44, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(44, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(44, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(44, 6, f'Vrednost na kraju tekuće godine', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
#     pdf = PDF()
#     pdf.add_page()
#     totals = [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
#     for row in data:
#         totals[0] += row["initial_price"]
#         totals[1] += row["write_off_until_current_year"]
#         totals[2] += row["depreciation_per_year"]
#         totals[3] += row["price_at_end_of_year"]
#         initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
#         write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
#         depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
#         price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
#         pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(44, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
#         pdf.cell(44, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(44, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(44, 6, f'{price_at_end_of_year}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
#         print(f'{totals=}')
#     pdf.set_fill_color(211, 211, 211)
#     pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[0].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)
    
    
#     path = os.path.join(project_folder, 'static', 'reports')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     file_name = f'category_reports_expediture.pdf'
#     pdf.output(os.path.join(path, file_name))


# def category_reports_new_purchases_pdf(data, inventory):
#     school = School.query.get_or_404(1)
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
#             self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#             self.set_font('DejaVuSansCondensed', 'B', 14)
#             self.cell(0, 10, f'Izveštaj o novim nabavkama po kontu po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             self.set_font('DejaVuSansCondensed', '', 8)
#             self.set_fill_color(211, 211, 211)
#             self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(44, 6, f'Nabavna vrednost', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
#     pdf = PDF()
#     pdf.add_page()
#     totals = [Decimal(0)]
#     for row in data:
#         totals[0] += row["initial_price"]
#         initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
#         pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(44, 6, f'{initial_price}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
        
#     print(f'{totals=}')
#     pdf.set_fill_color(211, 211, 211)
#     pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(44, 6, f'{locale.format_string("%.2f", Decimal(totals[0]).quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)

#     path = os.path.join(project_folder, 'static', 'reports')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     file_name = f'category_reports_new_purchases.pdf'
#     pdf.output(os.path.join(path, file_name))


# def category_reports_item_pdf(data, inventory, report_type):
#     school = School.query.get_or_404(1)
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(270/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(270/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(270/2, 7, school.address, new_y='LAST', align='L', border=0)
#             self.cell(270/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(270/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#             self.set_font('DejaVuSansCondensed', 'B', 14)
#             if report_type == 'new_purchases_item': 
#                 self.cell(0, 10, f'Izveštaj o novim nabavkama po kontu i predmetu po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             else:
#                 self.cell(0, 10, f'Izveštaj o isknjiženim stavkama po kontu i predmetu po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             self.set_font('DejaVuSansCondensed', '', 8)
#             self.set_fill_color(211, 211, 211)
#             self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(75, 6, f'Naziv inventara', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(12, 6, f'Kol', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Ukupan otpis', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Vrednost na kraju godine', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
#     pdf = PDF(orientation='L')
#     pdf.add_page()
#     totals = [0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
#     for row in data:
#         totals[0] += row["quantity"]
#         totals[1] += row["initial_price"]
#         totals[2] += row["write_off_until_current_year"]
#         totals[3] += row["depreciation_per_year"]
#         totals[4] += (row["write_off_until_current_year"] + row["depreciation_per_year"])
#         totals[5] += row["price_at_end_of_year"]
#         initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
#         write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
#         depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
#         price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
#         pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(75, 6, f'{row["item"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(12, 6, f'{row["quantity"]}', new_y='LAST', align='C', border=1)
#         pdf.cell(35, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{write_off_until_current_year + depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{price_at_end_of_year}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
#     print(f'{totals=}')
#     pdf.set_fill_color(211, 211, 211)
#     pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(75, 6, f'', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(12, 6, f'{totals[0]}', new_y='LAST', align='C', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[4].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[5].quantize(Decimal("0.01")), grouping=True)}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)

    
#     path = os.path.join(project_folder, 'static', 'reports')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     if report_type == 'new_purchases_item':
#         file_name = f'category_reports_new_purchases_item.pdf'
#     else:
#         file_name = f'category_reports_expediture_item.pdf'
#     pdf.output(os.path.join(path, file_name))


# def serial_reports_pdf(inventory_cumulatively_per_series_working, inventory):
#     school = School.query.get_or_404(1)
#     class PDF(FPDF):
#         def __init__(self, **kwargs):
#             super(PDF, self).__init__(**kwargs)
#             self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
#             self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
#         def header(self):
#             self.set_font('DejaVuSansCondensed', '', 12)
#             self.cell(270/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
#             self.cell(270/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(270/2, 7, school.address, new_y='LAST', align='L', border=0)
#             self.cell(270/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
#             self.cell(270/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
#             self.set_font('DejaVuSansCondensed', 'B', 14)
#             self.cell(0, 10, f'Rekapitulacija predmeta po seriji - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
#             self.set_font('DejaVuSansCondensed', '', 8)
#             self.set_fill_color(211, 211, 211)
#             self.cell(15, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(10, 6, f'Serija', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(70, 6, f'Naziv', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(10, 6, f'Kol', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Ukupan otpis', new_y='LAST', align='C', border=1, fill=True)
#             self.cell(35, 6, f'Vrednost na kraju godine', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
#     pdf = PDF(orientation='L')
#     pdf.add_page()
#     totals = [0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
#     for row in inventory_cumulatively_per_series_working:
#         totals[0] += row["quantity"]
#         totals[1] += row["initial_price"]
#         totals[2] += row["write_off_until_current_year"]
#         totals[3] += row["depreciation_per_year"]
#         totals[4] += (row["write_off_until_current_year"] + row["depreciation_per_year"])
#         totals[5] += row["price_at_end_of_year"]
        
#         # Formatiranje brojeva
#         initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
#         write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
#         depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
#         total_depreciation = locale.format_string('%.2f', (row["write_off_until_current_year"] + row["depreciation_per_year"]).quantize(Decimal("0.01")), grouping=True)
#         price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
        
#         # Ispis reda
#         pdf.cell(15, 6, f'{row["category_number"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(10, 6, f'{row["serial"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(70, 6, f'{row["name"]}', new_y='LAST', align='L', border=1)
#         pdf.cell(10, 6, f'{row["quantity"]}', new_y='LAST', align='C', border=1)
#         pdf.cell(35, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{total_depreciation}', new_y='LAST', align='R', border=1)
#         pdf.cell(35, 6, f'{price_at_end_of_year}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
    
#     # Ispis totala
#     pdf.set_fill_color(211, 211, 211)
#     pdf.cell(95, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
#     pdf.cell(10, 6, f'{totals[0]}', new_y='LAST', align='C', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[4].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
#     pdf.cell(35, 6, f'{locale.format_string("%.2f", totals[5].quantize(Decimal("0.01")), grouping=True)}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)
    
#     # Kreiranje i čuvanje PDF-a
#     path = os.path.join(project_folder, 'static', 'reports')
#     if not os.path.exists(path):
#         os.makedirs(path)
#     file_name = f'serial_reports.pdf'
#     pdf.output(os.path.join(path, file_name))


class BaseReportPDF(FPDF):
    """
    Bazna klasa za sve PDF izveštaje koja definiše zajednički izgled i funkcionalnosti.
    """
    def __init__(self, school, inventory, title, **kwargs):
        super().__init__(**kwargs)
        self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
        self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        self.school = school
        self.inventory = inventory
        self.title = title
        self.set_auto_page_break(auto=True, margin=50)
        
        # Definisanje boja
        self.colors = {
            'header_bg': (240, 240, 240),     # Svetlo siva za zaglavlje
            'border': (180, 180, 180),        # Siva za bordere
            'table_header': (60, 90, 150),    # Tamno plava za header tabele
            'alternate_row': (245, 245, 245), # Svetlo siva za alternativne redove
        }

    def header(self):
        """Generisanje standardnog zaglavlja za sve izveštaje."""
        # Podešavanje boja
        self.set_fill_color(*self.colors['header_bg'])
        self.set_draw_color(*self.colors['border'])

        # Zaglavlje sa podacima škole
        self.set_font('DejaVuSansCondensed', 'B', 14)
        self.cell(0, 10, self.school.schoolname, border=0, ln=True, align='C')
        
        self.set_font('DejaVuSansCondensed', '', 10)
        self.cell(0, 6, f'{self.school.address}, {self.school.city}', border=0, ln=True, align='C')
        self.cell(0, 6, f'MB: {self.school.mb}, JBKJS: {self.school.jbkjs}', border=0, ln=True, align='C')

        # Linija ispod zaglavlja
        self.ln(2)
        self.line(10, self.get_y(), self.w-10, self.get_y())  # Ispravljena linija
        self.ln(5)

        # Naslov izveštaja
        self.set_font('DejaVuSansCondensed', 'B', 12)
        self.cell(0, 10, f'{self.title} - {self.inventory.date.strftime("%d.%m.%Y.")}',
                    border=0, ln=True, align='C')
        self.ln(5)

    def footer(self):
        """Generisanje standardnog podnožja za sve izveštaje."""
        self.set_y(-25)
        self.set_font('DejaVuSansCondensed', '', 8)
        self.cell(0, 10, f'Strana {self.page_no()}/{{nb}}', 0, 0, 'C')

    def add_table_header(self, headers, col_widths):
        """Dodavanje standardizovanog zaglavlja tabele."""
        self.set_fill_color(*self.colors['table_header'])
        self.set_text_color(255, 255, 255)
        self.set_font('DejaVuSansCondensed', 'B', 8)

        for width, header in zip(col_widths, headers):
            self.cell(width, 6, str(header), 1, 0, 'C', True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def format_number(self, value, decimal_places=2):
        """Formatiranje brojeva sa lokalnim podešavanjima."""
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        return locale.format_string(f'%.{decimal_places}f', 
                                    value.quantize(Decimal(f'0.{"0" * decimal_places}')), 
                                    grouping=True)
    def _update_totals(self, totals, row):
        """Ažurira ukupne vrednosti."""
        # Konvertujemo sve vrednosti u Decimal
        for key in ['initial_price', 'write_off_until_current_year', 
                'depreciation_per_year', 'price_at_end_of_year']:
            if key in row:
                totals[key] += Decimal(str(row[key]))
        
        # Posebno rukujemo quantity jer može biti None ili 0
        if 'quantity' in row:
            totals['quantity'] += Decimal(str(row.get('quantity', 0)))


class CategoryReportPDF(BaseReportPDF):
    """
    Klasa za generisanje izveštaja po kontima.
    Podržava prikaz osnovnih i detaljnih izveštaja po kontima.
    """
    def __init__(self, school, inventory, report_type='basic', **kwargs):
        # Osiguravamo da je orientation='L' podrazumevano
        if 'orientation' not in kwargs:
            kwargs['orientation'] = 'L'
        title = self._get_title(report_type)
        super().__init__(school, inventory, title, **kwargs)
        self.report_type = report_type
        
    def _get_title(self, report_type):
        """Određuje naslov izveštaja na osnovu tipa."""
        titles = {
            'basic': 'Izveštaj po kontima',
            'expediture': 'Izveštaj o isknjiženim stavkama po kontu',
            'new_purchases': 'Izveštaj o novim nabavkama po kontu'
        }
        return titles.get(report_type, 'Izveštaj po kontima')

    def _get_column_config(self):
        """Definiše konfiguraciju kolona na osnovu tipa izveštaja."""
        common_columns = [
            ('Konto', 15, 'L'),
            ('Nabavna vrednost', 35, 'R'),
        ]
        
        if self.report_type == 'basic':
            return common_columns + [
                ('Otpis do tekuće godine', 35, 'R'),
                ('Otpis u tekućoj godini', 35, 'R'),
                ('Ukupan otpis', 35, 'R'),
                ('Vrednost na kraju godine', 35, 'R'),
                ('Količina', 15, 'R')
            ]
        elif self.report_type == 'expediture':
            return common_columns + [
                ('Otpis do tekuće godine', 45, 'R'),
                ('Otpis u tekućoj godini', 45, 'R'),
                ('Vrednost na kraju godine', 45, 'R')
            ]
        else:  # new_purchases
            return common_columns

    def create_report(self, data):
        """Kreira PDF izveštaj sa prosleđenim podacima."""
        self.alias_nb_pages()
        self.add_page()
        
        # Dobavljanje konfiguracije kolona
        columns = self._get_column_config()
        headers = [col[0] for col in columns]
        widths = [col[1] for col in columns]
        aligns = [col[2] for col in columns]
        
        # Dodavanje zaglavlja tabele
        self.add_table_header(headers, widths)
        
        # Inicijalizacija totala
        totals = defaultdict(Decimal)
        row_height = 6
        
        # Ispis podataka
        self.set_font('DejaVuSansCondensed', '', 8)
        for idx, row in enumerate(data):
            # Alternativna boja pozadine za svaki drugi red
            if idx % 2 == 1:
                self.set_fill_color(*self.colors['alternate_row'])
            else:
                self.set_fill_color(255, 255, 255)
            
            # Priprema vrednosti za prikaz
            values = self._prepare_row_values(row)
            
            # Ispis reda
            for value, width, align in zip(values, widths, aligns):
                self.cell(width, row_height, str(value), 1, 0, align, True)
            self.ln()
            
            # Ažuriranje totala
            self._update_totals(totals, row)
        
        # Ispis totala
        self._print_totals(totals, widths, aligns)
        
        # Čuvanje PDF-a
        self.save_pdf()

    def _prepare_row_values(self, row):
        """Priprema vrednosti reda za prikaz."""
        values = [
            row['category'],
            self.format_number(row['initial_price'])
        ]
        
        if self.report_type in ['basic', 'expediture']:
            values.extend([
                self.format_number(row['write_off_until_current_year']),
                self.format_number(row['depreciation_per_year'])
            ])
            
            if self.report_type == 'basic':
                total_writeoff = row['write_off_until_current_year'] + row['depreciation_per_year']
                values.extend([
                    self.format_number(total_writeoff),
                    self.format_number(row['price_at_end_of_year']),
                    str(row.get('quantity', 0))
                ])
            else:
                values.append(self.format_number(row['price_at_end_of_year']))
                
        return values


    def _print_totals(self, totals, widths, aligns):
        """Ispisuje red sa ukupnim vrednostima."""
        self.set_font('DejaVuSansCondensed', 'B', 8)
        self.set_fill_color(*self.colors['header_bg'])
        
        values = ['Ukupno:', self.format_number(totals['initial_price'])]
        
        if self.report_type in ['basic', 'expediture']:
            values.extend([
                self.format_number(totals['write_off_until_current_year']),
                self.format_number(totals['depreciation_per_year'])
            ])
            
            if self.report_type == 'basic':
                total_writeoff = totals['write_off_until_current_year'] + totals['depreciation_per_year']
                values.extend([
                    self.format_number(total_writeoff),
                    self.format_number(totals['price_at_end_of_year']),
                    str(totals['quantity'])
                ])
            else:
                values.append(self.format_number(totals['price_at_end_of_year']))
        
        for value, width, align in zip(values, widths, aligns):
            self.cell(width, 6, str(value), 1, 0, align, True)
        self.ln()

    def save_pdf(self):
        """Čuva PDF fajl u odgovarajućem direktorijumu."""
        path = os.path.join(project_folder, 'static', 'reports')
        os.makedirs(path, exist_ok=True)
        
        filenames = {
            'basic': 'category_reports_past.pdf',
            'expediture': 'category_reports_expediture.pdf',
            'new_purchases': 'category_reports_new_purchases.pdf'
        }
        
        filename = filenames.get(self.report_type, 'category_report.pdf')
        self.output(os.path.join(path, filename))

# Funkcije za kreiranje PDF izveštaja
def category_reports_past_pdf(data, inventory):
    """Kreira PDF izveštaj po kontima."""
    school = School.query.get_or_404(1)
    pdf = CategoryReportPDF(school, inventory, report_type='basic', orientation='L')
    pdf.create_report(data)

def category_reports_expediture_pdf(data, inventory):
    """Kreira PDF izveštaj o rashodu po kontima."""
    school = School.query.get_or_404(1)
    pdf = CategoryReportPDF(school, inventory, report_type='expediture', orientation='P')
    pdf.create_report(data)

def category_reports_new_purchases_pdf(data, inventory):
    """Kreira PDF izveštaj o novim nabavkama po kontima."""
    school = School.query.get_or_404(1)
    pdf = CategoryReportPDF(school, inventory, report_type='new_purchases', orientation='P')
    pdf.create_report(data)


class SerialReportPDF(BaseReportPDF):
    """
    Klasa za generisanje izveštaja po serijama.
    Podržava detaljni prikaz predmeta grupisanih po serijskim brojevima.
    """
    def __init__(self, school, inventory, **kwargs):
        title = 'Rekapitulacija predmeta po seriji'
        super().__init__(school, inventory, title, orientation='L', **kwargs)
        
    def _get_column_config(self):
        """Definiše konfiguraciju kolona za izveštaj."""
        return [
            ('Konto', 15, 'L'),
            ('Serija', 15, 'L'),
            ('Naziv', 70, 'L'),
            ('Kol', 10, 'C'),
            ('Nabavna vrednost', 35, 'R'),
            ('Otpis do tekuće godine', 35, 'R'),
            ('Otpis u tekućoj godini', 35, 'R'),
            ('Ukupan otpis', 35, 'R'),
            ('Vrednost na kraju godine', 35, 'R')
        ]

    def create_report(self, data):
        """Kreira PDF izveštaj sa prosleđenim podacima."""
        self.alias_nb_pages()
        self.add_page()
        
        # Dobavljanje konfiguracije kolona
        columns = self._get_column_config()
        headers = [col[0] for col in columns]
        widths = [col[1] for col in columns]
        aligns = [col[2] for col in columns]
        
        # Dodavanje zaglavlja tabele
        self.add_table_header(headers, widths)
        
        # Inicijalizacija totala
        totals = defaultdict(Decimal)
        totals['quantity'] = 0  # Posebna inicijalizacija za celobrojnu vrednost
        row_height = 6
        
        # Ispis podataka
        self.set_font('DejaVuSansCondensed', '', 8)
        for idx, row in enumerate(data):
            # Alternativna boja pozadine za svaki drugi red
            if idx % 2 == 1:
                self.set_fill_color(*self.colors['alternate_row'])
            else:
                self.set_fill_color(255, 255, 255)
            
            # Priprema vrednosti za red
            values = self._prepare_row_values(row)
            
            # Ispis reda
            for value, width, align in zip(values, widths, aligns):
                self.cell(width, row_height, str(value), 1, 0, align, True)
            self.ln()
            
            # Ažuriranje totala
            self._update_totals(totals, row)
        
        # Ispis totala
        self._print_totals(totals, widths, aligns)
        
        # Čuvanje PDF-a
        self.save_pdf()

    def _prepare_row_values(self, row):
        """Priprema vrednosti reda za prikaz."""
        total_writeoff = row['write_off_until_current_year'] + row['depreciation_per_year']
        
        return [
            row['category_number'],
            str(row['serial']),
            row['name'],
            str(row['quantity']),
            self.format_number(row['initial_price']),
            self.format_number(row['write_off_until_current_year']),
            self.format_number(row['depreciation_per_year']),
            self.format_number(total_writeoff),
            self.format_number(row['price_at_end_of_year'])
        ]


    def _print_totals(self, totals, widths, aligns):
        """Ispisuje red sa ukupnim vrednostima."""
        self.set_font('DejaVuSansCondensed', 'B', 8)
        self.set_fill_color(*self.colors['header_bg'])
        
        # Spajanje prve tri kolone za "Ukupno"
        total_width = sum(widths[:3])
        self.cell(total_width, 6, 'Ukupno:', 1, 0, 'L', True)
        
        # Ispis ostalih totala
        values = [
            str(totals['quantity']),
            self.format_number(totals['initial_price']),
            self.format_number(totals['write_off_until_current_year']),
            self.format_number(totals['depreciation_per_year']),
            self.format_number(totals['write_off_until_current_year'] + totals['depreciation_per_year']),
            self.format_number(totals['price_at_end_of_year'])
        ]
        
        for value, width, align in zip(values, widths[3:], aligns[3:]):
            self.cell(width, 6, str(value), 1, 0, align, True)
        self.ln()

    def save_pdf(self):
        """Čuva PDF fajl u odgovarajućem direktorijumu."""
        path = os.path.join(project_folder, 'static', 'reports')
        os.makedirs(path, exist_ok=True)
        filename = 'serial_reports.pdf'
        self.output(os.path.join(path, filename))

# Funkcija za kreiranje PDF izveštaja po serijama
def serial_reports_pdf(inventory_cumulatively_per_series_working, inventory):
    """Kreira PDF izveštaj po serijama."""
    school = School.query.get_or_404(1)
    pdf = SerialReportPDF(school, inventory)
    pdf.create_report(inventory_cumulatively_per_series_working)


class ItemReportPDF(BaseReportPDF):
    """
    Klasa za generisanje izveštaja po pojedinačnim predmetima.
    Podržava izveštaje za rashodovane predmete i nove nabavke.
    """
    def __init__(self, school, inventory, report_type, **kwargs):
        title = self._get_title(report_type)
        super().__init__(school, inventory, title, orientation='L', **kwargs)
        self.report_type = report_type
        
    def _get_title(self, report_type):
        """Određuje naslov izveštaja na osnovu tipa."""
        titles = {
            'expediture_item': 'izveštaj o isknjiženim stavkama po kontu i predmetu',
            'new_purchases_item': 'Izveštaj o novim nabavkama po kontu i predmetu po kontima',
            'basic': 'Izveštaj po kontima i predmetu'
        }
        return titles.get(report_type, 'Rekapitulacija predmeta po kontima')

    def _get_column_config(self):
        """Definiše konfiguraciju kolona za izveštaj."""
        return [
            ('Konto', 12, 'L'),
            ('Naziv inventara', 75, 'L'),
            ('Kol', 12, 'C'),
            ('Nabavna vrednost', 35, 'R'),
            ('Otpis do tekuće godine', 35, 'R'),
            ('Otpis u tekućoj godini', 35, 'R'),
            ('Ukupan otpis', 35, 'R'),
            ('Vrednost na kraju godine', 35, 'R')
        ]

    def create_report(self, data):
        """Kreira PDF izveštaj sa prosleđenim podacima."""
        self.alias_nb_pages()
        self.add_page()
        
        # Dobavljanje konfiguracije kolona
        columns = self._get_column_config()
        headers = [col[0] for col in columns]
        widths = [col[1] for col in columns]
        aligns = [col[2] for col in columns]
        
        # Dodavanje zaglavlja tabele
        self.add_table_header(headers, widths)
        
        # Inicijalizacija totala
        totals = defaultdict(Decimal)
        totals['quantity'] = 0
        row_height = 6
        
        # Ispis podataka
        self.set_font('DejaVuSansCondensed', '', 8)
        for idx, row in enumerate(data):
            # Alternativna boja pozadine
            if idx % 2 == 1:
                self.set_fill_color(*self.colors['alternate_row'])
            else:
                self.set_fill_color(255, 255, 255)
            
            # Priprema i ispis reda
            values = self._prepare_row_values(row)
            for value, width, align in zip(values, widths, aligns):
                self.cell(width, row_height, str(value), 1, 0, align, True)
            self.ln()
            
            # Ažuriranje totala
            self._update_totals(totals, row)
        
        # Ispis totala
        self._print_totals(totals, widths, aligns)
        
        # Čuvanje PDF-a
        self.save_pdf()

    def _prepare_row_values(self, row):
        """Priprema vrednosti reda za prikaz."""
        total_writeoff = row['write_off_until_current_year'] + row['depreciation_per_year']
        
        return [
            row['category'],
            row['item'],
            str(row['quantity']),
            self.format_number(row['initial_price']),
            self.format_number(row['write_off_until_current_year']),
            self.format_number(row['depreciation_per_year']),
            self.format_number(total_writeoff),
            self.format_number(row['price_at_end_of_year'])
        ]


    def _print_totals(self, totals, widths, aligns):
        """Ispisuje red sa ukupnim vrednostima."""
        self.set_font('DejaVuSansCondensed', 'B', 8)
        self.set_fill_color(*self.colors['header_bg'])
        
        # Spajanje prve dve kolone za "Ukupno"
        total_label_width = sum(widths[:2])
        self.cell(total_label_width, 6, 'Ukupno:', 1, 0, 'L', True)
        
        # Ispis ostalih totala
        values = [
            str(totals['quantity']),
            self.format_number(totals['initial_price']),
            self.format_number(totals['write_off_until_current_year']),
            self.format_number(totals['depreciation_per_year']),
            self.format_number(totals['write_off_until_current_year'] + totals['depreciation_per_year']),
            self.format_number(totals['price_at_end_of_year'])
        ]
        
        for value, width, align in zip(values, widths[2:], aligns[2:]):
            self.cell(width, 6, str(value), 1, 0, align, True)
        self.ln()

    def save_pdf(self):
        """Čuva PDF fajl u odgovarajućem direktorijumu."""
        path = os.path.join(project_folder, 'static', 'reports')
        os.makedirs(path, exist_ok=True)
        
        filenames = {
            'expediture_item': 'category_reports_expediture_item.pdf',
            'new_purchases_item': 'category_reports_new_purchases_item.pdf',
            'basic': 'category_reports_past_item.pdf'
        }
        
        filename = filenames.get(self.report_type, 'item_report.pdf')
        self.output(os.path.join(path, filename))

# Funkcija za kreiranje PDF izveštaja
def category_reports_item_pdf(data, inventory, report_type):
    """Kreira PDF izveštaj za pojedinačne predmete."""
    school = School.query.get_or_404(1)
    pdf = ItemReportPDF(school, inventory, report_type)
    pdf.create_report(data)