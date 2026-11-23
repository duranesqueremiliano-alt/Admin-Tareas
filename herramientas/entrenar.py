# entrenar.py
# Afina (fine-tuning) TrOCR manuscrito con TUS renglones de dataset/ usando PyTorch.
# Parte del modelo de Microsoft (letra a mano en inglés) y le enseña tu letra y el español (á, ñ, ¿...).
# El mejor modelo (menor error en validación) se guarda en modelos/propio_trocr/ y la app lo usa sola.
#
# Uso:
#   python herramientas/entrenar.py                 # 10 épocas
#   python herramientas/entrenar.py --epocas 20 --lote 8 --lr 3e-5
#   python herramientas/entrenar.py --continuar     # sigue desde tu modelo propio en vez del de Microsoft
import argparse
import csv
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from m import ocr  # noqa: E402

DATASET = os.path.join(RAIZ, "dataset")


def leer_etiquetas(nombre):
    carpeta = os.path.join(DATASET, nombre)
    archivo = os.path.join(carpeta, "labels.csv")
    if not os.path.isfile(archivo):
        return []
    with open(archivo, newline="", encoding="utf-8") as f:
        filas = [(os.path.join(carpeta, r["filename"]), r["words"].strip()) for r in csv.DictReader(f)]
    return [(ruta, texto) for ruta, texto in filas if texto and os.path.isfile(ruta)]


def distancia(a, b):
    """Distancia de Levenshtein: cuántas letras hay que cambiar, quitar o poner para pasar de a a b."""
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def error_por_letra(predichos, reales):
    """CER: porcentaje de letras mal leídas. 0 % = perfecto."""
    return sum(distancia(p, r) for p, r in zip(predichos, reales)) / max(sum(len(r) for r in reales), 1)


def main():
    import torch
    from PIL import Image

    p = argparse.ArgumentParser()
    p.add_argument("--epocas", type=int, default=10)
    p.add_argument("--lote", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--continuar", action="store_true", help="partir de modelos/propio_trocr")
    args = p.parse_args()

    entrenamiento, validacion = leer_etiquetas("entrenamiento"), leer_etiquetas("validacion")
    if not entrenamiento:
        print("No hay datos. Primero: python herramientas/crear_dataset.py tus_fotos/  y corrige labels.csv")
        return 1
    if not validacion:   # si no hay validación, aparta un 10 %
        random.shuffle(entrenamiento)
        corte = max(1, len(entrenamiento) // 10)
        validacion, entrenamiento = entrenamiento[:corte], entrenamiento[corte:] or entrenamiento[:corte]
    print(f"Renglones: {len(entrenamiento)} de entrenamiento, {len(validacion)} de validación")

    origen = ocr.CARPETA_PROPIO if args.continuar and ocr.hay_modelo_propio() else ocr.MODELO_BASE
    print("Partiendo de:", origen)
    procesador, modelo = ocr.cargar_trocr(origen)
    tok = procesador.tokenizer
    # El decodificador arranca con el mismo token que usa al generar (</s> en TrOCR), no con <s>.
    modelo.config.decoder_start_token_id = modelo.generation_config.decoder_start_token_id
    modelo.config.pad_token_id = tok.pad_token_id
    modelo.config.eos_token_id = tok.sep_token_id
    disp = ocr.dispositivo()
    modelo.to(disp)
    optimizador = torch.optim.AdamW(modelo.parameters(), lr=args.lr)

    def lote_a_tensores(lote):
        imagenes = [Image.open(ruta).convert("RGB") for ruta, _ in lote]
        pixeles = procesador(images=imagenes, return_tensors="pt").pixel_values
        etiquetas = tok([t for _, t in lote], padding=True, truncation=True, max_length=ocr.MAX_TOKENS,
                        return_tensors="pt").input_ids
        if tok.bos_token_id is not None and (etiquetas[:, 0] == tok.bos_token_id).all():
            etiquetas = etiquetas[:, 1:]   # quita <s>: el modelo no lo genera (con él la pérdida sale ~10 en vez de ~0)
        etiquetas[etiquetas == tok.pad_token_id] = -100   # el relleno no cuenta en la pérdida
        return pixeles.to(disp), etiquetas.to(disp)

    def evaluar():
        modelo.eval()
        predichos = []
        with torch.no_grad():
            for i in range(0, len(validacion), args.lote):
                pixeles, _ = lote_a_tensores(validacion[i:i + args.lote])
                ids = modelo.generate(pixeles, max_new_tokens=ocr.MAX_TOKENS, num_beams=3)
                predichos += [t.strip() for t in tok.batch_decode(ids, skip_special_tokens=True)]
        return error_por_letra(predichos, [t for _, t in validacion]), predichos

    mejor, ejemplos = evaluar()
    print(f"Error por letra ANTES de entrenar: {mejor:.1%}")
    for epoca in range(1, args.epocas + 1):
        modelo.train()
        random.shuffle(entrenamiento)
        total = 0.0
        for i in range(0, len(entrenamiento), args.lote):
            pixeles, etiquetas = lote_a_tensores(entrenamiento[i:i + args.lote])
            perdida = modelo(pixel_values=pixeles, labels=etiquetas).loss
            optimizador.zero_grad()
            perdida.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            optimizador.step()
            total += perdida.item()
        pasos = (len(entrenamiento) + args.lote - 1) // args.lote
        cer, ejemplos = evaluar()
        print(f"Época {epoca}/{args.epocas}  pérdida {total / pasos:.3f}  error por letra {cer:.1%}")
        if cer <= mejor:
            mejor = cer
            os.makedirs(ocr.CARPETA_PROPIO, exist_ok=True)
            modelo.save_pretrained(ocr.CARPETA_PROPIO)
            procesador.save_pretrained(ocr.CARPETA_PROPIO)
            print("   guardado en modelos/propio_trocr (el mejor hasta ahora)")
    print("\nEjemplos de validación en la última época (real -> leído):")
    for (_, real), leido in list(zip(validacion, ejemplos))[:5]:
        print(f"   {real!r} -> {leido!r}")
    if ocr.hay_modelo_propio():
        print(f"Mejor error por letra: {mejor:.1%}. Reinicia la app para usar el modelo nuevo.")
    else:
        print("No mejoró respecto al modelo original: no se guardó nada. Prueba más datos o más épocas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
