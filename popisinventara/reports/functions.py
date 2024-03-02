
from decimal import Decimal
from datetime import date
import os, locale
from fpdf import FPDF
from popisinventara.models import School


locale.setlocale(locale.LC_ALL, '')

def write_off_until_current_year(single_item, year=None):
    ''' funkcija otpis do tekuće godine '''
    if not year:
        current_year = date.today().year
    else:
        current_year = int(year)
    purchase_date = single_item.purchase_date
    input_in_app_date = single_item.input_in_app_date
    initial_price = Decimal(str(single_item.initial_price))
    if year and single_item.deprecation_value is not None:
        current_price = Decimal(str(single_item.initial_price)) - Decimal(str(single_item.deprecation_value))
    else:
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
    # elif single_item.expediture_date: #! ovo ček i ne treba, jer će se u category_reports_past filtrirati predmeti koji nisu rashodovani
    #     price_at_end_of_year = Decimal(0)
        
    return write_off, price_at_end_of_year, depreciation_per_year

current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')


def category_reports_past_pdf(data, inventory):
    school = School.query.get_or_404(1)
    class PDF(FPDF):
        def __init__(self, **kwargs):
            super(PDF, self).__init__(**kwargs)
            self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
            self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        def header(self):
            self.set_font('DejaVuSansCondensed', '', 12)
            self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
            self.set_font('DejaVuSansCondensed', 'B', 14)
            self.cell(0, 10, f'Izveštaj po kontima - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
            self.set_font('DejaVuSansCondensed', '', 8)
            self.set_fill_color(211, 211, 211)
            self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
            self.cell(40, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
            self.cell(40, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
            self.cell(40, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Vrednost na kraju tekuće godine', new_y='LAST', align='C', border=1, fill=True)
            self.cell(12, 6, f'Kol', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
    pdf = PDF()
    pdf.add_page()
    totals = [Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0]
    for row in data:
        totals[0] += row["initial_price"]
        totals[1] += row["write_off_until_current_year"]
        totals[2] += row["depreciation_per_year"]
        totals[3] += row["price_at_end_of_year"]
        totals[4] += row["quantity"]
        initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
        write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
        depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
        price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
        quantity = row["quantity"]
        pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
        pdf.cell(40, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
        pdf.cell(40, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
        pdf.cell(40, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{price_at_end_of_year}', new_y='LAST', align='R', border=1)
        pdf.cell(12, 6, f'{quantity}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
        print(f'{totals=}')
    pdf.set_fill_color(211, 211, 211)
    pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
    pdf.cell(40, 6, f'{locale.format_string("%.2f", totals[0].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(40, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(40, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(12, 6, f'{totals[4]}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)
    
    
    path = os.path.join(project_folder, 'static', 'reports')
    if not os.path.exists(path):
        os.makedirs(path)
    file_name = f'category_reports_past.pdf'
    pdf.output(os.path.join(path, file_name))
    

def category_reports_expediture_pdf(data, inventory):
    school = School.query.get_or_404(1)
    class PDF(FPDF):
        def __init__(self, **kwargs):
            super(PDF, self).__init__(**kwargs)
            self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
            self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        def header(self):
            self.set_font('DejaVuSansCondensed', '', 12)
            self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
            self.set_font('DejaVuSansCondensed', 'B', 14)
            self.cell(0, 10, f'Rekapitulacija rashoda po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
            self.set_font('DejaVuSansCondensed', '', 8)
            self.set_fill_color(211, 211, 211)
            self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Vrednost na kraju tekuće godine', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
    pdf = PDF()
    pdf.add_page()
    totals = [Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    for row in data:
        totals[0] += row["initial_price"]
        totals[1] += row["write_off_until_current_year"]
        totals[2] += row["depreciation_per_year"]
        totals[3] += row["price_at_end_of_year"]
        initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
        write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
        depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
        price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
        pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
        pdf.cell(44, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{price_at_end_of_year}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
        print(f'{totals=}')
    pdf.set_fill_color(211, 211, 211)
    pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[0].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)
    
    
    path = os.path.join(project_folder, 'static', 'reports')
    if not os.path.exists(path):
        os.makedirs(path)
    file_name = f'category_reports_expediture.pdf'
    pdf.output(os.path.join(path, file_name))


def category_reports_new_purchases_pdf(data, inventory):
    school = School.query.get_or_404(1)
    class PDF(FPDF):
        def __init__(self, **kwargs):
            super(PDF, self).__init__(**kwargs)
            self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
            self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        def header(self):
            self.set_font('DejaVuSansCondensed', '', 12)
            self.cell(190/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, school.address, new_y='LAST', align='L', border=0)
            self.cell(190/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(190/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
            self.set_font('DejaVuSansCondensed', 'B', 14)
            self.cell(0, 10, f'Rekapitulacija novih nabavki po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
            self.set_font('DejaVuSansCondensed', '', 8)
            self.set_fill_color(211, 211, 211)
            self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Nabavna vrednost', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
    pdf = PDF()
    pdf.add_page()
    totals = [Decimal(0)]
    for row in data:
        totals[0] += row["initial_price"]
        initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
        pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
        pdf.cell(44, 6, f'{initial_price}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
        
    print(f'{totals=}')
    pdf.set_fill_color(211, 211, 211)
    pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", Decimal(totals[0]).quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)

    path = os.path.join(project_folder, 'static', 'reports')
    if not os.path.exists(path):
        os.makedirs(path)
    file_name = f'category_reports_new_purchases.pdf'
    pdf.output(os.path.join(path, file_name))


def category_reports_item_pdf(data, inventory, report_type):
    school = School.query.get_or_404(1)
    class PDF(FPDF):
        def __init__(self, **kwargs):
            super(PDF, self).__init__(**kwargs)
            self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
            self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        def header(self):
            self.set_font('DejaVuSansCondensed', '', 12)
            self.cell(270/2, 7, school.schoolname, new_y='LAST', align='L', border=0)
            self.cell(270/2, 7, f'Matični broj: {school.mb}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(270/2, 7, school.address, new_y='LAST', align='L', border=0)
            self.cell(270/2, 7, f'JBKJS: {school.jbkjs}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
            self.cell(270/2, 7, f'{school.zip_code} {school.city}, {school.municipality}', new_x='LMARGIN', new_y='NEXT', align='L', border=0)
            self.set_font('DejaVuSansCondensed', 'B', 14)
            if report_type == 'new_purchases_item': 
                self.cell(0, 10, f'Rekapitulacija nabavljenih predmeta po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
            else:
                self.cell(0, 10, f'Rekapitulacija rashodovanih predmeta po kontu - datum popisa: {inventory.date.strftime("%d.%m.%Y.")}', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
            self.set_font('DejaVuSansCondensed', '', 8)
            self.set_fill_color(211, 211, 211)
            self.cell(12, 6, f'Konto', new_y='LAST', align='C', border=1, fill=True)
            self.cell(75, 6, f'Naziv inventara', new_y='LAST', align='C', border=1, fill=True)
            self.cell(12, 6, f'Kol', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Nabavna vrednost', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Otpis do tekuće godine', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Otpis u tekućoj godini', new_y='LAST', align='C', border=1, fill=True)
            self.cell(44, 6, f'Vrednost na kraju tekuće godine', new_x='LMARGIN', new_y='NEXT', align='C', border=1, fill=True)
    pdf = PDF(orientation='L')
    pdf.add_page()
    totals = [0, Decimal(0), Decimal(0), Decimal(0), Decimal(0)]
    for row in data:
        totals[0] += row["quantity"]
        totals[1] += row["initial_price"]
        totals[2] += row["write_off_until_current_year"]
        totals[3] += row["depreciation_per_year"]
        totals[4] += row["price_at_end_of_year"]
        initial_price = locale.format_string('%.2f', row["initial_price"].quantize(Decimal("0.01")), grouping=True)
        write_off_until_current_year = locale.format_string('%.2f', row["write_off_until_current_year"].quantize(Decimal("0.01")), grouping=True)
        depreciation_per_year = locale.format_string('%.2f', row["depreciation_per_year"].quantize(Decimal("0.01")), grouping=True)
        price_at_end_of_year = locale.format_string('%.2f', row["price_at_end_of_year"].quantize(Decimal("0.01")), grouping=True)
        pdf.cell(12, 6, f'{row["category"]}', new_y='LAST', align='L', border=1)
        pdf.cell(75, 6, f'{row["item"]}', new_y='LAST', align='L', border=1)
        pdf.cell(12, 6, f'{row["quantity"]}', new_y='LAST', align='C', border=1)
        pdf.cell(44, 6, f'{initial_price}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{write_off_until_current_year}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{depreciation_per_year}', new_y='LAST', align='R', border=1)
        pdf.cell(44, 6, f'{price_at_end_of_year}', new_x='LMARGIN', new_y='NEXT', align='R', border=1)
    print(f'{totals=}')
    pdf.set_fill_color(211, 211, 211)
    pdf.cell(12, 6, f'Ukupno', new_y='LAST', align='L', border=1, fill=True)
    pdf.cell(75, 6, f'', new_y='LAST', align='L', border=1, fill=True)
    pdf.cell(12, 6, f'{totals[0]}', new_y='LAST', align='C', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[1].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[2].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[3].quantize(Decimal("0.01")), grouping=True)}', new_y='LAST', align='R', border=1, fill=True)
    pdf.cell(44, 6, f'{locale.format_string("%.2f", totals[4].quantize(Decimal("0.01")), grouping=True)}', new_x='LMARGIN', new_y='NEXT', align='R', border=1, fill=True)

    
    path = os.path.join(project_folder, 'static', 'reports')
    if not os.path.exists(path):
        os.makedirs(path)
    if report_type == 'new_purchases_item':
        file_name = f'category_reports_new_purchases_item.pdf'
    else:
        file_name = f'category_reports_expediture_item.pdf'
    pdf.output(os.path.join(path, file_name))