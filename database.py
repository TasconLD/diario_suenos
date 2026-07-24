import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def obtener_conexion():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return psycopg2.connect(
            dbname="tu_bd_local",
            user="postgres",
            password="tu_password",
            host="localhost",
            port="5432"
        )

def inicializar_base_datos():
    """Crea las tablas en PostgreSQL si no existen al arrancar la aplicación."""
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Crear tabla de usuarios primero
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario VARCHAR(50) UNIQUE NOT NULL,
                    contrasena TEXT NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # 2. Crear tabla de suenos e incluir la columna vinculada al usuario
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