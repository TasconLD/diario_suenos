import os
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    # Flask App Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    JSON_AS_ASCII = False  # Evita que caracteres como 'ó' o 'ñ' se conviertan a \u00f3

    # OAuth Google
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    # Web Push / VAPID Config
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
    VAPID_CLAIMS = {
        "sub": os.environ.get("VAPID_MAILTO", "mailto:admin@diariosuenos.com")
    }

    # Ruta del archivo de suscripciones
    @staticmethod
    def get_subscriptions_file(root_path):
        if os.environ.get('RENDER'):
            return '/tmp/subscriptions.json'
        return os.path.join(root_path, 'subscriptions.json')