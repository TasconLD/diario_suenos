"""
Prueba unitaria: verifica que el Service Worker (static/sw.js) solo
precachee rutas que REALMENTE existen en la aplicación Flask.

Por qué existe este test:
Se encontró que STATIC_ASSETS en sw.js incluía rutas inventadas/viejas
('/dashboard', '/diario', '/estadisticas', '/perfil', '/suenos') que
nunca existieron como @app.route/@main_bp.route/@auth_bp.route reales.
El Service Worker las ignora silenciosamente (try/catch), pero el
resultado es que esas páginas fantasma ocupan espacio en la lista sin
aportar nada, y no avisa si en el futuro una ruta real se cae de la
lista de precaché por error.

IMPORTANTE - Lo que este test SÍ y NO verifica:
SÍ verifica: que la lista de páginas a guardar en caché esté bien escrita
             (coincide con rutas reales de Flask).
NO verifica: que el Service Worker realmente se instale, cachee, y sirva
             esas páginas sin internet en un navegador de verdad. Eso solo
             se confirma probando manualmente en Chrome DevTools:
             Application > Service Workers, y activando el checkbox
             "Offline" en la pestaña Network.

Este test NO necesita navegador, base de datos, ni variables de entorno:
solo lee los archivos .py y .js como texto.

Ubicación esperada: diario_suenos/tests/test_sw_precache_rutas_validas.py
(un nivel dentro de la raíz del proyecto, junto a app.py y static/)

Cómo correrlo (desde la raíz del proyecto):
    pip install pytest
    pytest tests/ -v
"""

import ast
import os
import re
import pytest


RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_APP_PY = os.path.join(RAIZ_PROYECTO, "app.py")
RUTA_MAIN_PY = os.path.join(RAIZ_PROYECTO, "routes", "main.py")
RUTA_AUTH_PY = os.path.join(RAIZ_PROYECTO, "routes", "auth.py")
RUTA_SW_JS = os.path.join(RAIZ_PROYECTO, "static", "sw.js")


def _extraer_rutas_flask(ruta_archivo):
    """
    Lee un archivo Python y devuelve el set de paths declarados en
    decoradores tipo @app.route('/algo') o @main_bp.route('/algo'),
    sin importar el archivo (evita necesitar DB/env vars).
    Excluye rutas con parámetros dinámicos (<id>, <tag>, etc.) porque
    esas nunca se precachean literalmente.
    """
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        arbol = ast.parse(f.read(), filename=os.path.basename(ruta_archivo))

    rutas = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        for decorador in nodo.decorator_list:
            if not isinstance(decorador, ast.Call):
                continue
            if not isinstance(decorador.func, ast.Attribute):
                continue
            if decorador.func.attr != "route":
                continue
            if not decorador.args or not isinstance(decorador.args[0], ast.Constant):
                continue

            path = decorador.args[0].value
            if "<" in path:  # ruta dinámica, no aplica a precaché literal
                continue
            rutas.add(path)

    return rutas


def _extraer_static_assets_de_sw_js():
    """
    Extrae el array STATIC_ASSETS del Service Worker mediante una
    expresión regular simple (no necesitamos un parser JS completo:
    el array es una lista plana de strings).
    """
    with open(RUTA_SW_JS, "r", encoding="utf-8") as f:
        contenido = f.read()

    match = re.search(r"STATIC_ASSETS\s*=\s*\[(.*?)\]", contenido, re.DOTALL)
    assert match, "No se encontró el array STATIC_ASSETS en static/sw.js"

    bloque = match.group(1)
    # Extrae todos los strings entre comillas simples o dobles
    items = re.findall(r"""['"]([^'"]+)['"]""", bloque)
    return items


def _todas_las_rutas_reales_del_proyecto():
    rutas = set()
    rutas |= _extraer_rutas_flask(RUTA_APP_PY)
    rutas |= _extraer_rutas_flask(RUTA_MAIN_PY)
    rutas |= _extraer_rutas_flask(RUTA_AUTH_PY)
    return rutas


def test_precache_no_incluye_rutas_inexistentes():
    """
    Cada entrada de STATIC_ASSETS que sea una ruta interna (empieza con
    '/' y no es un archivo bajo /static/) debe corresponder a una ruta
    Flask real. Si no, el precaché está guardando/intentando guardar
    una página que nunca existió.
    """
    assets = _extraer_static_assets_de_sw_js()
    rutas_reales = _todas_las_rutas_reales_del_proyecto()

    rutas_internas_en_precache = [
        a for a in assets
        if a.startswith("/") and not a.startswith("/static/")
    ]

    rutas_fantasma = [r for r in rutas_internas_en_precache if r not in rutas_reales]

    assert not rutas_fantasma, (
        f"static/sw.js intenta precachear rutas que NO existen en la app "
        f"Flask (revisa app.py / routes/main.py / routes/auth.py): {rutas_fantasma}"
    )


def test_paginas_de_navegacion_clave_estan_en_el_precache():
    """
    Chequeo complementario: las páginas principales que un usuario
    debería poder abrir sin internet SÍ deben estar en STATIC_ASSETS.
    Si agregas una página nueva importante, añádela también a esta
    lista para que el test te recuerde incluirla en el precaché.
    """
    assets = set(_extraer_static_assets_de_sw_js())

    paginas_clave = {
        "/",
        "/login",
        "/registro",
        "/senales",
        "/objetivos",
        "/entrenador",
        "/mapa",
        "/recordatorios",
        "/totem",
        "/offline",
    }

    faltantes = paginas_clave - assets

    assert not faltantes, (
        f"Estas páginas clave no están en STATIC_ASSETS de sw.js, así que "
        f"NO van a funcionar offline si el usuario nunca las visitó antes "
        f"estando conectado: {faltantes}"
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))