# colores.py
# Paleta de la app: escala de grises con rojo como único color.
# En Flet cada color es un solo valor. Los grises salen del tema (ft.Colors.ON_SURFACE...),
# así que cambian solos entre modo claro y oscuro. El rojo es fijo porque se ve bien en los dos.
import flet as ft

ROJO = "#E0283F"                         # acento: gastos, vencido, borrar
ROJO_SUAVE = "#E5707D"                   # avisos

TEXTO = ft.Colors.ON_SURFACE             # texto normal
GRIS = ft.Colors.ON_SURFACE_VARIANT      # texto secundario / informativo
GRIS_FUERTE = ft.Colors.ON_SURFACE       # cosas "bien" (ingresos, uso sano)

MENU_FONDO = ft.Colors.SURFACE_CONTAINER_LOW      # barra lateral
BORDE = ft.Colors.OUTLINE_VARIANT                 # bordes de cajas y listas
