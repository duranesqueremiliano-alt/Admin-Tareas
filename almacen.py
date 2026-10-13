# almacen.py
# Leer y guardar archivos JSON dentro de la carpeta datos/.

import json
import os

CARPETA_DATOS = "datos"


def leer_json(nombre_archivo, valor_por_defecto):
    """Lee datos/<nombre_archivo> y devuelve lo que contiene.
    Si no se puede leer, devuelve valor_por_defecto."""
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        return contenido
    except FileNotFoundError:
        return valor_por_defecto
    except json.JSONDecodeError:
        raise ArchivoDanado(f"El archivo {ruta} está dañado.")


def escribir_json(nombre_archivo, datos):
    """Guarda 'datos' en datos/<nombre_archivo>."""
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Prueba rápida: solo corre con "python almacen.py"
    escribir_json("prueba.json", ["Cálculo", "Física"])
    print("Leído:", leer_json("prueba.json", []))
    print("No existe:", leer_json("no_existe.json", []))
