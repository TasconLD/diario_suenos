from flask import Blueprint, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from database import obtener_conexion

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = (request.form.get('usuario') or '').strip().lower()
        contrasena = request.form.get('contrasena') or ''
        
        if not nombre_usuario or not contrasena:
            return render_template('login.html', error="Por favor completa todos los campos")
        
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM usuarios WHERE usuario = %s;", (nombre_usuario,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['contrasena'], contrasena):
                    session['usuario_id'] = user['id']
                    session['usuario_nombre'] = user['usuario']
                    return redirect(url_for('main.index'))
                else:
                    return render_template('login.html', error="Usuario o contraseña incorrectos")
                    
    return render_template('login.html')

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre_usuario = (request.form.get('usuario') or '').strip().lower()
        contrasena = request.form.get('contrasena') or ''
        
        if not nombre_usuario or not contrasena:
            return render_template('registro.html', error="Todos los campos son obligatorios")
            
        contrasena_encriptada = generate_password_hash(contrasena)
        
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s) RETURNING id;",
                        (nombre_usuario, contrasena_encriptada)
                    )
                    nuevo_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    session['usuario_id'] = nuevo_id
                    session['usuario_nombre'] = nombre_usuario
                    return redirect(url_for('main.index'))
        except psycopg2.IntegrityError:
            return render_template('registro.html', error="El nombre de usuario ya está en uso")
            
    return render_template('registro.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))