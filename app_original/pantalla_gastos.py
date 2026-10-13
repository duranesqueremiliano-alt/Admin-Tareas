"""Pantalla de gastos personales: movimientos, cuentas, pagos recurrentes y resumen."""

import calendar
import tkinter as tk
from datetime import date, timedelta

import customtkinter as ctk

from modelos import (MESES, TIPOS_CUENTA, FRECUENCIAS, COLORES_CUENTA, moneda, leer_monto, a_fecha,
                     fecha_corta, texto_dias, sumar_meses)
from ui_comun import (C, fuente, boton, Pestanas, Encabezado, BarraAviso, SelectorFecha, crear_tabla,
                      limpiar_tabla, Dialogo, confirmar, menu_contextual, limpiar_entrada)

TODAS = "Todas las cuentas"
TODAS_CAT = "Todas las categorías"
TODOS_MESES = "Todos los meses"


def etiqueta_mes(clave):
    anio, mes = clave.split("-")
    return f"{MESES[int(mes) - 1].capitalize()} {anio}"


def rango_mes(clave):
    anio, mes = map(int, clave.split("-"))
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])


def mensual_estimado(rec):
    factor = {"semanal": 52 / 12, "quincenal": 26 / 12, "mensual": 1, "bimestral": 0.5, "anual": 1 / 12}
    return rec["monto"] * factor.get(rec["frecuencia"], 1)


class PantallaGastos(ctk.CTkFrame):

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=C["fondo"], corner_radius=0)
        self.app = app
        self.store = app.gastos

        self.encabezado = Encabezado(self, "Gastos personales", app.mostrar_inicio)
        self.encabezado.pack(fill="x", padx=24, pady=(20, 14))

        self.pestanas = Pestanas(self, [("movimientos", "Movimientos"), ("cuentas", "Cuentas"),
                                        ("recurrentes", "Pagos recurrentes"), ("resumen", "Resumen por categoría")],
                                 self.ir_a)
        self.pestanas.pack(anchor="w", padx=24)

        self.area = ctk.CTkFrame(self, fg_color="transparent")
        self.area.pack(fill="both", expand=True, padx=24, pady=(12, 0))

        self.aviso = BarraAviso(self)
        self.aviso.pack(fill="x", padx=24, pady=(4, 10))

        self.tabs = {
            "movimientos": TabMovimientos(self.area, self),
            "cuentas": TabCuentas(self.area, self),
            "recurrentes": TabRecurrentes(self.area, self),
            "resumen": TabResumen(self.area, self),
        }
        self.actual = None
        self.ir_a("movimientos")

    def ir_a(self, clave):
        if self.actual:
            self.tabs[self.actual].pack_forget()
        self.actual = clave
        self.pestanas.seleccionar(clave, avisar=False)
        self.tabs[clave].pack(fill="both", expand=True)
        self.refrescar()

    def refrescar(self):
        hoy = date.today()
        mes = self.store.gasto_total(hoy.replace(day=1), hoy)
        self.encabezado.derecha.configure(text=f"Gastado en {MESES[hoy.month - 1]}: {moneda(mes)}")
        if self.actual:
            self.tabs[self.actual].refrescar()

    # utilidades compartidas por las pestañas
    def nombres_cuentas(self):
        return [c["nombre"] for c in self.store.cuentas]

    def id_cuenta(self, nombre):
        return next((c["id"] for c in self.store.cuentas if c["nombre"] == nombre), None)


# ======================================================================
# MOVIMIENTOS
# ======================================================================

class TabMovimientos(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store
        self._meses = {}

        self.tarjeta = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=12)
        self.tarjeta.pack(fill="x")
        self._crear_formulario()
        self._crear_sin_cuentas()

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", pady=(14, 8))
        ctk.CTkLabel(filtros, text="Ver:", text_color=C["suave"]).pack(side="left", padx=(0, 6))
        self.f_mes = ctk.CTkOptionMenu(filtros, values=[TODOS_MESES], width=160, command=lambda _: self.refrescar(),
                                       fg_color=C["panel2"], button_color=C["borde"])
        self.f_mes.pack(side="left")
        self.f_cuenta = ctk.CTkOptionMenu(filtros, values=[TODAS], width=170, command=lambda _: self.refrescar(),
                                          fg_color=C["panel2"], button_color=C["borde"])
        self.f_cuenta.pack(side="left", padx=6)
        self.f_cat = ctk.CTkOptionMenu(filtros, values=[TODAS_CAT], width=170, command=lambda _: self.refrescar(),
                                       fg_color=C["panel2"], button_color=C["borde"])
        self.f_cat.pack(side="left")
        self.f_texto = ctk.CTkEntry(filtros, placeholder_text="🔍 Buscar…", width=180)
        self.f_texto.pack(side="right")
        self.f_texto.bind("<KeyRelease>", lambda e: self.refrescar())

        marco, self.tree = crear_tabla(self, [
            ("fecha", "Fecha", 100, "center", False),
            ("desc", "Descripción", 260, "w", True),
            ("cat", "Categoría", 140, "w", False),
            ("cuenta", "Cuenta", 150, "w", False),
            ("monto", "Monto", 120, "e", False),
        ])
        marco.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.editar())
        self.tree.bind("<Delete>", lambda e: self.eliminar())
        self.tree.bind("<Button-3>", self._menu)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", pady=(8, 0))
        self.l_totales = ctk.CTkLabel(pie, text="", text_color=C["suave"], font=fuente(13))
        self.l_totales.pack(side="left")
        boton(pie, "🗑 Eliminar", self.eliminar, "neutro", width=100).pack(side="right")
        boton(pie, "✎ Editar", self.editar, "neutro", width=90).pack(side="right", padx=8)

        self.f_mes.set(etiqueta_mes(date.today().strftime("%Y-%m")))

    # ---------- formulario
    def _crear_formulario(self):
        self.form = ctk.CTkFrame(self.tarjeta, fg_color="transparent")

        f1 = ctk.CTkFrame(self.form, fg_color="transparent")
        f1.pack(fill="x", padx=14, pady=(14, 6))
        self.tipo = ctk.CTkSegmentedButton(f1, values=["Gasto", "Ingreso / pago"], command=self._cambiar_tipo,
                                           selected_color=C["acento"], selected_hover_color=C["acento_hover"])
        self.tipo.set("Gasto")
        self.tipo.pack(side="left")
        self.e_monto = ctk.CTkEntry(f1, placeholder_text="$ Monto", width=120, height=36, font=fuente(15, "bold"))
        self.e_monto.pack(side="left", padx=10)
        self.e_desc = ctk.CTkEntry(f1, placeholder_text="Descripción (ej. Súper del sábado)", height=36)
        self.e_desc.pack(side="left", fill="x", expand=True)

        f2 = ctk.CTkFrame(self.form, fg_color="transparent")
        f2.pack(fill="x", padx=14, pady=(0, 14))
        self.l_cat = ctk.CTkLabel(f2, text="Categoría", text_color=C["suave"])
        self.l_cat.pack(side="left")
        self.e_cat = ctk.CTkComboBox(f2, values=self.store.categorias, width=170)
        self.e_cat.set("Comida")
        self.e_cat.pack(side="left", padx=(6, 14))
        ctk.CTkLabel(f2, text="Cuenta", text_color=C["suave"]).pack(side="left")
        self.e_cuenta = ctk.CTkOptionMenu(f2, values=["—"], width=170)
        self.e_cuenta.pack(side="left", padx=(6, 14))
        ctk.CTkLabel(f2, text="Fecha", text_color=C["suave"]).pack(side="left")
        self.e_fecha = SelectorFecha(f2, date.today())
        self.e_fecha.pack(side="left", padx=(6, 0))
        self.b_agregar = boton(f2, "＋ Agregar gasto", self.agregar, width=150)
        self.b_agregar.pack(side="right")

        for w in (self.e_monto, self.e_desc):
            w.bind("<Return>", lambda e: self.agregar())

    def _crear_sin_cuentas(self):
        self.vacio = ctk.CTkFrame(self.tarjeta, fg_color="transparent")
        ctk.CTkLabel(self.vacio, text="Primero crea una cuenta", font=fuente(17, "bold")).pack(pady=(22, 4))
        ctk.CTkLabel(self.vacio, text="Agrega tu tarjeta de débito, de crédito o tu efectivo para empezar a registrar gastos.",
                     text_color=C["suave"]).pack()
        boton(self.vacio, "＋ Crear mi primera cuenta",
              lambda: (self.p.ir_a("cuentas"), self.p.tabs["cuentas"].nueva()), width=220).pack(pady=(12, 22))

    def _cambiar_tipo(self, valor):
        if valor == "Gasto":
            self.e_cat.configure(state="normal")
            self.l_cat.configure(text_color=C["suave"])
            self.b_agregar.configure(text="＋ Agregar gasto")
        else:
            self.e_cat.configure(state="disabled")
            self.l_cat.configure(text_color=C["borde"])
            self.b_agregar.configure(text="＋ Agregar ingreso")

    def preparar(self, tipo, cuenta_nombre):
        """Usado desde Cuentas: deja el formulario listo para un ingreso/pago en esa cuenta."""
        self.tipo.set(tipo)
        self._cambiar_tipo(tipo)
        self.e_cuenta.set(cuenta_nombre)
        self.e_monto.focus_set()

    def agregar(self):
        monto = leer_monto(self.e_monto.get())
        if monto is None:
            self.p.aviso.mostrar("Escribe un monto válido mayor a 0.", "error")
            self.e_monto.focus_set()
            return
        cuenta_id = self.p.id_cuenta(self.e_cuenta.get())
        if not cuenta_id:
            self.p.aviso.mostrar("Elige una cuenta.", "error")
            return
        fecha = self.e_fecha.get()
        if fecha is None:
            self.p.aviso.mostrar("Fecha no válida. Usa el calendario 📅.", "error")
            return
        es_gasto = self.tipo.get() == "Gasto"
        desc = self.e_desc.get().strip()
        if es_gasto:
            mov = self.store.agregar_movimiento("gasto", monto, cuenta_id, fecha, desc, self.e_cat.get())
            self.p.aviso.mostrar(f"✓ Gasto de {moneda(monto)} en {mov['categoria']} con {self.e_cuenta.get()}.")
        else:
            self.store.agregar_movimiento("abono", monto, cuenta_id, fecha, desc or "Ingreso / pago")
            self.p.aviso.mostrar(f"✓ Ingreso / pago de {moneda(monto)} registrado en {self.e_cuenta.get()}.")
        limpiar_entrada(self.e_desc)
        self.e_monto.delete(0, "end")
        self.e_monto.focus_set()
        self.p.refrescar()

    # ---------- lista
    def refrescar(self):
        tiene_cuentas = bool(self.store.cuentas)
        self.form.pack_forget()
        self.vacio.pack_forget()
        (self.form if tiene_cuentas else self.vacio).pack(fill="x")

        nombres = self.p.nombres_cuentas()
        self.e_cuenta.configure(values=nombres or ["—"])
        if self.e_cuenta.get() not in nombres:
            self.e_cuenta.set(nombres[0] if nombres else "—")
        self.e_cat.configure(values=self.store.categorias)

        self._meses = {etiqueta_mes(m): m for m in self.store.meses_con_datos()}
        self.f_mes.configure(values=[TODOS_MESES] + list(self._meses))
        self.f_cuenta.configure(values=[TODAS] + nombres)
        if self.f_cuenta.get() not in [TODAS] + nombres:
            self.f_cuenta.set(TODAS)
        self.f_cat.configure(values=[TODAS_CAT] + self.store.categorias)

        desde = hasta = None
        if self.f_mes.get() in self._meses:
            desde, hasta = rango_mes(self._meses[self.f_mes.get()])
        cuenta_id = self.p.id_cuenta(self.f_cuenta.get())
        cat = None if self.f_cat.get() == TODAS_CAT else self.f_cat.get()
        movs = self.store.movimientos_filtrados(desde, hasta, cuenta_id, cat, self.f_texto.get())

        seleccion = self.tree.selection()
        limpiar_tabla(self.tree)
        gastos = abonos = 0.0
        for i, m in enumerate(movs):
            f = a_fecha(m["fecha"])
            tags = ["par" if i % 2 == 0 else "impar"]
            if m["tipo"] == "abono":
                abonos += m["monto"]
                monto = "+" + moneda(m["monto"])
                tags.append("positivo")
                cat_txt = "Ingreso / pago"
            else:
                gastos += m["monto"]
                monto = moneda(m["monto"])
                cat_txt = m.get("categoria", "")
            desc = (m.get("descripcion") or "—") + ("  ⟳" if m.get("recurrente_id") else "")
            self.tree.insert("", "end", iid=m["id"], tags=tags, values=(
                f.strftime("%d/%m/%Y"), desc, cat_txt, self.store.nombre_cuenta(m["cuenta_id"]), monto))

        if seleccion and self.tree.exists(seleccion[0]):
            self.tree.selection_set(seleccion[0])
        texto = f"{len(movs)} movimientos   ·   Gastos: {moneda(gastos)}"
        if abonos:
            texto += f"   ·   Ingresos / pagos: {moneda(abonos)}"
        self.l_totales.configure(text=texto)

    def filtrar_categoria(self, categoria, clave_mes=None):
        self.f_cat.set(categoria)
        self.f_mes.set(etiqueta_mes(clave_mes) if clave_mes else TODOS_MESES)
        self.f_cuenta.set(TODAS)

    def _sel(self):
        s = self.tree.selection()
        return s[0] if s else None

    def _menu(self, e):
        fila = self.tree.identify_row(e.y)
        if fila:
            self.tree.selection_set(fila)
            menu_contextual(self.tree, [("✎ Editar", self.editar), None, ("🗑 Eliminar", self.eliminar)]).tk_popup(e.x_root, e.y_root)

    def editar(self):
        mid = self._sel()
        if mid:
            DialogoMovimiento(self.p, self.store.movimiento(mid)).mostrar()
        else:
            self.p.aviso.mostrar("Selecciona un movimiento de la lista.", "info")

    def eliminar(self):
        mid = self._sel()
        if not mid:
            self.p.aviso.mostrar("Selecciona un movimiento de la lista.", "info")
            return
        m = self.store.movimiento(mid)
        if confirmar(self.winfo_toplevel(), "Eliminar movimiento",
                     f"¿Eliminar «{m.get('descripcion') or m.get('categoria')}» por {moneda(m['monto'])}?"):
            self.store.eliminar_movimiento(mid)
            self.p.aviso.mostrar("Movimiento eliminado.", "info")
            self.p.refrescar()


class DialogoMovimiento(Dialogo):

    def __init__(self, pantalla, mov):
        super().__init__(pantalla.winfo_toplevel(), "Editar movimiento")
        self.p = pantalla
        self.mov = mov
        st = pantalla.store

        self.tipo = self.campo("Tipo", ctk.CTkSegmentedButton(self.cuerpo, values=["Gasto", "Ingreso / pago"],
                                                              command=self._tipo))
        self.tipo.set("Gasto" if mov["tipo"] == "gasto" else "Ingreso / pago")
        self.monto = self.campo("Monto", ctk.CTkEntry(self.cuerpo, width=300))
        self.monto.insert(0, f"{mov['monto']:.2f}")
        self.desc = self.campo("Descripción", ctk.CTkEntry(self.cuerpo))
        self.desc.insert(0, mov.get("descripcion", ""))
        self.cat = self.campo("Categoría", ctk.CTkComboBox(self.cuerpo, values=st.categorias))
        self.cat.set(mov.get("categoria") or "Otros")
        self.cuenta = self.campo("Cuenta", ctk.CTkOptionMenu(self.cuerpo, values=pantalla.nombres_cuentas()))
        self.cuenta.set(st.nombre_cuenta(mov["cuenta_id"]))
        self.fecha = self.campo("Fecha", SelectorFecha(self.cuerpo, a_fecha(mov["fecha"])))
        self._tipo(self.tipo.get())

    def _tipo(self, valor):
        self.cat.configure(state="normal" if valor == "Gasto" else "disabled")

    def aceptar(self):
        monto = leer_monto(self.monto.get())
        if monto is None:
            self.fallar("Monto no válido.")
            return False
        cuenta_id = self.p.id_cuenta(self.cuenta.get())
        fecha = self.fecha.get()
        if not cuenta_id or fecha is None:
            self.fallar("Revisa la cuenta y la fecha.")
            return False
        self.p.store.editar_movimiento(
            self.mov["id"], tipo="gasto" if self.tipo.get() == "Gasto" else "abono", monto=monto,
            descripcion=self.desc.get().strip(), categoria=self.cat.get(), cuenta_id=cuenta_id, fecha=fecha)
        self.p.aviso.mostrar("✓ Movimiento actualizado.")
        self.p.refrescar()
        return True


# ======================================================================
# CUENTAS
# ======================================================================

class TabCuentas(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))
        self.l_total = ctk.CTkLabel(barra, text="", font=fuente(14), text_color=C["suave"])
        self.l_total.pack(side="left")
        boton(barra, "＋ Nueva cuenta", self.nueva, width=150).pack(side="right")

        self.lista = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.lista.pack(fill="both", expand=True)
        for i in range(3):
            self.lista.grid_columnconfigure(i, weight=1, uniform="col")

    def nueva(self):
        DialogoCuenta(self.p, None).mostrar()

    def refrescar(self):
        for w in self.lista.winfo_children():
            w.destroy()

        disponible = sum(self.store.saldo(c) for c in self.store.cuentas if c["tipo"] != "credito")
        deuda = sum(self.store.saldo(c) for c in self.store.cuentas if c["tipo"] == "credito")
        self.l_total.configure(text=f"Dinero disponible: {moneda(disponible)}     ·     Deuda en tarjetas: {moneda(deuda)}")

        if not self.store.cuentas:
            ctk.CTkLabel(self.lista, text="Aún no tienes cuentas.\nCrea una de débito, crédito o efectivo.",
                         text_color=C["suave"], font=fuente(15)).grid(row=0, column=0, columnspan=3, pady=60)
            return

        for i, cuenta in enumerate(self.store.cuentas):
            self._tarjeta(cuenta).grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)

    def _tarjeta(self, cuenta):
        color = cuenta.get("color") or C["acento"]
        t = ctk.CTkFrame(self.lista, fg_color=C["panel"], corner_radius=12, border_width=2, border_color=color)

        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(cab, text=cuenta["nombre"], font=fuente(16, "bold")).pack(side="left")
        ctk.CTkLabel(cab, text=f" {TIPOS_CUENTA[cuenta['tipo']]} ", fg_color=color, corner_radius=6,
                     text_color="white", font=fuente(11, "bold")).pack(side="right")

        saldo = self.store.saldo(cuenta)
        es_credito = cuenta["tipo"] == "credito"

        if es_credito:
            info = self.store.info_credito(cuenta)
            ctk.CTkLabel(t, text="Deuda actual", text_color=C["suave"], font=fuente(12)).pack(anchor="w", padx=16, pady=(10, 0))
            ctk.CTkLabel(t, text=moneda(saldo), font=fuente(24, "bold")).pack(anchor="w", padx=16)
            if info["limite"]:
                barra = ctk.CTkProgressBar(t, height=8, progress_color=C["peligro"] if info["uso"] > 0.8 else color)
                barra.set(min(max(info["uso"], 0), 1))
                barra.pack(fill="x", padx=16, pady=(6, 2))
                ctk.CTkLabel(t, text=f"Disponible {moneda(info['disponible'])} de {moneda(info['limite'])}",
                             text_color=C["suave"], font=fuente(12)).pack(anchor="w", padx=16)
            filas = [
                ("Corte", f"{fecha_corta(info['proximo_corte'])}  ({texto_dias(info['dias_corte'])})", None),
                ("Pago límite", f"{fecha_corta(info['proximo_pago'])}  ({texto_dias(info['dias_pago'])})",
                 C["aviso"] if info["dias_pago"] <= 5 and saldo > 0 else None),
                ("Gastado este periodo", moneda(info["gasto_periodo_actual"]), None),
                ("Del periodo a pagar", moneda(info["gasto_facturado"]), None),
            ]
        else:
            ctk.CTkLabel(t, text="Saldo disponible", text_color=C["suave"], font=fuente(12)).pack(anchor="w", padx=16, pady=(10, 0))
            ctk.CTkLabel(t, text=moneda(saldo), font=fuente(24, "bold"),
                         text_color="#f87171" if saldo < 0 else C["texto"]).pack(anchor="w", padx=16)
            hoy = date.today()
            gastado = self.store.gasto_total(hoy.replace(day=1), hoy, cuenta["id"])
            filas = [("Gastado este mes", moneda(gastado), None)]

        detalle = ctk.CTkFrame(t, fg_color="transparent")
        detalle.pack(fill="x", padx=16, pady=(8, 0))
        for r, (k, v, col) in enumerate(filas):
            ctk.CTkLabel(detalle, text=k, text_color=C["suave"], font=fuente(12)).grid(row=r, column=0, sticky="w")
            ctk.CTkLabel(detalle, text=v, font=fuente(12, "bold"), text_color=col or C["texto"]).grid(row=r, column=1, sticky="e")
        detalle.grid_columnconfigure(1, weight=1)

        acc = ctk.CTkFrame(t, fg_color="transparent")
        acc.pack(fill="x", padx=12, pady=12)
        texto = "Registrar pago" if es_credito else "Agregar dinero"
        boton(acc, texto, lambda: self._abonar(cuenta), "neutro", height=30, width=120).pack(side="left", padx=2)
        boton(acc, "✎", lambda: DialogoCuenta(self.p, cuenta).mostrar(), "fantasma", height=30, width=36).pack(side="right")
        boton(acc, "🗑", lambda: self._eliminar(cuenta), "fantasma", height=30, width=36).pack(side="right")
        return t

    def _abonar(self, cuenta):
        self.p.ir_a("movimientos")
        self.p.tabs["movimientos"].preparar("Ingreso / pago", cuenta["nombre"])
        self.p.aviso.mostrar(f"Escribe el monto del {'pago a' if cuenta['tipo'] == 'credito' else 'ingreso en'} "
                             f"{cuenta['nombre']} y presiona Enter.", "info")

    def _eliminar(self, cuenta):
        movs, recs = self.store.uso_de_cuenta(cuenta["id"])
        extra = ""
        if movs or recs:
            extra = f"\n\nTambién se borrarán {movs} movimientos y {recs} pagos recurrentes de esta cuenta."
        if confirmar(self.winfo_toplevel(), "Eliminar cuenta", f"¿Eliminar la cuenta «{cuenta['nombre']}»?{extra}"):
            self.store.eliminar_cuenta(cuenta["id"])
            self.p.aviso.mostrar("Cuenta eliminada.", "info")
            self.p.refrescar()


class DialogoCuenta(Dialogo):

    def __init__(self, pantalla, cuenta):
        super().__init__(pantalla.winfo_toplevel(), "Editar cuenta" if cuenta else "Nueva cuenta")
        self.p = pantalla
        self.cuenta = cuenta
        c = cuenta or {}

        self.nombre = self.campo("Nombre", ctk.CTkEntry(self.cuerpo, width=300, placeholder_text="ej. BBVA Azul, Nu, Cartera"))
        self.nombre.insert(0, c.get("nombre", ""))

        tipos = list(TIPOS_CUENTA.values())
        self.tipo = self.campo("Tipo", ctk.CTkSegmentedButton(self.cuerpo, values=tipos, command=lambda _: self._tipo()))
        self.tipo.set(TIPOS_CUENTA[c.get("tipo", "debito")])

        self.saldo = ctk.CTkEntry(self.cuerpo)
        self.l_saldo = self._fila_ocultable("Saldo actual", self.saldo, "Lo que tienes hoy en esta cuenta.")
        self.saldo.insert(0, f"{float(c.get('saldo_inicial', 0) or 0):.2f}")

        self.limite = ctk.CTkEntry(self.cuerpo)
        self.l_limite = self._fila_ocultable("Límite de crédito", self.limite)
        self.limite.insert(0, f"{float(c.get('limite', 0) or 0):.2f}")

        dias = [str(d) for d in range(1, 32)]
        self.corte = ctk.CTkOptionMenu(self.cuerpo, values=dias, width=90)
        self.corte.set(str(c.get("dia_corte", 15)))
        self.l_corte = self._fila_ocultable("Día de corte", self.corte, "Día del mes en que cierra tu estado de cuenta.")
        self.pago = ctk.CTkOptionMenu(self.cuerpo, values=dias, width=90)
        self.pago.set(str(c.get("dia_pago", 5)))
        self.l_pago = self._fila_ocultable("Día límite de pago", self.pago, "Día del mes en que debes pagar.")

        colores = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.color = c.get("color", COLORES_CUENTA[len(pantalla.store.cuentas) % len(COLORES_CUENTA)])
        self._muestras = {}
        for col in COLORES_CUENTA:
            b = ctk.CTkButton(colores, text="", width=28, height=28, corner_radius=14, fg_color=col, hover_color=col,
                              border_color="white", command=lambda col=col: self._elegir_color(col))
            b.pack(side="left", padx=3)
            self._muestras[col] = b
        self.campo("Color", colores)
        self._elegir_color(self.color)
        self._tipo()
        self.nombre.focus_set()

    def _fila_ocultable(self, texto, widget, ayuda=None):
        """Igual que campo() pero recuerda los widgets para poder ocultarlos."""
        fila = self._fila_num()
        etiqueta = ctk.CTkLabel(self.cuerpo, text=texto, text_color=C["suave"], font=fuente(13))
        etiqueta.grid(row=fila, column=0, sticky="nw", pady=7, padx=(0, 14))
        widget.grid(row=fila, column=1, sticky="w" if isinstance(widget, ctk.CTkOptionMenu) else "we", pady=7)
        partes = [etiqueta, widget]
        if ayuda:
            a = ctk.CTkLabel(self.cuerpo, text=ayuda, text_color=C["suave"], font=fuente(11))
            a.grid(row=self._fila_num(), column=1, sticky="w", pady=(0, 4))
            partes.append(a)
        return partes

    def _fila_num(self):
        n = self._fila
        self._fila += 1
        return n

    def _elegir_color(self, col):
        self.color = col
        for c, b in self._muestras.items():
            b.configure(border_width=3 if c == col else 0)

    def _clave_tipo(self):
        return next(k for k, v in TIPOS_CUENTA.items() if v == self.tipo.get())

    def _tipo(self):
        credito = self._clave_tipo() == "credito"
        self.l_saldo[0].configure(text="Deuda actual" if credito else "Saldo actual")
        if len(self.l_saldo) > 2:
            self.l_saldo[2].configure(text="Lo que debes hoy en esta tarjeta." if credito
                                      else "Lo que tienes hoy en esta cuenta.")
        for partes in (self.l_limite, self.l_corte, self.l_pago):
            for w in partes:
                w.grid() if credito else w.grid_remove()

    def aceptar(self):
        nombre = self.nombre.get().strip()
        if not nombre:
            self.fallar("Ponle un nombre a la cuenta.")
            return False
        st = self.p.store
        if not st.nombre_disponible(nombre, self.cuenta["id"] if self.cuenta else None):
            self.fallar("Ya tienes una cuenta con ese nombre.")
            return False
        tipo = self._clave_tipo()
        saldo_txt = self.saldo.get().replace("$", "").replace(",", "").strip() or "0"
        try:
            saldo = round(float(saldo_txt), 2)
        except ValueError:
            self.fallar("El saldo no es un número válido.")
            return False
        datos = {"nombre": nombre, "tipo": tipo, "saldo_inicial": saldo, "color": self.color}
        if tipo == "credito":
            limite_txt = self.limite.get().replace("$", "").replace(",", "").strip() or "0"
            try:
                datos["limite"] = round(float(limite_txt), 2)
            except ValueError:
                self.fallar("El límite no es un número válido.")
                return False
            datos["dia_corte"] = int(self.corte.get())
            datos["dia_pago"] = int(self.pago.get())
        st.guardar_cuenta(datos, self.cuenta["id"] if self.cuenta else None)
        self.p.aviso.mostrar(f"✓ Cuenta «{nombre}» guardada.")
        self.p.refrescar()
        return True


# ======================================================================
# PAGOS RECURRENTES
# ======================================================================

class TabRecurrentes(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(barra, text="Renta, suscripciones, servicios… Los marcados como automáticos se registran solos al llegar su fecha.",
                     text_color=C["suave"]).pack(side="left")
        boton(barra, "＋ Nuevo pago recurrente", self.nuevo, width=200).pack(side="right")

        marco, self.tree = crear_tabla(self, [
            ("nombre", "Pago", 200, "w", True),
            ("monto", "Monto", 110, "e", False),
            ("cat", "Categoría", 130, "w", False),
            ("cuenta", "Cuenta", 140, "w", False),
            ("frec", "Frecuencia", 100, "center", False),
            ("prox", "Próximo pago", 120, "center", False),
            ("estado", "Estado", 150, "w", False),
        ])
        marco.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.editar())
        self.tree.bind("<Delete>", lambda e: self.eliminar())
        self.tree.bind("<Button-3>", self._menu)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._botones())

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.pack(fill="x", pady=(8, 0))
        self.l_total = ctk.CTkLabel(pie, text="", text_color=C["suave"], font=fuente(13))
        self.l_total.pack(side="left")
        boton(pie, "🗑 Eliminar", self.eliminar, "neutro", width=100).pack(side="right")
        self.b_pausa = boton(pie, "⏸ Pausar", self.pausar, "neutro", width=110)
        self.b_pausa.pack(side="right", padx=8)
        boton(pie, "✎ Editar", self.editar, "neutro", width=90).pack(side="right")
        boton(pie, "✓ Registrar pago ahora", self.registrar, "ok", width=190).pack(side="right", padx=8)

    def nuevo(self):
        if not self.store.cuentas:
            self.p.aviso.mostrar("Primero crea una cuenta en la pestaña Cuentas.", "aviso")
            return
        DialogoRecurrente(self.p, None).mostrar()

    def refrescar(self):
        seleccion = self.tree.selection()
        limpiar_tabla(self.tree)
        hoy = date.today()
        orden = sorted(self.store.recurrentes, key=lambda r: (not r.get("activo", True), r["proxima_fecha"]))
        mensual = 0.0
        for i, r in enumerate(orden):
            f = a_fecha(r["proxima_fecha"])
            dias = (f - hoy).days if f else 0
            tags = ["par" if i % 2 == 0 else "impar"]
            if not r.get("activo", True):
                estado = "⏸ Pausado"
                tags.append("apagado")
            else:
                mensual += mensual_estimado(r)
                if dias < 0:
                    estado = f"⚠ Atrasado {-dias} d"
                    tags.append("vencida")
                elif dias == 0:
                    estado = "● Vence hoy"
                    tags.append("urgente")
                elif dias <= 3:
                    estado = f"Vence {texto_dias(dias)}"
                    tags.append("urgente")
                else:
                    estado = f"Vence {texto_dias(dias)}"
                if r.get("automatico"):
                    estado += "  · auto"
            self.tree.insert("", "end", iid=r["id"], tags=tags, values=(
                r["nombre"], moneda(r["monto"]), r["categoria"], self.store.nombre_cuenta(r["cuenta_id"]),
                FRECUENCIAS.get(r["frecuencia"], r["frecuencia"]), f.strftime("%d/%m/%Y") if f else "", estado))
        if seleccion and self.tree.exists(seleccion[0]):
            self.tree.selection_set(seleccion[0])
        n = len(self.store.recurrentes)
        self.l_total.configure(text=f"{n} {'pago' if n == 1 else 'pagos'}   ·   Compromiso mensual estimado: {moneda(mensual)}" if n else
                               "Aún no tienes pagos recurrentes.")
        self._botones()

    def _botones(self):
        r = self.store.recurrente(self._sel()) if self._sel() else None
        self.b_pausa.configure(text="▶ Reanudar" if r and not r.get("activo", True) else "⏸ Pausar")

    def _sel(self):
        s = self.tree.selection()
        return s[0] if s else None

    def _menu(self, e):
        fila = self.tree.identify_row(e.y)
        if fila:
            self.tree.selection_set(fila)
            menu_contextual(self.tree, [("✓ Registrar pago ahora", self.registrar), ("✎ Editar", self.editar),
                                        ("⏸ Pausar / reanudar", self.pausar), None, ("🗑 Eliminar", self.eliminar)
                                        ]).tk_popup(e.x_root, e.y_root)

    def _requiere(self):
        rid = self._sel()
        if not rid:
            self.p.aviso.mostrar("Selecciona un pago de la lista.", "info")
        return rid

    def registrar(self):
        rid = self._requiere()
        if not rid:
            return
        rec = self.store.recurrente(rid)
        if not self.store.cuenta(rec["cuenta_id"]):
            self.p.aviso.mostrar("La cuenta de este pago ya no existe. Edítalo y elige otra.", "error")
            return
        self.store.registrar_recurrente(rid)
        self.p.aviso.mostrar(f"✓ Se registró {rec['nombre']} por {moneda(rec['monto'])}. "
                             f"Siguiente: {fecha_corta(a_fecha(rec['proxima_fecha']))}.")
        self.p.refrescar()

    def editar(self):
        rid = self._requiere()
        if rid:
            DialogoRecurrente(self.p, self.store.recurrente(rid)).mostrar()

    def pausar(self):
        rid = self._requiere()
        if rid:
            self.store.alternar_recurrente(rid)
            self.refrescar()
            self.tree.selection_set(rid)

    def eliminar(self):
        rid = self._requiere()
        if not rid:
            return
        rec = self.store.recurrente(rid)
        if confirmar(self.winfo_toplevel(), "Eliminar pago recurrente",
                     f"¿Eliminar «{rec['nombre']}»? Los gastos ya registrados se conservan."):
            self.store.eliminar_recurrente(rid)
            self.p.aviso.mostrar("Pago recurrente eliminado.", "info")
            self.p.refrescar()


class DialogoRecurrente(Dialogo):

    def __init__(self, pantalla, rec):
        super().__init__(pantalla.winfo_toplevel(), "Editar pago recurrente" if rec else "Nuevo pago recurrente")
        self.p = pantalla
        self.rec = rec
        r = rec or {}
        st = pantalla.store

        self.nombre = self.campo("Nombre", ctk.CTkEntry(self.cuerpo, width=300, placeholder_text="ej. Netflix, Renta, Luz"))
        self.nombre.insert(0, r.get("nombre", ""))
        self.monto = self.campo("Monto", ctk.CTkEntry(self.cuerpo, placeholder_text="$0.00"))
        if r:
            self.monto.insert(0, f"{r['monto']:.2f}")
        self.cat = self.campo("Categoría", ctk.CTkComboBox(self.cuerpo, values=st.categorias))
        self.cat.set(r.get("categoria", "Suscripciones"))
        nombres = pantalla.nombres_cuentas()
        self.cuenta = self.campo("Cuenta", ctk.CTkOptionMenu(self.cuerpo, values=nombres))
        self.cuenta.set(st.nombre_cuenta(r["cuenta_id"]) if r else nombres[0])
        self.frec = self.campo("Frecuencia", ctk.CTkOptionMenu(self.cuerpo, values=list(FRECUENCIAS.values())))
        self.frec.set(FRECUENCIAS[r.get("frecuencia", "mensual")])
        self.fecha = self.campo("Próximo pago", SelectorFecha(self.cuerpo, a_fecha(r.get("proxima_fecha", "")) or date.today()))
        self.auto = ctk.CTkCheckBox(self.cuerpo, text="Registrar el gasto automáticamente al llegar la fecha")
        if r.get("automatico"):
            self.auto.select()
        self.campo("", self.auto)
        self.nombre.focus_set()

    def aceptar(self):
        nombre = self.nombre.get().strip()
        monto = leer_monto(self.monto.get())
        fecha = self.fecha.get()
        cuenta_id = self.p.id_cuenta(self.cuenta.get())
        if not nombre:
            self.fallar("Escribe el nombre del pago.")
            return False
        if monto is None:
            self.fallar("Monto no válido.")
            return False
        if fecha is None or not cuenta_id:
            self.fallar("Revisa la fecha y la cuenta.")
            return False
        frecuencia = next(k for k, v in FRECUENCIAS.items() if v == self.frec.get())
        datos = {"nombre": nombre, "monto": monto, "categoria": self.cat.get(), "cuenta_id": cuenta_id,
                 "frecuencia": frecuencia, "proxima_fecha": fecha, "automatico": bool(self.auto.get())}
        self.p.store.guardar_recurrente(datos, self.rec["id"] if self.rec else None)
        creados = self.p.store.procesar_automaticos()
        msg = f"✓ Pago «{nombre}» guardado."
        if creados:
            msg += f" Se registraron {len(creados)} pagos automáticos pendientes."
        self.p.aviso.mostrar(msg)
        self.p.refrescar()
        return True


# ======================================================================
# RESUMEN POR CATEGORÍA
# ======================================================================

PERIODOS = ["Este mes", "Mes anterior", "Últimos 3 meses", "Este año", "Todo"]


def rango_periodo(nombre, hoy=None):
    hoy = hoy or date.today()
    inicio_mes = hoy.replace(day=1)
    if nombre == "Este mes":
        return inicio_mes, hoy
    if nombre == "Mes anterior":
        fin = inicio_mes - timedelta(days=1)
        return fin.replace(day=1), fin
    if nombre == "Últimos 3 meses":
        return sumar_meses(inicio_mes, -2), hoy
    if nombre == "Este año":
        return date(hoy.year, 1, 1), hoy
    return None, None


class TabResumen(ctk.CTkFrame):

    def __init__(self, padre, pantalla):
        super().__init__(padre, fg_color="transparent")
        self.p = pantalla
        self.store = pantalla.store
        self.filas = []

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(filtros, text="Periodo:", text_color=C["suave"]).pack(side="left", padx=(0, 6))
        self.periodo = ctk.CTkSegmentedButton(filtros, values=PERIODOS, command=lambda _: self.refrescar())
        self.periodo.set("Este mes")
        self.periodo.pack(side="left")
        self.cuenta = ctk.CTkOptionMenu(filtros, values=[TODAS], width=180, command=lambda _: self.refrescar(),
                                        fg_color=C["panel2"], button_color=C["borde"])
        self.cuenta.pack(side="right")

        # Indicadores
        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x", pady=(0, 10))
        self.kpi = {}
        for i, (clave, titulo) in enumerate((("total", "Total gastado"), ("n", "Número de gastos"),
                                              ("dia", "Promedio por día"), ("top", "Categoría principal"))):
            kpis.grid_columnconfigure(i, weight=1, uniform="k")
            caja = ctk.CTkFrame(kpis, fg_color=C["panel"], corner_radius=12)
            caja.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            ctk.CTkLabel(caja, text=titulo, text_color=C["suave"], font=fuente(12)).pack(anchor="w", padx=16, pady=(12, 0))
            valor = ctk.CTkLabel(caja, text="—", font=fuente(22, "bold"))
            valor.pack(anchor="w", padx=16)
            extra = ctk.CTkLabel(caja, text="", text_color=C["suave"], font=fuente(11))
            extra.pack(anchor="w", padx=16, pady=(0, 10))
            self.kpi[clave] = (valor, extra)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)
        cuerpo.grid_columnconfigure(0, weight=2, uniform="c")
        cuerpo.grid_columnconfigure(1, weight=3, uniform="c")
        cuerpo.grid_rowconfigure(0, weight=1)

        marco, self.tree = crear_tabla(cuerpo, [
            ("cat", "Categoría", 150, "w", True),
            ("total", "Total", 110, "e", False),
            ("pct", "%", 60, "e", False),
            ("n", "Gastos", 70, "center", False),
        ])
        marco.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.tree.bind("<Double-1>", self._ver_movimientos)

        grafica = ctk.CTkFrame(cuerpo, fg_color=C["panel"], corner_radius=12)
        grafica.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(grafica, text="Gasto por categoría", font=fuente(14, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        self.canvas = tk.Canvas(grafica, bg=C["panel"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.canvas.bind("<Configure>", lambda e: self._dibujar())

        ctk.CTkLabel(self, text="Doble clic en una categoría para ver sus movimientos.", text_color=C["suave"],
                     font=fuente(12)).pack(anchor="w", pady=(6, 0))

    def refrescar(self):
        nombres = self.p.nombres_cuentas()
        self.cuenta.configure(values=[TODAS] + nombres)
        if self.cuenta.get() not in [TODAS] + nombres:
            self.cuenta.set(TODAS)
        cuenta_id = self.p.id_cuenta(self.cuenta.get())

        desde, hasta = rango_periodo(self.periodo.get())
        self.filas = self.store.resumen_por_categoria(desde, hasta, cuenta_id)
        total = sum(f[1] for f in self.filas)
        cantidad = sum(f[2] for f in self.filas)

        limpiar_tabla(self.tree)
        for i, (cat, t, n) in enumerate(self.filas):
            pct = (t / total * 100) if total else 0
            self.tree.insert("", "end", iid=cat, tags=["par" if i % 2 == 0 else "impar"],
                             values=(cat, moneda(t), f"{pct:.1f}%", n))

        # días del periodo para el promedio
        if desde is None:
            fechas = [a_fecha(m["fecha"]) for m in self.store.movimientos_filtrados(cuenta_id=cuenta_id, tipo="gasto")]
            desde_real = min(fechas) if fechas else date.today()
            dias = (date.today() - desde_real).days + 1
        else:
            dias = (hasta - desde).days + 1

        self.kpi["total"][0].configure(text=moneda(total))
        self.kpi["total"][1].configure(text=self._comparacion(total, cuenta_id))
        self.kpi["n"][0].configure(text=str(cantidad))
        self.kpi["n"][1].configure(text=f"Promedio {moneda(total / cantidad)} por gasto" if cantidad else "")
        self.kpi["dia"][0].configure(text=moneda(total / dias if dias else 0))
        self.kpi["dia"][1].configure(text=f"en {dias} días")
        if self.filas:
            cat, t, _ = self.filas[0]
            self.kpi["top"][0].configure(text=cat)
            self.kpi["top"][1].configure(text=f"{moneda(t)} · {t / total * 100:.0f}% del total")
        else:
            self.kpi["top"][0].configure(text="—")
            self.kpi["top"][1].configure(text="Sin gastos en este periodo")
        self._dibujar()

    def _comparacion(self, total, cuenta_id):
        """Compara 'Este mes' contra el mismo tramo del mes anterior."""
        if self.periodo.get() != "Este mes":
            return ""
        hoy = date.today()
        ini_ant = sumar_meses(hoy.replace(day=1), -1)
        fin_ant = sumar_meses(hoy, -1)
        anterior = self.store.gasto_total(ini_ant, fin_ant, cuenta_id)
        if not anterior:
            return ""
        cambio = (total - anterior) / anterior * 100
        flecha = "▲" if cambio > 0 else "▼"
        return f"{flecha} {abs(cambio):.0f}% vs. mismo periodo del mes pasado"

    def _dibujar(self):
        cv = self.canvas
        cv.delete("all")
        ancho = cv.winfo_width()
        alto = cv.winfo_height()
        if ancho < 50:
            return
        if not self.filas:
            cv.create_text(ancho / 2, alto / 2, text="No hay gastos en este periodo", fill=C["suave"],
                           font=("Segoe UI", 11))
            return

        filas = self.filas[:9]
        if len(self.filas) > 9:
            resto = self.filas[9:]
            filas = filas + [("Otras", sum(f[1] for f in resto), sum(f[2] for f in resto))]
        total = sum(f[1] for f in self.filas)
        maximo = max(f[1] for f in filas) or 1

        etiqueta_w = 120
        valor_w = 140
        barra_max = max(ancho - etiqueta_w - valor_w - 10, 40)
        alto_fila = min(40, max(24, (alto - 10) / len(filas)))
        grosor = alto_fila * 0.55

        for i, (cat, t, _) in enumerate(filas):
            y = 8 + i * alto_fila + alto_fila / 2
            nombre = cat if len(cat) <= 16 else cat[:15] + "…"
            cv.create_text(etiqueta_w - 10, y, text=nombre, anchor="e", fill=C["texto"], font=("Segoe UI", 10))
            largo = max(3, barra_max * t / maximo)
            x0 = etiqueta_w
            # carril de fondo y barra (un solo tono: la longitud es la que comunica)
            cv.create_rectangle(x0, y - grosor / 2, x0 + barra_max, y + grosor / 2, fill="#273548", width=0)
            color = C["acento"] if i == 0 else "#60a5fa"
            cv.create_rectangle(x0, y - grosor / 2, x0 + largo, y + grosor / 2, fill=color, width=0)
            cv.create_text(x0 + barra_max + 10, y, anchor="w", fill=C["texto"], font=("Segoe UI", 10, "bold"),
                           text=f"{moneda(t)}")
            cv.create_text(x0 + barra_max + 10 + 82, y, anchor="w", fill=C["suave"], font=("Segoe UI", 9),
                           text=f"{t / total * 100:.0f}%")

    def _ver_movimientos(self, _e):
        sel = self.tree.selection()
        if not sel:
            return
        periodo = self.periodo.get()
        clave = None
        if periodo in ("Este mes", "Mes anterior"):
            desde, _ = rango_periodo(periodo)
            clave = desde.strftime("%Y-%m")
        tab = self.p.tabs["movimientos"]
        self.p.ir_a("movimientos")
        tab.filtrar_categoria(sel[0], clave)
        tab.refrescar()
