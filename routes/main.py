import time
from flask import Blueprint, render_template, request, redirect, url_for, Response, session
from psycopg2.extras import RealDictCursor
from database import obtener_conexion
from models import obtener_estadisticas
from pdf_generator import generar_pdf_suenos

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    usuario_id = session['usuario_id']
    query = request.args.get('q', '').strip().lower()
    categoria_filtro = request.args.get('cat', '').strip().lower()
    
    stats = obtener_estadisticas(usuario_id)
    
    condiciones = ["usuario_id = %s"]
    parametros = [usuario_id]
    sql_query = """SELECT * FROM suenos"""
    
    if categoria_filtro:
        if categoria_filtro == 'destacado':
            condiciones.append("destacado = TRUE")
        else:
            condiciones.append("%s = ANY(SELECT LOWER(c) FROM unnest(categorias) c)")
            parametros.append(categoria_filtro)
            
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
        stats=stats,
        usuario_nombre=session['usuario_nombre']
    )

@main_bp.route('/registrar', methods=['POST'])
def registrar():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    id_sueno = int(time.time() * 1000)
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
                INSERT INTO suenos (id, titulo, fecha, descripcion, categorias, calidad_sueno, destacado, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (id_sueno, titulo, fecha, descripcion, categorias, calidad_sueno, destacado, session['usuario_id']))
            conn.commit()
    
    return redirect(url_for('main.index'))

@main_bp.route('/editar/<id_sueno>', methods=['POST'])
def editar(id_sueno):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
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
                WHERE id = %s AND usuario_id = %s;
            """, (titulo, fecha, descripcion, categorias, calidad_sueno, destacado, int(id_sueno), session['usuario_id']))
            conn.commit()
            
    return redirect(url_for('main.index'))

@main_bp.route('/eliminar/<id_sueno>')
def eliminar(id_sueno):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
        
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""DELETE FROM suenos WHERE id = %s AND usuario_id = %s;""", (int(id_sueno), session['usuario_id']))
            conn.commit()
    
    return redirect(url_for('main.index'))

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