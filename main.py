# main.py

# Esto es una lista que simulará nuestra base de datos por ahora
base_de_datos_suenos = []

# Función para registrar un nuevo sueño
def registrar_sueno(titulo, descripcion, fecha, categorias, destacado, calidad_sueno):
    # Creamos el diccionario con toda la información del sueño
    nuevo_sueno = {
        "id": len(base_de_datos_suenos) + 1, # Autogenera un ID único (1, 2, 3...)
        "fecha": fecha,
        "titulo": titulo,
        "descripcion": descripcion,
        "categorias": categorias, # Aquí podemos meter varias, ej: ["lucido", "pesadilla"]
        "destacado": destacado,   # Será True (Verdadero) o False (Falso)
        "calidad_sueno": calidad_sueno # Puntuación del 1 al 5
    }
    
    # Guardamos el sueño en nuestra lista
    base_de_datos_suenos.append(nuevo_sueno)
    print(f"¡Sueño '{titulo}' registrado con éxito!")
    

#=====================================
# FUNCIONES DE BUSQUEDA Y ESTADISTICAS
#=====================================

# 1. Buscador por Palabra Clave
def buscar_por_palabra(palabra):
    print(f"\n🔍 Buscando la palabra '{palabra}' en tus sueños...")
    resultados = []
    
    for sueno in base_de_datos_suenos:
        # Convertimos a minúsculas (.lower()) para que busque igual "Chicle" o "chicle"
        if palabra.lower() in sueno["descripcion"].lower() or palabra.lower() in sueno["titulo"].lower():
            resultados.append(sueno)
            
    if len(resultados) == 0:
        print("❌ No se encontraron sueños con esa palabra.")
    else:
        print(f"✅ Se encontraron {len(resultados)} sueño(s):")
        for r in resultados:
            print(f"- [{r['fecha']}] {r['titulo']}: {r['descripcion']}")


# 2. Contador de Patrones (Estadísticas de palabras)
def contar_repeticiones_palabra(palabra):
    contador = 0
    palabra_buscar = palabra.lower()
    
    for sueno in base_de_datos_suenos:
        # Contamos cuántas veces aparece la palabra exacta en la descripción
        texto = sueno["descripcion"].lower()
        contador += texto.count(palabra_buscar)
        
    print(f"\n📊 ESTADÍSTICAS: La palabra '{palabra}' ha aparecido {contador} veces en total en tus descripciones.")
    
# 3. Mostrar Sueños Destacados (Tipo WhatsApp)
def mostrar_destacados():
    print("\n⭐ [ZONA] SUEÑOS DESTACADOS:")
    encontrados = False
    
    for sueno in base_de_datos_suenos:
        if sueno["destacado"] == True: # Si la casilla destacado es Verdadera
            print(f"- [{sueno['fecha']}] ⭐ {sueno['titulo']}")
            encontrados = True
            
    if not encontrados:
        print("No tienes sueños destacados todavía.")

# 4. Mostrar Sueños por Categoría Específica (Lúcidos, Pesadillas, etc.)
def mostrar_por_categoria(categoria_buscar):
    # Usamos .upper() para que resalte visualmente en la consola
    print(f"\n📁 [ZONA] SUEÑOS CATEGORÍA: {categoria_buscar.upper()}")
    contador = 0
    
    for sueno in base_de_datos_suenos:
        # Verificamos si la categoría que buscamos está dentro de la lista de categorías del sueño
        if categoria_buscar.lower() in sueno["categorias"]:
            print(f"- [{sueno['fecha']}] {sueno['titulo']} (Calidad: {sueno['calidad_sueno']}/5)")
            contador += 1
            
    if contador == 0:
        print(f"No hay sueños registrados en la categoría '{categoria_buscar}'.")    

# 5. Función que simula el menú de "3 puntos" (Editar, Eliminar, Organizar)
def modificar_sueno(id_sueno, accion, nuevo_valor=None):
    # Primero buscamos el sueño por su ID
    sueno_encontrado = None
    for sueno in base_de_datos_suenos:
        if sueno["id"] == id_sueno:
            sueno_encontrado = sueno
            break # Si lo encuentra, rompe el bucle para no seguir buscando
            
    if not sueno_encontrado:
        print(f"❌ No se encontró ningún sueño con el ID {id_sueno}")
        return

    # Ahora ejecutamos la acción según lo que el usuario elija
    if accion == "eliminar":
        base_de_datos_suenos.remove(sueno_encontrado)
        print(f"🗑️ Sueño ID {id_sueno} ('{sueno_encontrado['titulo']}') eliminado correctamente.")
        
    elif accion == "editar_texto":
        # Asumimos que nuevo_valor será un diccionario con los cambios
        if "titulo" in nuevo_valor: sueno_encontrado["titulo"] = nuevo_valor["titulo"]
        if "descripcion" in nuevo_valor: sueno_encontrado["descripcion"] = nuevo_valor["descripcion"]
        print(f"📝 Texto del sueño ID {id_sueno} actualizado.")
        
    elif accion == "organizar":
        # Cambiar o añadir categorías (nuevo_valor será la lista de nuevas categorías)
        sueno_encontrado["categorias"] = nuevo_valor
        print(f"🔄 Categorías del sueño ID {id_sueno} actualizadas a: {nuevo_valor}")
        
    elif accion == "destacar":
        # Cambia el estado (True/False)
        sueno_encontrado["destacado"] = not sueno_encontrado["destacado"] # Invierte el valor actual
        estado = "destacado" if sueno_encontrado["destacado"] else "quitado de destacados"
        print(f"⭐ Sueño ID {id_sueno} ha sido {estado}.")







# --- PRUEBA DEL CÓDIGO ---
# --- PRUEBAS CON MÁS SUEÑOS ---
# Sueño 1 (Tiene chicle)
registrar_sueno(
    titulo="Volando sobre la ciudad",
    descripcion="Estaba volando muy alto, pero de repente se me cayó un chicle en la boca y no podía hablar.",
    fecha="2026-07-15",
    categorias=["lucido", "pesadilla"],
    destacado=True,
    calidad_sueno=5
)

# Sueño 2 (No tiene chicle)
registrar_sueno(
    titulo="Examen sin estudiar",
    descripcion="Llegaba a la universidad y había un examen sorpresa de matemáticas. Qué pesadilla.",
    fecha="2026-07-17",
    categorias=["pesadilla"],
    destacado=False,
    calidad_sueno=2
)

# Sueño 3 (Tiene chicle otra vez)
registrar_sueno(
    titulo="Atrapado en el centro comercial",
    descripcion="La gente corría y yo estaba comprando un chicle gigante. El chicle se me pegó en los dedos.",
    fecha="2026-07-19",
    categorias=["bonito"],
    destacado=False,
    calidad_sueno=4
)

# --- EJECUTAMOS LAS PRUEBAS DE LAS SECCIONES ---

# --- PRUEBAS DE GESTIÓN (MENÚ 3 PUNTOS) ---

print("\n--- ESTADO INICIAL DEL SUEÑO 2 ---")
print(base_de_datos_suenos[1]) # Imprime el segundo sueño (ID 2, índice 1)

# 1. Probamos EDITAR el texto del Sueño 2
modificar_sueno(id_sueno=2, accion="editar_texto", nuevo_valor={"titulo": "¡Examen de matemáticas de terror!", "descripcion": "Era horrible, no sabía usar la calculadora."})

# 2. Probamos ORGANIZAR (cambiar de categoría) el Sueño 2
modificar_sueno(id_sueno=2, accion="organizar", nuevo_valor=["pesadilla", "lucido"])

# 3. Probamos DESTACAR el Sueño 2
modificar_sueno(id_sueno=2, accion="destacar")

print("\n--- ESTADO FINAL DEL SUEÑO 2 ---")
print(base_de_datos_suenos[1])

# 4. Probamos ELIMINAR el Sueño 3
modificar_sueno(id_sueno=3, accion="eliminar")
print(f"Total de sueños en la base de datos ahora: {len(base_de_datos_suenos)}")