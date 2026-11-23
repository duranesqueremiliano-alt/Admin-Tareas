# ocr.py
# Foto -> texto pensado para LETRA ESCRITA A MANO, todo sobre PyTorch.
#   1. Detector CRAFT (de EasyOCR): marca cada letra y la unión entre letras vecinas -> cajas de palabras.
#      Aquí juntamos esas cajas en renglones.
#   2. Reconocedor TrOCR manuscrito (Microsoft, entrenado con letra a mano): lee cada renglón completo.
#      Es un Transformer (imagen -> texto) que escribe el resultado pieza por pieza.
# Si entrenaste uno propio con herramientas/entrenar.py (carpeta modelos/propio_trocr) se usa ese.
import os
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_MODELOS = os.path.join(RAIZ, "modelos")
MODELO_BASE = "microsoft/trocr-base-handwritten"   # alternativa más rápida y ligera: microsoft/trocr-small-handwritten
CARPETA_PROPIO = os.path.join(CARPETA_MODELOS, "propio_trocr")
MARGEN = 6            # píxeles extra alrededor de cada renglón
MAX_TOKENS = 96       # largo máximo de lo que escribe por renglón

_modelos = None
_candado = threading.Lock()


class OCRNoInstalado(Exception):
    pass


def hay_modelo_propio():
    return os.path.isfile(os.path.join(CARPETA_PROPIO, "config.json"))


def listo():
    return _modelos is not None


def dispositivo():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def cargar_trocr(origen):
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    cache = os.path.join(CARPETA_MODELOS, "hf")
    procesador = TrOCRProcessor.from_pretrained(origen, cache_dir=cache)
    modelo = VisionEncoderDecoderModel.from_pretrained(origen, cache_dir=cache)
    return procesador, modelo


def obtener_modelos():
    """Carga detector y reconocedor la primera vez (la primera vez en la vida los descarga, ~1.4 GB)."""
    global _modelos
    with _candado:
        if _modelos is not None:
            return _modelos
        try:
            import torch
            import easyocr
            import transformers  # noqa: F401
        except ImportError as e:
            raise OCRNoInstalado("Falta instalar PyTorch/EasyOCR/transformers: pip install -r requirements.txt") from e
        os.makedirs(CARPETA_MODELOS, exist_ok=True)
        detector = easyocr.Reader(["en"], gpu=torch.cuda.is_available(), model_storage_directory=CARPETA_MODELOS,
                                  recognizer=False, verbose=False)
        procesador, modelo = cargar_trocr(CARPETA_PROPIO if hay_modelo_propio() else MODELO_BASE)
        modelo.to(dispositivo()).eval()
        _modelos = {"detector": detector, "procesador": procesador, "modelo": modelo}
        return _modelos


# ----- 1. Detección -----
def cajas_de_palabras(imagen):
    """[x1, y1, x2, y2] de cada palabra que encuentra CRAFT."""
    horizontales, libres = obtener_modelos()["detector"].detect(imagen, width_ths=0.7, add_margin=0.1)
    cajas = [[x1, y1, x2, y2] for x1, x2, y1, y2 in horizontales[0]]
    for poligono in libres[0]:   # palabras inclinadas: usamos el rectángulo que las encierra
        xs, ys = [p[0] for p in poligono], [p[1] for p in poligono]
        cajas.append([min(xs), min(ys), max(xs), max(ys)])
    return cajas


def agrupar_en_renglones(cajas):
    """Junta las cajas cuyo centro vertical cae dentro del renglón actual. Devuelve cajas de renglón."""
    renglones = []
    for x1, y1, x2, y2 in sorted(cajas, key=lambda c: (c[1] + c[3]) / 2):
        centro = (y1 + y2) / 2
        if renglones:
            r = renglones[-1]
            alto = max(r[3] - r[1], y2 - y1)
            if abs(centro - (r[1] + r[3]) / 2) < alto * 0.5:
                renglones[-1] = [min(r[0], x1), min(r[1], y1), max(r[2], x2), max(r[3], y2)]
                continue
        renglones.append([x1, y1, x2, y2])
    return renglones


def recortar(imagen, caja):
    alto, ancho = imagen.shape[:2]
    x1, y1, x2, y2 = caja
    return imagen[max(int(y1) - MARGEN, 0):min(int(y2) + MARGEN, alto),
                  max(int(x1) - MARGEN, 0):min(int(x2) + MARGEN, ancho)]


# ----- 2. Reconocimiento -----
def leer_recortes(recortes):
    """Lee varios recortes (numpy RGB) con TrOCR. Devuelve una lista de textos."""
    import torch
    from PIL import Image
    m = obtener_modelos()
    if not recortes:
        return []
    imagenes = [Image.fromarray(r) for r in recortes]
    pixeles = m["procesador"](images=imagenes, return_tensors="pt").pixel_values.to(dispositivo())
    with torch.no_grad():
        ids = m["modelo"].generate(pixeles, max_new_tokens=MAX_TOKENS, num_beams=3)
    return [t.strip() for t in m["procesador"].batch_decode(ids, skip_special_tokens=True)]


def detectar_renglones(imagen):
    """[(caja, recorte, texto)] por renglón, de arriba hacia abajo."""
    cajas = agrupar_en_renglones(cajas_de_palabras(imagen))
    recortes = [recortar(imagen, c) for c in cajas]
    pares = [(c, r) for c, r in zip(cajas, recortes) if r.size]
    textos = []
    for i in range(0, len(pares), 8):   # de 8 en 8 para no llenar la memoria
        textos += leer_recortes([r for _, r in pares[i:i + 8]])
    return [(c, r, t) for (c, r), t in zip(pares, textos)]


def foto_a_texto(ruta):
    return "\n".join(t for _, _, t in detectar_renglones(leer_imagen(ruta)) if t)


def leer_imagen(ruta):
    """Lee la imagen con Pillow (aguanta rutas con acentos) y respeta la rotación de fotos del celular."""
    import numpy as np
    from PIL import Image, ImageOps
    with Image.open(ruta) as img:
        img = ImageOps.exif_transpose(img)
        return np.array(img.convert("RGB"))
