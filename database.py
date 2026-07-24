import os
import psycopg2

# URL de Neon (tu base de datos en la nube)
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_bypqGueDk1v2@ep-odd-shape-awnugcx6-pooler.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require'
)

def obtener_conexion():
    """Se conecta a PostgreSQL usando DATABASE_URL (Neon en la nube o Render)."""
    return psycopg2.connect(DATABASE_URL)

def inicializar_base_datos():
    """Crea las tablas en PostgreSQL si no existen al arrancar la aplicación."""
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Tabla de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario VARCHAR(50) UNIQUE NOT NULL,
                    contrasena TEXT NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # 2. Tabla de sueños vinculada al usuario
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