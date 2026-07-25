from psycopg2.extras import RealDictCursor
from database import obtener_conexion

# BLOQUE: Estadísticas generales y por emoción del usuario
def obtener_estadisticas(usuario_id):
    """Calcula estadísticas filtradas por el usuario logueado, incluyendo emociones."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COALESCE(COUNT(*) FILTER (WHERE 'pesadilla' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as pesadillas,
                    COALESCE(COUNT(*) FILTER (WHERE 'lucido' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as lucidos,
                    COALESCE(COUNT(*) FILTER (WHERE 'bonito' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as bonitos,
                    COALESCE(COUNT(*) FILTER (WHERE 'falso despertar' = ANY(SELECT LOWER(c) FROM unnest(categorias) c) OR 'falsodespertar' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as falsos_despertares,
                    COALESCE(COUNT(*) FILTER (WHERE 'salida astral' = ANY(SELECT LOWER(c) FROM unnest(categorias) c) OR 'salidaastral' = ANY(SELECT LOWER(c) FROM unnest(categorias) c)), 0) as salidas_astrales,
                    COALESCE(ROUND(AVG(calidad_sueno), 1), 0.0) as promedio,
                    -- Conteos por emoción:
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) IN ('alegria', 'feliz')), 0) as emocion_alegria,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) IN ('tristeza', 'triste')), 0) as emocion_tristeza,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) = 'miedo'), 0) as emocion_miedo,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) = 'paz'), 0) as emocion_paz,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) IN ('confusion', 'ansioso')), 0) as emocion_confusion,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) = 'asombro'), 0) as emocion_asombro,
                    COALESCE(COUNT(*) FILTER (WHERE LOWER(emocion) = 'neutro'), 0) as emocion_neutro
                FROM suenos
                WHERE usuario_id = %s;
            """, (usuario_id,))
            return cursor.fetchone()

# BLOQUE: Carga de registros de sueños del usuario
def cargar_datos(usuario_id):
    """Trae los registros filtrados por el usuario logueado."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM suenos 
                WHERE usuario_id = %s 
                ORDER BY fecha DESC, id DESC;
            """, (usuario_id,))
            suenos = cursor.fetchall()
            for s in suenos:
                if s.get('fecha'):
                    s['fecha'] = s['fecha'].strftime('%Y-%m-%d')
                if s.get('hora'):
                    s['hora_formateada'] = s['hora'].strftime('%I:%M %p')
                else:
                    s['hora_formateada'] = None
            return suenos