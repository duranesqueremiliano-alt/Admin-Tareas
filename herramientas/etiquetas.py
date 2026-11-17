# etiquetas.py
# Lee y escribe los labels.csv de dataset/ y lleva el ESTADO de cada renglón:
#   pendiente  -> solo lo leyó el modelo
#   claude     -> Claude lo corrigió viendo la imagen (falta que tú lo confirmes)
#   ok         -> tú lo confirmaste en revisar.py: se usa para entrenar
#   descartado -> recorte malo (cortado, dos renglones, sin texto): no se usa
#
# Uso desde la terminal:
#   python herramientas/etiquetas.py resumen
#   python herramientas/etiquetas.py pendientes            # lista los renglones sin confirmar
#   python herramientas/etiquetas.py hojas carpeta_salida  # junta los recortes en hojas numeradas (para Claude)
#   python herramientas/etiquetas.py corregir textos.json  # {"entrenamiento/x.png": "texto", "...": null = descartar}
import csv
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(RAIZ, "dataset")
PARTES = ["entrenamiento", "validacion"]
CAMPOS = ["filename", "words", "ocr", "estado"]
SIN_CONFIRMAR = ("pendiente", "claude")
POR_HOJA = 10


def archivo(parte):
    return os.path.join(DATASET, parte, "labels.csv")


def leer(parte):
    if not os.path.isfile(archivo(parte)):
        return []
    with open(archivo(parte), newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for fila in filas:   # labels.csv viejos (solo filename,words): se toman como pendientes
        fila.setdefault("ocr", fila.get("words", ""))
        fila["estado"] = fila.get("estado") or "pendiente"
    return filas


def escribir(parte, filas):
    """Escribe a un archivo temporal y luego lo reemplaza: si algo falla no se pierde el CSV.
    En Windows no se puede reemplazar un archivo que otro programa tiene abierto en ese instante
    (Excel, o crear_dataset.py agregando renglones): se reintenta unos segundos."""
    temporal = archivo(parte) + ".tmp"
    with open(temporal, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)
    for intento in range(20):
        try:
            os.replace(temporal, archivo(parte))
            return
        except PermissionError:
            if intento == 19:
                raise
            time.sleep(0.25)


def agregar(parte, filas):
    """Agrega filas al final de labels.csv y lo cierra enseguida (para no bloquearlo)."""
    ruta = archivo(parte)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    nueva = not os.path.isfile(ruta) or os.path.getsize(ruta) == 0
    for intento in range(20):
        try:
            with open(ruta, "a", newline="", encoding="utf-8") as f:
                escritor = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
                if nueva:
                    escritor.writeheader()
                escritor.writerows(filas)
            return
        except PermissionError:
            if intento == 19:
                raise
            time.sleep(0.25)


def ruta_imagen(parte, fila):
    return os.path.join(DATASET, parte, fila["filename"])


def todas():
    """{parte: [filas]} de todo el dataset."""
    return {parte: leer(parte) for parte in PARTES}


def sin_confirmar():
    """[(clave 'parte/archivo', parte, fila)] de los renglones que faltan por confirmar, en orden."""
    return [(f"{parte}/{fila['filename']}", parte, fila)
            for parte, filas in todas().items() for fila in filas if fila["estado"] in SIN_CONFIRMAR]


# ----- Comandos -----
def resumen():
    conteo = {}
    for filas in todas().values():
        for fila in filas:
            conteo[fila["estado"]] = conteo.get(fila["estado"], 0) + 1
    if not conteo:
        print("No hay dataset todavía. Corre: python herramientas/crear_dataset.py tus_fotos/")
    for estado, n in sorted(conteo.items()):
        print(f"{estado:11s} {n}")


def pendientes():
    for clave, _parte, fila in sin_confirmar():
        print(f"{clave}\t[{fila['estado']}]\t{fila['words']}")


def hojas(salida):
    """Junta los recortes que solo leyó el modelo (estado 'pendiente') en imágenes de POR_HOJA
    renglones, numerados, para que Claude los lea de un vistazo. Escribe también indice.json
    (número -> clave). Los que ya corrigió Claude no se repiten."""
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(salida, exist_ok=True)
    lista = [x for x in sin_confirmar() if x[2]["estado"] == "pendiente"]
    ancho, margen, alto_num = 1400, 10, 34
    try:
        fuente = ImageFont.truetype(os.path.join(RAIZ, "fuentes", "Montserrat-Bold.ttf"), 26)
    except OSError:
        fuente = ImageFont.load_default()
    indice = {}
    for h in range(0, len(lista), POR_HOJA):
        grupo, bloques = lista[h:h + POR_HOJA], []
        for i, (clave, parte, fila) in enumerate(grupo, start=h + 1):
            indice[i] = clave
            img = Image.open(ruta_imagen(parte, fila)).convert("RGB")
            escala = min((ancho - 2 * margen) / img.width, 2.0)
            bloques.append((i, img.resize((int(img.width * escala), int(img.height * escala)))))
        hoja = Image.new("RGB", (ancho, sum(b.height + alto_num + margen for _, b in bloques) + margen), "white")
        dibujo, y = ImageDraw.Draw(hoja), margen
        for i, img in bloques:
            dibujo.text((margen, y), f"#{i}", fill=(200, 0, 0), font=fuente)
            hoja.paste(img, (margen, y + alto_num))
            y += img.height + alto_num + margen
            dibujo.line([(0, y - margen // 2), (ancho, y - margen // 2)], fill=(200, 200, 200), width=2)
        hoja.save(os.path.join(salida, f"hoja_{h // POR_HOJA + 1:02d}.png"))
    with open(os.path.join(salida, "indice.json"), "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=1)
    print(f"{len(lista)} renglones en {(len(lista) + POR_HOJA - 1) // POR_HOJA} hojas -> {salida}")


def corregir(ruta_json):
    """Aplica textos {clave: texto}. texto null o "" = descartar. Quedan como estado 'claude'."""
    with open(ruta_json, encoding="utf-8") as f:
        cambios = json.load(f)
    datos, aplicados = todas(), 0
    for clave, texto in cambios.items():
        parte, nombre = clave.split("/", 1)
        for fila in datos.get(parte, []):
            if fila["filename"] == nombre:
                if texto and texto.strip():
                    fila["words"], fila["estado"] = texto.strip(), "claude"
                else:
                    fila["estado"] = "descartado"
                aplicados += 1
                break
        else:
            print("No encontré:", clave)
    for parte, filas in datos.items():
        if filas:
            escribir(parte, filas)
    print(f"{aplicados} renglones actualizados. Revísalos con: python herramientas/revisar.py")


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "resumen"
    if comando == "resumen":
        resumen()
    elif comando == "pendientes":
        pendientes()
    elif comando == "hojas" and len(sys.argv) > 2:
        hojas(sys.argv[2])
    elif comando == "corregir" and len(sys.argv) > 2:
        corregir(sys.argv[2])
    else:
        print("Uso: etiquetas.py resumen | pendientes | hojas CARPETA | corregir ARCHIVO.json")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
