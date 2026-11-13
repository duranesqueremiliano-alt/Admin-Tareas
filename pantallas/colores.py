# colores.py
# Paleta de la app: escala de grises con rojo como único color.
# Cada color es (modo claro, modo oscuro), así CustomTkinter elige solo.
import os

TEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tema_gris_rojo.json")

ROJO = ("#C8102E", "#E0283F")           # acento: botones principales, gastos, vencido
ROJO_HOVER = ("#9B0C23", "#B51E31")
ROJO_SUAVE = ("#D9606F", "#F08A96")     # avisos (antes amarillo)

TEXTO = ("gray10", "gray90")            # texto normal
GRIS = ("gray40", "gray65")             # texto secundario / informativo (antes azul)
GRIS_FUERTE = ("gray30", "gray75")      # cosas "bien" (antes verde)

MENU_FONDO = ("gray85", "gray11")       # barra lateral
MENU_HOVER = ("gray78", "gray20")
MENU_ELEGIDO = ("gray75", "gray23")

BOTON_GRIS = ("gray55", "gray32")       # botones secundarios (Hoy, Pausar, Editar…)
BOTON_GRIS_HOVER = ("gray45", "gray40")
