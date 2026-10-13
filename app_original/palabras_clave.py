"""
Extracción de palabras clave de las notas.

1) Con IA (Claude): si hay una clave de API configurada, se le pide al modelo
   las palabras clave de la nota. Necesita internet.
2) Sin internet o sin clave: un extractor local de procesamiento de lenguaje
   natural (algoritmo RAKE + TF-IDF) con palabras vacías del español.
   Funciona siempre y no envía nada fuera de la computadora.
"""

import json
import math
import os
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

ARCHIVO_CONFIG = Path(__file__).resolve().parent / "config.json"
MODELO_IA = "claude-haiku-4-5-20251001"
URL_API = "https://api.anthropic.com/v1/messages"

PALABRAS_VACIAS = set("""
a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas aquello aquellos aqui asi aun aunque
bajo bien cada casi como con contra cual cuales cualquier cuando cuanto de del desde donde dos e el ella ellas ello
ellos en entonces entre era eran eres es esa esas ese eso esos esta estaba estaban estado estamos estan estar estas
este esto estos fue fueron fui ha haber habia hacen hacer hace hacia han hasta hay he la las le les lo los mas me
mi mis mismo mismos mucho muchos muy nada ni no nos nosotros nuestra nuestro o os otra otras otro otros para pero poco
por porque pues que quien quienes se sea sean ser si sido siempre sin sino sobre solo son su sus tal tambien tan tanto
te tener tiene tienen todo todos toda todas tu tus u un una unas uno unos usted ustedes va van y ya yo cosa cosas
puede pueden podemos debe deben dice dijo segun tipo tipos forma formas manera parte partes ejemplo ejemplos etc
clase tema temas profesor profesora maestro maestra hoy ayer manana dia dias vez veces luego despues primero primera
segundo segunda mismo misma importante importantes ver vimos visto hecho cual cuales cuyo cuya donde mientras
sigue siguen usa usan usar usamos usado utiliza utilizan utilizar convierte convierten gracias incluye incluyen
ocurre ocurren obtiene obtienen obtener calcula calcular sirve sirven permite permiten llama llaman llamado llamada
conoce conocen significa representa representan existe existen depende dependen forman genera generan produce
producen contiene contienen consiste consisten tarea tareas examen nota notas apunte apuntes principal principales
siguiente siguientes general varios varias diferente diferentes distinto distintos distinta nuevo nueva gran grande
mayor menor mejor peor decir explica explico dijo recordar revisar estudiar entregar ser seria pasa pasan tienes
mediante igual traves dentro fuera cerca durante tras
the of and to in is for on with as by an be are this that it
""".split())


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def raiz(palabra):
    """Normalización muy simple para tratar singular y plural como iguales."""
    p = sin_acentos(palabra)
    for fin in ("es", "s"):
        if len(p) > 5 and p.endswith(fin):
            return p[: -len(fin)]
    return p


# ==============================================================
# EXTRACTOR LOCAL (RAKE + TF-IDF)
# ==============================================================

_SEPARADORES = re.compile(r"[.,;:!?¿¡()\[\]{}\"“”'’\n\r\t•\-–—/|=+*<>]+")
_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+")


_VERBO = re.compile(r"(ó|aron|ieron|aban|ían|ando|iendo)$")
_CONECTORES = {"de", "del"}


def _es_vacia(palabra):
    p = sin_acentos(palabra)
    if p in PALABRAS_VACIAS or len(p) < 3 or p.isdigit():
        return True
    return bool(_VERBO.search(palabra.lower())) and len(p) > 4


def _frases_candidatas(texto):
    """
    Divide el texto en frases candidatas: secuencias de palabras con contenido,
    cortadas por palabras vacías o signos. Se permite un 'de' en medio
    (ej. 'ciclo de Calvin'). Cada palabra va con True si es inicio de oración.
    """
    frases = []
    for segmento in _SEPARADORES.split(texto):
        palabras = _PALABRA.findall(segmento)
        actual = []
        i = 0
        while i < len(palabras):
            palabra = palabras[i]
            inicio = i == 0
            if not _es_vacia(palabra):
                actual.append((palabra, inicio))
            elif (sin_acentos(palabra) in _CONECTORES and actual and i + 1 < len(palabras)
                  and not _es_vacia(palabras[i + 1])):
                actual.append((palabra, None))          # conector, no cuenta como palabra clave
            elif actual:
                frases.append(actual)
                actual = []
            i += 1
        if actual:
            frases.append(actual)

    resultado = []
    for f in frases:
        contenido = [x for x in f if x[1] is not None]
        if len(contenido) <= 3:
            resultado.append(f)
        else:                      # frase demasiado larga: se toman las palabras sueltas
            resultado.extend([x] for x in contenido)
    return resultado


def _mostrar(frase):
    """Respeta mayúsculas de nombres propios y siglas; lo demás en minúsculas."""
    propia = any(p[:1].isupper() and not inicio and inicio is not None for p, inicio in frase)
    if propia:
        return " ".join(p for p, _ in frase)
    return " ".join(p if (p.isupper() and len(p) > 1) else p.lower() for p, _ in frase)


def extraer_local(texto, otros_textos=(), cantidad=6):
    frases = _frases_candidatas(texto)
    if not frases:
        return []

    frecuencia = Counter()
    grado = Counter()
    for f in frases:
        contenido = [p for p, ini in f if ini is not None]
        for p in contenido:
            r = raiz(p)
            frecuencia[r] += 1
            grado[r] += len(contenido) - 1

    # IDF: penaliza palabras que aparecen en muchas otras notas
    documentos = [{raiz(p) for p in _PALABRA.findall(t)} for t in otros_textos]
    total = len(documentos) + 1

    def idf(r):
        df = sum(1 for d in documentos if r in d)
        return math.log((total + 1) / (df + 1)) + 1

    def puntaje_palabra(r):
        return ((grado[r] + frecuencia[r]) / frecuencia[r]) * (1 + math.log(frecuencia[r])) * idf(r)

    puntajes = {}
    forma = {}
    for f in frases:
        clave = tuple(raiz(p) for p, ini in f if ini is not None)
        puntajes[clave] = max(puntajes.get(clave, 0), sum(puntaje_palabra(r) for r in clave))
        forma.setdefault(clave, f)

    elegidas = []
    usadas = set()
    for clave in sorted(puntajes, key=lambda k: puntajes[k], reverse=True):
        if set(clave) <= usadas:
            continue
        elegidas.append(_mostrar(forma[clave]))
        usadas |= set(clave)
        if len(elegidas) >= cantidad:
            break
    return elegidas


# ==============================================================
# EXTRACTOR CON IA (Claude)
# ==============================================================

def leer_config():
    try:
        with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            return datos if isinstance(datos, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def guardar_clave_api(clave):
    datos = leer_config()
    datos["anthropic_api_key"] = clave.strip()
    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4)


def clave_api():
    return os.environ.get("ANTHROPIC_API_KEY") or leer_config().get("anthropic_api_key", "")


def interpretar_respuesta(texto):
    """Toma la respuesta del modelo y devuelve una lista limpia de palabras clave."""
    inicio, fin = texto.find("["), texto.rfind("]")
    if inicio == -1 or fin <= inicio:
        return []
    try:
        lista = json.loads(texto[inicio:fin + 1])
    except json.JSONDecodeError:
        return []
    limpias = []
    for item in lista:
        if isinstance(item, str):
            item = item.strip().strip(".").lower()
            if item and len(item) <= 40 and item not in limpias:
                limpias.append(item)
    return limpias[:7]


def extraer_con_ia(texto, materia="", tiempo_limite=20):
    """Devuelve la lista de palabras clave o lanza una excepción si no se pudo."""
    clave = clave_api()
    if not clave:
        raise RuntimeError("No hay clave de API configurada")
    instrucciones = (
        "Lee este apunte escolar y devuelve SOLO un arreglo JSON con entre 3 y 7 palabras o frases clave "
        "(máximo 3 palabras cada una), en el idioma del apunte y en minúsculas, que sirvan para encontrar "
        "la nota después con un buscador. Prefiere conceptos, nombres propios, fórmulas y términos técnicos. "
        "No agregues explicaciones.\n\n"
        f"Materia: {materia or 'sin materia'}\n\nApunte:\n{texto[:6000]}"
    )
    cuerpo = json.dumps({
        "model": MODELO_IA,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": instrucciones}],
    }).encode("utf-8")
    peticion = urllib.request.Request(URL_API, data=cuerpo, method="POST", headers={
        "x-api-key": clave,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    with urllib.request.urlopen(peticion, timeout=tiempo_limite) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    texto_respuesta = "".join(b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text")
    palabras = interpretar_respuesta(texto_respuesta)
    if not palabras:
        raise RuntimeError("La IA no devolvió palabras clave")
    return palabras


def extraer(texto, materia="", otros_textos=()):
    """
    Intenta con IA; si no hay clave o falla, usa el extractor local.
    Devuelve (palabras, fuente) donde fuente es "ia" o "local".
    """
    if clave_api():
        try:
            return extraer_con_ia(texto, materia), "ia"
        except Exception:
            pass
    return extraer_local(texto, otros_textos), "local"
