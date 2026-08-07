"""
Prueba unitaria: detecta endpoints duplicados en app.py ANTES de desplegar.

Por qué existe este test:
Render falló con "AssertionError: View function mapping is overwriting an
existing endpoint function: serve_sw" porque app.py tenía dos funciones
@app.route con el mismo nombre. Este test analiza el código estáticamente
(sin necesitar base de datos, variables de entorno VAPID, etc.) para que
puedas detectar este tipo de error en segundos, en tu máquina local,
antes de subir a Render.

Ubicación esperada: diario_suenos/tests/test_app_sin_rutas_duplicadas.py
(un nivel dentro de la raíz del proyecto, junto a app.py)

Cómo correrlo (desde la raíz del proyecto):
    pip install pytest
    pytest tests/ -v
    
    python -m pytest tests/ -v
"""

import ast
import os
import pytest

# BLOQUE: Configuración de Rutas de Prueba
RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_APP_PY = os.path.join(RAIZ_PROYECTO, "app.py")


# BLOQUE: Auxiliares de Análisis Estático (AST)
def _cargar_arbol_ast():
    """Lee app.py y lo convierte en un árbol AST, sin ejecutar el código."""
    with open(RUTA_APP_PY, "r", encoding="utf-8") as f:
        codigo_fuente = f.read()
    return ast.parse(codigo_fuente, filename="app.py")


def _extraer_funciones_decoradas_con_route(arbol):
    """
    Recorre el árbol AST y devuelve una lista de tuplas:
    (nombre_de_la_funcion, ruta_declarada_en_el_decorador)
    para cada función decorada con @app.route(...).
    """
    resultados = []

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef):
            continue

        for decorador in nodo.decorator_list:
            # Buscamos decoradores tipo: app.route('/algo')
            if isinstance(decorador, ast.Call) and isinstance(decorador.func, ast.Attribute):
                if decorador.func.attr == "route":
                    ruta = None
                    if decorador.args and isinstance(decorador.args[0], ast.Constant):
                        ruta = decorador.args[0].value
                    resultados.append((nodo.name, ruta))

    return resultados


# BLOQUE: Pruebas Unitarias de Integridad
def test_no_hay_nombres_de_funcion_duplicados():
    """
    Flask usa el NOMBRE de la función como identificador único del endpoint.
    Si dos funciones @app.route tienen el mismo nombre, Flask lanza
    AssertionError al iniciar (esto fue exactamente lo que pasó con serve_sw).
    """
    arbol = _cargar_arbol_ast()
    funciones = _extraer_funciones_decoradas_con_route(arbol)

    nombres = [nombre for nombre, _ in funciones]
    nombres_repetidos = {n for n in nombres if nombres.count(n) > 1}

    assert not nombres_repetidos, (
        f"Hay funciones de ruta con el mismo nombre (esto rompe el arranque "
        f"en Flask/Render): {nombres_repetidos}"
    )


def test_no_hay_misma_ruta_declarada_dos_veces():
    """
    Chequeo complementario: aunque las funciones se llamaran distinto,
    dos @app.route('/sw.js') apuntando al mismo path también es un
    problema de diseño (una nunca se ejecutaría). Lo detectamos aparte.
    """
    arbol = _cargar_arbol_ast()
    funciones = _extraer_funciones_decoradas_con_route(arbol)

    rutas = [ruta for _, ruta in funciones if ruta is not None]
    rutas_repetidas = {r for r in rutas if rutas.count(r) > 1}

    assert not rutas_repetidas, (
        f"Hay más de una función @app.route apuntando al mismo path: {rutas_repetidas}"
    )


def test_no_se_importa_send_from_directory_sin_usarlo():
    """
    Chequeo extra ligado a este fix: send_from_directory se eliminó del
    import porque ya no se usa en ningún lado del archivo. Si en el futuro
    se vuelve a importar sin usarse, este test avisa.
    """
    arbol = _cargar_arbol_ast()
    codigo_fuente = open(RUTA_APP_PY, "r", encoding="utf-8").read()

    importa_send_from_directory = any(
        isinstance(nodo, ast.ImportFrom)
        and any(alias.name == "send_from_directory" for alias in nodo.names)
        for nodo in ast.walk(arbol)
    )

    if importa_send_from_directory:
        usos = codigo_fuente.count("send_from_directory(")
        assert usos > 0, (
            "send_from_directory está importado pero no se usa en ninguna "
            "parte del archivo (import muerto)."
        )


# BLOQUE: Ejecución Directa de Tests
if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))