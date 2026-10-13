# Project Map

## Reescritura v2 (decidida 2026-10-12, sin código aún)
- Dónde (actualizado 2026-10-12 23:20): la app nueva vive en la raíz del repo; la app original se copió a
  `app_original/` (funciona ahí: sus rutas usan Path(__file__)). Pendiente: el learner borra los originales de la raíz.
- Quién escribe: el learner; el AI da bases, explica y revisa.
- Alcance: Notas + Tareas y trabajos. Gastos queda fuera.
- Requisitos del learner: foto de una nota → la IA identifica el texto y lo pasa a la app;
  palabras clave generadas automáticamente; poder importar fórmulas y diagramas.
- Interfaz: customtkinter (elegido por el learner).
- Nota (visión del learner): documento de texto; menú de notas con título + vista previa;
  menú deslizable con icono de la foto original, palabras clave y opciones (borrar, "bring to top").
- Tareas = trabajos (lo mismo), de uso general: escuela y vida diaria, con límite de tiempo.
- Plan del learner: después de esta app hará un programa (probablemente Gastos) sin ayuda de IA.
- Modelo de datos (CONFIRMADO 2026-10-12, no implementado):
  Learner's decisions: JSON en archivos separados (materias, notas, tareas); id aleatorio
  alfanumérico sin repetirse; Nota = id, materia, palabras_clave, ruta_imagen, orden;
  Tarea = id, titulo, descripcion, fecha_creacion, fecha_limite, materia/categoría, estado;
  "vencida" se calcula; una lista de materias compartida.
  AI additions (approved): nota también tiene titulo y texto; ruta_imagen = None si no hay foto;
  estado guardado solo "activa"/"completada"; fechas como texto con formato fijo "%Y-%m-%d %H:%M";
  uuid.uuid4().hex sugerido para ids.
  Unresolved: representación del orden (número vs posición en la lista).
- Flujo de crear nota (requisito del learner, 2026-10-12): "Crear nota" → Importar foto | Escribir nota;
  ambas terminan en el mismo editor (texto editable con formato básico); desde foto, el texto
  llega marcado: un color = no entendido, otro color = dudoso completado por la IA con el contexto;
  luego "Guardar nota".
- Formato de texto (negritas, etc.): pospuesto; en v1 `texto` es un string normal.
- Palabras clave: automáticas al guardar y regeneradas cada vez que se edita la nota (requisito del learner).
- Flujo "Guardar nota" (learner, 2026-10-12, no confirmado aún): id generado al pulsar "Nueva nota";
  título = primera línea del texto; materia desde desplegable (+ "Agregar materia"); al guardar,
  si ya existe una nota con ese id → reemplazar (edición), si no → agregar. Nota también guarda
  fecha de creación. Menú muestra título grande, preview, chips de palabras clave, fecha.
  Tooltip: "la primera línea es el título". Editor muestra ruta de la foto, fecha y palabras clave.
  Al guardar: mensaje "La nota se creó" / "La nota se actualizó". Menú se refresca al crear,
  con botón "Actualizar" y al abrir la app.
- Título: se calcula de la primera línea cada vez (no se guarda). Requisito: barra de búsqueda de notas
  (también por palabras clave). Icono en la nota que abre su imagen original si la tiene.
  Orden de notas editable en el menú (representación aún sin decidir).
- Estructura de archivos (CONFIRMADA 2026-10-12, no implementada):
  Learner: main.py (arranque), notas.py (crear, id, guardar), tareas.py; JSON separados poco
  accesibles; guardar devuelve a la pantalla si fue "creada" o "actualizada".
  AI additions (approved): almacen.py (leer/escribir JSON), materias.py, pantalla_notas.py,
  pantalla_tareas.py, ia.py (al final), carpeta datos/ con notas.json, materias.json, tareas.json;
  los módulos de datos no importan customtkinter; palabras_clave = [] hasta tener ia.py.
  Orden: almacen.py + notas.py (probar con print) → materias.py → pantallas/main → tareas → ia.
  ```
  main.py ──► pantalla_notas.py ──llama──► notas.py ──► almacen.py ──► datos/notas.json
                     ▲                         │
                     └──return "creada"/"actualizada"
  pantalla_tareas.py ──► tareas.py ──► almacen.py ──► datos/tareas.json
  notas.py / tareas.py ──► materias.py ──► datos/materias.json
  pantalla_notas.py ──► ia.py (después)
  ```
- almacen.py: código completo escrito por el AI a petición del learner (2026-10-12 23:15),
  verificado en el entorno del AI, entregado en el chat (no escrito en el repo por el AI).
  leer_json(nombre_archivo, valor_por_defecto) / escribir_json(nombre_archivo, datos).
  Archivo dañado (decisión del learner: no dejar guardar; mecanismo del AI, 23:30): leer_json lanza
  ArchivoDanado; escribir_json comprueba con leer_json antes de sobrescribir. Guardado en la raíz.
  La raíz ya solo tiene la app nueva; la vieja está en app_original/ (originales borrados por el learner).
- Requisitos nuevos (2026-10-13): icono en la nota que abre la imagen original; búsqueda también por palabras clave;
  orden de notas editable en el menú (representación: por decidir).
- Sin decidir:
  qué significa "importar" fórmulas/diagramas (¿desde la foto?, ¿archivos?, ¿LaTeX?), diferencia
  entre "tarea" y "trabajo".

```
v2:  ? interfaz ──► ? lógica Notas / Tareas ──► ? almacenamiento
     foto ──► IA (texto + ? fórmulas/diagramas) ──► nota      palabras clave ──► ?
```

## Versión vieja (rama main, referencia) — Purpose
Organizador personal de escritorio con tres secciones: Tareas (entregas con fecha
límite y alertas), Gastos (cuentas, movimientos, pagos recurrentes, resumen) y
Notas de clase (apuntes por materia con buscador y palabras clave).

## Requirements
- Conservar todas las funcionalidades actuales de las tres secciones.
- Mejorar la GUI para que sea lo más intuitiva posible (qué falta mejorar sobre la
  versión nueva: pendiente de que lo defina el learner).
- Nuevo: tomar una foto de una nota y obtener el texto transcrito (OCR) dentro de
  la sección Notas. Flujo, origen de la foto y motor de OCR: sin decidir.

## Components (verificados en el código, escaneo del 2026-10-09)
- `appprin.py`: punto de entrada. `App` (ventana `customtkinter`, tema oscuro), crea los tres
  stores, navega entre pantallas (`_mostrar` con caché en `self.pantallas`), atajos
  Ctrl+1/2/3 y Esc, revisión periódica cada 60 s (expiraciones, pagos automáticos al cambiar
  de día, alertas de 12 h). `PantallaInicio`: saludo + 3 tarjetas resumen clicables.
- `modelos.py`: lógica y datos sin interfaz. Utilidades de fechas/moneda, `leer_json` /
  `escribir_json` (escritura atómica vía `.tmp` + `os.replace`). `TareasStore`, `GastosStore`,
  `NotasStore` (búsqueda sin acentos con puntaje: palabra clave 3, título 2, texto 1).
- `ui_comun.py`: paleta `C`, `fuente`, `boton`, tablas (`crear_tabla`), `Pestanas`, `Encabezado`,
  `BarraAviso` (avisos en línea en vez de messagebox), `Calendario` / `SelectorFecha`,
  `Dialogo` base, `confirmar`, `menu_contextual`.
- `pantalla_tareas.py`: formulario rápido (Enter, calendario, botones Hoy/Mañana/1 semana),
  pestañas Pendientes/Completadas/Expiradas, buscador, tabla con "tiempo restante",
  doble clic = editar, Supr = eliminar, Enter = completar/reabrir, clic derecho = menú.
- `pantalla_gastos.py`: pestañas Movimientos, Cuentas, Pagos recurrentes, Resumen por categoría,
  cada una con su diálogo de edición.
- `pantalla_notas.py`: pestañas "Nueva nota" (materia, título, texto, Ctrl+Enter guarda) y
  "Mis notas" (buscador, filtro por materia, chips de palabras clave, panel de detalle).
  Las palabras clave se generan en un hilo aparte y vuelven por una `queue.Queue`
  revisada cada 150 ms con `after`.
- `palabras_clave.py`: extracción con IA (API de Anthropic vía `urllib`, clave en
  `config.json` o `ANTHROPIC_API_KEY`) y respaldo local sin internet (RAKE + TF-IDF).
- `instalar_dependencias.py` + `requirements.txt` (`customtkinter>=5.2`).
- `appprin_original.py`: versión vieja de un solo archivo (Tkinter puro). Rol: desconocido.
- `gitignore` (sin punto): copia de `.gitignore`, aparentemente sobrante. `tareas.json.txt`: vacío.

## Main Flow
```
appprin.py App ──crea──► TareasStore / GastosStore / NotasStore (modelos.py) ──lee──► *.json
App ──navega──► PantallaInicio | PantallaTareas | PantallaGastos | PantallaNotas
pantalla ──acción del usuario──► store.metodo() ──escribir_json──► archivo .json ──► pantalla.refrescar()
App.revision_periodica (60 s) ──► expirar tareas, pagos automáticos, alertas 12 h
Nueva nota ──guardar──► NotasStore.agregar ──hilo──► palabras_clave.extraer (IA o local) ──cola──► chips
foto de nota ──► ? (OCR) ──► ? texto en la nota     [no existe aún]
```

## Data and Trust Boundaries
- `tareas.json`: lista de `{id, nombre, descripcion, fecha_limite "%Y-%m-%d %H:%M", estado, alerta_12h_enviada}`.
- `gastos.json`: `{cuentas, movimientos, recurrentes, categorias}`.
- `notas.json`: `{materias, notas: [{id, materia, titulo, texto, fecha, palabras_clave, fuente}]}`.
- `config.json` (ignorado en Git): clave de API de Anthropic. Con clave, el texto de la nota
  sale a internet (api.anthropic.com); sin clave, todo queda local.

## Build and Deployment
- `python instalar_dependencias.py` una vez, luego `python appprin.py`.
- Windows; `__pycache__` indica Python 3.14. Sin tests ni empaquetado.

## Chosen design: foto → texto (confirmado 2026-10-09, no implementado)
Learner's decisions:
- Icono 📎 adjuntar junto a "Guardar nota"; la foto es un archivo adjunto.
- Cada foto crea una nota previa (borrador); se vuelve nota real solo al pulsar "Confirmar nota"
  en una ventana de vista previa editable.
- La nota escrita también pasa por esa ventana de vista previa (interpretación del AI presentada
  y confirmada; Ctrl+Enter deja de guardar directo).
- Texto deducido por la IA en otro color; si hay alternativas, al pasar el ratón se puede cambiar.
- Procesamiento en segundo plano; aviso pequeño en una esquina dentro de la app; al pulsarlo,
  lista de borradores listos o abre directo si es uno solo.
- Clave de API accesible desde la pantalla de inicio. Prioridad: precisión en letra a mano.
AI additions (approved with the design):
- Respuesta de IA como JSON por segmentos `{texto, seguro, opciones}`.
- Modelo de visión más fuerte que Haiku, en una constante.
- Pillow + pillow-heif: convertir a JPEG y reducir a ≤1568 px.
- Borradores en `notas.json` → `"borradores"`, copia de imagen en `borradores/` (ignorada en Git).
- Cola de procesamiento en `App`, una foto a la vez; varias fotos = un borrador por foto.
- Errores: sin clave → abre diálogo de clave; fallo → borrador "Error" con "Reintentar".
- Vista previa muestra la foto junto al texto; palabras clave se generan al confirmar.
- Botón "⚙ IA y clave" en Inicio abre el `DialogoIA` existente con texto actualizado.
Build order: (1) datos + IA + cola + clave en Inicio, (2) ventana de vista previa,
(3) aviso en esquina y lista de borradores.

## Unknowns
- Mejoras extra de la GUI fuera de esta función: no definidas.
- Si `appprin_original.py`, `gitignore` y `tareas.json.txt` siguen haciendo falta.
