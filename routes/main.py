import random
import time
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, Response, session, flash
from psycopg2.extras import RealDictCursor
from database import obtener_conexion
from models import obtener_estadisticas
from pdf_generator import generar_pdf_suenos

# BLOQUE: Inicialización del Blueprint principal
main_bp = Blueprint('main', __name__)

# BLOQUE: Ruta principal - listado de sueños con filtros y búsqueda
@main_bp.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']
    query = request.args.get('q', '').strip().lower()
    categoria_filtro = request.args.get('cat', '').strip().lower()
    emocion_filtro = request.args.get('emocion', '').strip() # <-- CAPTURA FILTRO EMOCIÓN
    
    stats = obtener_estadisticas(usuario_id)
    fecha_hoy = date.today().strftime('%Y-%m-%d')
    
    condiciones = ["usuario_id = %s"]
    parametros = [usuario_id]
    sql_query = """SELECT * FROM suenos"""
    
    # Manejo de filtros por categoría
    if categoria_filtro:
        if categoria_filtro == 'destacado':
            condiciones.append("destacado = TRUE")
        elif categoria_filtro == 'sin_fecha':
            condiciones.append("fecha IS NULL")
        else:
            condiciones.append("%s = ANY(SELECT LOWER(c) FROM unnest(categorias) c)")
            parametros.append(categoria_filtro)
    # SI NO HAY FILTROS ACTIVOS: Mantenemos la línea de tiempo limpia ocultando recuerdos sin fecha
    elif not emocion_filtro and not query:
        condiciones.append("fecha IS NOT NULL")

    # Manejo de filtro por emoción (FIX: Búsqueda flexible por coincidencia parcial para evitar discrepancias)
    if emocion_filtro:
        condiciones.append("TRIM(emocion) ILIKE %s")
        parametros.append(f"%{emocion_filtro}%")
            
    # Búsqueda por texto
    if query:
        condiciones.append("(titulo ILIKE %s OR descripcion ILIKE %s)")
        parametros.extend([f"%{query}%", f"%{query}%"])
        
    if condiciones:
        sql_query += " WHERE " + " AND ".join(condiciones)
        
    sql_query += " ORDER BY fecha DESC NULLS LAST, id DESC;"
    
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_query, parametros)
            suenos_filtrados = cursor.fetchall()
            
            for s in suenos_filtrados:
                if s.get('fecha'):
                    s['fecha'] = s['fecha'].strftime('%Y-%m-%d')
                else:
                    s['fecha'] = None

                if s.get('hora'):
                    s['hora_formateada'] = s['hora'].strftime('%I:%M %p')
                    s['hora'] = s['hora'].strftime('%H:%M')
                else:
                    s['hora_formateada'] = None
                    s['hora'] = ''
                    
    return render_template(
        'index.html', 
        suenos=suenos_filtrados, 
        query_busqueda=query, 
        categoria_actual=categoria_filtro,
        emocion_actual=emocion_filtro,
        stats=stats,
        usuario_nombre=session['usuario_nombre'],
        fecha_hoy=fecha_hoy
    )

# BLOQUE: Ruta para registrar un nuevo sueño
@main_bp.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    id_sueno = int(time.time() * 1000)
    titulo = request.form.get('titulo')
    
    sin_fecha = 'sin_fecha' in request.form
    fecha = None if sin_fecha else request.form.get('fecha')
    if fecha == '':
        fecha = None
        
    hora = request.form.get('hora')
    # Si no ingresó hora manualmente, asignamos automáticamente la hora actual del servidor
    if not hora or hora.strip() == '':
        hora = datetime.now().time().strftime('%H:%M:%S')

    descripcion = request.form.get('descripcion')
    
    categorias = request.form.getlist('categoria')
    if not categorias or categorias == ['']:
        categorias = ['General']
        
    emocion = request.form.get('emocion') # <-- CAPTURA DE EMOCIÓN
    if not emocion or emocion.strip() == '':
        emocion = None
    else:
        emocion = emocion.strip()

    # Procesar tags enviados desde el formulario (separados por coma)
    raw_tags = request.form.get('tags', '')
    tags = [t.strip().lower() for t in raw_tags.split(',') if t.strip()] if raw_tags else []

    calidad_sueno = int(request.form.get('calidad_sueno', 5))
    destacado = 'destacado' in request.form

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO suenos (id, titulo, fecha, hora, descripcion, categorias, emocion, calidad_sueno, destacado, usuario_id, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (id_sueno, titulo, fecha, hora, descripcion, categorias, emocion, calidad_sueno, destacado, session['usuario_id'], tags))
            conn.commit()
    
    return redirect(url_for('main.index'))

# BLOQUE: Ruta para editar un sueño existente
@main_bp.route('/editar/<id_sueno>', methods=['POST'])
def editar(id_sueno):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    titulo = request.form.get('titulo')
    
    sin_fecha = 'sin_fecha' in request.form
    fecha = None if sin_fecha else request.form.get('fecha')
    if fecha == '':
        fecha = None
        
    hora = request.form.get('hora')
    if not hora or hora.strip() == '':
        hora = None

    descripcion = request.form.get('descripcion')
    
    categorias = request.form.getlist('categoria')
    if not categorias or categorias == ['']:
        categorias = ['General']

    emocion = request.form.get('emocion') # <-- CAPTURA DE EMOCIÓN
    if not emocion or emocion.strip() == '':
        emocion = None

    # Procesar tags enviados desde el formulario de edición (separados por coma)
    raw_tags = request.form.get('tags', '')
    tags = [t.strip().lower() for t in raw_tags.split(',') if t.strip()] if raw_tags else []

    calidad_sueno = int(request.form.get('calidad_sueno', 5))
    destacado = 'destacado' in request.form

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE suenos 
                SET titulo = %s, fecha = %s, hora = %s, descripcion = %s, categorias = %s, emocion = %s, tags = %s, calidad_sueno = %s, destacado = %s
                WHERE id = %s AND usuario_id = %s;
            """, (titulo, fecha, hora, descripcion, categorias, emocion, tags, calidad_sueno, destacado, int(id_sueno), session['usuario_id']))
            conn.commit()
            
    return redirect(url_for('main.index'))

# BLOQUE: Ruta para eliminar un sueño
@main_bp.route('/eliminar/<id_sueno>')
def eliminar(id_sueno):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""DELETE FROM suenos WHERE id = %s AND usuario_id = %s;""", (int(id_sueno), session['usuario_id']))
            conn.commit()
    
    return redirect(url_for('main.index'))

# BLOQUE: Ruta para la sección independiente de Señales Oníricas
@main_bp.route('/senales')
def senales():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Obtener todas las etiquetas de los sueños con su conteo
            cursor.execute("""
                SELECT unnest(tags) AS tag_nombre, COUNT(*) AS total
                FROM suenos
                WHERE usuario_id = %s AND tags IS NOT NULL AND array_length(tags, 1) > 0
                GROUP BY tag_nombre
                ORDER BY total DESC;
            """, (usuario_id,))
            conteo_tags = {row[0]: row[1] for row in cursor.fetchall()}

            # 2. Obtener los significados/descripciones personales ya registradas
            cursor.execute("""
                SELECT tag, significado, categoria
                FROM senales_oniricas
                WHERE usuario_id = %s;
            """, (usuario_id,))
            info_senales = {row[0]: {'significado': row[1], 'categoria': row[2]} for row in cursor.fetchall()}

    # 3. Consolidar el diccionario de señales
    lista_senales = []
    # Incluimos los tags encontrados en sueños
    for tag_nombre, total in conteo_tags.items():
        detalle = info_senales.get(tag_nombre, {})
        lista_senales.append({
            'nombre': tag_nombre,
            'conteo': total,
            'significado': detalle.get('significado', ''),
            'categoria': detalle.get('categoria', 'General')
        })

    return render_template('senales.html', senales=lista_senales)

# BLOQUE: Ficha detallada de una señal onírica
@main_bp.route('/senales/<tag>')
def detalle_senal(tag):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']
    tag_clean = tag.strip().lower()

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Obtener la información/significado de la señal
            cursor.execute("""
                SELECT id, significado, categoria 
                FROM senales_oniricas 
                WHERE usuario_id = %s AND tag = %s;
            """, (usuario_id, tag_clean))
            registro = cursor.fetchone()

            # 2. Obtener los sueños asociados a este tag
            cursor.execute("""
                SELECT id, titulo, fecha, descripcion, categorias, emocion, calidad_sueno 
                FROM suenos 
                WHERE usuario_id = %s AND %s = ANY(tags)
                ORDER BY fecha DESC NULLS LAST, id DESC;
            """, (usuario_id, tag_clean))
            sueños_asociados = cursor.fetchall()

    info = {
        'tag': tag_clean,
        'significado': registro[1] if registro else '',
        'categoria': registro[2] if registro else 'Objeto',
        'conteo': len(sueños_asociados)
    }

    return render_template('ficha_senal.html', senal=info, suenos=sueños_asociados)


# BLOQUE: Guardar/Editar significado de una señal
@main_bp.route('/senales/guardar', methods=['POST'])
def guardar_senal():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']
    tag = request.form.get('tag', '').strip().lower()
    significado = request.form.get('significado', '').strip()
    categoria = request.form.get('categoria', 'Objeto')

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO senales_oniricas (usuario_id, tag, significado, categoria)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (usuario_id, tag) 
                DO UPDATE SET significado = EXCLUDED.significado, categoria = EXCLUDED.categoria;
            """, (usuario_id, tag, significado, categoria))
            conn.commit()

    # FIX BUG 2 (UX): Feedback explícito al usuario para saber que se guardó correctamente
    flash('¡Interpretación guardada con éxito!', 'exito')

    response = redirect(url_for('main.detalle_senal', tag=tag))
    
    # FIX BUG 3 (Caché Móvil / bfcache): Evita que el navegador del celular muestre una versión congelada
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# BLOQUE: Rutas para Objetivos / Metas Oníricas
@main_bp.route('/objetivos')
def objetivos():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM objetivos_oniricos
                WHERE usuario_id = %s
                ORDER BY 
                    CASE prioridad
                        WHEN 'Alta' THEN 1
                        WHEN 'Media' THEN 2
                        WHEN 'Baja' THEN 3
                        ELSE 4
                    END,
                    fecha_creacion DESC;
            """, (usuario_id,))
            lista_objetivos = cursor.fetchall()

            for obj in lista_objetivos:
                if obj.get('fecha_creacion'):
                    obj['fecha_creacion'] = obj['fecha_creacion'].strftime('%Y-%m-%d')

    return render_template('objetivos.html', objetivos=lista_objetivos)


@main_bp.route('/objetivos/crear', methods=['POST'])
def crear_objetivo():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']
    titulo = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    prioridad = request.form.get('prioridad', 'Media')
    categoria = request.form.get('categoria', 'Exploración')

    if not titulo:
        flash('El título del objetivo es obligatorio.', 'error')
        return redirect(url_for('main.objetivos'))

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO objetivos_oniricos (usuario_id, titulo, descripcion, prioridad, categoria)
                VALUES (%s, %s, %s, %s, %s);
            """, (usuario_id, titulo, descripcion, prioridad, categoria))
            conn.commit()

    flash('¡Objetivo creado con éxito! Mucha suerte en tus sueños.', 'exito')
    return redirect(url_for('main.objetivos'))


@main_bp.route('/objetivos/<int:objetivo_id>/cumplir', methods=['POST'])
def cumplir_objetivo(objetivo_id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE objetivos_oniricos
                SET veces_cumplido = veces_cumplido + 1
                WHERE id = %s AND usuario_id = %s;
            """, (objetivo_id, usuario_id))
            conn.commit()

    flash('🎉 ¡Enhorabuena! Has vuelto a cumplir esta meta onírica.', 'exito')
    return redirect(url_for('main.objetivos'))


@main_bp.route('/objetivos/<int:objetivo_id>/eliminar', methods=['POST'])
def eliminar_objetivo(objetivo_id):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']

    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM objetivos_oniricos
                WHERE id = %s AND usuario_id = %s;
            """, (objetivo_id, usuario_id))
            conn.commit()

    flash('Objetivo eliminado correctamente.', 'info')
    return redirect(url_for('main.objetivos'))


# BLOQUE: Eliminar registro de una señal
@main_bp.route('/senales/eliminar/<tag>', methods=['POST'])
def eliminar_senal(tag):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM senales_oniricas 
                WHERE usuario_id = %s AND tag = %s;
            """, (usuario_id, tag.strip().lower()))
            conn.commit()

    return redirect(url_for('main.senales'))

import random

# Datos locales para el Entrenador Onírico
TECNICAS_ONIRICAS = [
    {
        "id": "mild",
        "nombre": "MILD (Mnemonic Induction of Lucid Dreams)",
        "dificultad": "Principiante",
        "icono": "fa-brain",
        "resumen": "Inducción mnemónica repitiendo un mantra antes de dormir.",
        "pasos": [
            "Despiértate tras 4-5 horas de sueño y mantente despierto 15 minutos.",
            "Visualízate volviendo a tu último sueño, pero esta vez dándote cuenta de que estás soñando.",
            "Repite mentalmente: 'La próxima vez que esté soñando, recordaré que estoy soñando'.",
            "Mantiene esa intención firme mientras te vuelves a dormir."
        ]
    },
    {
        "id": "wild",
        "nombre": "WILD (Wake Initiated Lucid Dreams)",
        "dificultad": "Avanzado",
        "icono": "fa-bed",
        "resumen": "Pasar directamente del estado de vigilia al sueño lúcido sin perder la consciencia.",
        "pasos": [
            "Acuéstate completamente relajado tras 5 horas de sueño.",
            "Mantén la mente alerta mientras tu cuerpo entra en parálisis del sueño y relajación profunda.",
            "Observa las imágenes hipnagógicas (luces o formas tras los párpados) sin engancharte emocionalmente.",
            "Permite que la escena del sueño se forme a tu alrededor y entra en ella conscientemente."
        ]
    },
    {
        "id": "dild",
        "nombre": "DILD (Dream Initiated Lucid Dreams)",
        "dificultad": "Intermedio",
        "icono": "fa-wand-magic-sparkles",
        "resumen": "Volverse lúcido dentro del sueño al detectar una señal onírica o anomalía.",
        "pasos": [
            "Habitúa a tu mente durante el día a cuestionar la realidad (Pruebas de Realidad / Reality Checks).",
            "Cuando notes algo raro en tu sueño (una señal de tu lista), pregúntate: '¿Estoy soñando?'.",
            "Realiza una prueba física (mirar tus manos o intentar empujar un dedo a través de tu palma).",
            "Al confirmar que estás soñando, estabiliza el entorno frotando tus manos."
        ]
    }
]

CONSEJOS_DIARIOS = [
    "Mantén una libreta o esta app abierta al lado de tu cama. Al despertar, no te muevas durante 30 segundos y rememora las imágenes del sueño.",
    "Realiza al menos 5 'Pruebas de Realidad' al día: mira tu reloj, aparta la vista y vuelve a mirarlo. Si las horas cambian, estás soñando.",
    "Evita las pantallas 45 minutos antes de dormir para aumentar tus niveles de melatonina y la claridad de tu fase REM.",
    "Si te despiertas a medianoche, anota palabras clave de tus sueños antes de volver a dormirte para no perder los detalles al amanecer.",
    "La firmeza en la intención supera al esfuerzo físico: cree plenamente que hoy tendrás un sueño lúcido antes de cerrar los ojos."
]

CONSEJOS_HIGIENE = [
    {"id": "pantallas", "texto": "Sin pantallas 45 min antes de acostarte"},
    {"id": "horario", "texto": "Irte a dormir a la misma hora"},
    {"id": "oscuridad", "texto": "Habitación fresca, oscura y silenciosa"},
    {"id": "cafeina", "texto": "Cero cafeína 6 horas antes de dormir"},
    {"id": "meditacion", "texto": "5 minutos de respiración profunda en la cama"}
]


# BLOQUE: Rutas para el Entrenador Onírico
@main_bp.route('/entrenador')
def entrenador():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    # Seleccionar consejo del día basado en el día actual
    idx_consejo = random.Random().randint(0, len(CONSEJOS_DIARIOS) - 1)
    consejo_hoy = CONSEJOS_DIARIOS[idx_consejo]

    return render_template('entrenador.html', 
                           tecnicas=TECNICAS_ONIRICAS, 
                           consejo=consejo_hoy,
                           higienes=CONSEJOS_HIGIENE)

# BLOQUE: Ruta para exportar los sueños a PDF
@main_bp.route('/exportar')
def exportar():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    pdf_output = generar_pdf_suenos(session['usuario_id'], session['usuario_nombre'])
    
    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=Diario_{session['usuario_nombre']}.pdf"}
    )
    
    