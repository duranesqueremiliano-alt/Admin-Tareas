---
name: transcribir-apuntes
description: Pasa fotos de apuntes escritos a mano por el OCR de Admin-Tareas, corrige el texto de cada renglón leyendo las imágenes y abre la ventana de revisión para que el usuario confirme. Usar cuando el usuario diga /transcribir-apuntes, "transcribe mis apuntes", "prepara el dataset" o deje fotos nuevas para entrenar.
---

# Transcribir apuntes para entrenar el OCR

Objetivo: que cada renglón recortado de las fotos del usuario tenga el texto EXACTO que está escrito,
para entrenar TrOCR con su letra. El usuario confirma todo al final en `herramientas/revisar.py`.

## Pasos

1. **Fotos.** Usa la carpeta o archivos que diga el usuario; si no dice, `fotos_apuntes/` en la raíz
   del proyecto. Si no existe o está vacía, pídele que ponga ahí las fotos y para.

2. **Recortar renglones** (corre en segundo plano si hay más de 3 fotos: ~1 min por foto en CPU):
   ```
   python herramientas/crear_dataset.py <carpeta_o_fotos>
   ```
   Las fotos que ya están en `dataset/` se saltan solas (para volver a cortarlas: `--repetir`).

3. **Hojas para leer.** Junta los renglones que solo leyó el modelo (`pendiente`) en hojas numeradas, en el scratchpad:
   ```
   python herramientas/etiquetas.py hojas <scratchpad>/hojas_ocr
   ```
   Crea `hoja_01.png`, `hoja_02.png`… (10 renglones cada una, con `#número` en rojo) e `indice.json`
   (número -> clave `parte/archivo.png`).

4. **Leer y transcribir.** Abre cada hoja con Read. Si un renglón no se entiende, abre también la foto
   original para tener contexto (el tema ayuda a adivinar palabras). Reglas:
   - Escribe lo que DICE la imagen, letra por letra, con acentos, ñ, ¿¡, mayúsculas y puntuación
     como están escritos. No corrijas faltas de ortografía del usuario: el modelo debe aprender
     a leer lo escrito, no a corregirlo.
   - Solo el texto que está dentro del recorte. Si el recorte corta palabras a la orilla, transcribe
     solo la parte visible si se entiende; si no, descártalo.
   - Usa `null` (descartar) si el recorte tiene dos renglones mezclados, solo tachones, dibujos,
     una palomita/marca, o casi nada legible.
   - No inventes: si una palabra es ilegible, mejor descarta el renglón entero.

5. **Guardar.** Escribe un JSON en el scratchpad con `{"<clave de indice.json>": "texto" | null}` y aplícalo:
   ```
   python herramientas/etiquetas.py corregir <scratchpad>/textos.json
   ```
   Quedan con estado `claude` (todavía NO se usan para entrenar).

6. **Revisión del usuario.** Abre la ventana en segundo plano (no bloquees la terminal):
   ```
   python herramientas/revisar.py
   ```
   Dile al usuario: en cada renglón ve la imagen y el texto; Enter = aceptar, Ctrl+D = descartar,
   Ctrl+← = anterior. Solo lo que acepte se usa para entrenar. Avísale qué renglones te dieron más
   dudas (por número) para que los mire con cuidado.

7. **Resumen.** Cuando termine, `python herramientas/etiquetas.py resumen`. Si hay ~200+ renglones
   `ok`, ofrece entrenar: `python herramientas/entrenar.py --epocas 10` (largo: en segundo plano).

## Privacidad
Las fotos y `dataset/` son del usuario y están en `.gitignore`: no las subas a ningún lado, no las
publiques como artifact y no las copies fuera del proyecto o del scratchpad.
