# tareas.py
# Tareas de la escuela y de la vida diaria, con fecha límite.
from datetime import datetime
import uuid
import almacen
from notas import buscar_posicion

TAREAS = "tareas.json"
FECHA = "%Y-%m-%d %H:%M"


def cargar():
    contenido = almacen.leer_json(TAREAS, [])
    return contenido


def guardar_archivo(lista):
    almacen.escribir_json(TAREAS, lista)


def crear(titulo, fecha_limite, materia):
    Id = uuid.uuid4().hex
    fechadecreacion = datetime.now().strftime(FECHA)
    tarea = {
        "id": Id,
        "titulo": titulo,
        "descripcion": "",
        "fechacreacion": fechadecreacion,
        "fechalimite": fecha_limite,
        "materia": materia,
        "estado": "activa",
    }
    return tarea


def guardar(lista, tarea):
    posicion = buscar_posicion(lista, tarea["id"])
    if tarea["titulo"].strip() == "":
        if posicion is not None:
            lista.pop(posicion)
        return "borrada"
    if posicion is not None:
        vieja = lista.pop(posicion)
        tarea["fechacreacion"] = vieja["fechacreacion"]
        tipo = "actualizacion"
    else:
        tipo = "creacion"
    lista.insert(0, tarea)
    return tipo


def borrar(lista, id_tarea):
    posicion = buscar_posicion(lista, id_tarea)
    if posicion is None:
        return False
    lista.pop(posicion)
    return True


def esta_vencida(tarea):
    if tarea["estado"] == "completada":
        return False
    limite = datetime.strptime(tarea["fechalimite"], FECHA)
    return limite < datetime.now()


def completar(tarea):
    tarea["estado"] = "completada"


def reabrir(tarea):
    tarea["estado"] = "activa"


if __name__ == "__main__":
    lista = []
    t = crear("Ensayo", "2026-10-20 18:00", "Historia")
    print(guardar(lista, t))
    print(esta_vencida(t))
    completar(t)
    print(t["estado"])
    print(esta_vencida(t))
    print(guardar(lista, t))
    print(borrar(lista, t["id"]), len(lista))
