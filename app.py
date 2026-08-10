import os
from datetime import datetime
from flask import Flask, Response, request, jsonify, render_template, session
from authlib.integrations.flask_client import OAuth

from config import Config
from database import inicializar_base_datos
from routes.auth import auth_bp
from routes.main import main_bp
from services.push_service import (
    cargar_suscripciones, 
    guardar_suscripciones, 
    enviar_push, 
    iniciar_scheduler
)

from services.logger import obtener_logger
from translations import translate

logger = obtener_logger("app")
logger.info(" Servidor iniciado y logger comprobado correctamente.")

# BLOQUE: Creación e inicialización de la app Flask
app = Flask(__name__)
app.config.from_object(Config)
app.json.ensure_ascii = False
SUBSCRIPTIONS_FILE = Config.get_subscriptions_file(app.root_path)

# BLOQUE: Inicialización de la base de datos y tareas en segundo plano
inicializar_base_datos()
iniciar_scheduler(SUBSCRIPTIONS_FILE)

# BLOQUE: Registro de Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# BLOQUE: Configuración de OAuth (Google)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# BLOQUE: Servir el Service Worker (PWA)
@app.route('/sw.js')
def serve_sw():
    static_dir = os.path.join(app.root_path, 'static')
    filepath = os.path.join(static_dir, 'sw.js')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        response = Response(content, mimetype='application/javascript')
        response.headers['Service-Worker-Allowed'] = '/'
        return response
    return "Service Worker File Not Found", 404

# BLOQUE: Ruta de respaldo Offline para la PWA
@app.route('/offline')
def offline():
    return render_template('offline.html')

# BLOQUE: Endpoints de Suscripción WebPush y Diagnósticos
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    if not data or 'subscription' not in data:
        return jsonify({'error': 'Suscripción inválida'}), 400

    subscription = data['subscription']
    config = data.get('config', {})

    suscripciones = cargar_suscripciones(SUBSCRIPTIONS_FILE)
    endpoint_id = subscription.get('endpoint', '')[-20:]
    
    suscripciones[endpoint_id] = {
        'subscription': subscription,
        'config': config,
        'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    guardar_suscripciones(SUBSCRIPTIONS_FILE, suscripciones)
    return jsonify({'success': True, 'message': 'Suscripción Web Push registrada con éxito.'})

@app.route('/api/test-push-ahora', methods=['GET'])
def test_push_ahora():
    suscripciones = cargar_suscripciones(SUBSCRIPTIONS_FILE)
    if not suscripciones:
        return jsonify({'error': 'No hay ninguna suscripción guardada en el servidor'}), 400
    
    enviados = sum(
        1 for key, item in suscripciones.items() 
        if enviar_push(item.get('subscription'), "🚀 PRUEBA DIRECTA", "Si ves esto, las notificaciones Push funcionan 100%", "test")
    )
    return jsonify({'success': True, 'enviados': enviados, 'total': len(suscripciones)})

@app.route('/api/probar-alarmas-ahora', methods=['GET'])
def probar_alarmas_ahora():
    suscripciones = cargar_suscripciones(SUBSCRIPTIONS_FILE)
    if not suscripciones:
        return jsonify({
            'status': 'error', 
            'mensaje': 'No hay ningún dispositivo suscrito. Ve a la app en tu celular y mueve una hora para registrarte.'
        }), 400

    resultados = []
    for endpoint_id, item in suscripciones.items():
        sub = item.get('subscription')
        exito_matutino = enviar_push(sub, "☀️ PRUEBA DIURNA", "¡Funciona! Esta es la notificación matutina de prueba.", "matutino")
        exito_nocturno = enviar_push(sub, "🌙 PRUEBA NOCTURNA", "¡Funciona! Esta es la notificación nocturna de prueba.", "nocturno")

        resultados.append({
            'dispositivo': endpoint_id,
            'push_matutino_enviado': exito_matutino,
            'push_nocturno_enviado': exito_nocturno
        })

    return jsonify({'status': 'ok', 'resultados': resultados})

#BLOQUE: Procesador de Contexto (español ingles)
@app.context_processor
def inject_translate():
    def _(key):
        # Obtiene el idioma de la sesión activa, 'es' por defecto
        lang = session.get('lang', 'es')
        return translate(key, lang)
    return dict(_=_)

# BLOQUE: Arranque del servidor local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)