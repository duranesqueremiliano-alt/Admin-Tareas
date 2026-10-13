# almacen.py
# Leer y guardar archivos JSON dentro de la carpeta datos/.
# Este archivo NO importa customtkinter.

import json
import os
from pathlib import Path

CARPETA_DATOS = "datos"
os.makedirs("datos", exist_ok=True)

def leer_json(nombre_archivo, valor_por_defecto):
    #Lee datos/<nombre_archivo> y devuelve lo que contiene.
    #Si no se puede leer, devuelve valor_por_defecto.
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    try: 
        with open(ruta, "r", encoding="utf-8") as f: v = json.load(f)
        return v
    except FileNotFoundError:
        print('Archivo no encontrado, Intente de nuevo')
        return valor_por_defecto
    except json.JSONDecodeError:
        print('Falla en el archivo, Intente de nuevo')
        return valor_por_defecto
        
def escribir_json(nombre_archivo, datos):
    """Guarda 'datos' en datos/<nombre_archivo>."""
    os.makedirs("datos", exist_ok = True)
    ruta = os.path.join(CARPETA_DATOS, nombre_archivo)
    try: 
        with open(ruta, "w", encoding="utf-8") as f: v = json.dump(datos, f, ensure_ascii=False, indent=2)
        return v
    except FileNotFoundError:
        print('Archivo no encontrado, Intente de nuevo')
        return valor_por_defecto

if __name__ == "__main__":
    # Prueba rápida

    # TODO 7: escribe una lista de prueba en "prueba.json"
    # TODO 8: léela de vuelta y muéstrala con print
    # TODO 9: lee un archivo que no existe y muestra qué devuelve
    pass