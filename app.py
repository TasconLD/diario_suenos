from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import io
import os

app = Flask(__name__)

# 🔌 CONFIGURACIÓN DE CONEXIÓN A POSTGRESQL (Para el entorno local de Docker)
DB_CONFIG = {
    "dbname": "diario_suenos",
    "user": "usuario_diario",
    "password": "clave_secreta_123",
    "host": "localhost",
    "port": "5432"
}
# Reemplaza tu configuración de DB_CONFIG u obtener_conexion por algo como esto:
DATABASE_URL = os.environ.get('DATABASE_URL')

def obtener_conexion():
    if DATABASE_URL:
        # En Render (Producción) usará la URL larga de Neon
        return psycopg2.connect(DATABASE_URL)
    else:
        # En tu PC local (Desarrollo) usa los datos que tenías antes
        # Cambia esto por tus datos locales reales si los necesitas
        return psycopg2.connect(
            dbname="tu_bd_local",
            user="postgres",
            password="tu_password",
            host="localhost",
            port="5432"
        )

def inicializar_base_datos():
    """Crea la tabla en PostgreSQL si no existe al arrancar la aplicación."""
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suenos (
                    id BIGINT PRIMARY KEY,
                    titulo VARCHAR(255) NOT NULL,
                    descripcion TEXT NOT NULL,
                    fecha DATE NOT NULL,
                    calidad_sueno INTEGER DEFAULT 5,
                    destacado BOOLEAN DEFAULT FALSE,
                    categorias TEXT[] -- Permite guardar listas nativas de categorías
                );
            """)
            conn.commit()

# Inicializamos la base de datos automáticamente
inicializar_base_datos()

def obtener_estadisticas():
    """Calcula estadísticas directamente en PostgreSQL para optimizar rendimiento y memoria RAM."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # CORREGIDO: Se añade el filtro optimizado para contar la categoría 'bonito'
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COALESCE(COUNT(*) FILTER (WHERE 'pesadilla' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as pesadillas,
                    COALESCE(COUNT(*) FILTER (WHERE 'lucido' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as lucidos,
                    COALESCE(COUNT(*) FILTER (WHERE 'bonito' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as bonitos,
                    COALESCE(ROUND(AVG(calidad_sueno), 1), 0.0) as promedio
                FROM suenos;
            """)
            return cursor.fetchone()

def cargar_datos():
    """Trae todos los registros de la base de datos ordenados cronológicamente."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""SELECT * FROM suenos ORDER BY fecha DESC, id DESC;""")
            suenos = cursor.fetchall()
            
            # Transformamos las fechas a formato texto 'YYYY-MM-DD' para total compatibilidad con tu HTML
            for s in suenos:
                if s.get('fecha'):
                    s['fecha'] = s['fecha'].strftime('%Y-%m-%d')
            return suenos

@app.route('/')
def index():
    query = request.args.get('q', '').strip().lower()
    categoria_filtro = request.args.get('cat', '').strip().lower()
    
    # Cargamos estadísticas globales optimizadas desde PostgreSQL
    stats = obtener_estadisticas()
    
    # --- CONSULTA FILTRADA A POSTGRESQL ---
    condiciones = []
    parametros = []
    sql_query = """SELECT * FROM suenos"""
    
    # Filtro especial por botones de categorías
    if categoria_filtro:
        if categoria_filtro == 'destacado':
            condiciones.append("destacado = TRUE")
        else:
            condiciones.append("%s = ANY(SELECT LOWER(c) FROM unnest(categorias) c)")
            parametros.append(categoria_filtro)
            
    # Filtro por buscador de palabras clave
    if query:
        condiciones.append("(titulo ILIKE %s OR descripcion ILIKE %s)")
        parametros.extend([f"%{query}%", f"%{query}%"])
        
    if condiciones:
        sql_query += " WHERE " + " AND ".join(condiciones)
        
    sql_query += " ORDER BY fecha DESC, id DESC;"
    
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_query, parametros)
            suenos_filtrados = cursor.fetchall()
            
            for s in suenos_filtrados:
                if s.get('fecha'):
                    s['fecha'] = s['fecha'].strftime('%Y-%m-%d')
                    
    return render_template(
        'index.html', 
        suenos=suenos_filtrados, 
        query_busqueda=query, 
        categoria_actual=categoria_filtro,
        stats=stats
    )

@app.route('/registrar', methods=['POST'])
def registrar():
    id_sueno = int(time.time() * 1000)
    titulo = request.form.get('titulo')
    fecha = request.form.get('fecha')
    descripcion = request.form.get('descripcion')
    
    # Asegúrate de que esta línea esté limpia y bien indentada con 4 espacios
    categorias = request.form.getlist('categoria')
    if not categorias or categorias == ['']:
        categorias = ['General'] # Categoría por defecto si llega vacío
        
    calidad_sueno = int(request.form.get('calidad_sueno', 5))
    destacado = 'destacado' in request.form

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO suenos (id, titulo, fecha, descripcion, categorias, calidad_sueno, destacado)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (id_sueno, titulo, fecha, descripcion, categorias, calidad_sueno, destacado))
            conn.commit()
    
    return redirect(url_for('index'))

@app.route('/editar/<id_sueno>', methods=['POST'])
def editar(id_sueno):
    titulo = request.form.get('titulo')
    fecha = request.form.get('fecha')
    descripcion = request.form.get('descripcion')
    
    categorias = request.form.getlist('categoria')
    if not categorias or categorias == ['']:
        categorias = ['General']

    calidad_sueno = int(request.form.get('calidad_sueno', 5))
    destacado = 'destacado' in request.form

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE suenos 
                SET titulo = %s, fecha = %s, descripcion = %s, categorias = %s, calidad_sueno = %s, destacado = %s
                WHERE id = %s;
            """, (titulo, fecha, descripcion, categorias, calidad_sueno, destacado, int(id_sueno)))
            conn.commit()
            
    return redirect(url_for('index'))

@app.route('/eliminar/<id_sueno>')
def eliminar(id_sueno):
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""DELETE FROM suenos WHERE id = %s;""", (int(id_sueno),))
            conn.commit()
    
    return redirect(url_for('index'))

@app.route('/exportar')
def exportar():
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    import matplotlib
    matplotlib.use('Agg')  
    import matplotlib.pyplot as plt
    
    suenos_actuales = cargar_datos()
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
            self.cell(0, 10, "REPORTE: DIARIO DE SUEÑOS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
            
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
    
    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-disposition": "attachment; filename=Mi_Diario_de_Suenos.pdf"}
    )

@app.route('/sw.js')
def serve_sw():
    static_dir = os.path.join(app.root_path, 'static')
    filepath = os.path.join(static_dir, 'sw.js')
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
    else:
        return "Service Worker File Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)