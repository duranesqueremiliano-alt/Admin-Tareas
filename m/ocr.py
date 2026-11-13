# ocr.py
# Foto -> texto con EasyOCR (PyTorch).
#   1. CRAFT (detector) busca cada letra y la "afinidad" entre letras vecinas, y las une en palabras.
#   2. CRNN (reconocedor) lee cada palabra letra por letra (CNN + LSTM + CTC).
# El modelo se carga una sola vez (tarda) y se reutiliza.
import os
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_MODELOS = os.path.join(RAIZ, "modelos")
IDIOMAS = ["es", "en"]
MODELO_PROPIO = "propio"   # si existen modelos/propio.pth, .yaml y .py se usa en vez del de fábrica

_lector = None
_candado = threading.Lock()


class OCRNoInstalado(Exception):
    pass


def hay_modelo_propio():
    return all(os.path.isfile(os.path.join(CARPETA_MODELOS, MODELO_PROPIO + ext)) for ext in (".pth", ".yaml", ".py"))


def listo():
    return _lector is not None


def obtener_lector():
    """Crea el lector la primera vez. La primera vez en la vida descarga los modelos (~100 MB)."""
    global _lector
    with _candado:
        if _lector is not None:
            return _lector
        try:
            import torch
            import easyocr
        except ImportError as e:
            raise OCRNoInstalado("Falta instalar PyTorch/EasyOCR: pip install -r requirements.txt") from e
        os.makedirs(CARPETA_MODELOS, exist_ok=True)
        opciones = dict(gpu=torch.cuda.is_available(), model_storage_directory=CARPETA_MODELOS, verbose=False)
        if hay_modelo_propio():
            opciones.update(recog_network=MODELO_PROPIO, user_network_directory=CARPETA_MODELOS)
        _lector = easyocr.Reader(IDIOMAS, **opciones)
        return _lector


def detectar(imagen):
    """Devuelve [(caja, texto, confianza)]. imagen = ruta o arreglo numpy."""
    return obtener_lector().readtext(imagen, detail=1, paragraph=False)


def ordenar_en_lineas(resultados):
    """Agrupa las palabras detectadas en renglones (arriba->abajo) y cada renglón izquierda->derecha."""
    palabras = []
    for caja, texto, _conf in resultados:
        ys = [p[1] for p in caja]
        palabras.append({"x": min(p[0] for p in caja), "y": sum(ys) / 4, "alto": max(ys) - min(ys), "texto": texto})
    palabras.sort(key=lambda p: p["y"])
    lineas = []
    for p in palabras:
        # misma línea si su centro está a menos de medio alto del renglón actual
        if lineas and abs(p["y"] - lineas[-1]["y"]) < max(p["alto"], lineas[-1]["alto"]) / 2:
            lineas[-1]["palabras"].append(p)
        else:
            lineas.append({"y": p["y"], "alto": p["alto"], "palabras": [p]})
    return [" ".join(w["texto"] for w in sorted(l["palabras"], key=lambda w: w["x"])) for l in lineas]


def foto_a_texto(ruta):
    return "\n".join(ordenar_en_lineas(detectar(leer_imagen(ruta))))


def leer_imagen(ruta):
    """Lee la imagen con Pillow (aguanta rutas con acentos, a diferencia de cv2.imread en Windows)."""
    import numpy as np
    from PIL import Image, ImageOps
    with Image.open(ruta) as img:
        img = ImageOps.exif_transpose(img)   # respeta la rotación de fotos del celular
        return np.array(img.convert("RGB"))
