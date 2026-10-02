import json
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from pathlib import Path


# ==============================================================
# CONFIGURACIÓN GENERAL
# ==============================================================

ARCHIVO_DATOS = Path(__file__).with_name("tareas.json")
FORMATO_FECHA = "%Y-%m-%d %H:%M"

# Paleta de colores (tema oscuro consistente)
COLOR_BG           = "#0f172a"
COLOR_SIDEBAR      = "#1e293b"
COLOR_CARD         = "#1e293b"
COLOR_INPUT        = "#0f172a"
COLOR_BORDER       = "#334155"
COLOR_TEXT         = "#f1f5f9"
COLOR_TEXT_MUTED   = "#94a3b8"
COLOR_ACCENT       = "#3b82f6"
COLOR_ACCENT_HOVER = "#2563eb"
COLOR_SUCCESS      = "#10b981"
COLOR_SUCCESS_HOVER= "#059669"
COLOR_DANGER       = "#ef4444"
COLOR_DANGER_HOVER = "#dc2626"


# ==============================================================
# TOOLTIP (etiqueta flotante al pasar el ratón)
# ==============================================================

class ToolTip:
    """Muestra una etiqueta flotante cuando el ratón pasa sobre un widget."""

    def __init__(self, widget, text, delay=450):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        contenedor = tk.Frame(tw, background=COLOR_ACCENT, bd=0)
        contenedor.pack()

        etiqueta = tk.Label(
            contenedor,
            text=self.text,
            justify="left",
            background="#111827",
            foreground=COLOR_TEXT,
            font=("Segoe UI", 9),
            padx=10,
            pady=6,
            bd=0,
            highlightthickness=0,
        )
        etiqueta.pack(padx=1, pady=1)

    def _hide(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw is not None:
            tw.destroy()


# ==============================================================
# APLICACIÓN
# ==============================================================

class AdministradorTareas:

    def __init__(self, root):
        self.root = root
        self.root.title("Administrador de Tareas")
        self.root.geometry("1000x760")
        self.root.minsize(880, 660)
        self.root.configure(bg=COLOR_BG)

        self.tareas = []
        self.descripcion_visible = False
        self.tooltips = []  # mantener referencia viva

        self.configurar_estilos()
        self.crear_interfaz()
        self.cargar_tareas()
        self.actualizar_estados()
        self.refrescar_listas()

        self.root.after(1000, self.revisar_alertas_y_expiraciones)

    # ==========================================================
    # ESTILOS GLOBALES
    # ==========================================================

    def configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # -------- Frames --------
        style.configure("TFrame",         background=COLOR_BG)
        style.configure("Card.TFrame",    background=COLOR_CARD)
        style.configure("Sidebar.TFrame", background=COLOR_SIDEBAR)

        # -------- Labels --------
        style.configure("TLabel",
                        background=COLOR_BG, foreground=COLOR_TEXT,
                        font=("Segoe UI", 10))
        style.configure("Card.TLabel",
                        background=COLOR_CARD, foreground=COLOR_TEXT,
                        font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel",
                        background=COLOR_CARD, foreground=COLOR_TEXT,
                        font=("Segoe UI", 12, "bold"))
        style.configure("Sidebar.TLabel",
                        background=COLOR_SIDEBAR, foreground=COLOR_TEXT_MUTED,
                        font=("Segoe UI", 10))
        style.configure("SidebarTitle.TLabel",
                        background=COLOR_SIDEBAR, foreground=COLOR_TEXT,
                        font=("Segoe UI", 20, "bold"))
        style.configure("Title.TLabel",
                        background=COLOR_BG, foreground=COLOR_TEXT,
                        font=("Segoe UI", 22, "bold"))
        style.configure("Muted.TLabel",
                        background=COLOR_BG, foreground=COLOR_TEXT_MUTED,
                        font=("Segoe UI", 9))
        style.configure("SectionTitle.TLabel",
                        background=COLOR_BG, foreground=COLOR_TEXT,
                        font=("Segoe UI", 12, "bold"))

        # -------- Entry --------
        style.configure("TEntry",
                        fieldbackground=COLOR_INPUT,
                        foreground=COLOR_TEXT,
                        bordercolor=COLOR_BORDER,
                        lightcolor=COLOR_BORDER,
                        darkcolor=COLOR_BORDER,
                        insertcolor=COLOR_TEXT,
                        padding=6)
        style.map("TEntry",
                  bordercolor=[("focus", COLOR_ACCENT)],
                  lightcolor=[("focus", COLOR_ACCENT)],
                  darkcolor=[("focus", COLOR_ACCENT)])

        # -------- Botones --------
        style.configure("Accent.TButton",
                        background=COLOR_ACCENT, foreground="white",
                        borderwidth=0, focuscolor="none",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.map("Accent.TButton",
                  background=[("active", COLOR_ACCENT_HOVER),
                              ("pressed", COLOR_ACCENT_HOVER)])

        style.configure("Success.TButton",
                        background=COLOR_SUCCESS, foreground="white",
                        borderwidth=0, focuscolor="none",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.map("Success.TButton",
                  background=[("active", COLOR_SUCCESS_HOVER)])

        style.configure("Danger.TButton",
                        background=COLOR_DANGER, foreground="white",
                        borderwidth=0, focuscolor="none",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8))
        style.map("Danger.TButton",
                  background=[("active", COLOR_DANGER_HOVER)])

        style.configure("Secondary.TButton",
                        background=COLOR_BORDER, foreground=COLOR_TEXT,
                        borderwidth=0, focuscolor="none",
                        font=("Segoe UI", 10), padding=(14, 8))
        style.map("Secondary.TButton",
                  background=[("active", "#475569")])

        style.configure("Sidebar.TButton",
                        background=COLOR_SIDEBAR, foreground=COLOR_TEXT,
                        borderwidth=0, focuscolor="none",
                        font=("Segoe UI", 11), padding=(16, 12),
                        anchor="w")
        style.map("Sidebar.TButton",
                  background=[("active", COLOR_BORDER),
                              ("pressed", COLOR_BORDER)],
                  foreground=[("active", COLOR_TEXT)])

        # -------- Notebook: pestañas que crecen al seleccionar --------
        style.configure("TNotebook",
                        background=COLOR_BG, borderwidth=0,
                        tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab",
                        background=COLOR_CARD, foreground=COLOR_TEXT_MUTED,
                        padding=(14, 7), borderwidth=0,
                        font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_BG),
                              ("active", COLOR_BORDER)],
                  foreground=[("selected", COLOR_TEXT),
                              ("active", COLOR_TEXT)],
                  padding=[("selected", (26, 13))])

        # -------- Treeview --------
        style.configure("Treeview",
                        background=COLOR_CARD, foreground=COLOR_TEXT,
                        fieldbackground=COLOR_CARD,
                        borderwidth=0, rowheight=30,
                        font=("Segoe UI", 10))
        style.map("Treeview",
                  background=[("selected", COLOR_ACCENT)],
                  foreground=[("selected", "white")])

        style.configure("Treeview.Heading",
                        background=COLOR_BG, foreground=COLOR_TEXT,
                        relief="flat", borderwidth=0,
                        padding=(8, 10),
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview.Heading",
                  background=[("active", COLOR_BORDER)])

        # -------- Scrollbar --------
        style.configure("Vertical.TScrollbar",
                        background=COLOR_BORDER, troughcolor=COLOR_BG,
                        borderwidth=0, arrowcolor=COLOR_TEXT_MUTED,
                        gripcount=0)
        style.map("Vertical.TScrollbar",
                  background=[("active", COLOR_ACCENT)])

    # ==========================================================
    # INTERFAZ
    # ==========================================================

    def crear_interfaz(self):

        # ---------- SIDEBAR ----------
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="TASKFLOW",
                  style="SidebarTitle.TLabel").pack(
            anchor="w", padx=20, pady=(30, 4))
        ttk.Label(sidebar, text="Organiza tu día",
                  style="Sidebar.TLabel").pack(
            anchor="w", padx=20, pady=(0, 25))

        sep = tk.Frame(sidebar, bg=COLOR_BORDER, height=1)
        sep.pack(fill="x", padx=15, pady=(0, 15))

        btn_inicio = ttk.Button(sidebar, text="🏠   Inicio",
                                style="Sidebar.TButton",
                                command=lambda: self.notebook.select(0))
        btn_inicio.pack(fill="x", padx=10, pady=3)
        self._tip(btn_inicio, "Ir a la vista de tareas pendientes")

        btn_pend = ttk.Button(sidebar, text="⏳   Pendientes",
                              style="Sidebar.TButton",
                              command=lambda: self.notebook.select(0))
        btn_pend.pack(fill="x", padx=10, pady=3)
        self._tip(btn_pend, "Ver tareas pendientes")

        btn_comp = ttk.Button(sidebar, text="✅   Completadas",
                              style="Sidebar.TButton",
                              command=lambda: self.notebook.select(1))
        btn_comp.pack(fill="x", padx=10, pady=3)
        self._tip(btn_comp, "Ver tareas completadas")

        btn_exp = ttk.Button(sidebar, text="⚠️   Expiradas",
                             style="Sidebar.TButton",
                             command=lambda: self.notebook.select(2))
        btn_exp.pack(fill="x", padx=10, pady=3)
        self._tip(btn_exp, "Ver tareas expiradas")

        # ---------- ÁREA DE CONTENIDO ----------
        contenido = ttk.Frame(self.root, style="TFrame")
        contenido.pack(side="right", fill="both", expand=True,
                       padx=25, pady=20)

        ttk.Label(contenido, text="Administrador de Tareas",
                  style="Title.TLabel").pack(anchor="w")

        # ---------- FORMULARIO ----------
        form_card = ttk.Frame(contenido, style="Card.TFrame", padding=18)
        form_card.pack(fill="x", pady=(15, 12))

        ttk.Label(form_card, text="Nueva tarea",
                  style="CardTitle.TLabel").pack(anchor="w", pady=(0, 12))

        fila1 = ttk.Frame(form_card, style="Card.TFrame")
        fila1.pack(fill="x")

        ttk.Label(fila1, text="Nombre",
                  style="Card.TLabel").pack(side="left")
        self.entrada_nombre = ttk.Entry(fila1)
        self.entrada_nombre.pack(side="left", fill="x", expand=True,
                                 padx=(8, 15))

        ttk.Label(fila1, text="Fecha (AAAA-MM-DD)",
                  style="Card.TLabel").pack(side="left")
        self.entrada_fecha = ttk.Entry(fila1, width=14)
        self.entrada_fecha.pack(side="left", padx=(8, 15))

        ttk.Label(fila1, text="Hora (HH:MM)",
                  style="Card.TLabel").pack(side="left")
        self.entrada_hora = ttk.Entry(fila1, width=10)
        self.entrada_hora.pack(side="left", padx=(8, 0))

        fecha_sugerida = datetime.now() + timedelta(hours=24)
        self.entrada_fecha.insert(0, fecha_sugerida.strftime("%Y-%m-%d"))
        self.entrada_hora.insert(0, fecha_sugerida.strftime("%H:%M"))

        fila2 = ttk.Frame(form_card, style="Card.TFrame")
        fila2.pack(fill="x", pady=(12, 0))

        self.boton_descripcion = ttk.Button(
            fila2, text="＋ Añadir descripción",
            style="Secondary.TButton",
            command=self.alternar_descripcion)
        self.boton_descripcion.pack(side="left")
        self._tip(self.boton_descripcion,
                  "Muestra u oculta el campo de descripción")

        btn_agregar = ttk.Button(fila2, text="Agregar tarea",
                                 style="Accent.TButton",
                                 command=self.agregar_tarea)
        btn_agregar.pack(side="right")
        self._tip(btn_agregar,
                  "Guarda la tarea con el nombre, fecha y hora indicados")

        # ---------- DESCRIPCIÓN DESPLEGABLE ----------
        self.frame_descripcion = ttk.Frame(form_card, style="Card.TFrame")

        ttk.Label(self.frame_descripcion, text="Descripción opcional",
                  style="Card.TLabel").pack(anchor="w", pady=(12, 6))

        self.texto_descripcion = tk.Text(
            self.frame_descripcion, height=4, wrap="word",
            bg=COLOR_INPUT, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            relief="flat", font=("Segoe UI", 10),
            padx=8, pady=6,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_ACCENT)
        self.texto_descripcion.pack(fill="x")

        # ---------- AVISO ----------
        ttk.Label(contenido,
                  text="⚠ Las tareas que venzan dentro de 12 horas generarán una alerta.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        # ---------- PESTAÑAS ----------
        self.notebook = ttk.Notebook(contenido)
        self.notebook.pack(fill="both", expand=True)

        self.tree_pendientes  = self.crear_pestana("Pendientes")
        self.tree_completadas = self.crear_pestana("Completadas")
        self.tree_expiradas   = self.crear_pestana("Expiradas")

        # ---------- BOTONES INFERIORES ----------
        # Cabecera de la sección con título y subtítulo explicativo
        cabecera_acciones = ttk.Frame(contenido, style="TFrame")
        cabecera_acciones.pack(fill="x", pady=(18, 6))

        ttk.Label(cabecera_acciones,
                  text="Acciones sobre la tarea seleccionada",
                  style="SectionTitle.TLabel").pack(anchor="w")

        ttk.Label(cabecera_acciones,
                  text="Selecciona una tarea en la lista y usa estos botones "
                       "para cambiar su estado o editarla.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        botones = ttk.Frame(contenido, style="TFrame")
        botones.pack(fill="x")

        btn_completar = ttk.Button(botones,
                                   text="✓ Marcar como completada",
                                   style="Success.TButton",
                                   command=self.marcar_completada_actual)
        btn_completar.pack(side="left")
        self._tip(btn_completar,
                  "Marca la tarea seleccionada como completada")

        btn_reabrir = ttk.Button(botones,
                                 text="↺ Reabrir tarea",
                                 style="Secondary.TButton",
                                 command=self.reabrir_actual)
        btn_reabrir.pack(side="left", padx=8)
        self._tip(btn_reabrir,
                  "Devuelve una tarea completada al estado pendiente")

        btn_editar = ttk.Button(botones, text="✎ Editar tarea",
                                style="Secondary.TButton",
                                command=self.editar_actual)
        btn_editar.pack(side="left", padx=8)
        self._tip(btn_editar,
                  "Modifica el nombre, la fecha o la descripción de la tarea")

        btn_eliminar = ttk.Button(botones, text="🗑 Eliminar tarea",
                                  style="Danger.TButton",
                                  command=self.eliminar_actual)
        btn_eliminar.pack(side="left", padx=8)
        self._tip(btn_eliminar,
                  "Elimina la tarea seleccionada de forma permanente")

        btn_actualizar = ttk.Button(botones, text="⟳ Actualizar",
                                    style="Accent.TButton",
                                    command=self.actualizar_manual)
        btn_actualizar.pack(side="right")
        self._tip(btn_actualizar,
                  "Revisa expiraciones y alertas manualmente")

    # ---------- helpers ----------
    def _tip(self, widget, texto):
        self.tooltips.append(ToolTip(widget, texto))

    # ==========================================================
    # CREAR PESTAÑAS
    # ==========================================================

    def crear_pestana(self, titulo):
        frame = ttk.Frame(self.notebook, style="TFrame", padding=0)
        self.notebook.add(frame, text=titulo)

        columnas = ("nombre", "fecha", "descripcion")
        tree = ttk.Treeview(frame, columns=columnas,
                            show="headings", selectmode="browse")

        tree.heading("nombre", text="Tarea")
        tree.heading("fecha", text="Fecha límite")
        tree.heading("descripcion", text="Descripción")

        tree.column("nombre", width=220, anchor="w")
        tree.column("fecha", width=160, anchor="center")
        tree.column("descripcion", width=420, anchor="w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        return tree

    # ==========================================================
    # MOSTRAR / OCULTAR DESCRIPCIÓN
    # ==========================================================

    def alternar_descripcion(self):
        if self.descripcion_visible:
            self.frame_descripcion.pack_forget()
            self.boton_descripcion.config(text="＋ Añadir descripción")
            self.descripcion_visible = False
        else:
            self.frame_descripcion.pack(fill="x")
            self.boton_descripcion.config(text="▲ Ocultar descripción")
            self.descripcion_visible = True

    # ==========================================================
    # AGREGAR TAREA
    # ==========================================================

    def agregar_tarea(self):
        nombre = self.entrada_nombre.get().strip()
        fecha  = self.entrada_fecha.get().strip()
        hora   = self.entrada_hora.get().strip()
        descripcion = self.texto_descripcion.get("1.0", "end").strip()

        if not nombre:
            messagebox.showwarning("Falta información",
                                   "Escribe el nombre de la tarea.")
            return

        try:
            fecha_limite = datetime.strptime(f"{fecha} {hora}", FORMATO_FECHA)
        except ValueError:
            messagebox.showerror(
                "Fecha inválida",
                "Usa este formato:\n\n"
                "Fecha: AAAA-MM-DD\n"
                "Hora: HH:MM\n\n"
                "Ejemplo:\n2026-09-25\n18:30")
            return

        estado = "expirada" if fecha_limite <= datetime.now() else "pendiente"

        nueva_tarea = {
            "id": str(uuid.uuid4()),
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_limite": fecha_limite.strftime(FORMATO_FECHA),
            "estado": estado,
            "alerta_12h_enviada": False,
        }

        self.tareas.append(nueva_tarea)
        self.guardar_tareas()
        self.refrescar_listas()

        self.entrada_nombre.delete(0, "end")
        self.texto_descripcion.delete("1.0", "end")

        if estado == "expirada":
            messagebox.showinfo(
                "Tarea expirada",
                "La fecha indicada ya pasó.\n\n"
                "La tarea fue enviada a Expiradas.")
        else:
            messagebox.showinfo("Tarea agregada",
                                "La tarea se agregó correctamente.")

        self.comprobar_alertas()

    # ==========================================================
    # GUARDAR / CARGAR
    # ==========================================================

    def guardar_tareas(self):
        try:
            with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
                json.dump(self.tareas, archivo,
                          ensure_ascii=False, indent=4)
        except OSError as error:
            messagebox.showerror(
                "Error",
                f"No se pudieron guardar las tareas:\n{error}")

    def cargar_tareas(self):
        if not ARCHIVO_DATOS.exists():
            self.tareas = []
            return

        try:
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
            self.tareas = datos if isinstance(datos, list) else []
        except (json.JSONDecodeError, OSError):
            self.tareas = []
            messagebox.showwarning("Aviso", "No se pudo leer tareas.json.")

        for tarea in self.tareas:
            tarea.setdefault("id", str(uuid.uuid4()))
            tarea.setdefault("descripcion", "")
            tarea.setdefault("estado", "pendiente")
            tarea.setdefault("alerta_12h_enviada", False)

    # ==========================================================
    # ACTUALIZAR ESTADOS
    # ==========================================================

    def actualizar_estados(self):
        ahora = datetime.now()
        hubo_cambios = False

        for tarea in self.tareas:
            if tarea.get("estado") != "pendiente":
                continue
            try:
                fecha_limite = datetime.strptime(
                    tarea["fecha_limite"], FORMATO_FECHA)
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
        limite_alerta = ahora + timedelta(hours=12)
        por_vencer = []
        hubo_cambios = False

        for tarea in self.tareas:
            if tarea.get("estado") != "pendiente":
                continue
            try:
                fecha_limite = datetime.strptime(
                    tarea["fecha_limite"], FORMATO_FECHA)
            except (KeyError, ValueError):
                continue

            if fecha_limite <= ahora:
                tarea["estado"] = "expirada"
                hubo_cambios = True
                continue

            if (ahora < fecha_limite <= limite_alerta
                    and not tarea.get("alerta_12h_enviada", False)):
                por_vencer.append(tarea)
                tarea["alerta_12h_enviada"] = True
                hubo_cambios = True

        if hubo_cambios:
            self.guardar_tareas()
            self.refrescar_listas()

        if por_vencer:
            mensaje = ""
            for tarea in por_vencer:
                mensaje += (f"• {tarea['nombre']}\n"
                            f"  Vence: {tarea['fecha_limite']}\n\n")
            messagebox.showwarning(
                "⚠ Tareas próximas a vencer",
                "Estas tareas vencen dentro de las próximas 12 horas:\n\n"
                + mensaje)

    # ==========================================================
    # REVISIÓN AUTOMÁTICA
    # ==========================================================

    def revisar_alertas_y_expiraciones(self):
        self.actualizar_estados()
        self.comprobar_alertas()
        self.refrescar_listas()
        self.root.after(60000, self.revisar_alertas_y_expiraciones)

    # ==========================================================
    # REFRESCAR LISTAS
    # ==========================================================

    def refrescar_listas(self):
        for tree in (self.tree_pendientes,
                     self.tree_completadas,
                     self.tree_expiradas):
            for item in tree.get_children():
                tree.delete(item)

        for tarea in self.tareas:
            descripcion = tarea.get("descripcion", "").replace("\n", " ")
            valores = (tarea.get("nombre", ""),
                       tarea.get("fecha_limite", ""),
                       descripcion)

            estado = tarea.get("estado", "pendiente")
            if estado == "pendiente":
                tree = self.tree_pendientes
            elif estado == "completada":
                tree = self.tree_completadas
            else:
                tree = self.tree_expiradas

            tree.insert("", "end", iid=tarea["id"], values=valores)

        pendientes  = sum(1 for t in self.tareas if t.get("estado") == "pendiente")
        completadas = sum(1 for t in self.tareas if t.get("estado") == "completada")
        expiradas   = sum(1 for t in self.tareas if t.get("estado") == "expirada")

        self.notebook.tab(0, text=f"Pendientes ({pendientes})")
        self.notebook.tab(1, text=f"Completadas ({completadas})")
        self.notebook.tab(2, text=f"Expiradas ({expiradas})")

    # ==========================================================
    # TREE ACTUAL / SELECCIÓN
    # ==========================================================

    def obtener_tree_actual(self):
        indice = self.notebook.index(self.notebook.select())
        if indice == 0:
            return self.tree_pendientes
        elif indice == 1:
            return self.tree_completadas
        return self.tree_expiradas

    def obtener_id_seleccionado(self):
        tree = self.obtener_tree_actual()
        seleccion = tree.selection()
        if not seleccion:
            messagebox.showwarning("Selecciona una tarea",
                                   "Primero selecciona una tarea.")
            return None
        return seleccion[0]

    # ==========================================================
    # MARCAR COMPLETADA
    # ==========================================================

    def marcar_completada_actual(self):
        tarea_id = self.obtener_id_seleccionado()
        if tarea_id is None:
            return

        for tarea in self.tareas:
            if tarea["id"] == tarea_id:
                if tarea.get("estado") == "completada":
                    messagebox.showinfo("Información",
                                        "Esta tarea ya está completada.")
                    return
                tarea["estado"] = "completada"
                break

        self.guardar_tareas()
        self.refrescar_listas()

    # ==========================================================
    # REABRIR TAREA (Completada → Pendiente)
    # ==========================================================

    def reabrir_actual(self):
        tarea_id = self.obtener_id_seleccionado()
        if tarea_id is None:
            return

        for tarea in self.tareas:
            if tarea["id"] == tarea_id:
                if tarea.get("estado") != "completada":
                    messagebox.showinfo(
                        "Información",
                        "Solo se pueden reabrir tareas completadas.")
                    return

                # Si la fecha ya pasó, se envía directamente a Expiradas;
                # si no, vuelve a Pendientes.
                try:
                    fecha_limite = datetime.strptime(
                        tarea["fecha_limite"], FORMATO_FECHA)
                except (KeyError, ValueError):
                    fecha_limite = None

                if fecha_limite is not None and fecha_limite <= datetime.now():
                    tarea["estado"] = "expirada"
                else:
                    tarea["estado"] = "pendiente"
                    # Al reabrir, permitimos que vuelva a alertar 12h antes.
                    tarea["alerta_12h_enviada"] = False
                break

        self.guardar_tareas()
        self.refrescar_listas()

    # ==========================================================
    # EDITAR TAREA
    # ==========================================================

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

        ventana = tk.Toplevel(self.root)
        ventana.title("Editar tarea")
        ventana.geometry("520x560")
        ventana.configure(bg=COLOR_BG)
        ventana.transient(self.root)
        ventana.grab_set()

        cont = ttk.Frame(ventana, style="TFrame", padding=20)
        cont.pack(fill="both", expand=True)

        ttk.Label(cont, text="Nombre de la tarea",
                  style="TLabel").pack(anchor="w", pady=(0, 5))
        entrada_nombre = ttk.Entry(cont)
        entrada_nombre.pack(fill="x")
        entrada_nombre.insert(0, tarea_encontrada["nombre"])

        fecha_limite = datetime.strptime(
            tarea_encontrada["fecha_limite"], FORMATO_FECHA)

        ttk.Label(cont, text="Fecha (AAAA-MM-DD)",
                  style="TLabel").pack(anchor="w", pady=(15, 5))
        entrada_fecha = ttk.Entry(cont)
        entrada_fecha.pack(fill="x")
        entrada_fecha.insert(0, fecha_limite.strftime("%Y-%m-%d"))

        ttk.Label(cont, text="Hora (HH:MM)",
                  style="TLabel").pack(anchor="w", pady=(15, 5))
        entrada_hora = ttk.Entry(cont)
        entrada_hora.pack(fill="x")
        entrada_hora.insert(0, fecha_limite.strftime("%H:%M"))

        ttk.Label(cont, text="Descripción",
                  style="TLabel").pack(anchor="w", pady=(15, 5))
        entrada_descripcion = tk.Text(
            cont, height=6, wrap="word",
            bg=COLOR_INPUT, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            relief="flat", font=("Segoe UI", 10),
            padx=8, pady=6,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_ACCENT)
        entrada_descripcion.pack(fill="both", expand=True)
        entrada_descripcion.insert("1.0", tarea_encontrada.get("descripcion", ""))

        def guardar_cambios():
            nuevo_nombre = entrada_nombre.get().strip()
            nueva_fecha  = entrada_fecha.get().strip()
            nueva_hora   = entrada_hora.get().strip()
            nueva_descripcion = entrada_descripcion.get("1.0", "end").strip()

            if not nuevo_nombre:
                messagebox.showwarning("Aviso",
                                       "El nombre no puede estar vacío.")
                return

            try:
                nueva_fecha_limite = datetime.strptime(
                    f"{nueva_fecha} {nueva_hora}", FORMATO_FECHA)
            except ValueError:
                messagebox.showerror(
                    "Error",
                    "Fecha u hora incorrecta.\n\n"
                    "Fecha: AAAA-MM-DD\nHora: HH:MM")
                return

            tarea_encontrada["nombre"] = nuevo_nombre
            tarea_encontrada["descripcion"] = nueva_descripcion
            tarea_encontrada["fecha_limite"] = (
                nueva_fecha_limite.strftime(FORMATO_FECHA))

            if tarea_encontrada["estado"] == "expirada":
                if nueva_fecha_limite > datetime.now():
                    tarea_encontrada["estado"] = "pendiente"
            elif tarea_encontrada["estado"] == "pendiente":
                if nueva_fecha_limite <= datetime.now():
                    tarea_encontrada["estado"] = "expirada"

            tarea_encontrada["alerta_12h_enviada"] = False

            self.guardar_tareas()
            self.refrescar_listas()

            messagebox.showinfo("Tarea editada",
                                "Los cambios se guardaron correctamente.")
            ventana.destroy()

        botones = ttk.Frame(cont, style="TFrame")
        botones.pack(fill="x", pady=(20, 0))

        btn_cancelar = ttk.Button(botones, text="Cancelar",
                                  style="Secondary.TButton",
                                  command=ventana.destroy)
        btn_cancelar.pack(side="left")
        self._tip(btn_cancelar, "Descarta los cambios y cierra la ventana")

        btn_guardar = ttk.Button(botones, text="Guardar cambios",
                                 style="Accent.TButton",
                                 command=guardar_cambios)
        btn_guardar.pack(side="right")
        self._tip(btn_guardar, "Guarda los cambios de la tarea")

    # ==========================================================
    # ELIMINAR TAREA
    # ==========================================================

    def eliminar_actual(self):
        tarea_id = self.obtener_id_seleccionado()
        if tarea_id is None:
            return

        confirmar = messagebox.askyesno(
            "Eliminar tarea",
            "¿Seguro que quieres eliminar esta tarea?")
        if not confirmar:
            return

        self.tareas = [t for t in self.tareas if t["id"] != tarea_id]
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
# EJECUTAR
# ==============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = AdministradorTareas(root)
    root.mainloop()