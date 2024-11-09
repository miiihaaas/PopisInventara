from datetime import datetime
import os
from fpdf import FPDF
from popisinventara.models import Room, Inventory

current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')

class InventoryPDF(FPDF):
    def __init__(self, school, inventory, room, show_quantity=True, **kwargs):
        super().__init__(**kwargs)
        self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
        self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
        self.school = school
        self.inventory = inventory
        self.room = room
        self.show_quantity = show_quantity
        self.set_auto_page_break(auto=True, margin=50)

    def header(self):
        # Podešavanje boja i stilova
        self.set_fill_color(240, 240, 240)  # Svetlo siva pozadina za header
        self.set_draw_color(180, 180, 180)  # Svetlo siva boja za bordere

        # Logo i naziv škole
        self.set_font('DejaVuSansCondensed', 'B', 14)
        self.cell(0, 10, self.school.schoolname, border=0, ln=True, align='C')

        # Informacije o školi
        self.set_font('DejaVuSansCondensed', '', 10)
        self.cell(0, 6, f'{self.school.address}, {self.school.city}', border=0, ln=True, align='C')
        self.cell(0, 6, f'MB: {self.school.mb}, JBKJS: {self.school.jbkjs}', border=0, ln=True, align='C')

        # Linija ispod zaglavlja
        self.ln(2)
        self.line(10, self.get_y(), 290, self.get_y())
        self.ln(5)

        # Informacije o popisu
        self.set_font('DejaVuSansCondensed', 'B', 12)
        room_name = f'{self.room.building.name} - {self.room.name} ({self.room.dynamic_name})'
        
        # Grid sa informacijama
        self.set_fill_color(245, 245, 245)
        self.cell(140, 8, f'Datum popisa: {self.inventory.date.strftime("%d.%m.%Y.")}', 1, 0, 'L', True)
        self.cell(140, 8, f'Prostorija: {room_name}', 1, 1, 'L', True)
        self.cell(140, 8, f'Popisna lista broj: {self.inventory.id}/{self.room.id}', 1, 0, 'L', True)
        self.cell(140, 8, f'Status: {self.inventory.status.upper()}', 1, 1, 'L', True)

        self.ln(5)

        # Header tabele
        self.set_fill_color(60, 90, 150)  # Tamno plava za header tabele
        self.set_text_color(255, 255, 255)  # Beli tekst
        self.set_font('DejaVuSansCondensed', 'B', 10)

        # Definisanje širina kolona - ukupno 280 širina
        if self.show_quantity:
            col_widths = [90, 25, 40, 25, 25, 25, 50]  # Sa količinom
            headers = ['Naziv predmeta', 'Serija', 'Konto', 'Procenat', 'Kol.', 'Pop.', 'Komentar']
        else:
            col_widths = [100, 25, 45, 30, 30, 50]  # Bez količine
            headers = ['Naziv predmeta', 'Serija', 'Konto', 'Procenat', 'Pop.', 'Komentar']

        # Ispis hedera
        for width, header in zip(col_widths, headers):
            self.cell(width, 8, header, 1, 0, 'C', True)
        self.ln()
        
        # Reset boje teksta za sadržaj
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-45)
        self.set_font('DejaVuSansCondensed', '', 10)
        
        # Potpisi
        self.cell(0, 7, 'Potpisi članova popisne komisije:', ln=True)
        self.ln(5)
        for i in range(3):
            self.cell(95, 7, '_' * 30, 0, 0, 'C')
        self.ln()
        self.set_font('DejaVuSansCondensed', '', 8)
        for i in range(3):
            self.cell(95, 5, f'Član komisije {i+1}', 0, 0, 'C')
        
        # Broj stranice
        self.ln(10)
        self.set_font('DejaVuSansCondensed', '', 8)
        self.cell(0, 10, f'Strana {self.page_no()}/{{nb}}', 0, 0, 'C')

def popisna_lista_gen(inventory_item_list_data, room, inventory_id, school, inventory):
    """Generisanje popisne liste u PDF formatu."""
    
    # Generisanje dve verzije liste - sa i bez količina
    for show_quantity in [True, False]:
        pdf = InventoryPDF(
            school=school,
            inventory=inventory,
            room=room,
            show_quantity=show_quantity,
            orientation='L',
            unit='mm',
            format='A4'
        )
        
        pdf.alias_nb_pages()  # Za numeraciju stranica
        pdf.add_page()
        
        # Podešavanje stila za sadržaj
        pdf.set_font('DejaVuSansCondensed', '', 9)
        pdf.set_fill_color(255, 255, 255)
        line_height = 7

        # Alternating colors for rows
        row_colors = [(255, 255, 255), (245, 245, 245)]
        
        total_quantity = 0
        total_quantity_input = 0

        # Definisanje širina kolona - moraju se poklapati sa headerima
        if show_quantity:
            col_widths = [90, 25, 40, 25, 25, 25, 50]  # Sa količinom
        else:
            col_widths = [100, 25, 45, 30, 30, 50]  # Bez količine
        
        for idx, item in enumerate(inventory_item_list_data):
            # Alternating background colors
            pdf.set_fill_color(*row_colors[idx % 2])
            
            quantity = int(item.get('quantity', 0))
            quantity_input = int(item.get('quantity_input', 0))
            total_quantity += quantity
            total_quantity_input += quantity_input

            # Priprema podataka za red
            if show_quantity:
                row_data = [
                    str(item.get('name', '')),
                    '{0:05d}'.format(int(item.get('serial', 0))),
                    str(item.get('category_number', '')),
                    f"{item.get('depreciation_rate', 0)}%",
                    str(quantity),
                    str(quantity_input),
                    str(item.get('comment', ''))
                ]
            else:
                row_data = [
                    str(item.get('name', '')),
                    '{0:05d}'.format(int(item.get('serial', 0))),
                    str(item.get('category_number', '')),
                    f"{item.get('depreciation_rate', 0)}%",
                    str(quantity_input),
                    str(item.get('comment', ''))
                ]

            # Ispis reda
            for width, content in zip(col_widths, row_data):
                # Poravnanje brojeva desno, teksta levo
                align = 'R' if content.replace('.', '').isdigit() or '%' in content else 'L'
                pdf.cell(width, line_height, content, 1, 0, align, True)
            pdf.ln()

        # Dodavanje totala
        if show_quantity:
            pdf.set_font('DejaVuSansCondensed', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            total_width = sum(col_widths[:4])  # Zbir širina prvih 4 kolona
            pdf.cell(total_width, line_height, 'UKUPNO:', 1, 0, 'R', True)
            pdf.cell(25, line_height, str(total_quantity), 1, 0, 'R', True)
            pdf.cell(25, line_height, str(total_quantity_input), 1, 0, 'R', True)
            pdf.cell(50, line_height, '', 1, 1, 'L', True)

        # Čuvanje PDF-a
        path = os.path.join(project_folder, 'static', 'inventory_lists')
        os.makedirs(path, exist_ok=True)
        
        filename = f'inventory_room_list{"_with_quantities" if show_quantity else ""}.pdf'
        pdf.output(os.path.join(path, filename))

def popisne_liste_gen():
    """Placeholder za generisanje svih popisnih listi."""
    pass