import json
import uuid
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path


# Archivo donde se guardarán las tareas
ARCHIVO_DATOS = Path(__file__).with_name("tareas.json")

# Formato que utilizaremos para fechas
FORMATO_FECHA = "%Y-%m-%d %H:%M"


class AdministradorTareas:

    def __init__(self, root):

        self.root = root

        self.root.title("Administrador de Tareas")
        self.root.geometry("900x620")
        self.root.minsize(760, 520)

        self.tareas = []

        self.descripcion_visible = False

        # Crear interfaz
        self.crear_interfaz()

        # Cargar información guardada
        self.cargar_tareas()

        # Revisar tareas expiradas
        self.actualizar_estados()

        # Mostrar tareas
        self.refrescar_listas()

        # Primera revisión automática
        self.root.after(
            1000,
            self.revisar_alertas_y_expiraciones
        )


    # ==========================================================
    # INTERFAZ
    # ==========================================================

    def crear_interfaz(self):

        # ======================================================
        # ESTRUCTURA PRINCIPAL
        # ======================================================

        sidebar = ctk.CTkFrame(
            self.root,
            width=220,
            corner_radius=0
        )

        sidebar.pack(
            side="left",
            fill="y"
        )

        sidebar.pack_propagate(False)


        # Área derecha
        contenido = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color="#111827"
        )

        contenido.pack(
            side="right",
            fill="both",
            expand=True
        )


        # ======================================================
        # SIDEBAR
        # ======================================================

        logo = ctk.CTkLabel(
            sidebar,
            text="TASKFLOW",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        )

        logo.pack(
            padx=20,
            pady=(30, 35)
        )


        boton_inicio = ctk.CTkButton(
            sidebar,
            text="🏠  Inicio",
            anchor="w",
            height=45
        )

        boton_inicio.pack(
            fill="x",
            padx=15,
            pady=5
        )


        boton_tareas = ctk.CTkButton(
            sidebar,
            text="📋  Mis tareas",
            anchor="w",
            height=45
        )

        boton_tareas.pack(
            fill="x",
            padx=15,
            pady=5
        )


        boton_pendientes = ctk.CTkButton(
            sidebar,
            text="⏳  Pendientes",
            anchor="w",
            height=45,
            command=lambda: self.notebook.select(0)
        )

        boton_pendientes.pack(
            fill="x",
            padx=15,
            pady=5
        )


        boton_completadas = ctk.CTkButton(
            sidebar,
            text="✅  Completadas",
            anchor="w",
            height=45,
            command=lambda: self.notebook.select(1)
        )

        boton_completadas.pack(
            fill="x",
            padx=15,
            pady=5
        )


        boton_expiradas = ctk.CTkButton(
            sidebar,
            text="⚠  Expiradas",
            anchor="w",
            height=45,
            command=lambda: self.notebook.select(2)
        )

        boton_expiradas.pack(
            fill="x",
            padx=15,
            pady=5
        )


        # ======================================================
        # CONTENIDO PRINCIPAL
        # ======================================================

        contenedor = ctk.CTkFrame(
            contenido,
            fg_color="#111827",
            corner_radius=0
        )

        contenedor.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )


        # ======================================================
        # TÍTULO
        # ======================================================

        titulo = ctk.CTkLabel(
            contenedor,
            text="Administrador de Tareas",
            font=ctk.CTkFont(
                family="Arial",
                size=28,
                weight="bold"
            ),
            text_color="white"
        )

        titulo.pack(
            anchor="w",
            pady=(0, 15)
        )


        # ======================================================
        # FORMULARIO
        # ======================================================

        formulario = ttk.LabelFrame(
            contenedor,
            text="Nueva tarea",
            padding=12
        )

        formulario.pack(
            fill="x"
        )


        # Primera fila
        fila1 = ttk.Frame(
            formulario
        )

        fila1.pack(
            fill="x",
            pady=4
        )


        # Nombre
        ttk.Label(
            fila1,
            text="Nombre:"
        ).pack(
            side="left"
        )


        self.entrada_nombre = ttk.Entry(
            fila1
        )

        self.entrada_nombre.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(8, 15)
        )


        # Fecha
        ttk.Label(
            fila1,
            text="Fecha (AAAA-MM-DD):"
        ).pack(
            side="left"
        )


        self.entrada_fecha = ttk.Entry(
            fila1,
            width=12
        )

        self.entrada_fecha.pack(
            side="left",
            padx=(8, 15)
        )


        # Hora
        ttk.Label(
            fila1,
            text="Hora (HH:MM):"
        ).pack(
            side="left"
        )


        self.entrada_hora = ttk.Entry(
            fila1,
            width=8
        )

        self.entrada_hora.pack(
            side="left",
            padx=(8, 0)
        )


        # Fecha sugerida
        fecha_sugerida = datetime.now() + timedelta(
            hours=24
        )

        self.entrada_fecha.insert(
            0,
            fecha_sugerida.strftime("%Y-%m-%d")
        )

        self.entrada_hora.insert(
            0,
            fecha_sugerida.strftime("%H:%M")
        )


        # Segunda fila
        fila2 = ttk.Frame(
            formulario
        )

        fila2.pack(
            fill="x",
            pady=(8, 0)
        )


        # Descripción
        self.boton_descripcion = ttk.Button(
            fila2,
            text="Agregar descripción ▼",
            command=self.alternar_descripcion
        )

        self.boton_descripcion.pack(
            side="left"
        )


        # Agregar
        boton_agregar = ttk.Button(
            fila2,
            text="Agregar tarea",
            command=self.agregar_tarea
        )

        boton_agregar.pack(
            side="right"
        )


        # ======================================================
        # DESCRIPCIÓN DESPLEGABLE
        # ======================================================

        self.frame_descripcion = ttk.Frame(
            formulario
        )


        ttk.Label(
            self.frame_descripcion,
            text="Descripción opcional:"
        ).pack(
            anchor="w",
            pady=(8, 4)
        )


        self.texto_descripcion = tk.Text(
            self.frame_descripcion,
            height=4,
            wrap="word"
        )

        self.texto_descripcion.pack(
            fill="x"
        )


        # Aviso
        ttk.Label(
            contenedor,
            text="⚠ Las tareas que venzan dentro de 12 horas generarán una alerta."
        ).pack(
            anchor="w",
            pady=(8, 10)
        )


        # ======================================================
        # PESTAÑAS
        # ======================================================

        self.notebook = ttk.Notebook(
            contenedor
        )

        self.notebook.pack(
            fill="both",
            expand=True
        )


        self.tree_pendientes = self.crear_pestana(
            "Pendientes"
        )

        self.tree_completadas = self.crear_pestana(
            "Completadas"
        )

        self.tree_expiradas = self.crear_pestana(
            "Expiradas"
        )


        # ======================================================
        # BOTONES INFERIORES
        # ======================================================

        botones = ttk.Frame(
            contenedor
        )

        botones.pack(
            fill="x",
            pady=(10, 0)
        )


        ttk.Button(
            botones,
            text="✓ Marcar como completada",
            command=self.marcar_completada_actual
        ).pack(
            side="left"
        )


        ttk.Button(
            botones,
            text="✎ Editar tarea",
            command=self.editar_actual
        ).pack(
            side="left",
            padx=8
        )


        ttk.Button(
            botones,
            text="Eliminar tarea",
            command=self.eliminar_actual
        ).pack(
            side="left",
            padx=8
        )


        ttk.Button(
            botones,
            text="Actualizar",
            command=self.actualizar_manual
        ).pack(
            side="right"
        )

    # ==========================================================
    # CREAR PESTAÑAS
    # ==========================================================

    def crear_pestana(self, titulo):

        frame = ttk.Frame(
            self.notebook,
            padding=8
        )

        self.notebook.add(
            frame,
            text=titulo
        )


        columnas = (
            "nombre",
            "fecha",
            "descripcion"
        )


        tree = ttk.Treeview(
            frame,
            columns=columnas,
            show="headings",
            selectmode="browse"
        )


        # Encabezados
        tree.heading(
            "nombre",
            text="Tarea"
        )

        tree.heading(
            "fecha",
            text="Fecha límite"
        )

        tree.heading(
            "descripcion",
            text="Descripción"
        )


        # Tamaños
        tree.column(
            "nombre",
            width=220,
            anchor="w"
        )

        tree.column(
            "fecha",
            width=150,
            anchor="center"
        )

        tree.column(
            "descripcion",
            width=420,
            anchor="w"
        )


        # Scroll
        scroll = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=scroll.set
        )


        tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scroll.pack(
            side="right",
            fill="y"
        )


        return tree


    # ==========================================================
    # MOSTRAR / OCULTAR DESCRIPCIÓN
    # ==========================================================

    def alternar_descripcion(self):

        if self.descripcion_visible:

            self.frame_descripcion.pack_forget()

            self.boton_descripcion.config(
                text="Agregar descripción ▼"
            )

            self.descripcion_visible = False

        else:

            self.frame_descripcion.pack(
                fill="x"
            )

            self.boton_descripcion.config(
                text="Ocultar descripción ▲"
            )

            self.descripcion_visible = True


    # ==========================================================
    # AGREGAR TAREA
    # ==========================================================

    def agregar_tarea(self):

        nombre = self.entrada_nombre.get().strip()

        fecha = self.entrada_fecha.get().strip()

        hora = self.entrada_hora.get().strip()

        descripcion = self.texto_descripcion.get(
            "1.0",
            "end"
        ).strip()


        # Validar nombre
        if not nombre:

            messagebox.showwarning(
                "Falta información",
                "Escribe el nombre de la tarea."
            )

            return


        # Validar fecha
        try:

            fecha_limite = datetime.strptime(
                f"{fecha} {hora}",
                FORMATO_FECHA
            )

        except ValueError:

            messagebox.showerror(
                "Fecha inválida",
                "Usa este formato:\n\n"
                "Fecha: AAAA-MM-DD\n"
                "Hora: HH:MM\n\n"
                "Ejemplo:\n"
                "2026-09-25\n"
                "18:30"
            )

            return


        # Revisar si ya expiró
        if fecha_limite <= datetime.now():

            estado = "expirada"

        else:

            estado = "pendiente"


        # Crear tarea
        nueva_tarea = {

            "id": str(uuid.uuid4()),

            "nombre": nombre,

            "descripcion": descripcion,

            "fecha_limite":
                fecha_limite.strftime(FORMATO_FECHA),

            "estado": estado,

            "alerta_12h_enviada": False
        }


        # Agregar a la lista
        self.tareas.append(
            nueva_tarea
        )


        # Guardar
        self.guardar_tareas()

        self.refrescar_listas()


        # Limpiar campos
        self.entrada_nombre.delete(
            0,
            "end"
        )

        self.texto_descripcion.delete(
            "1.0",
            "end"
        )


        # Mensaje
        if estado == "expirada":

            messagebox.showinfo(
                "Tarea expirada",
                "La fecha indicada ya pasó.\n\n"
                "La tarea fue enviada a Expiradas."
            )

        else:

            messagebox.showinfo(
                "Tarea agregada",
                "La tarea se agregó correctamente."
            )


        # Revisar si ya está dentro de las 12 horas
        self.comprobar_alertas()


    # ==========================================================
    # GUARDAR
    # ==========================================================

    def guardar_tareas(self):

        try:

            with open(
                ARCHIVO_DATOS,
                "w",
                encoding="utf-8"
            ) as archivo:

                json.dump(
                    self.tareas,
                    archivo,
                    ensure_ascii=False,
                    indent=4
                )

        except OSError as error:

            messagebox.showerror(
                "Error",
                f"No se pudieron guardar las tareas:\n{error}"
            )


    # ==========================================================
    # CARGAR
    # ==========================================================

    def cargar_tareas(self):

        if not ARCHIVO_DATOS.exists():

            self.tareas = []

            return


        try:

            with open(
                ARCHIVO_DATOS,
                "r",
                encoding="utf-8"
            ) as archivo:

                datos = json.load(
                    archivo
                )


            if isinstance(datos, list):

                self.tareas = datos

            else:

                self.tareas = []


        except (json.JSONDecodeError, OSError):

            self.tareas = []

            messagebox.showwarning(
                "Aviso",
                "No se pudo leer tareas.json."
            )


        # Corregir tareas antiguas
        for tarea in self.tareas:

            tarea.setdefault(
                "id",
                str(uuid.uuid4())
            )

            tarea.setdefault(
                "descripcion",
                ""
            )

            tarea.setdefault(
                "estado",
                "pendiente"
            )

            tarea.setdefault(
                "alerta_12h_enviada",
                False
            )


    # ==========================================================
    # REVISAR TAREAS VENCIDAS
    # ==========================================================

    def actualizar_estados(self):

        ahora = datetime.now()

        hubo_cambios = False


        for tarea in self.tareas:

            if tarea.get("estado") != "pendiente":

                continue


            try:

                fecha_limite = datetime.strptime(
                    tarea["fecha_limite"],
                    FORMATO_FECHA
                )

            except (KeyError, ValueError):

                continue


            if fecha_limite <= ahora:

                tarea["estado"] = "expirada"

                hubo_cambios = True


        if hubo_cambios:

            self.guardar_tareas()


    # ==========================================================
    # COMPROBAR ALERTAS
    # ==========================================================

    def comprobar_alertas(self):

        ahora = datetime.now()

        limite_alerta = ahora + timedelta(
            hours=12
        )

        por_vencer = []

        hubo_cambios = False


        for tarea in self.tareas:

            if tarea.get("estado") != "pendiente":

                continue


            try:

                fecha_limite = datetime.strptime(
                    tarea["fecha_limite"],
                    FORMATO_FECHA
                )

            except (KeyError, ValueError):

                continue


            # Si ya venció
            if fecha_limite <= ahora:

                tarea["estado"] = "expirada"

                hubo_cambios = True

                continue


            # Si le quedan 12 horas o menos
            if (
                ahora < fecha_limite <= limite_alerta
                and
                not tarea.get(
                    "alerta_12h_enviada",
                    False
                )
            ):

                por_vencer.append(
                    tarea
                )

                tarea[
                    "alerta_12h_enviada"
                ] = True

                hubo_cambios = True


        if hubo_cambios:

            self.guardar_tareas()

            self.refrescar_listas()


        # Mostrar alerta
        if por_vencer:

            mensaje = ""


            for tarea in por_vencer:

                mensaje += (
                    f"• {tarea['nombre']}\n"
                    f"  Vence: {tarea['fecha_limite']}\n\n"
                )


            messagebox.showwarning(
                "⚠ Tareas próximas a vencer",
                "Estas tareas vencen dentro "
                "de las próximas 12 horas:\n\n"
                + mensaje
            )


    # ==========================================================
    # REVISIÓN AUTOMÁTICA
    # ==========================================================

    def revisar_alertas_y_expiraciones(self):

        self.actualizar_estados()

        self.comprobar_alertas()

        self.refrescar_listas()


        # Revisar nuevamente en 60 segundos
        self.root.after(
            60000,
            self.revisar_alertas_y_expiraciones
        )


    # ==========================================================
    # ACTUALIZAR LISTAS
    # ==========================================================

    def refrescar_listas(self):

        # Limpiar las 3 tablas
        for tree in (

            self.tree_pendientes,

            self.tree_completadas,

            self.tree_expiradas

        ):

            for item in tree.get_children():

                tree.delete(item)


        # Agregar las tareas
        for tarea in self.tareas:

            descripcion = tarea.get(
                "descripcion",
                ""
            ).replace(
                "\n",
                " "
            )


            valores = (

                tarea.get(
                    "nombre",
                    ""
                ),

                tarea.get(
                    "fecha_limite",
                    ""
                ),

                descripcion
            )


            estado = tarea.get(
                "estado",
                "pendiente"
            )


            if estado == "pendiente":

                tree = self.tree_pendientes


            elif estado == "completada":

                tree = self.tree_completadas


            else:

                tree = self.tree_expiradas


            tree.insert(

                "",

                "end",

                iid=tarea["id"],

                values=valores
            )


        # Contadores
        pendientes = len([
            t for t in self.tareas
            if t.get("estado") == "pendiente"
        ])

        completadas = len([
            t for t in self.tareas
            if t.get("estado") == "completada"
        ])

        expiradas = len([
            t for t in self.tareas
            if t.get("estado") == "expirada"
        ])


        self.notebook.tab(
            0,
            text=f"Pendientes ({pendientes})"
        )

        self.notebook.tab(
            1,
            text=f"Completadas ({completadas})"
        )

        self.notebook.tab(
            2,
            text=f"Expiradas ({expiradas})"
        )


    # ==========================================================
    # OBTENER PESTAÑA ACTUAL
    # ==========================================================

    def obtener_tree_actual(self):

        indice = self.notebook.index(
            self.notebook.select()
        )


        if indice == 0:

            return self.tree_pendientes


        elif indice == 1:

            return self.tree_completadas


        else:

            return self.tree_expiradas


    # ==========================================================
    # OBTENER TAREA SELECCIONADA
    # ==========================================================

    def obtener_id_seleccionado(self):

        tree = self.obtener_tree_actual()

        seleccion = tree.selection()


        if not seleccion:

            messagebox.showwarning(
                "Selecciona una tarea",
                "Primero selecciona una tarea."
            )

            return None


        return seleccion[0]


    # ==========================================================
    # MARCAR COMO COMPLETADA
    # ==========================================================

    def marcar_completada_actual(self):

        tarea_id = self.obtener_id_seleccionado()


        if tarea_id is None:

            return


        for tarea in self.tareas:

            if tarea["id"] == tarea_id:


                if tarea.get(
                    "estado"
                ) == "completada":

                    messagebox.showinfo(
                        "Información",
                        "Esta tarea ya está completada."
                    )

                    return


                tarea[
                    "estado"
                ] = "completada"

                break


        self.guardar_tareas()

        self.refrescar_listas()




    def editar_actual(self):
        
        tarea_id = self.obtener_id_seleccionado()

        if tarea_id is None:
            return
       
        tarea_encontrada = None

        for tarea in self.tareas:
            if tarea["id"] == tarea_id:
                tarea_encontrada = tarea
                break

        if tarea_encontrada is None:
            return


        ventana_editar = tk.Toplevel(self.root)
        ventana_editar.title("Editar tarea")
        ventana_editar.geometry("500x450")
        ventana_editar.transient(self.root)
        ventana_editar.grab_set()


        ttk.Label(
            ventana_editar,
            text="Nombre de la tarea:"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        entrada_nombre = ttk.Entry(ventana_editar)

        entrada_nombre.pack(
            fill="x",
            padx=20
        )

        entrada_nombre.insert(
            0,
            tarea_encontrada["nombre"]
        )


        fecha_limite = datetime.strptime(
            tarea_encontrada["fecha_limite"],
            FORMATO_FECHA
        )


        ttk.Label(
            ventana_editar,
            text="Fecha (AAAA-MM-DD):"
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        entrada_fecha = ttk.Entry(ventana_editar)

        entrada_fecha.pack(
            fill="x",
            padx=20
        )

        entrada_fecha.insert(
            0,
            fecha_limite.strftime("%Y-%m-%d")
        )


        ttk.Label(
            ventana_editar,
            text="Hora (HH:MM):"
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        entrada_hora = ttk.Entry(ventana_editar)

        entrada_hora.pack(
            fill="x",
            padx=20
        )

        entrada_hora.insert(
            0,
            fecha_limite.strftime("%H:%M")
        )


        ttk.Label(
            ventana_editar,
            text="Descripción:"
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        entrada_descripcion = tk.Text(
            ventana_editar,
            height=6
        )

        entrada_descripcion.pack(
            fill="both",
            padx=20
        )

        entrada_descripcion.insert(
            "1.0",
            tarea_encontrada.get("descripcion", "")
        )


        def guardar_cambios():

            nuevo_nombre = entrada_nombre.get().strip()
            nueva_fecha = entrada_fecha.get().strip()
            nueva_hora = entrada_hora.get().strip()

            nueva_descripcion = entrada_descripcion.get(
                "1.0",
                "end"
            ).strip()


            if not nuevo_nombre:
                messagebox.showwarning(
                    "Aviso",
                    "El nombre no puede estar vacío."
                )
                return


            try:
                nueva_fecha_limite = datetime.strptime(
                    f"{nueva_fecha} {nueva_hora}",
                    FORMATO_FECHA
                )

            except ValueError:
                messagebox.showerror(
                    "Error",
                    "Fecha u hora incorrecta.\n\n"
                    "Fecha: AAAA-MM-DD\n"
                    "Hora: HH:MM"
                )
                return


            tarea_encontrada["nombre"] = nuevo_nombre
            tarea_encontrada["descripcion"] = nueva_descripcion

            tarea_encontrada["fecha_limite"] = (
                nueva_fecha_limite.strftime(FORMATO_FECHA)
            )


            if tarea_encontrada["estado"] == "expirada":
                if nueva_fecha_limite > datetime.now():
                    tarea_encontrada["estado"] = "pendiente"

            elif tarea_encontrada["estado"] == "pendiente":
                if nueva_fecha_limite <= datetime.now():
                    tarea_encontrada["estado"] = "expirada"


            tarea_encontrada["alerta_12h_enviada"] = False

            self.guardar_tareas()
            self.refrescar_listas()

            messagebox.showinfo(
                "Tarea editada",
                "Los cambios se guardaron correctamente."
            )

            ventana_editar.destroy()


        ttk.Button(
            ventana_editar,
            text="Guardar cambios",
            command=guardar_cambios
        ).pack(
            pady=20
        )
    
    def eliminar_actual(self):

        tarea_id = self.obtener_id_seleccionado()


        if tarea_id is None:

            return


        confirmar = messagebox.askyesno(
            "Eliminar tarea",
            "¿Seguro que quieres eliminar esta tarea?"
        )


        if not confirmar:

            return


        self.tareas = [

            tarea

            for tarea in self.tareas

            if tarea["id"] != tarea_id

        ]


        self.guardar_tareas()

        self.refrescar_listas()


    # ==========================================================
    # ACTUALIZACIÓN MANUAL
    # ==========================================================

    def actualizar_manual(self):

        self.actualizar_estados()

        self.comprobar_alertas()

        self.refrescar_listas()


# ==============================================================
# EJECUTAR PROGRAMA
# ==============================================================

if __name__ == "__main__":

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()

    app = AdministradorTareas(
        root
    )

    root.mainloop()