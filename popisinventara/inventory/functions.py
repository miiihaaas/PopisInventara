from datetime import datetime
import os
from fpdf import FPDF
from popisinventara.models import Room, Inventory

current_file_path = os.path.abspath(__file__)
project_folder = os.path.dirname(os.path.dirname((current_file_path)))
font_path = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed.ttf')
font_path_B = os.path.join(project_folder, 'static', 'fonts', 'DejaVuSansCondensed-Bold.ttf')


def popisna_lista_gen(inventory_item_list_data, room, inventory_id, school):
    print(f'pokrenuta je funkcija popisna_lista_gen: {inventory_item_list_data=}')
    room_name = f'{Room.query.get_or_404(room.id).room_building.name} - ({Room.query.get_or_404(room.id).name}) {Room.query.get_or_404(room.id).dynamic_name}'
    room_id = room.id
    inventory = Inventory.query.get_or_404(inventory_id)
    i = 0
    while i < 2:
        class PDF(FPDF): #! sa količinam
            def __init__(self, **kwargs):
                super(PDF, self).__init__(**kwargs)
                self.add_font('DejaVuSansCondensed', '', font_path, uni=True)
                self.add_font('DejaVuSansCondensed', 'B', font_path_B, uni=True)
            # def set_landscape(self):
            #     self.set_display_mode('L')
            def header(self):
                self.set_font('DejaVuSansCondensed', 'B', 12)
                self.cell(135, 7, f'Datum: {datetime.now().strftime("%d.%m.%Y.")}', new_y='LAST', align='L', border=0)
                self.cell(135, 7, f'{school.schoolname}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
                self.cell(135, 7, f'Popisna lista: {room_id}', new_y='LAST', align='L', border=0)
                self.cell(135, 7, f'{school.address}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
                self.cell(135, 7, f'Prostorija: {room_name}', new_y='LAST', align='L', border=0)
                self.cell(135, 7, f'{school.city}', new_x='LMARGIN', new_y='NEXT', align='R', border=0)
                self.set_font('DejaVuSansCondensed', 'B', 16)
                self.cell(270, 10, f'Popis stavki', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
                self.cell(190, 10, f'', new_x='LMARGIN', new_y='NEXT', align='C', border=0)
                self.set_font('DejaVuSansCondensed', 'B', 10)
                self.set_fill_color(200, 200, 200)
                self.cell(10, 5, 'ID', new_y='LAST', align='C', border=1, fill=True)
                self.cell(10, 5, 'Ser', new_y='LAST', align='C', border=1, fill=True)
                self.cell(80, 5, 'Tip predmeta', new_y='LAST', align='C', border=1, fill=True)
                self.cell(80, 5, 'Naziv predmeta', new_y='LAST', align='C', border=1, fill=True)
                if i == 0:
                    self.cell(15, 5, 'Kol', new_y='LAST', align='C', border=1, fill=True)
                self.cell(15, 5, 'Pop kol', new_y='LAST', align='C', border=1, fill=True)
                self.cell(60, 5, 'Komentar', new_y='NEXT', new_x='LMARGIN', align='C', border=1, fill=True)
            def footer(self):
                self.set_y(-45)
                self.set_font('DejaVuSansCondensed', '', 8)
                self.cell(0, 7, f'Član popisne komisije: ________________________________________', new_y='NEXT', new_x='LMARGIN', align='R')
                self.cell(0, 7, f'Član popisne komisije: ________________________________________', new_y='NEXT', new_x='LMARGIN', align='R')
                self.cell(0, 7, f'Član popisne komisije: ________________________________________', new_y='NEXT', new_x='LMARGIN', align='R')
                
        pdf = PDF(orientation='L')
        pdf.add_page()
        # pdf.set_landscape()
        pdf.set_font('DejaVuSansCondensed', '', 10)
        pdf.set_fill_color(255, 255, 255)
        for item in inventory_item_list_data:
            pdf.cell(10, 5, f"{item['item_id']}", new_y='LAST', align='C', border=1, fill=True)
            pdf.cell(10, 5, f"{item['serial']}", new_y='LAST', align='C', border=1, fill=True)
            pdf.cell(80, 5, f"{item['item_name']}", new_y='LAST', align='L', border=1, fill=True)
            pdf.cell(80, 5, f"{item['name']}", new_y='LAST', align='L', border=1, fill=True)
            if i == 0:
                pdf.cell(15, 5, f"{item['quantity']}", new_y='LAST', align='C', border=1, fill=True)
                
            if inventory.status == 'active':
                pdf.cell(15, 5, f"", new_y='LAST', align='C', border=1, fill=True)
            else:
                pdf.cell(15, 5, f"{item['quantity_input']}", new_y='LAST', align='C', border=1, fill=True)
            pdf.cell(60, 5, f"{item['comment']}", new_y='NEXT', new_x='LMARGIN', align='L', border=1, fill=True)
        
        path = f"{project_folder}/static/inventory_lists/"
        path = os.path.join(project_folder, 'static', 'inventory_lists')
        if not os.path.exists(path):
            os.makedirs(path)
        if i == 0:
            file_name = f'inventory_room_list.pdf'
        else:
            file_name = f'inventory_room_list_no_quantity.pdf'
        pdf.output(os.path.join(path, file_name))
        i += 1


def popisne_liste_gen():
    pass