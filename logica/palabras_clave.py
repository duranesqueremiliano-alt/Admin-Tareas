# palabras_clave.py
# Palabras clave automáticas, sin internet: las palabras que más se repiten.
# Usa un diccionario como contador (palabra -> veces).
import re

VACIAS = {
    "para", "pero", "como", "este", "esta", "estos", "estas", "esto", "ese", "esa", "eso",
    "aquel", "aquella", "donde", "cuando", "porque", "sobre", "entre", "desde", "hasta",
    "tiene", "tienen", "hace", "hacer", "puede", "pueden", "sino", "también", "tambien",
    "cada", "todo", "todos", "toda", "todas", "otro", "otra", "otros", "otras", "muy",
    "más", "mas", "menos", "algo", "nada", "siempre", "nunca", "ahora", "luego", "antes",
    "después", "despues", "entonces", "aunque", "mismo", "misma", "solo", "sólo", "según",
    "segun", "cual", "cuál", "cuales", "quien", "quién", "qué", "sus", "les", "son", "fue",
    "era", "ser", "está", "están", "estan", "hay", "han", "había", "habia", "sea", "sean",
}


def extraer(texto, cuantas=5):
    conteo = {}
    for palabra in re.findall(r"[a-záéíóúüñ]+", texto.lower()):
        if len(palabra) >= 4 and palabra not in VACIAS:
            if palabra not in conteo:
                conteo[palabra] = 0
            conteo[palabra] += 1
    palabras = list(conteo)
    palabras.sort(key=conteo.get, reverse=True)
    return palabras[:cuantas]


if __name__ == "__main__":
    print(extraer("Derivadas\nLa derivada mide el cambio. Una derivada positiva indica que la función crece."))
