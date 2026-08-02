# BLOQUE: Inicialización de la Base de Datos (init_db.py)
import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Lee la URL desde las variables de entorno
DATABASE_URL = os.environ.get('DATABASE_URL')

def init_db():
    if not DATABASE_URL:
        print("❌ Error: La variable de entorno DATABASE_URL no está configurada en .env")
        return

    print("🔌 Conectando a PostgreSQL para inicializar la base de datos...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Crear la tabla de usuarios con soporte para Email, Verificación y OAuth
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                contrasena TEXT,
                email_verificado BOOLEAN DEFAULT FALSE,
                google_id VARCHAR(255) UNIQUE,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Crear la tabla de sueños vinculada al usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suenos (
                id BIGINT PRIMARY KEY,
                titulo VARCHAR(255) NOT NULL,
                descripcion TEXT NOT NULL,
                fecha DATE NOT NULL,
                calidad_sueno INTEGER DEFAULT 5,
                destacado BOOLEAN DEFAULT FALSE,
                categorias TEXT[],
                usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ ¡Tablas (usuarios y suenos) inicializadas con éxito en la base de datos!")
    except Exception as e:
        print(f"❌ Error al inicializar las tablas: {e}")

if __name__ == "__main__":
    init_db()