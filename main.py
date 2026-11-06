# main.py
# Arranca la app: carga los datos, arma las tres pestañas y guarda cada 30 segundos y al cerrar.
from datetime import date
import customtkinter as ctk
import almacen
import notas
import tareas
import materias
import gastos
from pantalla_notas import PantallaNotas
from pantalla_tareas import PantallaTareas
from pantalla_gastos import PantallaGastos

AUTOGUARDADO_MS = 30000


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
                                 text_color="#e5a50a")
            aviso.pack(fill="x", padx=12, pady=(10, 0))

        pestanas = ctk.CTkTabview(self)
        pestanas.pack(fill="both", expand=True, padx=12, pady=12)
        for nombre in ["Notas", "Tareas", "Gastos"]:
            pestanas.add(nombre)
        PantallaNotas(pestanas.tab("Notas"), self).pack(fill="both", expand=True)
        PantallaTareas(pestanas.tab("Tareas"), self).pack(fill="both", expand=True)
        PantallaGastos(pestanas.tab("Gastos"), self).pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.al_cerrar)
        self.after(AUTOGUARDADO_MS, self.autoguardar)

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
    ctk.set_appearance_mode("system")
    App().mainloop()
