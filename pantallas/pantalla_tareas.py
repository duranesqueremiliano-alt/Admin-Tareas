# pantalla_tareas.py
# Formulario arriba, filtro y lista de tareas abajo.
from datetime import datetime, timedelta
import customtkinter as ctk
from logica import tareas
from logica import materias

AGREGAR = "+ Agregar materia"


class PantallaTareas(ctk.CTkFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.tarea = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ----- Formulario -----
        form = ctk.CTkFrame(self)
        form.grid(row=0, column=0, sticky="ew")
        form.grid_columnconfigure(0, weight=1)
        self.titulo = ctk.CTkEntry(form, placeholder_text="¿Qué hay que hacer?")
        self.titulo.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.fecha = ctk.CTkEntry(form, width=150, placeholder_text="AAAA-MM-DD HH:MM")
        self.fecha.grid(row=0, column=1, padx=4)
        self.materia = ctk.CTkOptionMenu(form, values=self.opciones_materia(), command=self.elegir_materia, width=150)
        self.materia.grid(row=0, column=2, padx=4)
        ctk.CTkButton(form, text="Guardar", width=90, command=self.guardar).grid(row=0, column=3, padx=4)
        ctk.CTkButton(form, text="Nueva", width=70, fg_color="gray", command=self.nueva).grid(row=0, column=4, padx=(4, 8))
        rapidas = ctk.CTkFrame(form, fg_color="transparent")
        rapidas.grid(row=1, column=0, columnspan=5, sticky="w", padx=8, pady=(0, 8))
        for texto, dias in [("Hoy", 0), ("Mañana", 1), ("En 1 semana", 7)]:
            ctk.CTkButton(rapidas, text=texto, width=90, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                          command=lambda d=dias: self.poner_fecha(d)).pack(side="left", padx=(0, 6))
        self.mensaje = ctk.CTkLabel(rapidas, text="")
        self.mensaje.pack(side="left", padx=10)

        # ----- Filtro y lista -----
        self.filtro = ctk.CTkSegmentedButton(self, values=["Activas", "Vencidas", "Completadas", "Todas"],
                                             command=lambda v: self.refrescar())
        self.filtro.set("Activas")
        self.filtro.grid(row=1, column=0, sticky="w", pady=8)
        self.lista = ctk.CTkScrollableFrame(self)
        self.lista.grid(row=2, column=0, sticky="nsew")
        self.lista.grid_columnconfigure(1, weight=1)

        self.nueva()
        self.refrescar()

    def opciones_materia(self):
        opciones = list(self.app.materias)
        if not opciones:
            opciones = ["General"]
        opciones.append(AGREGAR)
        return opciones

    def elegir_materia(self, valor):
        if valor != AGREGAR:
            return
        nombre = ctk.CTkInputDialog(text="Nombre de la materia o categoría:", title="Agregar").get_input()
        if nombre and materias.agregar(self.app.materias, nombre):
            self.materia.configure(values=self.opciones_materia())
            self.materia.set(nombre.strip())
        else:
            self.materia.set(self.opciones_materia()[0])

    def poner_fecha(self, dias):
        fecha = datetime.now() + timedelta(days=dias)
        self.fecha.delete(0, "end")
        self.fecha.insert(0, fecha.strftime("%Y-%m-%d") + " 23:59")

    def nueva(self):
        self.tarea = None
        self.titulo.delete(0, "end")
        self.poner_fecha(1)
        self.mensaje.configure(text="")
        self.titulo.focus_set()

    def editar(self, tarea):
        self.tarea = tarea
        self.titulo.delete(0, "end")
        self.titulo.insert(0, tarea["titulo"])
        self.fecha.delete(0, "end")
        self.fecha.insert(0, tarea["fechalimite"])
        if tarea["materia"] in self.app.materias:
            self.materia.set(tarea["materia"])
        self.mensaje.configure(text="Editando: guarda para actualizarla.")

    def guardar(self):
        limite = self.fecha.get().strip()
        try:
            datetime.strptime(limite, tareas.FECHA)
        except ValueError:
            self.mensaje.configure(text="La fecha va así: 2026-11-20 23:59", text_color="#e5a50a")
            return
        materia = self.materia.get()
        if materia == AGREGAR:
            materia = ""
        if self.tarea is None:
            self.tarea = tareas.crear(self.titulo.get(), limite, materia)
        else:
            self.tarea["titulo"] = self.titulo.get()
            self.tarea["fechalimite"] = limite
            self.tarea["materia"] = materia
        tipo = tareas.guardar(self.app.tareas, self.tarea)
        mensajes = {"creacion": "La tarea se creó.", "actualizacion": "La tarea se actualizó.",
                    "borrada": "Sin título no se guarda."}
        self.mensaje.configure(text=mensajes[tipo], text_color=("gray10", "gray90"))
        self.tarea = None
        self.titulo.delete(0, "end")
        self.refrescar()

    def estado_de(self, tarea):
        if tarea["estado"] == "completada":
            return "Completada"
        if tareas.esta_vencida(tarea):
            return "Vencida"
        return "Activa"

    def refrescar(self):
        for hijo in self.lista.winfo_children():
            hijo.destroy()
        filtro = self.filtro.get()
        fila = 0
        for tarea in self.app.tareas:
            estado = self.estado_de(tarea)
            if filtro == "Activas" and estado != "Activa":
                continue
            if filtro == "Vencidas" and estado != "Vencida":
                continue
            if filtro == "Completadas" and estado != "Completada":
                continue
            marca = ctk.CTkCheckBox(self.lista, text="", width=24,
                                    command=lambda t=tarea: self.alternar(t))
            if estado == "Completada":
                marca.select()
            marca.grid(row=fila, column=0, padx=(4, 8), pady=4)
            texto = tarea["titulo"] + "\n" + tarea["materia"] + " · límite " + tarea["fechalimite"]
            etiqueta = ctk.CTkLabel(self.lista, text=texto, justify="left", anchor="w")
            etiqueta.grid(row=fila, column=1, sticky="ew")
            etiqueta.bind("<Button-1>", lambda e, t=tarea: self.editar(t))
            color = {"Vencida": "#e01b24", "Completada": "gray", "Activa": "#2ec27e"}[estado]
            ctk.CTkLabel(self.lista, text=estado, text_color=color, width=90).grid(row=fila, column=2)
            ctk.CTkButton(self.lista, text="✕", width=30, fg_color="#a33", hover_color="#822",
                          command=lambda t=tarea: self.borrar(t)).grid(row=fila, column=3, padx=4)
            fila += 1
        if fila == 0:
            ctk.CTkLabel(self.lista, text="No hay tareas aquí.", text_color="gray").grid(row=0, column=1, pady=20)

    def alternar(self, tarea):
        if tarea["estado"] == "completada":
            tareas.reabrir(tarea)
        else:
            tareas.completar(tarea)
        self.refrescar()

    def borrar(self, tarea):
        tareas.borrar(self.app.tareas, tarea["id"])
        self.refrescar()
