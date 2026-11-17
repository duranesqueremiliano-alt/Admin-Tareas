# ocr.py
# Foto -> texto pensado para LETRA ESCRITA A MANO, todo sobre PyTorch.
#   1. Detector CRAFT (de EasyOCR): marca cada letra y la unión entre letras vecinas -> cajas de palabras.
#      Aquí juntamos esas cajas en renglones.
#   2. Reconocedor TrOCR manuscrito (Microsoft, entrenado con letra a mano): lee cada renglón completo.
#      Es un Transformer (imagen -> texto) que escribe el resultado pieza por pieza.
# Si entrenaste uno propio con herramientas/entrenar.py (carpeta modelos/propio_trocr) se usa ese.
import math
import os
import statistics
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_MODELOS = os.path.join(RAIZ, "modelos")
MODELO_BASE = "microsoft/trocr-base-handwritten"   # alternativa más rápida y ligera: microsoft/trocr-small-handwritten
CARPETA_PROPIO = os.path.join(CARPETA_MODELOS, "propio_trocr")
MARGEN = 6            # píxeles extra alrededor de cada renglón
MAX_TOKENS = 96       # largo máximo de lo que escribe por renglón
LADO_MAXIMO = 2400    # las fotos más grandes se reducen a este lado mayor (suficiente para leer una hoja)

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
    from transformers.utils import logging as registro
    registro.set_verbosity_error()        # oculta el reporte "MISSING pooler": esa capa no se usa al leer
    registro.disable_progress_bar()
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


def inclinacion(imagen, cajas=None, maximo=10.0):
    """Ángulo (grados, como lo usa PIL.rotate) que deja los renglones horizontales.
    Prueba ángulos y se queda con el que hace más "nítido" el perfil horizontal de la tinta:
    con los renglones derechos, las filas con texto y las vacías se alternan con fuerza.
    Solo mira la zona con texto (cajas) y toma como tinta lo que es más oscuro que su alrededor,
    para que el fondo, la mesa o una laptop en la foto no confundan."""
    import numpy as np
    from PIL import Image, ImageFilter
    gris = Image.fromarray(imagen).convert("L")
    if cajas:
        alto, ancho = imagen.shape[:2]
        x1 = max(min(c[0] for c in cajas), 0)
        y1 = max(min(c[1] for c in cajas), 0)
        x2 = min(max(c[2] for c in cajas), ancho)
        y2 = min(max(c[3] for c in cajas), alto)
        if x2 - x1 > 50 and y2 - y1 > 50:
            gris = gris.crop((int(x1), int(y1), int(x2), int(y2)))
    gris.thumbnail((900, 900))
    arreglo = np.asarray(gris, dtype=np.float32)
    fondo = np.asarray(gris.filter(ImageFilter.BoxBlur(12)), dtype=np.float32)
    tinta = Image.fromarray(((arreglo < fondo - 20) * 255).astype(np.uint8))

    def nitidez(angulo):
        perfil = np.asarray(tinta.rotate(angulo, resample=Image.NEAREST), dtype=np.float32).sum(axis=1)
        return float(np.sum(np.diff(perfil) ** 2))

    mejor = max(np.arange(-maximo, maximo + 0.01, 0.5), key=nitidez)
    mejor = max(np.arange(mejor - 0.5, mejor + 0.51, 0.1), key=nitidez)   # afinar
    return float(round(mejor, 2))


def _girar_punto(x, y, centro, angulo):
    """Dónde queda (x, y) al girar la imagen `angulo` grados (como PIL.rotate) alrededor de `centro`."""
    a = math.radians(angulo)
    dx, dy = x - centro[0], y - centro[1]
    return centro[0] + dx * math.cos(a) + dy * math.sin(a), centro[1] - dx * math.sin(a) + dy * math.cos(a)


def agrupar_en_renglones(cajas, angulo=0.0, centro=(0.0, 0.0)):
    """Junta las palabras en renglones. Devuelve (grupos, alto_normal): cada grupo es la lista de
    índices de `cajas` de un renglón, de arriba hacia abajo.
    - Agrupa como si la foto estuviera enderezada `angulo` grados (los renglones inclinados se cruzan).
    - Descarta cajas mucho más altas o bajas que una palabra normal (tachones, palomitas, manchas).
    - Una palabra entra a un renglón si su centro está cerca del centro PROMEDIO del renglón
      (no de la caja acumulada, que crece y se traga el renglón de abajo)."""
    if not cajas:
        return [], 0.0
    seno = abs(math.sin(math.radians(angulo)))
    puntos = []
    for i, (x1, y1, x2, y2) in enumerate(cajas):
        _, cy = _girar_punto((x1 + x2) / 2, (y1 + y2) / 2, centro, angulo)
        alto = max((y2 - y1) - (x2 - x1) * seno, 0.4 * (y2 - y1))   # la caja inclinada sale más alta
        puntos.append((i, cy, alto))
    alto_normal = statistics.median(p[2] for p in puntos)
    puntos = [p for p in puntos if 0.3 * alto_normal <= p[2] <= 2.2 * alto_normal]
    renglones = []
    for i, cy, _alto in sorted(puntos, key=lambda p: p[1]):
        for r in renglones:
            if abs(cy - r["centro"]) < 0.6 * alto_normal:
                r["indices"].append(i)
                r["suma"] += cy
                r["centro"] = r["suma"] / len(r["indices"])
                break
        else:
            renglones.append({"centro": cy, "suma": cy, "indices": [i]})
    grupos = [r["indices"] for r in renglones]
    return refinar_renglones(grupos, cajas, angulo, alto_normal), alto_normal


def _recta(cajas, angulo):
    """(pendiente, ordenada) de la recta que pasa por los centros de las palabras de un renglón.
    Con una sola palabra (o muy juntas) usa la inclinación de la página."""
    import numpy as np
    xs = [(c[0] + c[2]) / 2 for c in cajas]
    ys = [(c[1] + c[3]) / 2 for c in cajas]
    m_pagina = math.tan(math.radians(angulo))
    alto = statistics.median(c[3] - c[1] for c in cajas)
    if len(cajas) >= 2 and max(xs) - min(xs) > 3 * alto:
        m = float(np.polyfit(xs, ys, 1)[0])
        tope = math.tan(math.radians(6))
        m = max(m_pagina - tope, min(m_pagina + tope, m))
    else:
        m = m_pagina
    b = statistics.mean(y - m * x for x, y in zip(xs, ys))
    return m, b


def refinar_renglones(grupos, cajas, angulo, alto_normal, vueltas=3):
    """En fotos con perspectiva cada renglón tiene su propia inclinación, y agrupar con un solo
    ángulo parte renglones o los mezcla. Aquí: recta por renglón -> cada palabra va a la recta más
    cercana -> se juntan renglones que son el mismo. Se repite unas vueltas."""
    centro_x = statistics.median((c[0] + c[2]) / 2 for c in cajas)
    for _ in range(vueltas):
        grupos = [g for g in grupos if g]
        rectas = [_recta([cajas[i] for i in g], angulo) for g in grupos]
        # juntar renglones cuyas rectas casi coinciden
        orden = sorted(range(len(grupos)), key=lambda k: rectas[k][0] * centro_x + rectas[k][1])
        juntos, rectas_juntas = [], []
        for k in orden:
            m, b = rectas[k]
            if rectas_juntas:
                m0, b0 = rectas_juntas[-1]
                if abs((m * centro_x + b) - (m0 * centro_x + b0)) < 0.45 * alto_normal:
                    juntos[-1] = juntos[-1] + grupos[k]
                    rectas_juntas[-1] = _recta([cajas[i] for i in juntos[-1]], angulo)
                    continue
            juntos.append(list(grupos[k]))
            rectas_juntas.append((m, b))
        # cada palabra a la recta más cercana
        nuevos = [[] for _ in juntos]
        for g in juntos:
            for i in g:
                x, y = (cajas[i][0] + cajas[i][2]) / 2, (cajas[i][1] + cajas[i][3]) / 2
                k = min(range(len(rectas_juntas)), key=lambda k: abs(y - (rectas_juntas[k][0] * x + rectas_juntas[k][1])))
                nuevos[k].append(i)
        grupos = nuevos
    grupos = [g for g in grupos if g]
    rectas = [_recta([cajas[i] for i in g], angulo) for g in grupos]
    return [g for _, g in sorted(zip(rectas, grupos), key=lambda p: p[0][0] * centro_x + p[0][1])]


def recortar_renglon(imagen, cajas, angulo_pagina, izquierda, derecha):
    """Recorta UN renglón enderezándolo con su propio ángulo: ajusta una recta a los centros de sus
    palabras (en fotos con perspectiva cada renglón está inclinado distinto), gira la foto alrededor
    del renglón y corta una franja de su alto. Devuelve (caja aproximada, recorte)."""
    import numpy as np
    from PIL import Image
    # misma recta que usó refinar_renglones (con una sola palabra, o palabras apiladas, toma la de la página)
    m, b = _recta(cajas, angulo_pagina)
    angulo = max(angulo_pagina - 4, min(angulo_pagina + 4, math.degrees(math.atan(m))))   # sin ángulos locos
    medio_x = (izquierda + derecha) / 2
    centro_y = m * medio_x + b
    seno = abs(math.sin(math.radians(angulo)))
    alto = statistics.median(max((c[3] - c[1]) - (c[2] - c[0]) * seno, 0.4 * (c[3] - c[1])) for c in cajas)
    medio = 0.65 * alto + MARGEN
    girada = Image.fromarray(imagen).rotate(angulo, resample=Image.BICUBIC, center=(medio_x, centro_y),
                                            fillcolor=(255, 255, 255))
    caja = [izquierda, centro_y - medio, derecha, centro_y + medio]
    alto_img, ancho_img = imagen.shape[:2]
    recorte = np.array(girada.crop((int(max(izquierda, 0)), int(max(centro_y - medio, 0)),
                                    int(min(derecha, ancho_img)), int(min(centro_y + medio, alto_img)))))
    return caja, recorte


def renglones_de(imagen):
    """[(caja, recorte)] de cada renglón de la foto, de arriba hacia abajo."""
    cajas = cajas_de_palabras(imagen)
    if not cajas:
        return []
    alto_img, ancho_img = imagen.shape[:2]
    centro = (ancho_img / 2, alto_img / 2)
    angulo = inclinacion(imagen, cajas)
    grupos, alto_normal = agrupar_en_renglones(cajas, angulo, centro)
    usadas = [cajas[i] for g in grupos for i in g]
    if not usadas:
        return []
    # cada renglón cruza todo el ancho del texto (+ holgura de ~1.5 letras): así no se pierden
    # palabras de las orillas que el detector no marcó
    holgura = 1.5 * alto_normal
    izquierda = max(min(c[0] for c in usadas) - holgura, 0)
    derecha = min(max(c[2] for c in usadas) + holgura, ancho_img)
    resultado = []
    for g in grupos:
        caja, recorte = recortar_renglon(imagen, [cajas[i] for i in g], angulo, izquierda, derecha)
        if recorte.size:
            resultado.append((caja, recorte))
    return resultado


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
    pares = renglones_de(imagen)
    textos = []
    for i in range(0, len(pares), 8):   # de 8 en 8 para no llenar la memoria
        textos += leer_recortes([r for _, r in pares[i:i + 8]])
    return [(c, r, t) for (c, r), t in zip(pares, textos)]


def foto_a_texto(ruta):
    return "\n".join(t for _, _, t in detectar_renglones(leer_imagen(ruta)) if t)


def leer_imagen(ruta):
    """Lee la imagen con Pillow (aguanta rutas con acentos), respeta la rotación de fotos del celular
    y la reduce si es enorme: más píxeles no ayudan a leer y en CPU la vuelven lentísima."""
    import numpy as np
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = None   # la reducimos enseguida, así que no hace falta el aviso de "imagen gigante"
    with Image.open(ruta) as img:
        img.draft("RGB", (LADO_MAXIMO, LADO_MAXIMO))   # en JPEG decodifica ya reducido (mucho más rápido)
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)   # mantiene la proporción
        return np.array(img)
