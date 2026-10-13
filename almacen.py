# almacen.py
# Leer y guardar archivos JSON dentro de la carpeta datos/.
# Este archivo NO importa customtkinter.

import json
import os

CARPETA_DATOS = "datos"


class ArchivoDanado(Exception):
    """El archivo existe, pero su contenido no es JSON válido."""


def leer_json(nombre_archivo, valor_por_defecto):
    """Lee datos/<nombre_archivo> y devuelve lo que contiene.
    - Si el archivo no existe, devuelve valor_por_defecto.
    - Si el archivo está dañado, lanza ArchivoDanado."""
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        return contenido
    except FileNotFoundError:
        # Normal la primera vez: el archivo aún no existe.
        return valor_por_defecto
    except json.JSONDecodeError:
        # El archivo existe pero está dañado: avisar en vez de fingir que está vacío.
        raise ArchivoDanado(f"El archivo {ruta} está dañado.")


def escribir_json(nombre_archivo, datos):
    """Guarda 'datos' en datos/<nombre_archivo>.
    Si el archivo que ya existe está dañado, NO lo sobrescribe: lanza ArchivoDanado."""
    # Revisión antes de escribir: si el archivo actual está dañado,
    # leer_json lanza ArchivoDanado y esta función se detiene aquí,
    # antes de abrir el archivo en modo "w" (que lo vaciaría).
    leer_json(nombre_archivo, None)

    os.makedirs(CARPETA_DATOS, exist_ok=True)
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Prueba rápida: solo corre con "python almacen.py"
    escribir_json("prueba.json", ["Cálculo", "Física"])
    print("Leído:", leer_json("prueba.json", []))
    print("No existe:", leer_json("no_existe.json", []))

    # Simular un archivo dañado
    with open(os.path.join(CARPETA_DATOS, "danado.json"), "w", encoding="utf-8") as f:
        f.write('["Cálculo", "Fís')
    try:
        leer_json("danado.json", [])
    except ArchivoDanado as error:
        print("Al leer:", error)
    try:
        escribir_json("danado.json", ["nota nueva"])
    except ArchivoDanado as error:
        print("Al guardar:", error)
    with open(os.path.join(CARPETA_DATOS, "danado.json"), encoding="utf-8") as f:
        print("El archivo dañado sigue intacto:", f.read())

    # Limpiar los archivos de prueba
    os.remove(os.path.join(CARPETA_DATOS, "prueba.json"))
    os.remove(os.path.join(CARPETA_DATOS, "danado.json"))
