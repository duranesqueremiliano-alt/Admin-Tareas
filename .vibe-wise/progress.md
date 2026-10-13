# Learning Progress

## Pending decision
- Decision: notas.py — funciones (qué recibe y qué devuelve cada una).
- Stage: Build checkpoint — awaiting reasoning.
- Learner listed (2026-10-13 00:10): crear nota nueva con id, guardar (crear o reemplazar), borrar, buscar, título de la primera línea; nuevos requisitos: si la nota viene de una imagen, un icono lleva a ella; palabras clave buscables; orden editable en el menú de notas.
- Not yet answered: recibe/devuelve de cada función. Asked now: llenar tabla recibe/devuelve; cómo se representa el orden (pendiente desde el modelo de datos); si cada función lee/escribe el archivo o trabaja con la lista en memoria.

## Archivo dañado (resuelto 2026-10-12 23:30)
- Learner decided: no dejar guardar si el archivo está dañado.
- Learner pidió explícitamente la respuesta → AI diseñó e implementó (propuesta del AI, no razonamiento del learner): excepción propia ArchivoDanado; leer_json la lanza ante JSONDecodeError (FileNotFoundError sigue devolviendo valor_por_defecto); escribir_json llama primero a leer_json para comprobar el archivo antes de abrir en "w"; pruebas en __main__ con limpieza. Verificado por el AI (archivo dañado queda intacto). Guardado en la raíz del proyecto.
- Pendiente para pantalla_notas.py: atrapar ArchivoDanado, mostrar mensaje y desactivar Guardar.
- Riesgo conocido (no resuelto): si la app se cierra a mitad de escritura, el archivo queda vacío → contaría como dañado. Mejora posible: escritura atómica (.tmp + os.replace).
- Introduced (AI explained): class para excepción propia, raise, excepciones que suben, modo "w" vacía al abrir.

## almacen.py (historial)
- Was: Primer código — almacen.py (leer/escribir JSON). El learner escribe el código.
- Asked: nombre, parámetros y retorno de las dos funciones; qué devuelve leer cuando el archivo aún no existe (primera vez) o está vacío/dañado. Él lo escribe y lo comparte para revisión.
- Learner pidió "las bases" de almacen.py → AI dio un esqueleto con TODOs (propuesta del AI: leer_json(nombre_archivo, valor_por_defecto), escribir_json(nombre_archivo, datos), CARPETA_DATOS = "datos", bloque if __name__ == "__main__" para probar). Learner rellena los TODOs. Preguntas abiertas: qué hacer si el archivo está dañado (riesgo de sobrescribir y perder notas).
- Introduced (AI explained): os.path.join, if __name__ == "__main__", riesgo de devolver vacío ante archivo dañado.
- Learner's first draft (2026-10-12 22:07), reviewed: usó bien with/open/encoding, json.dump con ensure_ascii/indent, atrapó FileNotFoundError y JSONDecodeError, makedirs con exist_ok. Errores: try+with en una línea (SyntaxError, verificado); leer_json no hace return (json.load descartado, valor_por_defecto sin usar); escribir_json usa 'ruta' que no existe ahí (alcance de variables); except mal indentados; excepts imposibles al escribir (JSONDecodeError); si falta la carpeta imprime en vez de crearla; mezcla os y pathlib; "datos" repetido a mano en vez de CARPETA_DATOS; prints de "intente de nuevo" en módulo de datos. TODO 3 (archivo dañado) sin decidir; pruebas sin escribir. Aún no lo ejecutó.
- Introduced (AI explained): return vs print; alcance (scope) de variables locales; bloques compuestos necesitan nueva línea + sangría.
- Review delivered in chat 22:08 (same points). Awaiting: learner's corrected almacen.py, ejecutado, con su salida; decisión del TODO 3.
- Draft 2 (22:22), reviewed: corrigió try en su propia línea; añadió ruta en escribir_json; añadió return. Persisten: resultado de json.load no se guarda en variable; return json.load(f) fuera del with (archivo cerrado → ValueError; si no existe → UnboundLocalError, ambos verificados); valor_por_defecto sin usar; `if Path.is_dir(...) = False` sin ":" (SyntaxError verificado; = vs ==); JSONDecodeError al escribir; "datos" a mano; sin pruebas; sigue sin ejecutar el archivo él mismo. TODO 3 sin responder.
- Introduced (AI explained): with cierra el archivo al terminar el bloque; guardar resultado en variable y devolverla; = vs ==; leer tracebacks.
- 22:31 learner pidió una referencia detallada de todos los comandos del archivo, sin el código armado. AI la dio (import, constantes, def/parámetros, return, alcance, os.path.join, os.makedirs, try/except y flujo, FileNotFoundError/JSONDecodeError, with open y modos r/w, json.load/dump y conversiones, if __name__, print, =/==, bloques e indentación). Sigue esperando su versión corregida.
- Draft 3 (23:03), reviewed and run by AI with tests: ¡ya corre! escribir_json funciona (acentos e indent correctos); los except de leer devuelven valor_por_defecto (correcto). Falla: leer_json hace `return f` (objeto archivo) en vez del contenido de json.load → confunde archivo con contenido. escribir_json: `return f` innecesario; except FileNotFoundError imposible tras makedirs y usa valor_por_defecto inexistente (NameError latente); "datos" a mano; makedirs global redundante; Path sin usar. Implícitamente eligió "devolver valor por defecto" ante archivo dañado → se le preguntó si acepta el riesgo de sobrescribir. Aún no escribe pruebas ni ejecuta él mismo.
- Demonstrated: usar return en cada rama del try/except con valor_por_defecto.
- Needs reinforcement: distinguir el archivo (f) de su contenido (resultado de json.load).
- Needs reinforcement: return vs print; sintaxis de bloques; leer mensajes de error.

## División en archivos (Design checkpoint confirmado 2026-10-12, 11:4x)
- Learner: main.py (arranque), notas.py (crear, id, datos), tareas.py; materias en JSON aparte; materias/notas/tareas en archivos poco accesibles al usuario (carpeta datos/ junto al programa, elegido antes en picker; requiere añadir datos/ a .gitignore); título calculado; la verificación crear/reemplazar "manda un mensaje" a la pantalla; nuevo requisito: barra de búsqueda de notas. Pidió recomendación de más archivos.
- AI proposed (approved): almacen.py (antes llamado archivos.py en una propuesta previa), materias.py, pantalla_notas.py, pantalla_tareas.py, ia.py al final; búsqueda en notas.py; regla "módulos de datos no importan customtkinter"; palabras_clave = [] hasta tener ia.py; primer paso almacen.py + notas.py probados con print.

## Flujo de guardar nota (2026-10-12)
- Learner: "Crear nota" → Importar foto | Escribir nota → mismo editor; colores para texto no entendido / dudoso completado por la IA; formato (negritas) pospuesto; id generado al pulsar "Nueva nota", al guardar busca si el id existe → reemplaza (edición) o agrega; título = primera línea (tooltip lo indica); materia desde desplegable + "Agregar materia"; fecha de creación; palabras clave automáticas, regeneradas al editar; mensaje "La nota se creó/actualizó"; menú se refresca al crear, con botón "Actualizar" y al abrir la app.
- Later topic flagged: generar palabras clave con IA tarda segundos → hilos/no congelar la ventana.

## Reescritura — decisiones previas (2026-10-12)
- Learner: rama nueva de Git; sin Gastos; él escribe el código; customtkinter.
- Side question (AI recommendation, not learner's decision): hacer Notas con IA primero y Gastos después solo.
- The earlier pending "foto → texto" design checkpoint (for the old vibecoded code) was superseded by the rewrite; its learner decisions remain in project-map.md as reference.

## Modelo de datos y arquitectura (v2)
- Introduced (AI explained): identificador único; dato guardado vs dato calculado; memoria vs disco; JSON vs SQLite; módulo uuid; módulos y separación pantalla/datos; valor de retorno como "mensaje" de datos a pantalla.
- Demonstrated reasoning: tradujo la interfaz a datos persistentes ("bring to top" requiere guardar orden; ruta de imagen en vez de imagen); eligió calcular "vencida" y luego el título (aplicó guardado vs calculado por segunda vez); cambió por su cuenta a id aleatorio para evitar reutilizar ids; JSON separados "para evitar sobreescrituras"; resolvió crear vs editar (id al iniciar "Nueva nota" + comprobar si existe); propuso que la lógica de guardar avise a la pantalla.
- Needs reinforcement: tiende a responder con lo que ve el usuario en vez de pasos internos; necesitó ayuda para clasificar pantalla vs datos; persistencia (memoria vs disco) recién explicada.

## OCR de notas
- Introduced (AI explained): qué es OCR; motores locales vs nube (precisión en letra a mano, internet, costo, privacidad); hilos + cola + after() para no congelar Tkinter; respuesta estructurada (JSON) para marcar partes dudosas.
- Demonstrated reasoning: eligió precisión en escritura a mano sobre funcionamiento sin internet; diseñó el flujo desde el usuario (borrador revisable, marcar lo deducido por la IA, no bloquear al usuario).
- Needs reinforcement: casos de error (no los definió).
