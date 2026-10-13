#Todas las funciones de las notas
from datetime import datetime
import uuid
import almacen

NOTAS = "notas.json"
FECHA = "%Y-%m-%d %H:%M"

def cargar():
    contenido = almacen.leer_json(NOTAS, [])
    return contenido

def guardar_archivo(NOTAS, lista):
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

#def titulo(nota):
    
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