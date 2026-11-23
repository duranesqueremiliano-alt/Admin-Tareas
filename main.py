# main.py
# Arranca la app: carga los datos, arma el menú lateral con las tres pantallas
# y guarda cada 30 segundos y al cerrar.
import asyncio
from datetime import date
import os
import flet as ft
import flet_shadcn_ui as shad
from m import almacen, notas, tareas, materias, gastos
from pantallas.pantalla_notas import PantallaNotas
from pantallas.pantalla_tareas import PantallaTareas
from pantallas.pantalla_gastos import PantallaGastos
from pantallas import colores
from pantallas.comun import texto

AUTOGUARDADO_S = 30
ANCHO_MENU = 170
SECCIONES = ["Notas", "Tareas", "Gastos"]
ICONOS = {"Notas": shad.LucideIcons.NOTEBOOK_PEN, "Tareas": shad.LucideIcons.LIST_TODO,
          "Gastos": shad.LucideIcons.WALLET}
FUENTE = "Montserrat"
CARPETA = os.path.dirname(os.path.abspath(__file__))


class App:
    # Ya no es una ventana: es una clase normal que guarda los datos y la página de Flet.
    def __init__(self, page):
        self.page = page
        page.title = "Admin-Tareas"
        page.window.width = 1050
        page.window.height = 680
        page.window.min_width = 820
        page.window.min_height = 540
        page.padding = 0
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.fonts = {FUENTE: "Montserrat-Regular.ttf"}
        page.theme = ft.Theme(font_family=FUENTE)
        page.dark_theme = ft.Theme(font_family=FUENTE)
        # Español para los calendarios (nombres de meses y días).
        page.locale_configuration = ft.LocaleConfiguration(supported_locales=[ft.Locale("es", "MX")],
                                                           current_locale=ft.Locale("es", "MX"))

        self.danados = []
        self.notas = self.cargar(notas, "notas.json", [])
        self.tareas = self.cargar(tareas, "tareas.json", [])
        self.materias = self.cargar(materias, "materias.json", [])
        self.gastos = self.cargar(gastos, "gastos.json", None)
        if self.gastos is None:
            self.gastos = gastos.vacio()
        gastos.procesar_automaticos(self.gastos, date.today())

        # Las 3 pantallas viven siempre en la página; solo se ve una (visible=True).
        self.pantallas = {
            "Notas": PantallaNotas(self),
            "Tareas": PantallaTareas(self),
            "Gastos": PantallaGastos(self),
        }
        contenido = ft.Stack([self.pantallas[n].vista for n in SECCIONES], expand=True)

        self.botones = {}
        menu = ft.Column(self.armar_logo(), spacing=4)
        for nombre in SECCIONES:
            boton = shad.Button(nombre, leading=ICONOS[nombre], width=ANCHO_MENU - 16, color=colores.TEXTO,
                                on_click=lambda e, n=nombre: self.mostrar(n))
            menu.controls.append(boton)
            self.botones[nombre] = boton

        filas = []
        if self.danados:
            filas.append(shad.Alert(title="Archivo dañado: " + ", ".join(self.danados),
                                    description="No se guardará encima hasta que lo repares.",
                                    variant=shad.AlertVariant.DESTRUCTIVE))
        filas.append(ft.Row([
            ft.Container(menu, width=ANCHO_MENU, bgcolor=colores.MENU_FONDO, padding=8),
            ft.Container(contenido, expand=True, padding=12),
        ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH))

        page.add(shad.Theme(color_scheme=shad.ColorScheme.RED, expand=True,
                            content=ft.Column(filas, expand=True, spacing=0)))
        self.mostrar("Notas")

        page.on_keyboard_event = self.teclas
        page.window.prevent_close = True       # así podemos guardar antes de cerrar
        page.window.on_event = self.evento_ventana
        page.run_task(self.autoguardar)

    def armar_logo(self):
        # Logo provisional: cuadro rojo con las iniciales y el nombre debajo.
        cuadro = ft.Container(texto("AT", color="white", tamano=22, negrita=True), width=52, height=52,
                              bgcolor=colores.ROJO, border_radius=12, alignment=ft.Alignment.CENTER)
        return [
            ft.Container(height=10),
            ft.Row([cuadro], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([texto("Admin Tareas", tamano=15, negrita=True)], alignment=ft.MainAxisAlignment.CENTER),
            shad.Separator(color=colores.ROJO, thickness=2, margin=ft.Margin.symmetric(vertical=8)),
        ]

    def mostrar(self, nombre):
        for n in SECCIONES:
            elegida = n == nombre
            self.pantallas[n].vista.visible = elegida
            # la sección actual va con el botón relleno; las demás, transparentes
            self.botones[n].variant = shad.ButtonVariant.SECONDARY if elegida else shad.ButtonVariant.GHOST
        self.page.update()

    def materias_cambiaron(self):
        # Notas y Tareas comparten la lista self.materias, pero cada una tiene su propio desplegable.
        # Cuando una agrega una materia, aquí se avisa a todas para que rehagan su desplegable.
        for pantalla in self.pantallas.values():
            if hasattr(pantalla, "actualizar_materias"):
                pantalla.actualizar_materias()

    def teclas(self, e):
        # Ctrl+1, Ctrl+2, Ctrl+3 cambian de sección.
        if e.ctrl and e.key in ("1", "2", "3"):
            self.mostrar(SECCIONES[int(e.key) - 1])

    def cargar(self, modulo, nombre, por_defecto):
        try:
            return modulo.cargar()
        except almacen.ArchivoDanado:
            self.danados.append(nombre)
            return por_defecto

    def guardar_todo(self):
        pares = [(notas, self.notas), (tareas, self.tareas), (materias, self.materias), (gastos, self.gastos)]
        for modulo, datos in pares:
            try:
                modulo.guardar_archivo(datos)
            except almacen.ArchivoDanado:
                pass

    async def autoguardar(self):
        # Corre "en paralelo" con la app: espera 30 s, guarda, y vuelve a empezar.
        while True:
            await asyncio.sleep(AUTOGUARDADO_S)
            self.guardar_todo()

    async def evento_ventana(self, e):
        if e.type == ft.WindowEventType.CLOSE:
            self.guardar_todo()
            await self.page.window.destroy()


def main(page: ft.Page):
    App(page)


if __name__ == "__main__":
    os.chdir(CARPETA)   # datos/ se busca desde aquí, igual que antes con el .bat
    ft.run(main, assets_dir=os.path.join(CARPETA, "fuentes"))
