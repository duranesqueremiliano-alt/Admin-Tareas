# Admin-Tareas

Organizador personal de escritorio en Python con **customtkinter**: notas, tareas y gastos.

Es la segunda versión. La primera la hice con IA ("vibecoding") y está en `app_original/`.
Esta la reescribí yo, línea por línea, para entender cómo funciona cada parte.

## Cómo correrla

```
pip install -r requirements.txt
python main.py
```

Los datos se guardan en la carpeta `datos/` (no se sube a GitHub).

## Cómo está armada

| Archivo | Qué hace |
|---|---|
| `main.py` | Arranca la app, carga los datos y guarda cada 30 segundos y al cerrar |
| `almacen.py` | Lee y escribe JSON en `datos/`; no deja guardar encima de un archivo dañado |
| `notas.py` | Notas: crear, guardar, borrar, mover, buscar y sacar el título |
| `materias.py` | La lista de materias que comparten notas y tareas |
| `tareas.py` | Tareas con fecha límite; "vencida" se calcula |
| `gastos.py` | Cuentas (débito, crédito, efectivo), movimientos, pagos recurrentes y resumen por categoría |
| `palabras_clave.py` | Palabras clave automáticas (las que más se repiten) |
| `pantalla_*.py` | Las pantallas, sencillas, con customtkinter |
| `indice_demo.py` | Demo: buscar en una lista contra buscar en un diccionario por id |
| `docs/ruta-notas.html` | La Ruta: página para aprender escribiendo cada línea del proyecto |

Los archivos de datos (`almacen`, `notas`, `materias`, `tareas`, `gastos`) no importan customtkinter:
se pueden probar solos con `python archivo.py`.

## Estructuras de datos que usa

- **Lista de diccionarios** para notas y tareas; el orden del menú es la posición en la lista (`insert`, `pop`).
- **Búsqueda lineal** en `buscar_posicion` (O(n)). `indice_demo.py` muestra la mejora con un diccionario por id (O(1)).
- **Diccionario como contador** en `resumen_por_categoria` y en `palabras_clave.extraer`.
- **JSON** para guardar listas y diccionarios en disco.

## Pendiente

- Foto de una nota → texto con IA.
- Importar fórmulas y diagramas.
- Papelera (con una cola) y deshacer (con una pila).
