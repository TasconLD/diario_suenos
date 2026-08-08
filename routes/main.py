import random
import re
from collections import Counter
import time
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, Response, session, flash, jsonify
from psycopg2.extras import RealDictCursor
from database import obtener_conexion
from models import obtener_estadisticas
import json
import os
from pdf_generator import generar_pdf_suenos, generar_pdf_diario_formateado, generar_pdf_estadisticas, generar_pdf_senales
from datetime import date, datetime, time
from io import BytesIO
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# BLOQUE: Inicialización del Blueprint principal
main_bp = Blueprint('main', __name__)

# Lista de palabras a ignorar (stopwords en español)
STOPWORDS_ES = {
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 
    'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 
    'porque', 'esta', 'son', 'entre', 'está', 'cuando', 'muy', 'sin', 'sobre', 'también', 'me', 
    'hasta', 'hay', 'donde', 'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 
    'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'antes', 'algunos', 
    'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 
    'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas', 'algo', 'nosotros', 
    'mi', 'mis', 'tus', 'tu', 'fui', 'iba', 'estaba', 'había', 'tenía', 'ver', 'vía', 'dijo', 'sueño',
    'estoy', 'era', 'luego', 'casa', 'escena', 'entonces', 'ahi', 'lugar', 'mama', 'ahí','mamá', 'creo',
    'recuerdo', 'cosas', 'cuenta', 'momento', 'digo', 'tipo', 'dice', 'fue', 'personas', 'vez', 'dos',
    'decía', 'voy', 'así', 'habitación','algún', 'vida', 'veo', 'puedo', 'soñe', 'dentro', 'soñando',
    'veia','veía', 'dije','unas', 'lado','ser', 'parte', 'podía', 'tengo','tiene', 'llega','estamos',
    'doy', 'solo', 'hacer', 'hace', 'siempre', 

}

# BLOQUE: Ruta principal - listado de sueños con filtros y búsqueda
@main_bp.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']
    query = request.args.get('q', '').strip().lower()
    categoria_filtro = request.args.get('cat', '').strip().lower()
    emocion_filtro = request.args.get('emocion', '').strip()
    
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
    # SI NO HAY FILTROS ACTIVOS: Ocultamos recuerdos sin fecha
    elif not emocion_filtro and not query:
        condiciones.append("fecha IS NOT NULL")

    # Manejo de filtro por emoción
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
            # 0. Obtener datos del usuario (necesario para verificar google_id en el modal de cuenta)
            cursor.execute("SELECT id, usuario, email, google_id FROM usuarios WHERE id = %s;", (usuario_id,))
            usuario_actual = cursor.fetchone()

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

            # --- MÉTRICAS Y ESTADÍSTICAS AVANZADAS ---
            total_recuerdos = stats.get('total', 0) if isinstance(stats, dict) else 0
            lucidos = stats.get('lucidos', 0) if isinstance(stats, dict) else 0
            pesadillas = stats.get('pesadillas', 0) if isinstance(stats, dict) else 0
            salida_astral = stats.get('salidas_astrales', 0) if isinstance(stats, dict) else 0

            pct_lucidos = round((lucidos / total_recuerdos * 100), 1) if total_recuerdos > 0 else 0
            pct_pesadillas = round((pesadillas / total_recuerdos * 100), 1) if total_recuerdos > 0 else 0
            pct_astral = round((salida_astral / total_recuerdos * 100), 1) if total_recuerdos > 0 else 0

            # 1. Top 3 Señales / Tags
            cursor.execute("""
                SELECT 
                    TRIM(LOWER(tag)) as tag, 
                    COUNT(*) as uso_count
                FROM suenos, 
                     UNNEST(tags) AS tag
                WHERE usuario_id = %s 
                  AND TRIM(tag) != ''
                GROUP BY TRIM(LOWER(tag))
                ORDER BY uso_count DESC, tag ASC
                LIMIT 3;
            """, (usuario_id,))
            top_senales = cursor.fetchall() or []

            # 2. Top Emociones más repetidas
            cursor.execute("""
                SELECT 
                    TRIM(LOWER(emocion)) as emocion, 
                    COUNT(*) as cantidad
                FROM suenos
                WHERE usuario_id = %s 
                  AND emocion IS NOT NULL 
                  AND TRIM(emocion) != ''
                GROUP BY TRIM(LOWER(emocion))
                ORDER BY cantidad DESC
                LIMIT 3;
            """, (usuario_id,))
            top_emociones = cursor.fetchall() or []

            # 3. Top Palabras clave más frecuentes en descripciones
            cursor.execute("""
                SELECT descripcion 
                FROM suenos 
                WHERE usuario_id = %s AND descripcion IS NOT NULL AND TRIM(descripcion) != '';
            """, (usuario_id,))
            filas_desc = cursor.fetchall() or []
            
            palabras_conteo = Counter()
            for f in filas_desc:
                texto = f['descripcion'].lower()
                # Extrae palabras alfanuméricas de más de 2 caracteres
                palabras = re.findall(r'\b[a-záéíóúñ]{3,}\b', texto)
                for p in palabras:
                    if p not in STOPWORDS_ES:
                        palabras_conteo[p] += 1
                        
            top_palabras = [{'palabra': p, 'cantidad': c} for p, c in palabras_conteo.most_common(5)]

            # 4. Tendencia mensual
            cursor.execute("""
                SELECT mes, cantidad
                    FROM (
                SELECT 
                    TO_CHAR(fecha, 'YYYY-MM') as mes, 
                    COUNT(*) as cantidad
                FROM suenos
                WHERE usuario_id = %s AND fecha IS NOT NULL
                GROUP BY TO_CHAR(fecha, 'YYYY-MM')
                ORDER BY mes DESC
                LIMIT 12
                ) sub
                ORDER BY mes ASC;
            """, (usuario_id,))
            tendencia_mensual = cursor.fetchall() or []

    return render_template(
        'index.html', 
        suenos=suenos_filtrados, 
        query_busqueda=query, 
        categoria_actual=categoria_filtro,
        emocion_actual=emocion_filtro,
        stats=stats or {},
        usuario=usuario_actual,
        usuario_nombre=session.get('usuario_nombre', 'Usuario'),
        fecha_hoy=fecha_hoy,
        pct_lucidos=pct_lucidos,
        pct_pesadillas=pct_pesadillas,
        pct_astral=pct_astral,
        top_senales=top_senales,
        top_emociones=top_emociones,
        top_palabras=top_palabras,
        tendencia_mensual=tendencia_mensual
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
    

#BLOQUE: Rutas para el Mapa Onírico

# RUTA 1: Renderiza la vista independiente con la pestaña
@main_bp.route('/mapa')
def vista_mapa():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('mapa.html')

# RUTA 2: API que envía los datos del grafo en JSON (Llamada por el mapa.html)
@main_bp.route('/api/mapa-onirico')
def mapa_onirico():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
        
    usuario_id = session['usuario_id']
    nodos = []
    enlaces = []
    nodos_existentes = set()

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, titulo, emocion, tags 
                FROM suenos 
                WHERE usuario_id = %s;
            """, (usuario_id,))
            suenos = cursor.fetchall() or []

            for s in suenos:
                s_id = f"sueño_{s['id']}"
                
                # Nodo del Sueño
                if s_id not in nodos_existentes:
                    nodos.append({
                        'id': s_id,
                        'label': s['titulo'] or f"Sueño #{s['id']}",
                        'group': 'sueno',
                        'shape': 'dot',
                        'size': 18
                    })
                    nodos_existentes.add(s_id)
                
                # Nodos de Emoción
                if s.get('emocion') and s['emocion'].strip():
                    em_id = f"emocion_{s['emocion'].strip().lower()}"
                    if em_id not in nodos_existentes:
                        nodos.append({
                            'id': em_id,
                            'label': s['emocion'].capitalize(),
                            'group': 'emocion',
                            'shape': 'diamond',
                            'size': 14
                        })
                        nodos_existentes.add(em_id)
                    enlaces.append({'from': s_id, 'to': em_id})

                # Nodos de Tags
                if s.get('tags') and isinstance(s['tags'], list):
                    for tag in s['tags']:
                        tag_clean = tag.strip().lower()
                        if not tag_clean:
                            continue
                        tag_id = f"tag_{tag_clean}"
                        if tag_id not in nodos_existentes:
                            nodos.append({
                                'id': tag_id,
                                'label': f"#{tag_clean}",
                                'group': 'tag',
                                'shape': 'ellipse',
                                'size': 12
                            })
                            nodos_existentes.add(tag_id)
                        enlaces.append({'from': s_id, 'to': tag_id})

    return jsonify({'nodes': nodos, 'edges': enlaces})


# BLOQUE: Recordatorios, Notificaciones y Reality Checks (PWA / Offline)
@main_bp.route('/recordatorios')
def vista_recordatorios():
    """Renders the notifications and reality checks settings page."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('recordatorios.html')

#BLOQUE: Ruta del Totem Personal (HTML y API)
@main_bp.route('/totem')
def totem():
    """Ruta para renderizar la vista de configuración del tótem."""
    return render_template('totem.html')

@main_bp.route('/api/totem', methods=['GET', 'POST'])
def api_totem():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'error': 'No autorizado'}), 401

    conn = obtener_conexion()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'GET':
        cur.execute("SELECT * FROM totems WHERE usuario_id = %s", (usuario_id,))
        totem = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({'totem': totem})

    if request.method == 'POST':
        data = request.json or {}
        nombre = data.get('nombre', 'Mi Tótem')
        tipo = data.get('tipo', 'frase')
        frase = data.get('frase', '')
        sonido = data.get('sonido', '')
        vibracion = data.get('vibracion', '')
        imagen = data.get('imagen', '')

        # Insertar o actualizar si ya existe
        query = """
            INSERT INTO totems (usuario_id, nombre, tipo, frase, sonido, vibracion, imagen, fecha_actualizacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (usuario_id) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                tipo = EXCLUDED.tipo,
                frase = EXCLUDED.frase,
                sonido = EXCLUDED.sonido,
                vibracion = EXCLUDED.vibracion,
                imagen = EXCLUDED.imagen,
                fecha_actualizacion = NOW();
        """
        cur.execute(query, (usuario_id, nombre, tipo, frase, sonido, vibracion, imagen))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'success': True, 'mensaje': 'Tótem guardado correctamente en Neon DB'})
    
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
    
# BLOQUE: Ruta para exportar el diario personalizado (formato libro con filtros)
@main_bp.route('/exportar/personalizado')
def exportar_personalizado():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    fecha_inicio = request.args.get('fecha_inicio', '').strip() or None
    fecha_fin = request.args.get('fecha_fin', '').strip() or None
    categorias_filtro = request.args.getlist('categoria') or None

    pdf_output = generar_pdf_diario_formateado(
        session['usuario_id'],
        session['usuario_nombre'],
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        categorias_filtro=categorias_filtro
    )

    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=Diario_Personalizado_{session['usuario_nombre']}.pdf"}
    )   

# BLOQUE: Ruta para exportar reporte de estadísticas generales a PDF
@main_bp.route('/exportar/estadisticas')
def exportar_estadisticas_pdf():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    pdf_output = generar_pdf_estadisticas(
        session['usuario_id'],
        session['usuario_nombre']
    )

    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=Reporte_Estadisticas_{session['usuario_nombre']}.pdf"}
    )


# BLOQUE: Ruta para exportar reporte de señales oníricas a PDF
@main_bp.route('/exportar/senales')
def exportar_senales_pdf():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    pdf_output = generar_pdf_senales(
        session['usuario_id'],
        session['usuario_nombre']
    )

    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=Reporte_Senales_Oniricas_{session['usuario_nombre']}.pdf"}
    )
    
# BLOQUE: Exportación / Importación Manual de Base de Datos (JSON)
def serializador_json(obj):
    """Soporte para convertir objetos date, datetime y time a formato legible en JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    raise TypeError(f"Tipo {type(obj)} no es serializable en JSON")

@main_bp.route('/backup/exportar')
def backup_exportar():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']

    try:
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. Exportar Sueños
                cursor.execute("SELECT * FROM suenos WHERE usuario_id = %s ORDER BY id ASC;", (usuario_id,))
                suenos = cursor.fetchall() or []

                # 2. Exportar Señales Oníricas
                cursor.execute("SELECT * FROM senales_oniricas WHERE usuario_id = %s ORDER BY id ASC;", (usuario_id,))
                senales = cursor.fetchall() or []

                # 3. Exportar Objetivos Oníricos
                cursor.execute("SELECT * FROM objetivos_oniricos WHERE usuario_id = %s ORDER BY id ASC;", (usuario_id,))
                objetivos = cursor.fetchall() or []

                # 4. Exportar Higiene de Sueño Logs
                cursor.execute("SELECT * FROM higiene_sueno_logs WHERE usuario_id = %s ORDER BY id ASC;", (usuario_id,))
                higiene = cursor.fetchall() or []

                # 5. Exportar Tótemps
                cursor.execute("SELECT * FROM totems WHERE usuario_id = %s ORDER BY id ASC;", (usuario_id,))
                totems = cursor.fetchall() or []

        data_backup = {
            "version": "1.0",
            "fecha_backup": datetime.now().isoformat(),
            "usuario": session.get('usuario_nombre', 'Usuario'),
            "suenos": suenos,
            "senales_oniricas": senales,
            "objetivos_oniricos": objetivos,
            "higiene_sueno_logs": higiene,
            "totems": totems
        }

        json_str = json.dumps(data_backup, default=serializador_json, ensure_ascii=False, indent=2)
        filename = f"backup_diario_suenos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"Error al exportar respaldo: {e}")
        flash("Ocurrió un error al generar la copia de seguridad.", "error")
        return redirect(request.referrer or url_for('main.index'))


@main_bp.route('/backup/importar', methods=['POST'])
def backup_importar():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']

    if 'backup_file' not in request.files:
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(request.referrer or url_for('main.index'))

    file = request.files['backup_file']
    if file.filename == '':
        flash("Nombre de archivo no válido.", "error")
        return redirect(request.referrer or url_for('main.index'))

    try:
        data = json.load(file)
    except Exception as e:
        flash("El archivo subido no es un JSON válido.", "error")
        return redirect(request.referrer or url_for('main.index'))

    suenos = data.get('suenos', [])
    senales = data.get('senales_oniricas') or data.get('senales', [])
    objetivos = data.get('objetivos_oniricos') or data.get('objetivos', [])
    higiene = data.get('higiene_sueno_logs', [])
    totems = data.get('totems', [])

    insertados = 0

    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                # 1. Importar Sueños
                for s in suenos:
                    cursor.execute("""
                        INSERT INTO suenos (usuario_id, titulo, descripcion, fecha, hora, calidad_sueno, destacado, emocion, categorias, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        usuario_id,
                        s.get('titulo', 'Sin Título'),
                        s.get('descripcion', ''),
                        s.get('fecha'),
                        s.get('hora'),
                        s.get('calidad_sueno'),
                        s.get('destacado', False),
                        s.get('emocion'),
                        s.get('categorias'),
                        s.get('tags')
                    ))
                    insertados += 1

                # 2. Importar Señales Oníricas
                for sen in senales:
                    tag_valor = sen.get('tag') or sen.get('nombre')
                    cursor.execute("""
                        INSERT INTO senales_oniricas (usuario_id, tag, categoria, significado)
                        VALUES (%s, %s, %s, %s);
                    """, (
                        usuario_id,
                        tag_valor,
                        sen.get('categoria'),
                        sen.get('significado')
                    ))

                # 3. Importar Objetivos Oníricos
                for obj in objetivos:
                    cursor.execute("""
                        INSERT INTO objetivos_oniricos (usuario_id, titulo, descripcion, prioridad, categoria, veces_cumplido)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (
                        usuario_id,
                        obj.get('titulo'),
                        obj.get('descripcion'),
                        obj.get('prioridad'),
                        obj.get('categoria'),
                        obj.get('veces_cumplido', 0)
                    ))

                # 4. Importar Higiene de Sueño Logs
                for h in higiene:
                    cursor.execute("""
                        INSERT INTO higiene_sueno_logs (usuario_id, habito, completado, fecha)
                        VALUES (%s, %s, %s, %s);
                    """, (
                        usuario_id,
                        h.get('habito'),
                        h.get('completado', False),
                        h.get('fecha')
                    ))

                # 5. Importar Tótemps
                for t in totems:
                    cursor.execute("""
                        INSERT INTO totems (usuario_id, nombre, tipo, frase, sonido, vibracion, imagen)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        usuario_id,
                        t.get('nombre'),
                        t.get('tipo'),
                        t.get('frase'),
                        t.get('sonido'),
                        t.get('vibracion'),
                        t.get('imagen')
                    ))

            conn.commit()

        flash(f"Copia de seguridad restaurada con éxito ({insertados} sueños importados).", "success")

    except Exception as e:
        print(f"Error al importar respaldo: {e}")
        flash("Ocurrió un error al procesar la importación en la base de datos.", "error")

    return redirect(request.referrer or url_for('main.index'))

# Scope: solo acceso a los archivos creados específicamente por esta app
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']


def obtener_credenciales_drive(usuario_id):
    """Obtiene y refresca las credenciales OAuth2 de Google Drive del usuario."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT google_drive_refresh_token FROM usuarios WHERE id = %s;",
                (usuario_id,),
            )
            res = cursor.fetchone()

    if not res or not res.get("google_drive_refresh_token"):
        return None

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    return Credentials(
        token=None,
        refresh_token=res["google_drive_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=DRIVE_SCOPES,
    )


# BLOQUE: Sincronización Automática con Google Drive
@main_bp.route("/backup/drive/conectar")
def drive_conectar():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = url_for("main.drive_callback", _external=True)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=DRIVE_SCOPES,
        redirect_uri=redirect_uri,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )

    session["oauth_drive_state"] = state
    return redirect(authorization_url)


@main_bp.route("/backup/drive/callback")
def drive_callback():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    state = session.get("oauth_drive_state")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = url_for("main.drive_callback", _external=True)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=DRIVE_SCOPES,
        state=state,
        redirect_uri=redirect_uri,
    )

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    if credentials.refresh_token:
        usuario_id = session["usuario_id"]
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE usuarios 
                    SET google_drive_refresh_token = %s, google_drive_sync_activa = TRUE 
                    WHERE id = %s;
                """,
                    (credentials.refresh_token, usuario_id),
                )
            conn.commit()
        flash("Google Drive vinculado exitosamente.", "success")
    else:
        flash(
            "No se pudo obtener el acceso continuo a Google Drive. Reintenta la vinculación.",
            "error",
        )

    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/backup/drive/sincronizar", methods=["POST", "GET"])
def drive_sincronizar():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))

    usuario_id = session["usuario_id"]
    creds = obtener_credenciales_drive(usuario_id)

    if not creds:
        flash("Debes vincular tu cuenta de Google Drive primero.", "warning")
        return redirect(url_for("main.drive_conectar"))

    try:
        # 1. Recopilar datos para la copia de seguridad
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM suenos WHERE usuario_id = %s ORDER BY id ASC;",
                    (usuario_id,),
                )
                suenos = cursor.fetchall() or []

                cursor.execute(
                    "SELECT * FROM senales_oniricas WHERE usuario_id = %s ORDER BY id ASC;",
                    (usuario_id,),
                )
                senales = cursor.fetchall() or []

                cursor.execute(
                    "SELECT * FROM objetivos_oniricos WHERE usuario_id = %s ORDER BY id ASC;",
                    (usuario_id,),
                )
                objetivos = cursor.fetchall() or []

                cursor.execute(
                    "SELECT * FROM higiene_sueno_logs WHERE usuario_id = %s ORDER BY id ASC;",
                    (usuario_id,),
                )
                higiene = cursor.fetchall() or []

                cursor.execute(
                    "SELECT * FROM totems WHERE usuario_id = %s ORDER BY id ASC;",
                    (usuario_id,),
                )
                totems = cursor.fetchall() or []

        data_backup = {
            "version": "1.0",
            "fecha_backup": datetime.now().isoformat(),
            "usuario": session.get("usuario_nombre", "Usuario"),
            "suenos": suenos,
            "senales_oniricas": senales,
            "objetivos_oniricos": objetivos,
            "higiene_sueno_logs": higiene,
            "totems": totems,
        }

        json_bytes = json.dumps(
            data_backup,
            default=serializador_json,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        media = MediaIoBaseUpload(
            BytesIO(json_bytes), mimetype="application/json", resumable=True
        )

        service = build("drive", "v3", credentials=creds)

        # 2. Buscar o crear la carpeta 'Bitacora_Onirica_Backups'
        response = (
            service.files()
            .list(
                q="name = 'Bitacora_Onirica_Backups' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
        )

        folders = response.get("files", [])
        if not folders:
            folder_metadata = {
                "name": "Bitacora_Onirica_Backups",
                "mimeType": "application/vnd.google-apps.folder",
            }
            folder = (
                service.files().create(body=folder_metadata, fields="id").execute()
            )
            folder_id = folder.get("id")
        else:
            folder_id = folders[0].get("id")

        # 3. Guardar/actualizar la copia de seguridad dentro de la carpeta
        nombre_archivo = "backup_onirico_auto.json"

        search_file = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and name = '{nombre_archivo}' and trashed = false",
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
        )

        if search_file:
            file_id = search_file[0].get("id")
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {
                "name": nombre_archivo,
                "parents": [folder_id],
            }
            service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute()

        flash(
            "Copia de seguridad sincronizada exitosamente en tu Google Drive.",
            "success",
        )

    except Exception as e:
        print(f"Error al sincronizar con Google Drive: {e}")
        flash("Ocurrió un error al sincronizar con Google Drive.", "error")

    return redirect(request.referrer or url_for("main.index"))