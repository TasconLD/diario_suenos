import psycopg2

# PEGA AQUÍ TU URL DE NEON (La que acabas de copiar)
URL_NEON = "postgresql://neondb_owner:npg_bypqGueDk1v2@ep-odd-shape-awnugcx6-pooler.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def migrar_nube():
    print("Conectando a Neon para crear las tablas...")
    try:
        conn = psycopg2.connect(URL_NEON)
        cursor = conn.cursor()
        
        # Crear la tabla de sueños idéntica a la local
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suenos (
                id BIGINT PRIMARY KEY,
                titulo VARCHAR(255) NOT NULL,
                fecha DATE NOT NULL,
                descripcion TEXT NOT NULL,
                categorias TEXT[] DEFAULT '{}',
                calidad_sueno INT NOT NULL,
                destacado BOOLEAN DEFAULT FALSE
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("¡Tablas creadas con éxito en la nube de Neon!")
    except Exception as e:
        print(f"Error al crear las tablas: {e}")

if __name__ == "__main__":
    migrar_nube()