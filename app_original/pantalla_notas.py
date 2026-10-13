"""Pantalla de notas de clase: captura rápida, gestor con buscador y palabras clave por IA."""

import queue
import threading
from datetime import datetime

import customtkinter as ctk

import palabras_clave as PC
from modelos import FORMATO_FECHA, MESES_CORTOS
from ui_comun import (C, fuente, boton, Pestanas, Encabezado, BarraAviso, crear_tabla, limpiar_tabla,
                      Dialogo, confirmar, menu_contextual, limpiar_entrada)

TODAS_MATERIAS = "Todas las materias"


def fecha_nota(texto):
    try:
        f = datetime.strptime(texto, FORMATO_FECHA)
        return f"{f.day} {MESES_CORTOS[f.month - 1]} {f.year}"
    except ValueError:
        return texto


def chips(padre, palabras, al_clic, ancho_max=44, fuente_ia=False):
    """Dibuja las palabras clave como botones redondeados, partiendo en filas."""
    firma = (tuple(palabras), fuente_ia, ancho_max)
    if getattr(padre, "_firma_chips", None) == firma:
        return                      # ya están dibujadas: no se reconstruyen (más rápido)
    padre._firma_chips = firma
    for w in padre.winfo_children():
        w.destroy()
    if not palabras:
        return
    fila = ctk.CTkFrame(padre, fg_color="transparent")
    fila.pack(anchor="w")
    usado = 0
    for p in palabras:
        if usado + len(p) + 4 > ancho_max and usado:
            fila = ctk.CTkFrame(padre, fg_color="transparent")
            fila.pack(anchor="w", pady=(4, 0))
            usado = 0
        ctk.CTkButton(fila, text=p, height=26, corner_radius=13, font=fuente(12),
                      fg_color="#1e3a5f" if fuente_ia else C["panel2"], hover_color=C["borde"],
                      text_color=C["texto"], width=20, command=lambda p=p: al_clic(p)).pack(side="left", padx=(0, 6))
        usado += len(p) + 4


class PantallaNotas(ctk.CTkFrame):

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=C["fondo"], corner_radius=0)
        self.app = app
        self.store = app.notas
        self.cola = queue.Queue()
        self.en_proceso = set()

        self.encabezado = Encabezado(self, "Notas de clase", app.mostrar_inicio)
        self.encabezado.pack(fill="x", padx=24, pady=(20, 14))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=24)
        self.pestanas = Pestanas(barra, [("nueva", "✏  Nueva nota"), ("gestor", "📚  Mis notas")], self.ir_a)
        self.pestanas.pack(side="left")
        self.b_ia = ctk.CTkButton(barra, text="", height=30, corner_radius=15, font=fuente(12),
                                  fg_color=C["panel"], hover_color=C["panel2"], text_color=C["suave"],
                                  command=lambda: DialogoIA(self).mostrar())
        self.b_ia.pack(side="right")

        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=24, pady=(12, 0))
        self.aviso = BarraAviso(self)
        self.aviso.pack(fill="x", padx=24, pady=(4, 10))

        self.tabs = {"nueva": TabNueva(self.area, self), "gestor": TabGestor(self.area, self)}
        self.actual = None
        self.ir_a("nueva")
        self.after(150, self._revisar_cola)

    def ir_a(self, clave):
        if self.actual:
            self.tabs[self.actual].pack_forget()
        self.actual = clave
        self.pestanas.seleccionar(clave, avisar=False)
        self.tabs[clave].pack(fill="both", expand=True)
        self.refrescar()
        self.tabs[clave].enfocar()

    def refrescar(self):
        n = len(self.store.notas)
        m = len(self.store.materias_en_uso())
        self.encabezado.derecha.configure(
            text=f"{n} {'nota' if n == 1 else 'notas'} · {m} {'materia' if m == 1 else 'materias'}" if n else "")
        self.pestanas.texto("gestor", f"📚  Mis notas  {n}")
        self.b_ia.configure(text="✨ Palabras clave con IA (Claude)" if PC.clave_api()
                            else "⚙ Palabras clave: modo local · activar IA")
        if self.actual:
            self.tabs[self.actual].refrescar()

    # ------------------------------------------------ palabras clave en segundo plano

    def generar_palabras(self, nota_id):
        """Extrae las palabras clave sin congelar la ventana."""
        nota = self.store.nota(nota_id)
        if nota is None or nota_id in self.en_proceso:
            return
        self.en_proceso.add(nota_id)
        texto, materia, otros = nota["texto"], nota["materia"], self.store.otros_textos(nota_id)

        def trabajo():
            try:
                palabras, origen = PC.extraer(texto, materia, otros)
            except Exception:
                palabras, origen = [], "local"
            self.cola.put((nota_id, palabras, origen))

        threading.Thread(target=trabajo, daemon=True).start()

    def _revisar_cola(self):
        try:
            while True:
                nota_id, palabras, origen = self.cola.get_nowait()
                self.en_proceso.discard(nota_id)
                self.store.poner_palabras(nota_id, palabras, origen)
                nota = self.store.nota(nota_id)
                if nota:
                    etiqueta = "con IA ✨" if origen == "ia" else "en modo local"
                    if palabras:
                        self.aviso.mostrar(f"Palabras clave {etiqueta}: {', '.join(palabras)}")
                    else:
                        self.aviso.mostrar("No se encontraron palabras clave; puedes escribirlas al editar la nota.", "info")
                self.refrescar()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(150, self._revisar_cola)

    def buscar_palabra(self, palabra):
        self.ir_a("gestor")
        self.tabs["gestor"].poner_busqueda(palabra)


# ======================================================================
# NUEVA NOTA
# ======================================================================

class TabNueva(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store
        self.ultima_id = None

        tarjeta = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=12)
        tarjeta.pack(fill="both", expand=True)

        fila = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(fila, text="Materia", text_color=C["suave"]).pack(side="left")
        self.materia = ctk.CTkComboBox(fila, values=self.store.materias or ["General"], width=220)
        self.materia.set(self.store.materias[-1] if self.store.materias else "General")
        self.materia.pack(side="left", padx=(8, 16))
        self.titulo = ctk.CTkEntry(fila, placeholder_text="Título (opcional)", height=32)
        self.titulo.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(tarjeta, text="Escribe o pega tu apunte:", text_color=C["suave"],
                     font=fuente(12)).pack(anchor="w", padx=16)
        self.texto = ctk.CTkTextbox(tarjeta, font=fuente(14), wrap="word", fg_color=C["fondo"],
                                    border_width=1, border_color=C["borde"], corner_radius=8)
        self.texto.pack(fill="both", expand=True, padx=16, pady=(4, 10))
        self.texto.bind("<Control-Return>", self._atajo)

        pie = ctk.CTkFrame(tarjeta, fg_color="transparent")
        pie.pack(fill="x", padx=16, pady=(0, 16))
        boton(pie, "💾  Guardar nota", self.guardar, "primario", width=160, height=40).pack(side="left")
        ctk.CTkLabel(pie, text="Ctrl+Enter para guardar · las palabras clave se generan solas",
                     text_color=C["suave"], font=fuente(12)).pack(side="left", padx=14)

        # Última nota guardada
        self.ultima = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=12)
        self.l_ultima = ctk.CTkLabel(self.ultima, text="", font=fuente(13, "bold"), anchor="w")
        self.l_ultima.pack(fill="x", padx=16, pady=(12, 4))
        self.chips = ctk.CTkFrame(self.ultima, fg_color="transparent")
        self.chips.pack(fill="x", padx=16, pady=(0, 12))

    def enfocar(self):
        self.texto.focus_set()

    def _atajo(self, _e):
        self.guardar()
        return "break"

    def guardar(self):
        texto = self.texto.get("1.0", "end").strip()
        if not texto:
            self.p.aviso.mostrar("Escribe algo en la nota antes de guardar.", "error")
            self.texto.focus_set()
            return
        materia = self.materia.get().strip()
        if not materia:
            self.p.aviso.mostrar("Escribe o elige la materia de la nota.", "error")
            self.materia.focus_set()
            return
        nota = self.store.agregar(materia, self.titulo.get(), texto)
        self.ultima_id = nota["id"]
        self.texto.delete("1.0", "end")
        limpiar_entrada(self.titulo)
        self.materia.set(nota["materia"])
        self.p.aviso.mostrar(f"✓ Nota guardada en {nota['materia']}. Buscando palabras clave…")
        self.p.generar_palabras(nota["id"])
        self.p.refrescar()
        self.texto.focus_set()

    def refrescar(self):
        self.materia.configure(values=self.store.materias or ["General"])
        nota = self.store.nota(self.ultima_id) if self.ultima_id else None
        if not nota:
            self.ultima.pack_forget()
            return
        self.ultima.pack(fill="x", pady=(10, 0))
        if nota["fuente"] == "pendiente":
            estado = "buscando palabras clave…"
        elif nota["palabras_clave"]:
            estado = "palabras clave" + (" (IA)" if nota["fuente"] == "ia" else "")
        else:
            estado = "sin palabras clave"
        self.l_ultima.configure(text=f"Última nota · {nota['materia']} · {self.store.titulo_de(nota)}  —  {estado}")
        chips(self.chips, nota["palabras_clave"], self.p.buscar_palabra, 110, nota["fuente"] == "ia")


# ======================================================================
# GESTOR DE NOTAS
# ======================================================================

class TabGestor(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store

        busqueda = ctk.CTkFrame(self, fg_color="transparent")
        busqueda.pack(fill="x")
        self.buscar = ctk.CTkEntry(busqueda, placeholder_text="🔍  Busca por tema, palabra clave o texto…",
                                   height=40, font=fuente(14))
        self.buscar.pack(side="left", fill="x", expand=True)
        self._espera = None
        self.buscar.bind("<KeyRelease>", self._al_escribir)
        boton(busqueda, "✕", lambda: self.poner_busqueda(""), "fantasma", width=40, height=40).pack(side="left", padx=4)
        self.materia = ctk.CTkOptionMenu(busqueda, values=[TODAS_MATERIAS], width=200, height=40,
                                         command=lambda _: self.refrescar(), fg_color=C["panel2"], button_color=C["borde"])
        self.materia.pack(side="left")

        frecuentes = ctk.CTkFrame(self, fg_color="transparent")
        frecuentes.pack(fill="x", pady=(10, 8))
        ctk.CTkLabel(frecuentes, text="Más usadas:", text_color=C["suave"], font=fuente(12)).pack(side="left", padx=(0, 8))
        self.frecuentes = ctk.CTkFrame(frecuentes, fg_color="transparent")
        self.frecuentes.pack(side="left", fill="x", expand=True)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)
        cuerpo.grid_columnconfigure(0, weight=3, uniform="c")
        cuerpo.grid_columnconfigure(1, weight=2, uniform="c")
        cuerpo.grid_rowconfigure(0, weight=1)

        marco, self.tree = crear_tabla(cuerpo, [
            ("fecha", "Fecha", 95, "center", False),
            ("materia", "Materia", 120, "w", False),
            ("titulo", "Nota", 200, "w", True),
            ("claves", "Palabras clave", 220, "w", True),
        ])
        marco.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._mostrar_detalle())
        self.tree.bind("<Double-1>", lambda e: self.editar())
        self.tree.bind("<Delete>", lambda e: self.eliminar())
        self.tree.bind("<Button-3>", self._menu)

        self.detalle = ctk.CTkFrame(cuerpo, fg_color=C["panel"], corner_radius=12)
        self.detalle.grid(row=0, column=1, sticky="nsew")
        self.d_titulo = ctk.CTkLabel(self.detalle, text="", font=fuente(17, "bold"), anchor="w", justify="left",
                                     wraplength=360)
        self.d_titulo.pack(fill="x", padx=16, pady=(14, 0))
        self.d_meta = ctk.CTkLabel(self.detalle, text="", text_color=C["suave"], font=fuente(12), anchor="w")
        self.d_meta.pack(fill="x", padx=16)
        self.d_chips = ctk.CTkFrame(self.detalle, fg_color="transparent")
        self.d_chips.pack(fill="x", padx=16, pady=(8, 6))
        self.d_texto = ctk.CTkTextbox(self.detalle, wrap="word", font=fuente(13), fg_color=C["fondo"],
                                      corner_radius=8)
        self.d_texto.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        acciones = ctk.CTkFrame(self.detalle, fg_color="transparent")
        acciones.pack(fill="x", padx=16, pady=(0, 14))
        self.b_editar = boton(acciones, "✎ Editar", self.editar, "neutro", width=90, height=32)
        self.b_editar.pack(side="left")
        self.b_regenerar = boton(acciones, "↻ Palabras clave", self.regenerar, "neutro", width=140, height=32)
        self.b_regenerar.pack(side="left", padx=6)
        self.b_eliminar = boton(acciones, "🗑", self.eliminar, "neutro", width=40, height=32)
        self.b_eliminar.pack(side="right")

    def enfocar(self):
        self.buscar.focus_set()

    def _al_escribir(self, _e=None):
        """Espera a que dejes de escribir un momento antes de buscar."""
        if self._espera:
            self.after_cancel(self._espera)
        self._espera = self.after(250, self.refrescar)

    def poner_busqueda(self, texto):
        self.buscar.delete(0, "end")
        if texto:
            self.buscar.insert(0, texto)
        self.refrescar()

    def _materia(self):
        m = self.materia.get()
        return None if m == TODAS_MATERIAS else m

    def refrescar(self):
        materias = self.store.materias_en_uso()
        self.materia.configure(values=[TODAS_MATERIAS] + materias)
        if self.materia.get() not in [TODAS_MATERIAS] + materias:
            self.materia.set(TODAS_MATERIAS)

        frecuentes = [p for p, _ in self.store.palabras_frecuentes(self._materia(), 10)]
        chips(self.frecuentes, frecuentes, self.poner_busqueda, 140)
        if not frecuentes and not self.frecuentes.winfo_children():
            ctk.CTkLabel(self.frecuentes, text="(aparecerán cuando guardes notas)", text_color=C["suave"],
                         font=fuente(12)).pack(anchor="w")

        seleccion = self.tree.selection()
        limpiar_tabla(self.tree)
        notas = self.store.buscar(self.buscar.get(), self._materia())
        for i, n in enumerate(notas):
            if n["id"] in self.p.en_proceso or n["fuente"] == "pendiente":
                claves = "buscando…"
            else:
                claves = ", ".join(n["palabras_clave"])
            self.tree.insert("", "end", iid=n["id"], tags=["par" if i % 2 == 0 else "impar"],
                             values=(fecha_nota(n["fecha"]), n["materia"], self.store.titulo_de(n), claves))
        if seleccion and self.tree.exists(seleccion[0]):
            self.tree.selection_set(seleccion[0])
        elif notas:
            self.tree.selection_set(notas[0]["id"])
        self._mostrar_detalle()

    def _sel(self):
        s = self.tree.selection()
        return s[0] if s else None

    def _mostrar_detalle(self):
        nota = self.store.nota(self._sel()) if self._sel() else None
        self.d_texto.configure(state="normal")
        self.d_texto.delete("1.0", "end")
        botones = (self.b_editar, self.b_regenerar, self.b_eliminar)
        if not nota:
            busqueda = self.buscar.get().strip()
            if not self.store.notas:
                self.d_titulo.configure(text="Aún no tienes notas")
                self.d_meta.configure(text="Escribe tu primera nota en la pestaña «Nueva nota».")
            else:
                self.d_titulo.configure(text="Sin resultados")
                self.d_meta.configure(text=f"Ninguna nota coincide con «{busqueda}»." if busqueda else "")
            chips(self.d_chips, [], None)
            self.d_texto.configure(state="disabled")
            for b in botones:
                b.configure(state="disabled")
            return
        for b in botones:
            b.configure(state="normal")
        self.d_titulo.configure(text=self.store.titulo_de(nota))
        origen = {"ia": " · palabras clave por IA ✨", "manual": " · palabras clave editadas",
                  "pendiente": " · buscando palabras clave…"}.get(nota["fuente"], "")
        self.d_meta.configure(text=f"{nota['materia']} · {fecha_nota(nota['fecha'])}{origen}")
        chips(self.d_chips, nota["palabras_clave"], self.poner_busqueda, 44, nota["fuente"] == "ia")
        self.d_texto.insert("1.0", nota["texto"])
        self.d_texto.configure(state="disabled")

    def _menu(self, e):
        fila = self.tree.identify_row(e.y)
        if fila:
            self.tree.selection_set(fila)
            menu_contextual(self.tree, [("✎ Editar", self.editar), ("↻ Volver a generar palabras clave", self.regenerar),
                                        None, ("🗑 Eliminar", self.eliminar)]).tk_popup(e.x_root, e.y_root)

    def editar(self):
        nid = self._sel()
        if nid:
            DialogoNota(self.p, self.store.nota(nid)).mostrar()

    def regenerar(self):
        nid = self._sel()
        if nid:
            self.store.poner_palabras(nid, self.store.nota(nid)["palabras_clave"], "pendiente")
            self.p.generar_palabras(nid)
            self.p.aviso.mostrar("Buscando palabras clave…", "info")
            self.refrescar()

    def eliminar(self):
        nid = self._sel()
        if not nid:
            return
        nota = self.store.nota(nid)
        if confirmar(self.winfo_toplevel(), "Eliminar nota", f"¿Eliminar «{self.store.titulo_de(nota)}»?"):
            self.store.eliminar(nid)
            self.p.aviso.mostrar("Nota eliminada.", "info")
            self.p.refrescar()


class DialogoNota(Dialogo):

    def __init__(self, pantalla, nota):
        super().__init__(pantalla.winfo_toplevel(), "Editar nota")
        self.p = pantalla
        self.nota = nota
        st = pantalla.store
        self.materia = self.campo("Materia", ctk.CTkComboBox(self.cuerpo, values=st.materias, width=420))
        self.materia.set(nota["materia"])
        self.titulo = self.campo("Título", ctk.CTkEntry(self.cuerpo))
        self.titulo.insert(0, nota.get("titulo", ""))
        self.texto = self.campo("Nota", ctk.CTkTextbox(self.cuerpo, height=220, wrap="word"))
        self.texto.insert("1.0", nota["texto"])
        self.palabras_originales = ", ".join(nota["palabras_clave"])
        self.palabras = self.campo("Palabras clave", ctk.CTkEntry(self.cuerpo),
                                   "Separadas por comas. Si cambias el texto y no las tocas, se generan de nuevo.")
        self.palabras.insert(0, self.palabras_originales)

    def aceptar(self):
        texto = self.texto.get("1.0", "end").strip()
        if not texto:
            self.fallar("La nota no puede quedar vacía.")
            return False
        palabras_txt = self.palabras.get().strip()
        cambio_palabras = palabras_txt != self.palabras_originales
        cambio_texto = texto != self.nota["texto"]
        palabras = None
        if cambio_palabras:
            palabras = [p.strip() for p in palabras_txt.split(",") if p.strip()]
        self.p.store.editar(self.nota["id"], self.materia.get(), self.titulo.get(), texto, palabras)
        if cambio_texto and not cambio_palabras:
            self.p.store.poner_palabras(self.nota["id"], self.nota["palabras_clave"], "pendiente")
            self.p.generar_palabras(self.nota["id"])
            self.p.aviso.mostrar("✓ Nota actualizada. Actualizando palabras clave…")
        else:
            self.p.aviso.mostrar("✓ Nota actualizada.")
        self.p.refrescar()
        return True


class DialogoIA(Dialogo):

    def __init__(self, pantalla):
        super().__init__(pantalla.winfo_toplevel(), "Palabras clave con IA")
        self.p = pantalla
        ctk.CTkLabel(
            self.cuerpo, justify="left", wraplength=440, text_color=C["suave"], font=fuente(12),
            text=("Sin clave, la app extrae las palabras clave con un analizador local (RAKE + TF-IDF) "
                  "que funciona sin internet.\n\nPara usar IA (Claude), pega una clave de API de "
                  "console.anthropic.com. Se guarda solo en config.json dentro de la carpeta del proyecto. "
                  "No subas ese archivo a GitHub.")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self._fila = 1
        self.clave = self.campo("Clave de API", ctk.CTkEntry(self.cuerpo, width=360, show="•",
                                                             placeholder_text="sk-ant-…"))
        actual = PC.leer_config().get("anthropic_api_key", "")
        if actual:
            self.clave.insert(0, actual)

    def aceptar(self):
        clave = self.clave.get().strip()
        PC.guardar_clave_api(clave)
        self.p.aviso.mostrar("✓ IA activada: las próximas notas usarán Claude." if clave
                             else "IA desactivada: se usará el modo local.", "ok" if clave else "info")
        self.p.refrescar()
        return True
