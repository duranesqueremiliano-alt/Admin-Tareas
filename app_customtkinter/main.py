# main.py
# Arranca la app: carga los datos, arma las tres pestañas y guarda cada 30 segundos y al cerrar.
from datetime import date
import customtkinter as ctk
import ctypes
import os
from m import almacen, notas, tareas, materias, gastos
from pantallas.pantalla_notas import PantallaNotas
from pantallas.pantalla_tareas import PantallaTareas
from pantallas.pantalla_gastos import PantallaGastos
from pantallas import colores

AUTOGUARDADO_MS = 30000
ANCHO_MENU = 150
SECCIONES = ["Notas", "Tareas", "Gastos"]
FUENTE = "Montserrat"

def cargar_fuentes():
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuentes")
    if os.name != "nt" or not os.path.isdir(carpeta):
        return
    for archivo in os.listdir(carpeta):
        if archivo.lower().endswith(".ttf"):
            # 0x10 = solo para este programa, no se instala en Windows
            ctypes.windll.gdi32.AddFontResourceExW(os.path.join(carpeta, archivo), 0x10, 0)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Admin-Tareas")
        self.geometry("1050x680")
        self.minsize(820, 540)

        self.danados = []
        self.notas = self.cargar(notas, "notas.json", [])
        self.tareas = self.cargar(tareas, "tareas.json", [])
        self.materias = self.cargar(materias, "materias.json", [])
        self.gastos = self.cargar(gastos, "gastos.json", None)
        if self.gastos is None:
            self.gastos = gastos.vacio()
        gastos.procesar_automaticos(self.gastos, date.today())

        if self.danados:
            aviso = ctk.CTkLabel(self, text="Archivo dañado: " + ", ".join(self.danados) + ". No se guardará encima hasta que lo repares.",
                                 text_color=colores.ROJO_SUAVE)
            aviso.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 0))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Menú lateral: ancho fijo, solo los nombres
        menu = ctk.CTkFrame(self, width=ANCHO_MENU, corner_radius=0, fg_color=colores.MENU_FONDO)
        menu.grid(row=1, column=0, sticky="ns")
        menu.grid_propagate(False)   # que respete el ancho aunque los botones sean chicos
        menu.pack_propagate(False)

        # Contenido: las 3 pantallas en la misma celda
        contenido = ctk.CTkFrame(self, fg_color="transparent")
        contenido.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)
        contenido.grid_rowconfigure(0, weight=1)
        contenido.grid_columnconfigure(0, weight=1)
        self.pantallas = {
            "Notas": PantallaNotas(contenido, self),
            "Tareas": PantallaTareas(contenido, self),
            "Gastos": PantallaGastos(contenido, self),
        }

        self.armar_logo(menu)
        fuente_menu = ctk.CTkFont(family=FUENTE, size=14)
        self.botones = {}
        for i, nombre in enumerate(SECCIONES, start=1):
            self.pantallas[nombre].grid(row=0, column=0, sticky="nsew")
            boton = ctk.CTkButton(menu, text=nombre, font=fuente_menu, anchor="w", height=38,
                                fg_color="transparent", text_color=colores.TEXTO,
                                hover_color=colores.MENU_HOVER,
                                command=lambda n=nombre: self.mostrar(n))
            boton.pack(fill="x", padx=8, pady=4)
            self.botones[nombre] = boton
            self.bind(f"<Control-Key-{i}>", lambda e, n=nombre: self.mostrar(n))   # Ctrl+1, Ctrl+2, Ctrl+3
        self.mostrar("Notas")
      
        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)
        self.after(AUTOGUARDADO_MS, self.autoguardar)

    def armar_logo(self, menu):
        # Logo provisional: cuadro rojo con las iniciales y el nombre debajo.
        ctk.CTkLabel(menu, text="AT", width=52, height=52, corner_radius=12, fg_color=colores.ROJO,
                     text_color="white", font=ctk.CTkFont(family=FUENTE, size=22, weight="bold")).pack(pady=(18, 6))
        ctk.CTkLabel(menu, text="Admin Tareas", text_color=colores.TEXTO,
                     font=ctk.CTkFont(family=FUENTE, size=15, weight="bold")).pack()
        ctk.CTkFrame(menu, height=2, corner_radius=0, fg_color=colores.ROJO).pack(fill="x", padx=16, pady=(10, 12))

    def mostrar(self, nombre):
        self.pantallas[nombre].tkraise()
        for n, boton in self.botones.items():   # resalta la sección actual en rojo
            if n == nombre:
                boton.configure(fg_color=colores.MENU_ELEGIDO, text_color=colores.ROJO)
            else:
                boton.configure(fg_color="transparent", text_color=colores.TEXTO)

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

    def autoguardar(self):
        self.guardar_todo()
        self.after(AUTOGUARDADO_MS, self.autoguardar)

    def al_cerrar(self):
        self.guardar_todo()
        self.destroy()


if __name__ == "__main__":
    cargar_fuentes()
    ctk.set_default_color_theme(colores.TEMA)   # grises con rojo (pantallas/tema_gris_rojo.json)
    ctk.ThemeManager.theme["CTkFont"]["family"] = FUENTE   # antes de crear widgets para que todos la usen
    ctk.set_appearance_mode("system")
    App().mainloop()