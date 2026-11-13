# pantalla_notas.py
# Menú de notas a la izquierda (con buscador) y editor a la derecha.
import customtkinter as ctk
from m import notas
from m import materias
from m import palabras_clave
from pantallas.colores import ROJO, ROJO_HOVER

AGREGAR = "+ Agregar materia"


class PantallaNotas(ctk.CTkFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.nota = None
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # ----- Menú de notas -----
        izq = ctk.CTkFrame(self)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        izq.grid_rowconfigure(2, weight=1)
        izq.grid_columnconfigure(0, weight=1)
        self.buscador = ctk.CTkEntry(izq, placeholder_text="Buscar en notas y palabras clave")
        self.buscador.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.buscador.bind("<KeyRelease>", lambda e: self.refrescar())
        ctk.CTkButton(izq, text="Nueva nota", command=self.nueva).grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        self.lista = ctk.CTkScrollableFrame(izq)
        self.lista.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 8))

        # ----- Editor -----
        der = ctk.CTkFrame(self)
        der.grid(row=0, column=1, sticky="nsew")
        der.grid_rowconfigure(2, weight=1)
        der.grid_columnconfigure(0, weight=1)
        fila = ctk.CTkFrame(der, fg_color="transparent")
        fila.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkLabel(fila, text="Materia:").pack(side="left")
        self.materia = ctk.CTkOptionMenu(fila, values=self.opciones_materia(), command=self.elegir_materia)
        self.materia.pack(side="left", padx=6)
        foto = ctk.CTkButton(fila, text="Foto → texto (pendiente)", state="disabled", width=170)
        foto.pack(side="right")
        ctk.CTkLabel(der, text="La primera línea es el título.", text_color="gray").grid(row=1, column=0, sticky="w", padx=10)
        self.editor = ctk.CTkTextbox(der, wrap="word")
        self.editor.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self.info = ctk.CTkLabel(der, text="", text_color="gray", anchor="w")
        self.info.grid(row=3, column=0, sticky="ew", padx=10)
        abajo = ctk.CTkFrame(der, fg_color="transparent")
        abajo.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 8))
        ctk.CTkButton(abajo, text="Guardar nota", command=self.guardar).pack(side="left")
        self.mensaje = ctk.CTkLabel(abajo, text="")
        self.mensaje.pack(side="left", padx=10)

        self.nueva()
        self.refrescar()

    # ----- Materias -----
    def opciones_materia(self):
        opciones = list(self.app.materias)
        if not opciones:
            opciones = ["General"]
        opciones.append(AGREGAR)
        return opciones

    def elegir_materia(self, valor):
        if valor != AGREGAR:
            return
        nombre = ctk.CTkInputDialog(text="Nombre de la materia:", title="Agregar materia").get_input()
        if nombre and materias.agregar(self.app.materias, nombre):
            self.materia.configure(values=self.opciones_materia())
            self.materia.set(nombre.strip())
        else:
            self.materia.set(self.opciones_materia()[0])

    # ----- Menú -----
    def refrescar(self):
        for hijo in self.lista.winfo_children():
            hijo.destroy()
        for nota in notas.buscar(self.app.notas, self.buscador.get()):
            self.tarjeta(nota)

    def tarjeta(self, nota):
        caja = ctk.CTkFrame(self.lista, border_width=2 if nota is self.nota else 0)
        caja.pack(fill="x", pady=4)
        caja.grid_columnconfigure(0, weight=1)
        titulo = ctk.CTkLabel(caja, text=notas.titulo(nota), font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
        titulo.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        lineas = nota["texto"].strip().splitlines()
        vista = " ".join(lineas[1:])[:70]
        detalle = vista + "\n" + nota["materia"] + " · " + nota["fechacreacion"]
        if nota["palabrasclave"]:
            detalle += "\n# " + "  # ".join(nota["palabrasclave"])
        texto = ctk.CTkLabel(caja, text=detalle, justify="left", anchor="w", text_color="gray", wraplength=260)
        texto.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        botones = ctk.CTkFrame(caja, fg_color="transparent")
        botones.grid(row=0, column=1, rowspan=2, padx=4)
        ctk.CTkButton(botones, text="▲", width=30, command=lambda: self.subir(nota)).pack(pady=2)
        ctk.CTkButton(botones, text="✕", width=30, fg_color=ROJO, hover_color=ROJO_HOVER,
                      command=lambda: self.borrar(nota)).pack(pady=2)
        for elemento in (caja, titulo, texto):
            elemento.bind("<Button-1>", lambda e: self.abrir(nota))

    # ----- Acciones -----
    def nueva(self):
        self.nota = notas.crear(self.materia.get())
        self.editor.delete("1.0", "end")
        self.info.configure(text="Nota nueva")
        self.mensaje.configure(text="")
        self.editor.focus_set()

    def abrir(self, nota):
        self.nota = nota
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", nota["texto"])
        if nota["materia"] in self.app.materias:
            self.materia.set(nota["materia"])
        self.info.configure(text="Creada: " + nota["fechacreacion"] + "   Palabras clave: " + ", ".join(nota["palabrasclave"]))
        self.mensaje.configure(text="")
        self.refrescar()

    def guardar(self):
        texto = self.editor.get("1.0", "end").rstrip("\n")
        self.nota["texto"] = texto
        materia = self.materia.get()
        if materia != AGREGAR:
            self.nota["materia"] = materia
        self.nota["palabrasclave"] = palabras_clave.extraer(texto)
        tipo = notas.guardar(self.app.notas, self.nota)
        mensajes = {"creacion": "La nota se creó.", "actualizacion": "La nota se actualizó.",
                    "borrada": "La nota estaba vacía: no se guardó."}
        self.mensaje.configure(text=mensajes[tipo])
        if tipo == "borrada":
            self.nota = notas.crear(self.materia.get())
        else:
            self.info.configure(text="Creada: " + self.nota["fechacreacion"] + "   Palabras clave: " + ", ".join(self.nota["palabrasclave"]))
        self.refrescar()

    def subir(self, nota):
        notas.mover(self.app.notas, nota["id"], 0)
        self.refrescar()

    def borrar(self, nota):
        notas.borrar(self.app.notas, nota["id"])
        if nota is self.nota:
            self.nueva()
        self.refrescar()
