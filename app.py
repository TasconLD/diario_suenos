import os
from flask import Flask, Response
from database import inicializar_base_datos
from routes.auth import auth_bp
from routes.main import main_bp

# BLOQUE: Creación e inicialización de la app Flask
app = Flask(__name__)

# Clave secreta para cookies de sesión
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_dificil_de_adivinar_123')

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

# BLOQUE: Arranque del servidor local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)