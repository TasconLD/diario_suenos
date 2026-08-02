import os
import json
from datetime import datetime, timedelta
from flask import Flask, Response, request, jsonify, render_template, redirect, url_for, session, flash
from pywebpush import webpush, WebPushException
from apscheduler.schedulers.background import BackgroundScheduler

from database import inicializar_base_datos
from routes.auth import auth_bp
from routes.main import main_bp

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv


# Cargar variables de entorno al iniciar la app
load_dotenv()

# -------------------------------------------------------------
# CONFIGURACIÓN DE CLAVES VAPID (WEB PUSH)
# -------------------------------------------------------------
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")

VAPID_CLAIMS = {
    "sub": os.environ.get("VAPID_MAILTO", "mailto:admin@diariosuenos.com")
}
# BLOQUE: Creación e inicialización de la app Flask
app = Flask(__name__)

# Clave secreta para cookies de sesión
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')

# Configurar duración de la sesión en 30 días cuando se activa "Recordarme"
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# BLOQUE: Inicialización de la base de datos
inicializar_base_datos()

# BLOQUE: Registro de Blueprints (rutas de auth y main)
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# BLOQUE: Servir el Service Worker (para PWA/offline)
@app.route('/sw.js')
def serve_sw():
    static_dir = os.path.join(app.root_path, 'static')
    filepath = os.path.join(static_dir, 'sw.js')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        response = Response(content, mimetype='application/javascript')
        # Habilitar scope global para que capture toda la app y no solo /static/
        response.headers['Service-Worker-Allowed'] = '/'
        return response
    else:
        return "Service Worker File Not Found", 404

# ==============================================================================
# SISTEMA WEB PUSH & SUSCRIPCIONES
# ==============================================================================

SUBSCRIPTIONS_FILE = '/tmp/subscriptions.json' if os.environ.get('RENDER') else os.path.join(app.root_path, 'subscriptions.json')

def cargar_suscripciones():
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def guardar_suscripciones(data):
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    if not data or 'subscription' not in data:
        return jsonify({'error': 'Suscripción inválida'}), 400

    subscription = data['subscription']
    config = data.get('config', {})  # Configuración de horas enviada desde el front

    suscripciones = cargar_suscripciones()
    
    # Usar los últimos 20 caracteres del endpoint como ID único del dispositivo
    endpoint_id = subscription.get('endpoint', '')[-20:]
    
    suscripciones[endpoint_id] = {
        'subscription': subscription,
        'config': config,
        'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    guardar_suscripciones(suscripciones)
    return jsonify({'success': True, 'message': 'Suscripción Web Push registrada con éxito.'})

def enviar_push(subscription_info, titulo, mensaje, tag="general"):
    try:
        payload = json.dumps({
            "title": titulo,
            "body": mensaje,
            "tag": tag,
            "url": "/recordatorios"
        })
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        return True
    except WebPushException as ex:
        print(f"❌ Error enviando Push: {ex}")
        return False

# ==============================================================================
# PROGRAMADOR DE TAREAS EN SEGUNDO PLANO (APScheduler)
# ==============================================================================

def verificar_recordatorios():
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M")
    minutos_del_dia = ahora.hour * 60 + ahora.minute

    suscripciones = cargar_suscripciones()
    for key, item in list(suscripciones.items()):
        sub = item.get('subscription')
        cfg = item.get('config', {})

        # 1. Notificación Matutina
        if cfg.get('notif_matutino') and cfg.get('hora_matutino') == hora_actual:
            enviar_push(sub, "☀️ ¡Buenos días!", "No olvides registrar tu sueño antes de que se borre de tu memoria.", "matutino")

        # 2. Notificación Nocturna
        if cfg.get('notif_nocturno') and cfg.get('hora_nocturno') == hora_actual:
            enviar_push(sub, "🌙 Repaso Nocturno", "Repasa tus objetivos e intenciones antes de dormir.", "nocturno")

        # 3. Reality Checks
        if cfg.get('notif_rc'):
            frec = int(cfg.get('frec_rc', 120))
            if minutos_del_dia > 0 and minutos_del_dia % frec == 0:
                enviar_push(sub, "👁️ Reality Check", "¿Estás soñando ahora mismo? Revisa tus manos o mira un reloj.", "rc")

# Iniciar el scheduler de segundo plano
scheduler = BackgroundScheduler()
scheduler.add_job(func=verificar_recordatorios, trigger="interval", minutes=1)
scheduler.start()

###### BLOQUES DE DIAGNOSTICOS TEMPORAL NOTIFICACIONES #####

# BLOQUE: endpoint temporal de prueba directa
@app.route('/api/test-push-ahora', methods=['GET'])
def test_push_ahora():
    suscripciones = cargar_suscripciones()
    if not suscripciones:
        return jsonify({'error': 'No hay ninguna suscripción guardada en el servidor'}), 400
    
    enviados = 0
    for key, item in list(suscripciones.items()):
        sub = item.get('subscription')
        if enviar_push(sub, "🚀 PRUEBA DIRECTA", "Si ves esto, las notificaciones Push funcionan 100%", "test"):
            enviados += 1
            
    return jsonify({'success': True, 'enviados': enviados, 'total': len(suscripciones)})

# -------------------------------------------------------------
# RUTA DE DIAGNÓSTICO: PROBAR NOTIFICACIÓN DIURNA Y NOCTURNA
# -------------------------------------------------------------
@app.route('/api/probar-alarmas-ahora', methods=['GET'])
def probar_alarmas_ahora():
    suscripciones = cargar_suscripciones()
    if not suscripciones:
        return jsonify({
            'status': 'error', 
            'mensaje': 'No hay ningún dispositivo suscrito. Ve a la app en tu celular y mueve una hora para registrarte.'
        }), 400

    resultados = []
    for endpoint_id, item in suscripciones.items():
        sub = item.get('subscription')
        
        # Intentar enviar notificación de prueba
        exito_matutino = enviar_push(
            sub, 
            "☀️ PRUEBA DIURNA", 
            "¡Funciona! Esta es la notificación matutina de prueba.", 
            "matutino"
        )
        
        exito_nocturno = enviar_push(
            sub, 
            "🌙 PRUEBA NOCTURNA", 
            "¡Funciona! Esta es la notificación nocturna de prueba.", 
            "nocturno"
        )

        resultados.append({
            'dispositivo': endpoint_id,
            'push_matutino_enviado': exito_matutino,
            'push_nocturno_enviado': exito_nocturno
        })

    return jsonify({'status': 'ok', 'resultados': resultados})

# BLOQUE: Configuración de Authlib (OAuth con Google)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# BLOQUE: Configuración de Authlib en app.py
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'dev_client_id'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'dev_client_secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# BLOQUE: Ruta de respaldo Offline para la PWA
@app.route('/offline')
def offline():
    """Muestra la vista de cortesía cuando el usuario no tiene conexión a internet."""
    return render_template('offline.html')

# BLOQUE: Arranque del servidor local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)