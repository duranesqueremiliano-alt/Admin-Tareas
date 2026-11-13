# crear_dataset.py
# Convierte TUS fotos en datos de entrenamiento para EasyOCR.
# Recorta cada palabra que detecta CRAFT y la guarda como imagen, con lo que el modelo leyó.
# Tú corriges labels.csv y con eso reentrenas el reconocedor (ver README, "Entrenar con tus datos").
#
# Uso:
#   python herramientas/crear_dataset.py foto1.jpg foto2.png
#   python herramientas/crear_dataset.py carpeta_con_fotos/
import csv
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from m import ocr  # noqa: E402

SALIDA = os.path.join(RAIZ, "dataset")
CADA_CUANTO_VALIDACION = 10   # 1 de cada 10 recortes va a validación, el resto a entrenamiento
MARGEN = 4                    # píxeles extra alrededor de cada palabra
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


def preparar_carpeta(nombre):
    carpeta = os.path.join(SALIDA, nombre)
    os.makedirs(carpeta, exist_ok=True)
    etiquetas = os.path.join(carpeta, "labels.csv")
    nueva = not os.path.isfile(etiquetas)
    archivo = open(etiquetas, "a", newline="", encoding="utf-8")
    escritor = csv.writer(archivo)
    if nueva:
        escritor.writerow(["filename", "words"])
    total = len([f for f in os.listdir(carpeta) if f.endswith(".png")])
    return {"carpeta": carpeta, "archivo": archivo, "escritor": escritor, "total": total}


def recortar(imagen, caja):
    alto, ancho = imagen.shape[:2]
    x1 = max(int(min(p[0] for p in caja)) - MARGEN, 0)
    y1 = max(int(min(p[1] for p in caja)) - MARGEN, 0)
    x2 = min(int(max(p[0] for p in caja)) + MARGEN, ancho)
    y2 = min(int(max(p[1] for p in caja)) + MARGEN, alto)
    return imagen[y1:y2, x1:x2]


def main():
    from PIL import Image
    fotos = listar_fotos(sys.argv[1:])
    if not fotos:
        print("Uso: python herramientas/crear_dataset.py foto1.jpg [foto2.jpg ...]   o   carpeta/")
        return 1
    partes = {"entrenamiento": preparar_carpeta("entrenamiento"), "validacion": preparar_carpeta("validacion")}
    contador = sum(p["total"] for p in partes.values())
    for ruta in fotos:
        print("Procesando", ruta)
        imagen = ocr.leer_imagen(ruta)
        base = os.path.splitext(os.path.basename(ruta))[0]
        for caja, texto, confianza in ocr.detectar(imagen):
            recorte = recortar(imagen, caja)
            if recorte.size == 0:
                continue
            contador += 1
            parte = partes["validacion" if contador % CADA_CUANTO_VALIDACION == 0 else "entrenamiento"]
            nombre = f"{base}_{contador:05d}.png"
            Image.fromarray(recorte).save(os.path.join(parte["carpeta"], nombre))
            parte["escritor"].writerow([nombre, texto])
            print(f"   {nombre}  ->  {texto!r}  ({confianza:.0%})")
    for parte in partes.values():
        parte["archivo"].close()
    print("\nListo. Ahora abre dataset/entrenamiento/labels.csv y dataset/validacion/labels.csv")
    print("y corrige la columna 'words' para que diga EXACTAMENTE lo que está escrito en cada recorte.")
    print("Borra las filas (y sus .png) de recortes que no sirvan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
