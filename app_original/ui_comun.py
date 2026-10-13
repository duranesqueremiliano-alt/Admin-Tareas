"""
Piezas de interfaz que comparten todas las pantallas:
colores, estilos de tablas, selector de fecha con calendario, diálogos y avisos.
"""

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

import customtkinter as ctk

from modelos import MESES, a_fecha, FORMATO_DIA

# ==============================================================
# COLORES
# ==============================================================

C = {
    "fondo": "#111827",
    "panel": "#1f2937",
    "panel2": "#273548",
    "borde": "#374151",
    "texto": "#f3f4f6",
    "suave": "#9ca3af",
    "acento": "#3b82f6",
    "acento_hover": "#2563eb",
    "ok": "#22c55e",
    "ok_hover": "#16a34a",
    "aviso": "#f59e0b",
    "peligro": "#ef4444",
    "peligro_hover": "#dc2626",
    "neutro": "#374151",
    "neutro_hover": "#4b5563",
}


def fuente(tam=14, peso="normal"):
    return ctk.CTkFont(size=tam, weight=peso)


# ==============================================================
# ESTILO DE TABLAS (ttk.Treeview en tema oscuro)
# ==============================================================

def aplicar_estilo_tablas(root):
    try:
        escala = ctk.ScalingTracker.get_window_scaling(root)
    except Exception:
        escala = 1.0
    estilo = ttk.Style(root)
    estilo.theme_use("clam")
    estilo.configure(
        "Treeview",
        background=C["panel"], fieldbackground=C["panel"], foreground=C["texto"],
        bordercolor=C["panel"], borderwidth=0, rowheight=int(32 * escala),
        font=("Segoe UI", 10),
    )
    estilo.map(
        "Treeview",
        background=[("selected", C["acento"])],
        foreground=[("selected", "white")],
    )
    estilo.configure(
        "Treeview.Heading",
        background=C["panel2"], foreground=C["suave"], relief="flat",
        borderwidth=0, font=("Segoe UI", 10, "bold"), padding=(8, 6),
    )
    estilo.map("Treeview.Heading", background=[("active", C["borde"])])
    estilo.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    estilo.configure(
        "Vertical.TScrollbar", background=C["panel2"], troughcolor=C["panel"],
        bordercolor=C["panel"], arrowcolor=C["suave"], relief="flat",
    )


def crear_tabla(padre, columnas, alto=10):
    """
    columnas: lista de (clave, titulo, ancho, alineacion, estirar)
    Devuelve (frame, tree).
    """
    marco = ctk.CTkFrame(padre, fg_color=C["panel"], corner_radius=10)
    tree = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings",
                        selectmode="browse", height=alto)
    for clave, titulo, ancho, alin, estirar in columnas:
        tree.heading(clave, text=titulo, anchor=alin)
        tree.column(clave, width=ancho, minwidth=60, anchor=alin, stretch=estirar)
    barra = ttk.Scrollbar(marco, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=barra.set)
    tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
    barra.pack(side="right", fill="y", pady=6, padx=(0, 4))

    tree.tag_configure("par", background=C["panel"])
    tree.tag_configure("impar", background="#232f3f")
    tree.tag_configure("urgente", foreground=C["aviso"])
    tree.tag_configure("vencida", foreground="#f87171")
    tree.tag_configure("positivo", foreground="#4ade80")
    tree.tag_configure("apagado", foreground=C["suave"])
    return marco, tree


def limpiar_tabla(tree):
    tree.delete(*tree.get_children())


# ==============================================================
# BOTONES
# ==============================================================

def boton(padre, texto, comando, tipo="primario", **kw):
    colores = {
        "primario": (C["acento"], C["acento_hover"], "white"),
        "ok": (C["ok"], C["ok_hover"], "white"),
        "peligro": (C["peligro"], C["peligro_hover"], "white"),
        "neutro": (C["neutro"], C["neutro_hover"], C["texto"]),
        "fantasma": ("transparent", C["panel2"], C["texto"]),
    }
    fg, hover, txt = colores[tipo]
    kw.setdefault("height", 36)
    kw.setdefault("corner_radius", 8)
    return ctk.CTkButton(padre, text=texto, command=comando, fg_color=fg, hover_color=hover,
                         text_color=txt, font=fuente(13, "bold" if tipo != "fantasma" else "normal"), **kw)


class Pestanas(ctk.CTkFrame):
    """Fila de pestañas simples (texto actualizable, p. ej. con contadores)."""

    def __init__(self, padre, opciones, al_cambiar):
        super().__init__(padre, fg_color=C["panel"], corner_radius=10)
        self.al_cambiar = al_cambiar
        self.botones = {}
        self.actual = opciones[0][0]
        for clave, texto in opciones:
            b = ctk.CTkButton(self, text=texto, height=34, corner_radius=8, font=fuente(13, "bold"),
                              command=lambda k=clave: self.seleccionar(k))
            b.pack(side="left", padx=4, pady=4)
            self.botones[clave] = b
        self._pintar()

    def seleccionar(self, clave, avisar=True):
        self.actual = clave
        self._pintar()
        if avisar:
            self.al_cambiar(clave)

    def texto(self, clave, texto):
        self.botones[clave].configure(text=texto)

    def _pintar(self):
        for clave, b in self.botones.items():
            if clave == self.actual:
                b.configure(fg_color=C["acento"], hover_color=C["acento_hover"], text_color="white")
            else:
                b.configure(fg_color="transparent", hover_color=C["panel2"], text_color=C["suave"])


# ==============================================================
# ENCABEZADO DE PANTALLA
# ==============================================================

class Encabezado(ctk.CTkFrame):

    def __init__(self, padre, titulo, al_volver):
        super().__init__(padre, fg_color="transparent")
        boton(self, "← Inicio", al_volver, "fantasma", width=90).pack(side="left")
        ctk.CTkLabel(self, text=titulo, font=fuente(24, "bold"), text_color=C["texto"]).pack(side="left", padx=(12, 0))
        self.derecha = ctk.CTkLabel(self, text="", font=fuente(13), text_color=C["suave"])
        self.derecha.pack(side="right")


class BarraAviso(ctk.CTkLabel):
    """Mensaje breve que desaparece solo (en lugar de ventanas emergentes)."""

    def __init__(self, padre):
        super().__init__(padre, text="", font=fuente(13), text_color=C["suave"], anchor="w")
        self._tarea = None

    def mostrar(self, texto, tipo="ok"):
        color = {"ok": "#4ade80", "error": "#f87171", "info": C["suave"], "aviso": C["aviso"]}[tipo]
        self.configure(text=texto, text_color=color)
        if self._tarea:
            self.after_cancel(self._tarea)
        self._tarea = self.after(5000, lambda: self.configure(text=""))


# ==============================================================
# CALENDARIO / SELECTOR DE FECHA
# ==============================================================

DIAS_CORTOS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


class Calendario(ctk.CTkToplevel):

    def __init__(self, padre, fecha_inicial, al_elegir):
        super().__init__(padre)
        self.title("Elegir fecha")
        self.resizable(False, False)
        self.configure(fg_color=C["panel"])
        self.al_elegir = al_elegir
        self.seleccionada = fecha_inicial or date.today()
        self.anio = self.seleccionada.year
        self.mes = self.seleccionada.month

        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=10, pady=(10, 4))
        boton(cabecera, "‹", lambda: self.mover(-1), "fantasma", width=34).pack(side="left")
        self.titulo = ctk.CTkLabel(cabecera, text="", font=fuente(15, "bold"))
        self.titulo.pack(side="left", expand=True)
        boton(cabecera, "›", lambda: self.mover(1), "fantasma", width=34).pack(side="right")

        self.rejilla = ctk.CTkFrame(self, fg_color="transparent")
        self.rejilla.pack(padx=10, pady=4)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=10, pady=(4, 10))
        boton(pie, "Hoy", lambda: self.elegir(date.today()), "neutro", height=30).pack(side="left")
        boton(pie, "Cerrar", self.destroy, "fantasma", height=30).pack(side="right")

        self.bind("<Escape>", lambda e: self.destroy())
        self.dibujar()
        ventana_modal(self, padre)

    def mover(self, delta):
        total = self.anio * 12 + self.mes - 1 + delta
        self.anio, self.mes = divmod(total, 12)
        self.mes += 1
        self.dibujar()

    def dibujar(self):
        for w in self.rejilla.winfo_children():
            w.destroy()
        self.titulo.configure(text=f"{MESES[self.mes - 1].capitalize()} {self.anio}")
        for i, d in enumerate(DIAS_CORTOS):
            ctk.CTkLabel(self.rejilla, text=d, width=38, text_color=C["suave"], font=fuente(12)).grid(row=0, column=i)
        hoy = date.today()
        for fila, semana in enumerate(calendar.Calendar(0).monthdayscalendar(self.anio, self.mes), start=1):
            for col, dia in enumerate(semana):
                if dia == 0:
                    continue
                f = date(self.anio, self.mes, dia)
                if f == self.seleccionada:
                    fg, txt = C["acento"], "white"
                elif f == hoy:
                    fg, txt = C["borde"], C["texto"]
                else:
                    fg, txt = "transparent", C["texto"]
                ctk.CTkButton(self.rejilla, text=str(dia), width=38, height=32, corner_radius=6,
                              fg_color=fg, hover_color=C["panel2"], text_color=txt, font=fuente(13),
                              command=lambda f=f: self.elegir(f)).grid(row=fila, column=col, padx=1, pady=1)

    def elegir(self, f):
        self.al_elegir(f)
        self.destroy()


class SelectorFecha(ctk.CTkFrame):
    """Campo de fecha con botón de calendario. get() -> date o None."""

    def __init__(self, padre, fecha=None, ancho=110):
        super().__init__(padre, fg_color="transparent")
        self.entrada = ctk.CTkEntry(self, width=ancho, placeholder_text="AAAA-MM-DD")
        self.entrada.pack(side="left")
        ctk.CTkButton(self, text="📅", width=36, height=28, fg_color=C["neutro"], hover_color=C["neutro_hover"],
                      command=self.abrir).pack(side="left", padx=(4, 0))
        if fecha:
            self.set(fecha)

    def abrir(self):
        Calendario(self.winfo_toplevel(), self.get(), self.set)

    def set(self, f):
        self.entrada.delete(0, "end")
        self.entrada.insert(0, f.strftime(FORMATO_DIA))

    def get(self):
        return a_fecha(self.entrada.get())


HORAS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)] + ["23:59"]


def leer_hora(texto):
    texto = texto.strip()
    for formato in ("%H:%M", "%H"):
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            pass
    return None


# ==============================================================
# VENTANAS / DIÁLOGOS
# ==============================================================

def ventana_modal(ventana, padre):
    """Centra la ventana sobre el padre, la trae al frente y bloquea el resto."""
    ventana.transient(padre)
    ventana.update_idletasks()
    try:
        x = padre.winfo_rootx() + (padre.winfo_width() - ventana.winfo_reqwidth()) // 2
        y = padre.winfo_rooty() + (padre.winfo_height() - ventana.winfo_reqheight()) // 3
        ventana.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    except tk.TclError:
        pass

    def al_frente():
        try:
            ventana.lift()
            ventana.focus_force()
            ventana.grab_set()
        except tk.TclError:
            pass

    ventana.after(120, al_frente)


class Dialogo(ctk.CTkToplevel):
    """Ventana de formulario: self.cuerpo para los campos, botones Guardar/Cancelar abajo."""

    def __init__(self, padre, titulo, texto_ok="Guardar"):
        super().__init__(padre)
        self.title(titulo)
        self.configure(fg_color=C["fondo"])
        self.resizable(False, False)
        ctk.CTkLabel(self, text=titulo, font=fuente(20, "bold")).pack(anchor="w", padx=24, pady=(20, 8))
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True, padx=24)
        self.cuerpo.grid_columnconfigure(1, weight=1)
        self.error = ctk.CTkLabel(self, text="", text_color="#f87171", font=fuente(13))
        self.error.pack(anchor="w", padx=24)
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", padx=24, pady=(6, 20))
        boton(pie, texto_ok, self._ok, "primario", width=120).pack(side="right")
        boton(pie, "Cancelar", self.destroy, "neutro", width=100).pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: None if isinstance(e.widget, tk.Text) else self._ok())
        self._fila = 0
        self._padre = padre

    def campo(self, etiqueta, widget, ayuda=None):
        """Coloca etiqueta + widget en la siguiente fila del cuerpo."""
        ctk.CTkLabel(self.cuerpo, text=etiqueta, text_color=C["suave"], font=fuente(13)).grid(
            row=self._fila, column=0, sticky="nw", pady=7, padx=(0, 14))
        widget.grid(row=self._fila, column=1, sticky="we", pady=7)
        self._fila += 1
        if ayuda:
            ctk.CTkLabel(self.cuerpo, text=ayuda, text_color=C["suave"], font=fuente(11)).grid(
                row=self._fila, column=1, sticky="w", pady=(0, 4))
            self._fila += 1
        return widget

    def mostrar(self):
        ventana_modal(self, self._padre)

    def fallar(self, texto):
        self.error.configure(text=texto)

    def _ok(self):
        if self.aceptar():
            self.destroy()

    def aceptar(self):
        """Las subclases validan y guardan aquí. Devuelven True para cerrar."""
        return True


def limpiar_entrada(entrada):
    """Vacía un CTkEntry y vuelve a mostrar su texto de ayuda si no tiene el foco."""
    entrada.delete(0, "end")
    try:
        if entrada.focus_get() is not entrada._entry:
            entrada._activate_placeholder()
    except Exception:
        pass


def avisar(padre, titulo, mensaje):
    """Mensaje informativo con un solo botón."""
    confirmar(padre, titulo, mensaje, "Entendido", peligro=False, solo_ok=True)


def confirmar(padre, titulo, mensaje, texto_si="Eliminar", peligro=True, solo_ok=False):
    """Confirmación con estilo de la app. Devuelve True/False."""
    resultado = {"ok": False}
    v = ctk.CTkToplevel(padre)
    v.title(titulo)
    v.configure(fg_color=C["fondo"])
    v.resizable(False, False)
    ctk.CTkLabel(v, text=titulo, font=fuente(18, "bold")).pack(anchor="w", padx=24, pady=(20, 6))
    ctk.CTkLabel(v, text=mensaje, font=fuente(13), text_color=C["suave"], justify="left",
                 wraplength=380).pack(anchor="w", padx=24)
    pie = ctk.CTkFrame(v, fg_color="transparent")
    pie.pack(fill="x", padx=24, pady=20)

    def si():
        resultado["ok"] = True
        v.destroy()

    boton(pie, texto_si, si, "peligro" if peligro else "primario", width=110).pack(side="right")
    if not solo_ok:
        boton(pie, "Cancelar", v.destroy, "neutro", width=100).pack(side="right", padx=8)
    v.bind("<Escape>", lambda e: v.destroy())
    v.bind("<Return>", lambda e: si())
    ventana_modal(v, padre)
    padre.wait_window(v)
    return resultado["ok"]


def menu_contextual(widget, opciones):
    """Crea un menú de clic derecho. opciones: lista de (texto, funcion) o None para separador."""
    menu = tk.Menu(widget, tearoff=0, bg=C["panel"], fg=C["texto"], activebackground=C["acento"],
                   activeforeground="white", bd=0, font=("Segoe UI", 10))
    for op in opciones:
        if op is None:
            menu.add_separator()
        else:
            menu.add_command(label=op[0], command=op[1])
    return menu
