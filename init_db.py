import os
import psycopg2

# Lee la URL desde las variables de entorno o usa la URL de Neon si no está configurada
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    'postgresql://neondb_owner:npg_bypqGueDk1v2@ep-odd-shape-awnugcx6-pooler.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require'
)

def migrar_nube():
    print("Conectando a PostgreSQL (Neon) para crear las tablas...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Crear la tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(50) UNIQUE NOT NULL,
                contrasena TEXT NOT NULL,
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
        print("¡Tablas (usuarios y suenos) creadas con éxito en la base de datos!")
    except Exception as e:
        print(f"Error al crear las tablas: {e}")

if __name__ == "__main__":
    migrar_nube()