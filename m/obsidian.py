# obsidian.py
# Exporta las notas como archivos .md para abrirlas en una bóveda de Obsidian.
# Cada nota es un archivo; la materia y las palabras clave van como etiquetas (#tags).
import json
import os
import re
from m import notas

PROHIBIDOS = r'[\\/:*?"<>|#^\[\]]'   # caracteres que Windows u Obsidian no aceptan en un nombre


def nombre_archivo(titulo):
    nombre = re.sub(PROHIBIDOS, "", titulo).strip().strip(".")
    return nombre[:80] or "Sin título"


def etiqueta(texto):
    # "Cálculo integral" -> "cálculo-integral" (una etiqueta de Obsidian no lleva espacios).
    texto = re.sub(r"\s+", "-", texto.strip().lower())
    return re.sub(r"[^\w\-/]", "", texto)


def contenido_md(nota):
    etiquetas = []
    for palabra in [nota["materia"]] + nota["palabrasclave"]:
        limpia = etiqueta(palabra)
        if limpia and limpia not in etiquetas:
            etiquetas.append(limpia)
    # json.dumps pone comillas válidas para YAML (el bloque --- de arriba es el "frontmatter").
    lineas = [
        "---",
        "materia: " + json.dumps(nota["materia"], ensure_ascii=False),
        "creada: " + json.dumps(nota["fechacreacion"]),
        "tags: " + json.dumps(etiquetas, ensure_ascii=False),
        "id: " + nota["id"],
        "---",
        "",
        nota["texto"],
        "",
    ]
    return "\n".join(lineas)


def exportar(lista, carpeta):
    # Escribe (o reescribe) un .md por nota. Devuelve cuántos archivos escribió.
    os.makedirs(carpeta, exist_ok=True)
    usados = set()
    for nota in lista:
        base = nombre_archivo(notas.titulo(nota))
        nombre = base
        numero = 2
        while nombre.lower() in usados:   # dos notas con el mismo título
            nombre = base + " (" + str(numero) + ")"
            numero += 1
        usados.add(nombre.lower())
        with open(os.path.join(carpeta, nombre + ".md"), "w", encoding="utf-8") as f:
            f.write(contenido_md(nota))
    return len(usados)


if __name__ == "__main__":
    import tempfile
    nota = notas.crear("Cálculo integral")
    nota["texto"] = "Derivadas: ¿qué son?\nLa pendiente de una curva."
    nota["palabrasclave"] = ["derivada", "pendiente"]
    print(nombre_archivo(notas.titulo(nota)))
    print(contenido_md(nota))
    print(exportar([nota, nota], tempfile.mkdtemp()))
