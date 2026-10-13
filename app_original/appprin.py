"""
Organizador personal: Tareas + Gastos + Notas de clase.

Ejecutar:  python appprin.py
Requiere:  python instalar_dependencias.py  (instala customtkinter una vez)

Archivos:
  appprin.py          -> ventana principal y pantalla de inicio
  pantalla_tareas.py  -> sección de tareas
  pantalla_gastos.py  -> sección de gastos personales
  pantalla_notas.py   -> notas de clase con buscador
  palabras_clave.py   -> extracción de palabras clave (IA o local)
  ui_comun.py         -> colores, calendario, diálogos
  modelos.py          -> lógica y guardado (tareas.json, gastos.json, notas.json)
"""

from datetime import date, datetime

try:
    import customtkinter as ctk
except ImportError:
    import sys
    print("\nFalta la librería customtkinter.\n"
          "Instálala una vez con:  python instalar_dependencias.py\n"
          "   (o bien:  python -m pip install customtkinter)\n")
    sys.exit(1)

from modelos import TareasStore, GastosStore, NotasStore, fecha_larga, fecha_corta, texto_dias, moneda, tiempo_restante, MESES
from ui_comun import C, fuente, boton, aplicar_estilo_tablas, avisar
from pantalla_tareas import PantallaTareas
from pantalla_gastos import PantallaGastos
from pantalla_notas import PantallaNotas


class PantallaInicio(ctk.CTkFrame):

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=C["fondo"], corner_radius=0)
        self.app = app

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.47, anchor="center", relwidth=0.86)

        self.saludo = ctk.CTkLabel(centro, text="", font=fuente(30, "bold"), anchor="w")
        self.saludo.pack(fill="x")
        self.fecha = ctk.CTkLabel(centro, text="", font=fuente(15), text_color=C["suave"], anchor="w")
        self.fecha.pack(fill="x", pady=(2, 26))

        tarjetas = ctk.CTkFrame(centro, fg_color="transparent")
        tarjetas.pack(fill="x")
        tarjetas.grid_columnconfigure((0, 1, 2), weight=1, uniform="t")

        self.t_tareas = self._tarjeta(tarjetas, 0, "📋", "Tareas", "Entregas y alertas",
                                      C["acento"], app.mostrar_tareas)
        self.t_gastos = self._tarjeta(tarjetas, 1, "💳", "Gastos", "Cuentas y pagos",
                                      "#22c55e", app.mostrar_gastos)
        self.t_notas = self._tarjeta(tarjetas, 2, "📝", "Notas", "Apuntes por materia",
                                     "#a855f7", app.mostrar_notas)

        ctk.CTkLabel(centro, text="Atajos:  Ctrl+1 Tareas  ·  Ctrl+2 Gastos  ·  Ctrl+3 Notas  ·  Esc volver al inicio",
                     text_color=C["suave"], font=fuente(12)).pack(pady=(22, 0))

    def _tarjeta(self, padre, col, icono, titulo, sub, color, accion):
        t = ctk.CTkFrame(padre, fg_color=C["panel"], corner_radius=16, border_width=1, border_color=C["borde"])
        t.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0 if col == 2 else 8))

        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(cab, text=icono, font=fuente(30)).pack(side="left")
        textos = ctk.CTkFrame(cab, fg_color="transparent")
        textos.pack(side="left", padx=12)
        ctk.CTkLabel(textos, text=titulo, font=fuente(22, "bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(textos, text=sub, font=fuente(13), text_color=C["suave"], anchor="w").pack(fill="x")

        numero = ctk.CTkLabel(t, text="", font=fuente(34, "bold"), anchor="w", text_color=color)
        numero.pack(fill="x", padx=24, pady=(18, 0))
        etiqueta = ctk.CTkLabel(t, text="", font=fuente(13), text_color=C["suave"], anchor="w")
        etiqueta.pack(fill="x", padx=24)

        lista = ctk.CTkFrame(t, fg_color=C["panel2"], corner_radius=10)
        lista.pack(fill="x", padx=24, pady=(14, 0))

        ctk.CTkButton(t, text=f"Abrir {titulo}  →", height=42, corner_radius=10, font=fuente(14, "bold"),
                      fg_color=color, hover_color=("#2563eb", "#16a34a", "#9333ea")[col],
                      command=accion).pack(fill="x", padx=24, pady=22)

        # toda la tarjeta es clicable
        for w in (t, cab, textos, numero, etiqueta):
            w.bind("<Button-1>", lambda e: accion())
        return {"numero": numero, "etiqueta": etiqueta, "lista": lista}

    @staticmethod
    def _llenar(lista, filas, vacio):
        for w in lista.winfo_children():
            w.destroy()
        if not filas:
            ctk.CTkLabel(lista, text=vacio, text_color=C["suave"], font=fuente(12)).pack(anchor="w", padx=14, pady=10)
            return
        for izq, der, color in filas:
            f = ctk.CTkFrame(lista, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(f, text=izq, font=fuente(13), anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=der, font=fuente(12, "bold"), text_color=color or C["suave"]).pack(side="right")
        lista.winfo_children()[0].pack_configure(pady=(10, 3))
        lista.winfo_children()[-1].pack_configure(pady=(3, 10))

    def refrescar(self):
        hora = datetime.now().hour
        saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
        self.saludo.configure(text=f"{saludo} 👋")
        hoy = date.today()
        self.fecha.configure(text=f"Hoy es {fecha_larga(hoy)} de {hoy.year}. ¿Qué quieres organizar?")

        # --- Tareas
        st = self.app.tareas
        st.actualizar_estados()
        pendientes = st.contar("pendiente")
        self.t_tareas["numero"].configure(text=str(pendientes))
        expiradas = st.contar("expirada")
        extra = f"  ·  {expiradas} expiradas" if expiradas else ""
        self.t_tareas["etiqueta"].configure(text=("tarea pendiente" if pendientes == 1 else "tareas pendientes") + extra)
        ahora = datetime.now()
        filas = []
        for t in st.proximas(3):
            f = st.fecha_de(t)
            urgente = (f - ahora).total_seconds() <= 12 * 3600
            nombre = t["nombre"] if len(t["nombre"]) <= 22 else t["nombre"][:21] + "…"
            filas.append((nombre, tiempo_restante(f, ahora), C["aviso"] if urgente else None))
        self._llenar(self.t_tareas["lista"], filas, "Sin pendientes. ¡Todo al día! 🎉")

        # --- Gastos
        g = self.app.gastos
        total_mes = g.gasto_total(hoy.replace(day=1), hoy)
        self.t_gastos["numero"].configure(text=moneda(total_mes))
        self.t_gastos["etiqueta"].configure(text=f"gastado en {MESES[hoy.month - 1]}")
        filas = []
        for p in g.proximos_pagos(7)[:3]:
            dias = (p["fecha"] - hoy).days
            nombre = p["nombre"] if len(p["nombre"]) <= 14 else p["nombre"][:13] + "…"
            color = "#f87171" if dias < 0 else C["aviso"] if dias <= 2 else None
            filas.append((f"{nombre} · {moneda(p['monto'])}", texto_dias(dias), color))
        vacio = "Sin pagos en los próximos 7 días." if g.cuentas else "Aún no tienes cuentas. Empieza creando una."
        self._llenar(self.t_gastos["lista"], filas, vacio)

        # --- Notas
        notas = self.app.notas
        total = len(notas.notas)
        self.t_notas["numero"].configure(text=str(total))
        self.t_notas["etiqueta"].configure(
            text=f"{'nota' if total == 1 else 'notas'} en {len(notas.materias_en_uso())} "
                 f"{'materia' if len(notas.materias_en_uso()) == 1 else 'materias'}")
        filas = []
        for n in notas.recientes(3):
            titulo = notas.titulo_de(n)
            titulo = titulo if len(titulo) <= 20 else titulo[:19] + "…"
            filas.append((titulo, n["materia"][:14].rstrip(), None))
        self._llenar(self.t_notas["lista"], filas, "Aún no tienes notas.")


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Organizador personal · Tareas, Gastos y Notas")
        self.geometry("1180x760")
        self.minsize(1100, 680)
        self.configure(fg_color=C["fondo"])
        aplicar_estilo_tablas(self)

        self.tareas = TareasStore()
        self.gastos = GastosStore()
        self.notas = NotasStore()
        if self.tareas.error_carga:
            self.after(500, lambda: avisar(self, "Aviso", "No se pudo leer tareas.json; se empezó con una lista vacía."))
        self._automaticos = self.gastos.procesar_automaticos()

        self.contenedor = ctk.CTkFrame(self, fg_color=C["fondo"], corner_radius=0)
        self.contenedor.pack(fill="both", expand=True)
        self.pantallas = {}
        self.actual = None
        self._dia = date.today()

        self.bind("<Escape>", lambda e: self.mostrar_inicio() if e.widget.winfo_toplevel() is self else None)
        self.bind("<Control-Key-1>", lambda e: self.mostrar_tareas())
        self.bind("<Control-Key-2>", lambda e: self.mostrar_gastos())
        self.bind("<Control-Key-3>", lambda e: self.mostrar_notas())

        self.mostrar_inicio()
        self.after(1200, self.revision_periodica)

    # ---------------- navegación
    def _mostrar(self, clave, clase):
        if clave not in self.pantallas:
            self.pantallas[clave] = clase(self.contenedor, self)
        if self.actual:
            self.pantallas[self.actual].pack_forget()
        self.actual = clave
        pantalla = self.pantallas[clave]
        pantalla.pack(fill="both", expand=True)
        pantalla.refrescar()
        return pantalla

    def mostrar_inicio(self):
        self._mostrar("inicio", PantallaInicio)

    def mostrar_tareas(self):
        p = self._mostrar("tareas", PantallaTareas)
        p.e_nombre.focus_set()

    def mostrar_gastos(self):
        p = self._mostrar("gastos", PantallaGastos)
        if self._automaticos:
            total = sum(m["monto"] for m in self._automaticos)
            p.aviso.mostrar(f"⟳ Se registraron {len(self._automaticos)} pagos recurrentes automáticos "
                            f"({moneda(total)}).", "info")
            self._automaticos = []

    def mostrar_notas(self):
        self._mostrar("notas", PantallaNotas)

    # ---------------- revisiones automáticas
    def revisar_alertas(self):
        alertas = self.tareas.nuevas_alertas(12)
        if alertas:
            texto = "\n".join(f"• {t['nombre']}  —  vence {t['fecha_limite']}" for t in alertas)
            avisar(self, "⚠ Tareas próximas a vencer",
                   f"Estas tareas vencen dentro de las próximas 12 horas:\n\n{texto}")

    def revision_periodica(self):
        cambios = self.tareas.actualizar_estados()
        if date.today() != self._dia:
            self._dia = date.today()
            self._automaticos += self.gastos.procesar_automaticos()
            cambios = True
        if cambios and self.actual:
            self.pantallas[self.actual].refrescar()
        elif self.actual == "tareas":
            self.pantallas["tareas"].refrescar()   # actualiza "tiempo restante"
        self.revisar_alertas()
        self.after(60_000, self.revision_periodica)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
