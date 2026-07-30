from flask import Blueprint, render_template, request, redirect, url_for, session, flash
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

# ==============================================================================
# RUTA PARA CAMBIO DE CONTRASEÑA (DESDE EL MODAL)
# ==============================================================================
@auth_bp.route('/cambiar-contrasena', methods=['POST'])
def cambiar_contrasena():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']
    contrasena_actual = request.form.get('contrasena_actual')
    contrasena_nueva = request.form.get('contrasena_nueva')
    contrasena_confirmar = request.form.get('contrasena_confirmar')

    destino_redirect = request.referrer or url_for('main.index')

    # Validar coincidencia de nuevas contraseñas
    if contrasena_nueva != contrasena_confirmar:
        flash('Las contraseñas nuevas no coinciden.', 'error')
        return redirect(destino_redirect)

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT contrasena FROM usuarios WHERE id = %s;", (usuario_id,))
            user = cursor.fetchone()
            
            # Validar si la contraseña actual es correcta
            if not user or not check_password_hash(user['contrasena'], contrasena_actual):
                flash('La contraseña actual es incorrecta.', 'error')
                return redirect(destino_redirect)

            # Si todo está bien, actualizar
            nueva_encriptada = generate_password_hash(contrasena_nueva)
            cursor.execute(
                "UPDATE usuarios SET contrasena = %s WHERE id = %s;", 
                (nueva_encriptada, usuario_id)
            )
            conn.commit()

    flash('¡Contraseña actualizada con éxito!', 'success')
    return redirect(destino_redirect)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))