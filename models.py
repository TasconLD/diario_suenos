from psycopg2.extras import RealDictCursor
from database import obtener_conexion

def obtener_estadisticas(usuario_id):
    """Calcula estadísticas filtradas por el usuario logueado."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COALESCE(COUNT(*) FILTER (WHERE 'pesadilla' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as pesadillas,
                    COALESCE(COUNT(*) FILTER (WHERE 'lucido' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as lucidos,
                    COALESCE(COUNT(*) FILTER (WHERE 'bonito' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as bonitos,
                    COALESCE(ROUND(AVG(calidad_sueno), 1), 0.0) as promedio
                FROM suenos
                WHERE usuario_id = %s;
            """, (usuario_id,))
            return cursor.fetchone()

def cargar_datos(usuario_id):
    """Trae los registros filtrados por el usuario logueado."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""SELECT * FROM suenos WHERE usuario_id = %s ORDER BY fecha DESC, id DESC;""", (usuario_id,))
            suenos = cursor.fetchall()
            for s in suenos:
                if s.get('fecha'):
                    s['fecha'] = s['fecha'].strftime('%Y-%m-%d')
            return suenos