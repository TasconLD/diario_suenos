import os
from flask import Flask, Response
from database import inicializar_base_datos
from routes.auth import auth_bp
from routes.main import main_bp

app = Flask(__name__)

# Clave secreta para cookies de sesión
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_dificil_de_adivinar_123')

# Inicializar Base de Datos en PostgreSQL
inicializar_base_datos()

# Registrar Módulos / Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

@app.route('/sw.js')
def serve_sw():
    static_dir = os.path.join(app.root_path, 'static')
    filepath = os.path.join(static_dir, 'sw.js')
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
    else:
        return "Service Worker File Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)