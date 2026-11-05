# indice_demo.py
# Demo para la presentación: buscar una nota por id en una LISTA (búsqueda lineal, O(n))
# contra buscarla en un DICCIONARIO por id (O(1) en promedio).
import time
import uuid
from notas import buscar_posicion

CUANTAS = 50000
BUSQUEDAS = 1000

lista = []
for i in range(CUANTAS):
    lista.append({"id": uuid.uuid4().hex, "texto": "Nota " + str(i)})

indice = {}
for nota in lista:
    indice[nota["id"]] = nota

# Buscamos siempre las últimas notas: el peor caso para la lista.
ids = []
for nota in lista[-BUSQUEDAS:]:
    ids.append(nota["id"])

inicio = time.perf_counter()
for id_nota in ids:
    lista[buscar_posicion(lista, id_nota)]
tiempo_lista = time.perf_counter() - inicio

inicio = time.perf_counter()
for id_nota in ids:
    indice[id_nota]
tiempo_dict = time.perf_counter() - inicio

print("Notas:", CUANTAS, "| búsquedas:", BUSQUEDAS)
print("Lista (buscar_posicion):", round(tiempo_lista * 1000, 1), "ms")
print("Diccionario por id:     ", round(tiempo_dict * 1000, 3), "ms")
print("El diccionario fue unas", round(tiempo_lista / tiempo_dict), "veces más rápido.")
