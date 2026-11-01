#Todas las funciones de las notas
from datetime import datetime
import uuid
import almacen

NOTAS = "notas.json"
FECHA = "%Y-%m-%d %H:%M"

def cargar():
    contenido = almacen.leer_json(NOTAS, [])
    return contenido

def guardar_archivo(lista):
    almacen.escribir_json(NOTAS, lista)

def crear(materia):
    Id = uuid.uuid4().hex
    fechadecreacion = datetime.now().strftime(FECHA)
    nota = {
        "id": (Id),
        "texto": "",
        "materia": materia,
        "palabrasclave": [],
        "rutaimagen": None,
        "fechacreacion": fechadecreacion,
    }
    return nota

def buscar_posicion(lista, id_nota):
    for i, nota in enumerate(lista):
        if nota["id"] == (id_nota):
            return i
    return None

def guardar(lista, nota):
    posicion = buscar_posicion(lista, nota["id"])
    if nota["texto"].strip() == "":
        if posicion is not None:
            lista.pop(posicion)
        return "borrada"
    elif posicion != None:
        vieja = lista.pop(posicion)
        fecha = vieja["fechacreacion"]
        nota["fechacreacion"] = fecha
        tipo = "actualizacion"
    else:
        tipo = "creacion"
    lista.insert(0, nota)
    return tipo

def titulo(nota):
    for linea in nota["texto"].splitlines():
        if linea.strip() != "":
            return linea.strip()
    return "Sin título"

def borrar(lista, id_nota):
    posicion = buscar_posicion(lista, id_nota)
    if posicion is None:
        return False
    lista.pop(posicion)
    return True

def mover(lista, id_nota, nueva_posicion):
    posicion = buscar_posicion(lista, id_nota)
    if posicion is None:
        return
    nota = lista.pop(posicion)
    lista.insert(nueva_posicion, nota)

def buscar(lista, texto):
    texto = texto.strip().lower()
    if texto == "":
        return lista
    resultados = []
    for nota in lista:
        encontrada = texto in nota["texto"].lower()
        for palabra in nota["palabrasclave"]:
            if texto in palabra.lower():
                encontrada = True
        if encontrada:
            resultados.append(nota)
    return resultados

if __name__ == "__main__":
    lista = []
    a = crear("Física")
    a["texto"] = "Nota A"
    print(guardar(lista, a))            # creacion
    b = crear("Física")
    b["texto"] = "Nota B"
    print(guardar(lista, b))            # creacion
    a["texto"] = "Nota A editada"
    print(guardar(lista, a))            # actualizacion
    print([n["texto"] for n in lista])  # ['Nota A editada', 'Nota B']

    # 1.1 nota nueva vacía
    n = crear("Física")
    print(guardar(lista, n))            # borrada
    print(len(lista))                   # 2

    # 2.1 titulo
    print(titulo(a))                                 # Nota A editada
    print(titulo({"texto": "\n\n  Límites \nbla"}))  # Límites
    print(titulo({"texto": ""}))                     # Sin título

    # 2.2 borrar
    print(borrar(lista, b["id"]))       # True
    print(borrar(lista, b["id"]))       # False
    print([n["texto"] for n in lista])  # ['Nota A editada']

    # 2.3 mover
    c = crear("Cálculo")
    c["texto"] = "Derivadas"
    guardar(lista, c)
    print([n["texto"] for n in lista])  # ['Derivadas', 'Nota A editada']
    mover(lista, c["id"], 1)
    print([n["texto"] for n in lista])  # ['Nota A editada', 'Derivadas']

    # 2.4 buscar
    c["palabrasclave"] = ["cálculo"]
    print([n["texto"] for n in buscar(lista, "DERIV")])  # ['Derivadas']
    print([n["texto"] for n in buscar(lista, "CÁL")])    # ['Derivadas']
    print(len(buscar(lista, "  ")))                      # 2

    # 1.2 guardar_archivo
    # OJO: esta prueba escribe datos/notas.json. Quítala cuando empieces a usar la app con notas reales.
    guardar_archivo(lista)
    print([n["texto"] for n in cargar()])  # ['Nota A editada', 'Derivadas']
