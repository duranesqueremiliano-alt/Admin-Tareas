# materias.py
# La lista de materias que comparten notas y tareas.
from m import almacen

MATERIAS = "materias.json"


def cargar():
    contenido = almacen.leer_json(MATERIAS, [])
    return contenido


def guardar_archivo(lista):
    almacen.escribir_json(MATERIAS, lista)


def agregar(lista, nombre):
    nombre = nombre.strip()
    if nombre == "":
        return False
    for materia in lista:
        if materia.lower() == nombre.lower():
            return False
    lista.append(nombre)
    return True


if __name__ == "__main__":
    lista = []
    print(agregar(lista, "  Cálculo "))
    print(agregar(lista, "cálculo"))
    print(agregar(lista, ""))
    print(agregar(lista, "Física"))
    print(lista)
