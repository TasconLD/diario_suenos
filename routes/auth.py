from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from database import obtener_conexion


auth_bp = Blueprint('auth', __name__)

#BLOQUE: Login
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
# BLOQUE: Google OAuth
@auth_bp.route('/login/google')
def google_login():
    from app import oauth
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize/google')
def google_authorize():
    from app import oauth
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        return render_template('login.html', error="Error al obtener datos de Google.")
    
    email = user_info['email']
    nombre = user_info.get('name', email.split('@')[0])
    
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Buscar si el usuario ya existe por email o usuario
            cursor.execute("SELECT * FROM usuarios WHERE usuario = %s;", (email,))
            user = cursor.fetchone()
            
            if not user:
                # Si no existe, lo creamos automáticamente
                import secrets
                random_password = generate_password_hash(secrets.token_hex(16))
                cursor.execute(
                    "INSERT INTO usuarios (usuario, contrasena) VALUES (%s, %s) RETURNING id;",
                    (email, random_password)
                )
                user_id = cursor.fetchone()['id']
                conn.commit()
            else:
                user_id = user['id']
                
            session['usuario_id'] = user_id
            session['usuario_nombre'] = email
            
    return redirect(url_for('main.index'))
# BLOQUE: Procesamiento de Registro con captura de Email
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        email = request.form.get('email')
        contrasena = request.form.get('contrasena')

        # Validar que no falten campos
        if not usuario or not email or not contrasena:
            return render_template('registro.html', error="Todos los campos son obligatorios.")

        contrasena_hash = generate_password_hash(contrasena)

        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    # Verificar si el usuario o el email ya existen
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE usuario = %s OR email = %s;",
                        (usuario, email)
                    )
                    if cursor.fetchone():
                        return render_template('registro.html', error="El nombre de usuario o el correo ya están registrados.")

                    # Insertar nuevo usuario con email
                    cursor.execute(
                        "INSERT INTO usuarios (usuario, email, contrasena, email_verificado) VALUES (%s, %s, %s, FALSE);",
                        (usuario, email, contrasena_hash)
                    )
                    conn.commit()
            
            flash('¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"Error en registro: {e}")
            return render_template('registro.html', error="Ocurrió un error al registrar la cuenta.")

    return render_template('registro.html')

#BLOQUE: Cambiar contraseña desde modal
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

# BLOQUE: Lógica de Verificación de Correo y Tokens
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import smtplib
from email.mime.text import MIMEText

def generar_token_verificacion(email):
    """Genera un token cifrado con el email del usuario."""
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='email-confirm-salt')

def confirmar_token_verificacion(token, max_age=86400):  # Token válido por 24 horas (86400 seg)
    """Decodifica el token y retorna el email si no ha expirado."""
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=max_age)
        return email
    except Exception:
        return None

def enviar_correo_verificacion(email, token):
    """Envía el correo con la URL de confirmación usando las variables SMTP de la App."""
    url_confirmacion = url_for('auth.confirmar_email', token=token, _external=True)
    
    mensaje = MIMEText(f"""
    ¡Hola!

    Gracias por registrarte en Entrenador Onírico. 
    Por favor confirma tu correo electrónico haciendo clic en el siguiente enlace:

    {url_confirmacion}

    Este enlace expirará en 24 horas. Si no creaste esta cuenta, puedes ignorar este mensaje.
    """)
    mensaje['Subject'] = 'Confirma tu correo - Entrenador Onírico'
    mensaje['From'] = current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@entrenadoronirico.com')
    mensaje['To'] = email

    try:
        server_host = current_app.config.get('MAIL_SERVER')
        server_port = current_app.config.get('MAIL_PORT', 587)
        mail_user = current_app.config.get('MAIL_USERNAME')
        mail_pass = current_app.config.get('MAIL_PASSWORD')

        if server_host and mail_user and mail_pass:
            with smtplib.SMTP(server_host, server_port) as server:
                server.starttls()
                server.login(mail_user, mail_pass)
                server.send_message(mensaje)
            print(f"--> Correo de verificación enviado con éxito a: {email}")
        else:
            print(f"\n[MODO DEV] Enlace de confirmación para {email}:\n{url_confirmacion}\n")
    except Exception as e:
        print(f"Error al enviar correo de verificación: {e}")


@auth_bp.route('/confirmar-email/<token>')
def confirmar_email(token):
    """Ruta a la que llega el usuario al hacer clic en el enlace del correo."""
    email = confirmar_token_verificacion(token)
    if not email:
        flash('El enlace de verificación es inválido o ha expirado.', 'error')
        return redirect(url_for('auth.login'))

    try:
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET email_verificado = TRUE WHERE email = %s;",
                    (email,)
                )
                conn.commit()

        flash('¡Tu correo electrónico ha sido verificado con éxito!', 'success')
    except Exception as e:
        print(f"Error al confirmar email: {e}")
        flash('Ocurrió un error al verificar tu cuenta.', 'error')

    return redirect(url_for('auth.login'))

# BLOQUE: Rutas de Recuperación de Contraseña
def generar_token_reset(email):
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    return serializer.dumps(email, salt='reset-password-salt')

def confirmar_token_reset(token, max_age=3600):  # Válido por 1 hora (3600 seg)
    serializer = URLSafeTimedSerializer(current_app.secret_key)
    try:
        return serializer.loads(token, salt='reset-password-salt', max_age=max_age)
    except Exception:
        return None

@auth_bp.route('/solicitar-reset', methods=['GET', 'POST'])
def solicitar_reset():
    if request.method == 'POST':
        email = request.form.get('email')
        
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE email = %s;", (email,))
                usuario = cursor.fetchone()

        if usuario:
            token = generar_token_reset(email)
            url_reset = url_for('auth.reset_password', token=token, _external=True)
            
            # Construir correo de restablecimiento
            mensaje = MIMEText(f"""
            Has solicitado restablecer tu contraseña en Entrenador Onírico.
            
            Haz clic en el siguiente enlace para crear una nueva contraseña:
            {url_reset}
            
            Si no solicitaste este cambio, ignora este correo. El enlace expira en 1 hora.
            """)
            mensaje['Subject'] = 'Restablecer Contraseña - Entrenador Onírico'
            mensaje['From'] = current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@entrenadoronirico.com')
            mensaje['To'] = email

            try:
                server_host = current_app.config.get('MAIL_SERVER')
                server_port = current_app.config.get('MAIL_PORT', 587)
                mail_user = current_app.config.get('MAIL_USERNAME')
                mail_pass = current_app.config.get('MAIL_PASSWORD')

                if server_host and mail_user and mail_pass:
                    with smtplib.SMTP(server_host, server_port) as server:
                        server.starttls()
                        server.login(mail_user, mail_pass)
                        server.send_message(mensaje)
                else:
                    print(f"\n[MODO DEV] Enlace Reset para {email}:\n{url_reset}\n")
            except Exception as e:
                print(f"Error enviando email reset: {e}")

        # Mensaje de seguridad ambiguo para no revelar si el correo existe o no
        flash('Si el correo está registrado, recibirás un enlace de recuperación.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('solicitar_reset.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirmar_token_reset(token)
    if not email:
        flash('El enlace de restablecimiento es inválido o ha expirado.', 'error')
        return redirect(url_for('auth.solicitar_reset'))

    if request.method == 'POST':
        nueva_contrasena = request.form.get('contrasena')
        if not nueva_contrasena:
            return render_template('reset_password.html', error="La contraseña no puede estar vacía.")

        nueva_hash = generate_password_hash(nueva_contrasena)

        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE usuarios SET contrasena = %s WHERE email = %s;",
                    (nueva_hash, email)
                )
                conn.commit()

        flash('¡Tu contraseña ha sido actualizada exitosamente! Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')



#BLOQUE: Cerrar sesion
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))