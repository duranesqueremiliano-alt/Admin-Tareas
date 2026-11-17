# crear_dataset.py
# Convierte TUS fotos de letra a mano en datos de entrenamiento.
# Recorta cada renglón (igual que lo hace la app) y lo guarda como imagen junto con lo que el modelo leyó.
# Tú corriges labels.csv y luego entrenas con:  python herramientas/entrenar.py
#
# Uso:
#   python herramientas/crear_dataset.py foto1.jpg foto2.png
#   python herramientas/crear_dataset.py carpeta_con_fotos/
#   python herramientas/crear_dataset.py --repetir foto1.jpg   # vuelve a cortar una foto que ya estaba
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m import ocr  # noqa: E402
import etiquetas  # noqa: E402

SALIDA = os.path.join(RAIZ, "dataset")
CADA_CUANTO_VALIDACION = 10   # 1 de cada 10 renglones va a validación, el resto a entrenamiento
EXTENSIONES = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


def listar_fotos(argumentos):
    fotos = []
    for arg in argumentos:
        if os.path.isdir(arg):
            fotos += [os.path.join(arg, f) for f in sorted(os.listdir(arg)) if f.lower().endswith(EXTENSIONES)]
        elif os.path.isfile(arg):
            fotos.append(arg)
        else:
            print("No existe:", arg)
    return fotos


def ya_procesadas(partes):
    """Nombres base de las fotos que ya tienen renglones en dataset/ (foto_00012.png -> foto)."""
    nombres = set()
    for parte in partes.values():
        for f in os.listdir(parte["carpeta"]):
            coincide = re.fullmatch(r"(.+)_\d{5}\.png", f)
            if coincide:
                nombres.add(coincide.group(1))
    return nombres


def preparar_carpeta(nombre):
    carpeta = os.path.join(SALIDA, nombre)
    os.makedirs(carpeta, exist_ok=True)
    total = len([f for f in os.listdir(carpeta) if f.endswith(".png")])
    return {"nombre": nombre, "carpeta": carpeta, "total": total}


def main():
    from PIL import Image
    argumentos = [a for a in sys.argv[1:] if a != "--repetir"]
    repetir = len(argumentos) != len(sys.argv) - 1
    fotos = listar_fotos(argumentos)
    if not fotos:
        print("Uso: python herramientas/crear_dataset.py foto1.jpg [foto2.jpg ...]   o   carpeta/")
        return 1
    partes = {"entrenamiento": preparar_carpeta("entrenamiento"), "validacion": preparar_carpeta("validacion")}
    contador = sum(p["total"] for p in partes.values())
    hechas = set() if repetir else ya_procesadas(partes)
    for ruta in fotos:
        base = os.path.splitext(os.path.basename(ruta))[0]
        if base in hechas:   # si no, se duplicarían sus renglones
            print("Ya estaba en dataset/, se salta:", ruta, "(usa --repetir para cortarla de nuevo)")
            continue
        print("Procesando", ruta)
        for _caja, recorte, texto in ocr.detectar_renglones(ocr.leer_imagen(ruta)):
            contador += 1
            parte = partes["validacion" if contador % CADA_CUANTO_VALIDACION == 0 else "entrenamiento"]
            nombre = f"{base}_{contador:05d}.png"
            Image.fromarray(recorte).save(os.path.join(parte["carpeta"], nombre))
            # se abre y se cierra en cada renglón: así revisar.py puede guardar mientras esto corre
            etiquetas.agregar(parte["nombre"], [{"filename": nombre, "words": texto, "ocr": texto,
                                                 "estado": "pendiente"}])
            print(f"   {nombre}  ->  {texto!r}")
    print("\nListo. Revisa cada renglón con:  python herramientas/revisar.py")
    print("(o pídele a Claude /transcribir-apuntes para que los corrija antes). Luego: python herramientas/entrenar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
