# Admin-Tareas

App de escritorio (Python + customtkinter) para organizar notas, tareas y gastos.
Tus datos se guardan en tu PC, en `datos/`.

## Cómo correrla
pip install -r requirements.txt
python main.py

## Foto → texto (letra a mano)
En **Notas**, botón **Foto → texto**: eliges una foto y el texto se pega donde está el cursor.
Todo corre en PyTorch, en dos pasos (`m/ocr.py`):
1. **Detector CRAFT** (de [EasyOCR](https://github.com/JaidedAI/EasyOCR)): encuentra cada letra y la unión
   entre letras vecinas, arma las palabras y la app las junta en renglones.
2. **Reconocedor [TrOCR manuscrito](https://huggingface.co/microsoft/trocr-base-handwritten)** (Microsoft):
   un Transformer entrenado con letra a mano que lee cada renglón completo.

La primera vez descarga los modelos (~1.4 GB) a `modelos/`.
El TrOCR original aprendió con letra a mano **en inglés**: lee bien la mayoría de las palabras, pero falla
con acentos, ñ y ¿¡ hasta que lo entrenes con tu letra (abajo). No existe un TrOCR manuscrito en español ya hecho.

## Entrenar con tu letra (ampliar la muestra)
1. **Junta fotos** de tu letra: apuntes, tareas, hojas escritas a propósito. Buena luz, foto derecha.
2. **Córtalas en renglones**:
   `python herramientas/crear_dataset.py carpeta_con_fotos/`
   Crea `dataset/entrenamiento/` y `dataset/validacion/`: un `.png` por renglón y un `labels.csv` con lo que leyó.
3. **Revisa cada renglón**: `python herramientas/revisar.py`
   Una ventana te muestra el recorte y el texto propuesto; corrígelo para que diga exactamente lo escrito,
   con acentos. Enter = aceptar, Ctrl+D = descartar (recorte malo), Ctrl+← = anterior. Solo los aceptados
   se usan para entrenar. Con ~200 renglones ya se nota; con 1000+ mucho más.
   Atajo: pídele a Claude `/transcribir-apuntes` y él propone el texto de cada renglón antes de que lo revises.
   `python herramientas/etiquetas.py resumen` dice cuántos llevas.
4. **Entrena**: `python herramientas/entrenar.py --epocas 10`
   Muestra el *error por letra* antes y después de cada época y guarda el mejor en `modelos/propio_trocr/`.
   En CPU tarda (minutos por cada 100 renglones por época); con tarjeta NVIDIA es mucho más rápido.
5. **Reinicia la app**: si existe `modelos/propio_trocr/`, la usa en vez del modelo de Microsoft.
   Cuando juntes más fotos, repite 2–4 con `--continuar` para seguir desde tu modelo
   (las fotos que ya estaban en `dataset/` se saltan solas).
