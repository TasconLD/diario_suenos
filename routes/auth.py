# BLOQUE: Imports y Configuración
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from database import obtener_conexion
from itsdangerous import URLSafeTimedSerializer
from services.email_service import EmailService
from translations import translate

auth_bp = Blueprint('auth', __name__)


# BLOQUE: Helper de traducción (usa el idioma guardado en sesión)
def _(clave):
    return translate(clave, session.get('lang', 'es'))


# BLOQUE: Login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombre_usuario = (request.form.get('usuario') or '').strip().lower()
        contrasena = request.form.get('contrasena') or ''
        
        if not nombre_usuario or not contrasena:
            return render_template('login.html', error=_('msg_login_missing_fields'))
        
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM usuarios WHERE usuario = %s OR email = %s;", (nombre_usuario, nombre_usuario))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['contrasena'], contrasena):
                    session['usuario_id'] = user['id']
                    session['usuario_nombre'] = user['usuario']
                    return redirect(url_for('main.index'))
                else:
                    return render_template('login.html', error=_('msg_login_invalid_credentials'))
                    
    return render_template('login.html')

# BLOQUE: Google OAuth (Login, Vinculación e Inicio Único)
@auth_bp.route('/login/google')
def google_login():
    from app import oauth
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri, prompt='select_account')

@auth_bp.route('/authorize/google')
def google_authorize():
    from app import oauth
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash(_('msg_google_data_error'), "error")
        return redirect(url_for('auth.login'))
    
    google_sub = user_info['sub']
    email = user_info['email']

    # CASO 1: El usuario ya tiene la sesión iniciada -> Quiere VINCULAR su cuenta con Google
    if 'usuario_id' in session:
        usuario_id = session['usuario_id']
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE google_id = %s AND id != %s;", (google_sub, usuario_id))
                existente = cursor.fetchone()
                if existente:
                    flash(_('msg_google_already_linked'), 'error')
                    return redirect(url_for('main.index'))

                cursor.execute("UPDATE usuarios SET google_id = %s WHERE id = %s;", (google_sub, usuario_id))
                conn.commit()

        flash(_('msg_google_linked_success'), 'success')
        return redirect(url_for('main.index'))

    # CASO 2: El usuario NO ha iniciado sesión -> Quiere HACER LOGIN con Google
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE google_id = %s;", (google_sub,))
            user = cursor.fetchone()

            if not user:
                cursor.execute("SELECT * FROM usuarios WHERE email = %s;", (email,))
                user = cursor.fetchone()

                if user:
                    cursor.execute("UPDATE usuarios SET google_id = %s, email_verificado = TRUE WHERE id = %s;", (google_sub, user['id']))
                    conn.commit()

            if not user:
                import secrets
                random_password = generate_password_hash(secrets.token_hex(16))
                cursor.execute(
                    "INSERT INTO usuarios (usuario, email, contrasena, email_verificado, google_id) VALUES (%s, %s, %s, TRUE, %s) RETURNING id, usuario;",
                    (email, email, random_password, google_sub)
                )
                user = cursor.fetchone()
                conn.commit()

            session['usuario_id'] = user['id']
            session['usuario_nombre'] = user['usuario']

    return redirect(url_for('main.index'))

# BLOQUE: Desvinculación de Proveedores OAuth
@auth_bp.route('/desvincular/<proveedor>', methods=['POST'])
def desvincular_oauth(proveedor):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']
    destino_redirect = request.referrer or url_for('main.index')

    if proveedor != 'google':
        flash(_('msg_invalid_provider'), 'error')
        return redirect(destino_redirect)

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT contrasena, google_id FROM usuarios WHERE id = %s;", (usuario_id,))
            user = cursor.fetchone()

            if not user or not user['google_id']:
                flash(_('msg_google_not_linked'), 'error')
                return redirect(destino_redirect)

            # Seguridad: Impedir la desvinculación si el usuario no tiene una contraseña funcional configurada
            # (evita que la cuenta quede bloqueada e inaccesible).
            if not user['contrasena']:
                flash(_('msg_need_password_before_unlink'), 'error')
                return redirect(destino_redirect)

            cursor.execute("UPDATE usuarios SET google_id = NULL WHERE id = %s;", (usuario_id,))
            conn.commit()

    flash(_('msg_google_unlinked_success'), 'success')
    return redirect(destino_redirect)

# BLOQUE: Registro de usuarios
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        email = request.form.get('email')
        contrasena = request.form.get('contrasena')

        if not usuario or not email or not contrasena:
            return render_template('registro.html', error=_('msg_register_fields_required'))

        contrasena_hash = generate_password_hash(contrasena)

        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE usuario = %s OR email = %s;",
                        (usuario, email)
                    )
                    if cursor.fetchone():
                        return render_template('registro.html', error=_('msg_register_user_exists'))

                    cursor.execute(
                        "INSERT INTO usuarios (usuario, email, contrasena, email_verificado) VALUES (%s, %s, %s, FALSE);",
                        (usuario, email, contrasena_hash)
                    )
                    conn.commit()

            # Envío de correo de confirmación
            token = generar_token_verificacion(email)
            url_confirmacion = url_for('auth.confirmar_email', token=token, _external=True)
            EmailService.enviar_correo_verificacion(email, url_confirmacion)
            
            flash(_('msg_register_created_success'), 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Error en registro: {e}")
            return render_template('registro.html', error=_('msg_register_error'))

    return render_template('registro.html')

# BLOQUE: Cambiar contraseña desde sesión activa
@auth_bp.route('/cambiar-contrasena', methods=['POST'])
def cambiar_contrasena():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    usuario_id = session['usuario_id']
    contrasena_actual = request.form.get('contrasena_actual')
    contrasena_nueva = request.form.get('contrasena_nueva')
    contrasena_confirmar = request.form.get('contrasena_confirmar')

    destino_redirect = request.referrer or url_for('main.index')

    if contrasena_nueva != contrasena_confirmar:
        flash(_('msg_password_mismatch'), 'error')
        return redirect(destino_redirect)

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT contrasena FROM usuarios WHERE id = %s;", (usuario_id,))
            user = cursor.fetchone()
            
            if not user or not check_password_hash(user['contrasena'], contrasena_actual):
                flash(_('msg_current_password_incorrect'), 'error')
                return redirect(destino_redirect)

            nueva_encriptada = generate_password_hash(contrasena_nueva)
            cursor.execute(
                "UPDATE usuarios SET contrasena = %s WHERE id = %s;", 
                (nueva_encriptada, usuario_id)
            )
            conn.commit()

    flash(_('msg_password_updated_success'), 'success')
    return redirect(destino_redirect)

# BLOQUE: Tokens de Verificación de Email
def generar_token_verificacion(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='email-confirm-salt')

def confirmar_token_verificacion(token, max_age=86400):  # 24 horas
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        return serializer.loads(token, salt='email-confirm-salt', max_age=max_age)
    except Exception:
        return None

@auth_bp.route('/confirmar-email/<token>')
def confirmar_email(token):
    email = confirmar_token_verificacion(token)
    if not email:
        flash(_('msg_verification_link_invalid'), 'error')
        return redirect(url_for('auth.login'))

    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET email_verificado = TRUE WHERE email = %s;",
                    (email,)
                )
                conn.commit()

        flash(_('msg_email_verified_success'), 'success')
    except Exception as e:
        print(f"Error al confirmar email: {e}")
        flash(_('msg_email_verification_error'), 'error')

    return redirect(url_for('auth.login'))

# BLOQUE: Tokens y Rutas de Recuperación de Contraseña
def generar_token_reset(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='reset-password-salt')

def confirmar_token_reset(token, max_age=3600):  # 1 hora
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        return serializer.loads(token, salt='reset-password-salt', max_age=max_age)
    except Exception:
        return None

@auth_bp.route('/solicitar-reset', methods=['GET', 'POST'])
def solicitar_reset():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        
        if email:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id FROM usuarios WHERE email = %s;", (email,))
                    usuario = cursor.fetchone()

            if usuario:
                token = generar_token_reset(email)
                url_reset = url_for('auth.reset_password', token=token, _external=True)
                EmailService.enviar_correo_restablecimiento(email, url_reset)

        flash(_('msg_reset_link_sent_generic'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('solicitar_reset.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirmar_token_reset(token)
    if not email:
        flash(_('msg_reset_link_invalid'), 'error')
        return redirect(url_for('auth.solicitar_reset'))

    if request.method == 'POST':
        nueva_contrasena = request.form.get('contrasena')
        if not nueva_contrasena:
            return render_template('reset_password.html', error=_('msg_password_empty'))

        nueva_hash = generate_password_hash(nueva_contrasena)

        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET contrasena = %s WHERE email = %s;",
                    (nueva_hash, email)
                )
                conn.commit()

        flash(_('msg_password_reset_success'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')

# BLOQUE: Logout
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))