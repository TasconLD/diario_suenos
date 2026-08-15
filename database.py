import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# URL de la base de datos (PostgreSQL)
DATABASE_URL = os.environ.get('DATABASE_URL')


def obtener_conexion():
    """Se conecta a PostgreSQL usando DATABASE_URL."""
    if not DATABASE_URL:
        raise ValueError("Error: La variable de entorno DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL)

# BLOQUE: Inicialización de Base de Datos y migración de esquema de Usuarios (con OAuth)
def inicializar_base_datos():
    """Crea las tablas en PostgreSQL si no existen y actualiza columnas pendientes al arrancar."""
    with obtener_conexion() as conn:
        with conn.cursor() as cursor:
            # 1. Tabla de usuarios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario VARCHAR(50) UNIQUE NOT NULL,
                    contrasena TEXT,
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

            # 3. Migración de esquema: Agregar columnas de Email, Verificación y Google OAuth
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;
                
                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS email_verificado BOOLEAN DEFAULT FALSE;

                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;

                ALTER TABLE usuarios 
                ALTER COLUMN contrasena DROP NOT NULL;
            """)

            # 4. Migración de esquema: Sincronización con Google Drive
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS google_drive_refresh_token TEXT,
                ADD COLUMN IF NOT EXISTS google_drive_sync_activa BOOLEAN DEFAULT FALSE;
            """)

            # 5. Migración de esquema: Gamificación (Racha activa)
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS racha_actual INT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS ultima_fecha_registro DATE;
            """)

            # 6. Tabla de Logros y Medallas Desbloqueadas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logros_usuario (
                    id SERIAL PRIMARY KEY,
                    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    codigo_logro VARCHAR(50) NOT NULL,
                    fecha_desbloqueo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(usuario_id, codigo_logro)
                );
            """)

            # BLOQUE: Migración de esquema - Columna de idioma preferido del usuario
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN IF NOT EXISTS idioma VARCHAR(5) DEFAULT 'es';
            """)

            # 7. Tabla de Bitácora de Vigilia (Registros de Vida Real)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros_vigilia (
                    id SERIAL PRIMARY KEY,
                    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
                    titulo VARCHAR(255) NOT NULL,
                    descripcion TEXT NOT NULL,
                    estado_animo INT CHECK (estado_animo BETWEEN 1 AND 5),
                    personas_clave TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()