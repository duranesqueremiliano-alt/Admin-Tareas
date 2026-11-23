# comun.py
# Piezas que usan varias pantallas: textos, cajas, listas de opciones y la ventanita para pedir un nombre.
import flet as ft
import flet_shadcn_ui as shad
from pantallas.colores import GRIS, BORDE


def texto(valor="", color=None, tamano=None, negrita=False, **otros):
    peso = ft.FontWeight.BOLD if negrita else None
    return ft.Text(valor, color=color, size=tamano, weight=peso, **otros)


def gris(valor="", **otros):
    return texto(valor, color=GRIS, **otros)


def caja(contenido, **otros):
    # Un recuadro con borde suave (lo que antes era un CTkFrame).
    return ft.Container(content=contenido, border=ft.Border.all(1, BORDE), border_radius=8, padding=8, **otros)


def opciones(valores):
    # Convierte una lista de textos en opciones para un shad.Select.
    return [shad.SelectOption(value=v, text=v) for v in valores]


def avisar(etiqueta, mensaje, color=None):
    # Cambia el texto de una etiqueta de mensajes (lo que antes era label.configure(text=...)).
    etiqueta.value = mensaje
    etiqueta.color = color


def confirmar(page, titulo, detalle, al_aceptar):
    # Ventana "¿Seguro?" antes de borrar algo. Solo llama a al_aceptar() si dices que sí.
    def si(e):
        page.pop_dialog()
        al_aceptar()
        page.update()

    page.show_dialog(shad.Dialog(
        title=titulo, description=detalle, variant=shad.DialogVariant.ALERT,
        actions=[shad.Button("Cancelar", variant=shad.ButtonVariant.OUTLINE, on_click=lambda e: page.pop_dialog()),
                 shad.Button("Borrar", variant=shad.ButtonVariant.DESTRUCTIVE, on_click=si)]))


def pedir_texto(page, titulo, ejemplo, al_terminar):
    # Ventana con una caja de texto. Llama a al_terminar(nombre) o al_terminar(None) si se cancela.
    entrada = shad.Input(placeholder=ejemplo, autofocus=True)
    respondio = []   # se llena al pulsar un botón, para no responder dos veces

    def aceptar(e):
        respondio.append(True)
        page.pop_dialog()
        al_terminar(entrada.value)
        page.update()

    def cancelar(e):
        respondio.append(True)
        page.pop_dialog()
        al_terminar(None)
        page.update()

    def cerrada(e):
        # Si la cerraron con la X, cuenta como cancelar.
        if not respondio:
            al_terminar(None)
            page.update()

    entrada.on_submit = aceptar
    page.show_dialog(shad.Dialog(
        title=titulo, content=entrada, modal=True, on_dismiss=cerrada,
        actions=[shad.Button("Cancelar", variant=shad.ButtonVariant.OUTLINE, on_click=cancelar),
                 shad.Button("Agregar", on_click=aceptar)]))
