import io
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models import cargar_datos, cargar_datos_filtrados, obtener_estadisticas
from database import obtener_conexion
from psycopg2.extras import RealDictCursor

# BLOQUE: Generación del PDF básico (reporte plano de todos los sueños)
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


# BLOQUE: Colores e íconos por categoría (compartido por el PDF formateado)
COLORES_CATEGORIA = {
    'lucido': (255, 202, 40),
    'pesadilla': (239, 83, 80),
    'bonito': (74, 222, 128),
    'falso despertar': (99, 102, 241),
    'falsodespertar': (99, 102, 241),
    'salida astral': (168, 85, 247),
    'salidaastral': (168, 85, 247),
}
COLOR_CATEGORIA_DEFECTO = (148, 163, 184)


def _limpiar_texto(texto):
    """Convierte texto a latin-1 reemplazando caracteres no soportados por fpdf2 clásico."""
    if not texto:
        return ""
    return str(texto).encode('latin-1', 'replace').decode('latin-1')


def _generar_grafica_dona(conteos):
    """
    Genera la imagen de la gráfica de dona a partir de un diccionario
    {etiqueta: cantidad}, omitiendo las categorías en cero. Devuelve un
    BytesIO con el PNG, o None si no hay datos.
    """
    labels = [k for k, v in conteos.items() if v > 0]
    sizes = [v for v in conteos.values() if v > 0]
    if not sizes:
        return None

    paleta = {
        'Bonitos': '#4ade80',
        'Lúcidos': '#ffca28',
        'Pesadillas': '#ef5350',
        'Falso Despertar': '#6366f1',
        'Salida Astral': '#a855f7',
    }
    colors = [paleta.get(l, '#94a3b8') for l in labels]

    fig, ax = plt.subplots(figsize=(3, 3))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.0f%%',
        startangle=90,
        pctdistance=0.75,
        textprops={'fontsize': 8, 'color': '#1e293b', 'weight': 'bold'}
    )
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(8)

    centre_circle = plt.Circle((0, 0), 0.55, fc='white')
    fig.gca().add_artist(centre_circle)
    ax.axis('equal')
    plt.tight_layout()

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=200, transparent=True)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf


# BLOQUE: Generación del PDF formateado tipo libro/diario con filtros
def generar_pdf_diario_formateado(usuario_id, usuario_nombre, fecha_inicio=None, fecha_fin=None, categorias_filtro=None):
    """
    Genera un PDF con diseño de libro/diario: portada con resumen y
    gráfica, y una página dedicada por cada sueño (en vez del reporte
    compacto de generar_pdf_suenos). Admite filtros opcionales por
    rango de fechas y por categorías.
    """
    suenos = cargar_datos_filtrados(
        usuario_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        categorias_filtro=categorias_filtro
    )
    total = len(suenos)

    # Conteo de las 5 categorías reales para la gráfica de la portada
    conteos = {'Bonitos': 0, 'Lúcidos': 0, 'Pesadillas': 0, 'Falso Despertar': 0, 'Salida Astral': 0}
    suma_calidad = 0
    for s in suenos:
        cats = [c.lower() for c in s.get('categorias', []) if c]
        if 'lucido' in cats:
            conteos['Lúcidos'] += 1
        if 'pesadilla' in cats:
            conteos['Pesadillas'] += 1
        if 'bonito' in cats:
            conteos['Bonitos'] += 1
        if 'falso despertar' in cats or 'falsodespertar' in cats:
            conteos['Falso Despertar'] += 1
        if 'salida astral' in cats or 'salidaastral' in cats:
            conteos['Salida Astral'] += 1
        try:
            suma_calidad += int(s.get('calidad_sueno', 5))
        except (ValueError, TypeError):
            suma_calidad += 5

    promedio = round(suma_calidad / total, 1) if total > 0 else 0.0
    img_buf = _generar_grafica_dona(conteos)

    class PDFLibro(FPDF):
        def footer(self):
            if self.page_no() == 1:
                return  # sin numeración en la portada
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            self.cell(0, 10, f"Pagina {self.page_no() - 1}", align="C")

    pdf = PDFLibro()
    pdf.set_margins(20, 20, 20)

    # --- Portada ---
    pdf.add_page()
    pdf.set_y(70)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 14, "Diario de Suenos", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 10, _limpiar_texto(usuario_nombre), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    if fecha_inicio or fecha_fin:
        rango_txt = f"Del {fecha_inicio or 'inicio'} al {fecha_fin or 'hoy'}"
    else:
        rango_txt = "Historial completo"
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, rango_txt, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if categorias_filtro:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, f"Categorias: {_limpiar_texto(', '.join(categorias_filtro))}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 6, f"{total} recuerdos  |  Descanso promedio: {promedio}/5", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if img_buf:
        y_imagen = pdf.get_y() + 8
        pdf.image(img_buf, x=65, y=y_imagen, w=80)
        pdf.set_y(y_imagen + 80 + 10)
    else:
        pdf.ln(15)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Generado el {datetime.now().strftime('%d/%m/%Y')}", align="C")

    # --- Una página por cada sueño, estilo entrada de diario ---
    for s in suenos:
        pdf.add_page()

        categorias_orig = [c for c in s.get('categorias', []) if c]
        cats_lower = [c.lower() for c in categorias_orig]
        color_cat = COLOR_CATEGORIA_DEFECTO
        for cat in cats_lower:
            if cat in COLORES_CATEGORIA:
                color_cat = COLORES_CATEGORIA[cat]
                break

        # Franja de color decorativa en la parte superior (efecto "cinta de libro")
        pdf.set_fill_color(*color_cat)
        pdf.rect(0, 0, 210, 6, style="F")

        pdf.set_y(20)
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*color_cat)
        fecha_txt = s.get('fecha') or 'Recuerdo antiguo'
        hora_txt = f"  -  {s['hora_formateada']}" if s.get('hora_formateada') else ""
        pdf.cell(0, 8, _limpiar_texto(f"{fecha_txt}{hora_txt}"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(15, 23, 42)
        destacado_txt = "  *" if s.get('destacado') else ""
        pdf.multi_cell(0, 10, _limpiar_texto(f"{s.get('titulo', '')}{destacado_txt}"), align="C")

        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        etiquetas_extra = []
        if categorias_orig:
            etiquetas_extra.append(', '.join(categorias_orig))
        if s.get('emocion'):
            etiquetas_extra.append(f"Emocion: {s['emocion']}")
        etiquetas_extra.append(f"Calidad: {s.get('calidad_sueno', 5)}/5")
        pdf.cell(0, 6, _limpiar_texto("  |  ".join(etiquetas_extra)), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if s.get('tags'):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(129, 140, 248)
            tags_txt = '  '.join(f"#{t}" for t in s['tags'])
            pdf.cell(0, 6, _limpiar_texto(tags_txt), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(10)
        pdf.set_draw_color(226, 232, 240)
        pdf.line(40, pdf.get_y(), 170, pdf.get_y())
        pdf.ln(10)

        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 7, _limpiar_texto(s.get('descripcion', '')))

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_output = pdf_buffer.getvalue()
    pdf_buffer.close()

    if img_buf:
        img_buf.close()

    return pdf_output

# BLOQUE: Generación de PDF de Reporte de Estadísticas Generales
def generar_pdf_estadisticas(usuario_id, usuario_nombre):
    """
    Genera un PDF con el resumen ejecutivo de estadísticas del usuario:
    métricas clave y distribución de emociones.
    """
    stats = obtener_estadisticas(usuario_id) or {}
    total = stats.get('total', 0)
    
    # Mapeo de emociones desde el query de models.py
    conteos_emociones = {
        'Alegría': stats.get('emocion_alegria', 0),
        'Tristeza': stats.get('emocion_tristeza', 0),
        'Miedo': stats.get('emocion_miedo', 0),
        'Confusión': stats.get('emocion_confusion', 0),
        'Neutro': stats.get('emocion_neutro', 0)
    }
    
    img_buf_emociones = _generar_grafica_dona(conteos_emociones) if sum(conteos_emociones.values()) > 0 else None

    class PDFStats(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    pdf = PDFStats()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Cabecera / Título
    pdf.set_y(20)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 12, "Reporte de Estadísticas Oníricas", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, _limpiar_texto(usuario_nombre), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Métricas Clave
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Métricas Generales", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    
    col_w = 85
    pdf.cell(col_w, 8, _limpiar_texto(f"• Total de Sueños Registrados: {total}"), ln=0)
    pdf.cell(col_w, 8, _limpiar_texto(f"• Sueños Lúcidos: {stats.get('lucidos', 0)}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(col_w, 8, _limpiar_texto(f"• Pesadillas: {stats.get('pesadillas', 0)}"), ln=0)
    pdf.cell(col_w, 8, _limpiar_texto(f"• Calidad Promedio: {stats.get('promedio', 0.0)}/5"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)

    # Gráfica de Emociones
    if img_buf_emociones:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "Distribución Emocional", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        y_grafica = pdf.get_y() + 4
        pdf.image(img_buf_emociones, x=65, y=y_grafica, w=80)
        pdf.set_y(y_grafica + 85)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_output = pdf_buffer.getvalue()
    pdf_buffer.close()

    if img_buf_emociones:
        img_buf_emociones.close()

    return pdf_output


# BLOQUE: Generación de PDF de Reporte de Señales Oníricas
def generar_pdf_senales(usuario_id, usuario_nombre):
    """
    Genera un PDF con el inventario de Señales Oníricas del usuario.
    """
    senales = []
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM senales_oniricas 
                WHERE usuario_id = %s 
                ORDER BY frecuencia DESC, nombre ASC;
            """, (usuario_id,))
            senales = cursor.fetchall()

    class PDFSenales(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    pdf = PDFSenales()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Encabezado
    pdf.set_y(20)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 12, "Catálogo de Señales Oníricas", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, _limpiar_texto(usuario_nombre), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Total de señales registradas: {len(senales)}  |  Generado el {datetime.now().strftime('%d/%m/%Y')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    if not senales:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 10, "No se encontraron señales oníricas registradas aún.", align="C")
    else:
        for s in senales:
            if pdf.get_y() > 240:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 8, _limpiar_texto(f"• {s.get('nombre', 'Sin Nombre')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(99, 102, 241)
            frecuencia = s.get('frecuencia', 1)
            cat_txt = s.get('categoria', 'General')
            pdf.cell(0, 5, _limpiar_texto(f"Categoría: {cat_txt}  |  Apariciones: {frecuencia} veces"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            if s.get('significado'):
                pdf.ln(2)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(51, 65, 85)
                pdf.multi_cell(0, 6, _limpiar_texto(f"Significado Personal: {s.get('significado')}"))

            pdf.ln(4)
            pdf.set_draw_color(241, 245, 249)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(6)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_output = pdf_buffer.getvalue()
    pdf_buffer.close()

    return pdf_output

# BLOQUE: Generación de PDF de Reporte de Señales Oníricas
def generar_pdf_senales(usuario_id, usuario_nombre):
    """
    Genera un PDF con el inventario completo de Señales Oníricas consolidadas
    a partir de los tags de los sueños y sus significados registrados.
    """
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Conteo de apariciones de cada tag
            cursor.execute("""
                SELECT unnest(tags) AS tag_nombre, COUNT(*) AS total
                FROM suenos
                WHERE usuario_id = %s AND tags IS NOT NULL AND array_length(tags, 1) > 0
                GROUP BY tag_nombre
                ORDER BY total DESC;
            """, (usuario_id,))
            conteo_tags = {row[0]: row[1] for row in cursor.fetchall()}

            # 2. Obtener significados y categorías registradas
            cursor.execute("""
                SELECT tag, significado, categoria
                FROM senales_oniricas
                WHERE usuario_id = %s;
            """, (usuario_id,))
            info_senales = {row[0]: {'significado': row[1], 'categoria': row[2]} for row in cursor.fetchall()}

    # 3. Consolidar lista de señales
    senales = []
    for tag_nombre, total in conteo_tags.items():
        detalle = info_senales.get(tag_nombre, {})
        senales.append({
            'nombre': tag_nombre,
            'frecuencia': total,
            'significado': detalle.get('significado', ''),
            'categoria': detalle.get('categoria', 'General')
        })

    class PDFSenales(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(148, 163, 184)
            self.cell(0, 10, f"Página {self.page_no()}", align="C")

    pdf = PDFSenales()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    # Encabezado
    pdf.set_y(20)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 12, "Catálogo de Señales Oníricas", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, _limpiar_texto(usuario_nombre), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, f"Total de señales encontradas: {len(senales)}  |  Generado el {datetime.now().strftime('%d/%m/%Y')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(8)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Listado de Señales
    if not senales:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 10, "No se encontraron señales oníricas registradas aún.", align="C")
    else:
        for s in senales:
            if pdf.get_y() > 240:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 8, _limpiar_texto(f"• #{s['nombre']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(99, 102, 241)
            pdf.cell(0, 5, _limpiar_texto(f"Categoría: {s['categoria']}  |  Apariciones: {s['frecuencia']} veces"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            if s['significado']:
                pdf.ln(2)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(51, 65, 85)
                pdf.multi_cell(0, 6, _limpiar_texto(f"Significado Personal: {s['significado']}"))

            pdf.ln(4)
            pdf.set_draw_color(241, 245, 249)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(6)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_output = pdf_buffer.getvalue()
    pdf_buffer.close()

    return pdf_output