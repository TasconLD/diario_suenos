import io
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models import cargar_datos

def generar_pdf_suenos(usuario_id, usuario_nombre):
    suenos_actuales = cargar_datos(usuario_id)
    total = len(suenos_actuales)
    lucidos = 0
    pesadillas = 0
    suma_calidad = 0
    
    for s in suenos_actuales:
        categorias_lista = [c.lower() for c in s.get('categorias', []) if c]
        if 'lucido' in categorias_lista:
            lucidos += 1
        if 'pesadilla' in categorias_lista:
            pesadillas += 1
        try:
            suma_calidad += int(s.get('calidad_sueno', 5))
        except (ValueError, TypeError):
            suma_calidad += 5
            
    promedio = round(suma_calidad / total, 1) if total > 0 else 0.0
    bonitos = max(0, total - (lucidos + pesadillas))

    img_buf = None
    if total > 0:
        labels = ['Bonitos', 'Lúcidos', 'Pesadillas']
        sizes = [bonitos, lucidos, pesadillas]
        colors = ['#4ade80', '#ffca28', '#ef5350']
        
        labels_filtrados = [l for i, l in enumerate(labels) if sizes[i] > 0]
        colors_filtrados = [c for i, c in enumerate(colors) if sizes[i] > 0]
        sizes_filtrados = [s for s in sizes if s > 0]

        fig, ax = plt.subplots(figsize=(3, 3))
        wedges, texts, autotexts = ax.pie(
            sizes_filtrados, 
            labels=labels_filtrados, 
            colors=colors_filtrados, 
            autopct='%1.0f%%', 
            startangle=90, 
            pctdistance=0.75,
            textprops={'fontsize': 9, 'color': '#1e293b', 'weight': 'bold'}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(8)

        centre_circle = plt.Circle((0,0), 0.55, fc='white')
        fig.gca().add_artist(centre_circle)
        ax.axis('equal')  
        plt.tight_layout()
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=200, transparent=True)
        img_buf.seek(0)
        plt.close(fig)

    class PDFDiary(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(59, 130, 246)
            self.cell(0, 10, f"REPORTE DE: {usuario_nombre.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
            self.set_font("Helvetica", "I", 10)
            self.set_text_color(100, 116, 139)
            self.cell(0, 5, "Historial completo de tu actividad onirica", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

    pdf = PDFDiary()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(15, 32, 180, 20, style="FD")
    
    pdf.set_y(35)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    
    pdf.cell(45, 5, f"Recuerdos: {total}", align="C")
    pdf.cell(45, 5, f"Lucidos: {lucidos}", align="C")
    pdf.cell(45, 5, f"Pesadillas: {pesadillas}", align="C")
    pdf.cell(45, 5, f"Descanso: {promedio}/5", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if img_buf:
        pdf.ln(5)
        pdf.image(img_buf, x=75, y=pdf.get_y(), w=60)
        pdf.set_y(pdf.get_y() + 65)  
    else:
        pdf.ln(12)
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "Registros Cronologicos", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    
    for s in suenos_actuales:
        categorias_orig = [c for c in s.get('categorias', []) if c]
        categories = [c.lower() for c in categorias_orig]
        
        if 'lucido' in categories:
            pdf.set_draw_color(255, 202, 40)
        elif 'pesadilla' in categories:
            pdf.set_draw_color(239, 83, 80)
        elif 'bonito' in categories:
            pdf.set_draw_color(74, 222, 128)
        else:
            pdf.set_draw_color(148, 163, 184)
            
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(59, 130, 246)
        fecha_txt = s.get('fecha', '')
        calidad_txt = f"Calidad: {s.get('calidad_sueno', 5)}/5"
        pdf.cell(0, 4, f"FECHA: {fecha_txt}   |   {calidad_txt}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        destacado_txt = " (Destacado)" if s.get('destacado') else ""
        pdf.cell(0, 6, f"{s.get('titulo', '')}{destacado_txt}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, f"Categorias: {', '.join(categorias_orig)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        descripcion_limpia = s.get('descripcion', '').encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, descripcion_limpia)
        
        pdf.set_draw_color(241, 245, 249)
        pdf.line(15, pdf.get_y() + 4, 195, pdf.get_y() + 4)
        pdf.ln(8)
        
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_output = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    if img_buf:
        img_buf.close()
        
    return pdf_output