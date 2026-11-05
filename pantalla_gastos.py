# pantalla_gastos.py
# Cuatro pestañas: Movimientos, Cuentas, Recurrentes y Resumen.
from datetime import date
import customtkinter as ctk
import gastos

TIPOS_CUENTA = {"Débito": "debito", "Crédito": "credito", "Efectivo": "efectivo"}
FRECUENCIAS = ["mensual", "semanal", "quincenal", "bimestral", "anual"]


def dinero(monto):
    return "${:,.2f}".format(monto)


def limpiar(marco):
    for hijo in marco.winfo_children():
        hijo.destroy()


class PantallaGastos(ctk.CTkFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.datos = app.gastos
        self.pestanas = ctk.CTkTabview(self, command=self.refrescar_todo)
        self.pestanas.pack(fill="both", expand=True)
        for nombre in ["Movimientos", "Cuentas", "Recurrentes", "Resumen"]:
            self.pestanas.add(nombre)
        self.armar_movimientos(self.pestanas.tab("Movimientos"))
        self.armar_cuentas(self.pestanas.tab("Cuentas"))
        self.armar_recurrentes(self.pestanas.tab("Recurrentes"))
        self.armar_resumen(self.pestanas.tab("Resumen"))
        self.refrescar_todo()

    # ---------- Ayudantes ----------
    def nombres_cuentas(self):
        nombres = []
        for cuenta in self.datos["cuentas"]:
            nombres.append(cuenta["nombre"])
        if not nombres:
            nombres = ["(crea una cuenta)"]
        return nombres

    def cuenta_por_nombre(self, nombre):
        for cuenta in self.datos["cuentas"]:
            if cuenta["nombre"] == nombre:
                return cuenta
        return None

    def numero(self, entrada, mensaje, nombre):
        try:
            return float(entrada.get().replace(",", "").replace("$", ""))
        except ValueError:
            mensaje.configure(text=nombre + " debe ser un número.", text_color="#e5a50a")
            return None

    def fecha(self, entrada, mensaje):
        try:
            return gastos.a_fecha(entrada.get().strip())
        except ValueError:
            mensaje.configure(text="La fecha va así: 2026-11-05", text_color="#e5a50a")
            return None

    def refrescar_todo(self):
        for menu in (self.mov_cuenta, self.rec_cuenta):
            menu.configure(values=self.nombres_cuentas())
            if menu.get() not in self.nombres_cuentas():
                menu.set(self.nombres_cuentas()[0])
        self.mov_categoria.configure(values=self.datos["categorias"])
        self.rec_categoria.configure(values=self.datos["categorias"])
        self.refrescar_movimientos()
        self.refrescar_cuentas()
        self.refrescar_recurrentes()
        self.refrescar_resumen()

    # ---------- Movimientos ----------
    def armar_movimientos(self, tab):
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        self.mov_tipo = ctk.CTkSegmentedButton(form, values=["gasto", "abono"])
        self.mov_tipo.set("gasto")
        self.mov_tipo.grid(row=0, column=0, padx=8, pady=8)
        self.mov_monto = ctk.CTkEntry(form, width=100, placeholder_text="Monto")
        self.mov_monto.grid(row=0, column=1, padx=4)
        self.mov_cuenta = ctk.CTkOptionMenu(form, values=self.nombres_cuentas(), width=140)
        self.mov_cuenta.grid(row=0, column=2, padx=4)
        self.mov_fecha = ctk.CTkEntry(form, width=110)
        self.mov_fecha.insert(0, date.today().strftime(gastos.DIA))
        self.mov_fecha.grid(row=0, column=3, padx=4)
        self.mov_desc = ctk.CTkEntry(form, placeholder_text="Descripción")
        self.mov_desc.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        self.mov_categoria = ctk.CTkComboBox(form, values=self.datos["categorias"], width=140)
        self.mov_categoria.set("Otros")
        self.mov_categoria.grid(row=1, column=2, padx=4, pady=(0, 8))
        ctk.CTkButton(form, text="Agregar", width=100, command=self.agregar_mov).grid(row=1, column=3, padx=4, pady=(0, 8))
        self.mov_msg = ctk.CTkLabel(form, text="")
        self.mov_msg.grid(row=2, column=0, columnspan=4, sticky="w", padx=8)
        self.mov_buscar = ctk.CTkEntry(tab, placeholder_text="Buscar por descripción o categoría")
        self.mov_buscar.pack(fill="x", pady=8)
        self.mov_buscar.bind("<KeyRelease>", lambda e: self.refrescar_movimientos())
        self.mov_lista = ctk.CTkScrollableFrame(tab)
        self.mov_lista.pack(fill="both", expand=True)
        self.mov_lista.grid_columnconfigure(1, weight=1)

    def agregar_mov(self):
        cuenta = self.cuenta_por_nombre(self.mov_cuenta.get())
        if cuenta is None:
            self.mov_msg.configure(text="Primero crea una cuenta.", text_color="#e5a50a")
            return
        monto = self.numero(self.mov_monto, self.mov_msg, "El monto")
        fecha = self.fecha(self.mov_fecha, self.mov_msg)
        if monto is None or fecha is None:
            return
        gastos.agregar_movimiento(self.datos, self.mov_tipo.get(), monto, cuenta["id"], fecha,
                                  self.mov_desc.get().strip(), self.mov_categoria.get())
        self.mov_monto.delete(0, "end")
        self.mov_desc.delete(0, "end")
        self.mov_msg.configure(text="Movimiento agregado.", text_color=("gray10", "gray90"))
        self.refrescar_todo()

    def refrescar_movimientos(self):
        limpiar(self.mov_lista)
        movimientos = gastos.filtrar(self.datos, texto=self.mov_buscar.get())[:200]
        for fila, mov in enumerate(movimientos):
            cuenta = gastos.buscar_cuenta(self.datos, mov["cuentaid"])
            nombre = cuenta["nombre"] if cuenta else "(sin cuenta)"
            ctk.CTkLabel(self.mov_lista, text=mov["fecha"], width=90).grid(row=fila, column=0, padx=4, pady=2)
            texto = (mov["descripcion"] or "(sin descripción)") + "   ·   " + (mov["categoria"] or "ingreso") + "   ·   " + nombre
            ctk.CTkLabel(self.mov_lista, text=texto, anchor="w").grid(row=fila, column=1, sticky="ew")
            signo = "-" if mov["tipo"] == "gasto" else "+"
            color = "#e01b24" if mov["tipo"] == "gasto" else "#2ec27e"
            ctk.CTkLabel(self.mov_lista, text=signo + dinero(mov["monto"]), text_color=color, width=110).grid(row=fila, column=2)
            ctk.CTkButton(self.mov_lista, text="✕", width=30, fg_color="#a33", hover_color="#822",
                          command=lambda m=mov: self.borrar_mov(m)).grid(row=fila, column=3, padx=4)
        if not movimientos:
            ctk.CTkLabel(self.mov_lista, text="Sin movimientos todavía.", text_color="gray").grid(row=0, column=1, pady=20)

    def borrar_mov(self, mov):
        gastos.borrar_movimiento(self.datos, mov["id"])
        self.refrescar_todo()

    # ---------- Cuentas ----------
    def armar_cuentas(self, tab):
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        self.cta_nombre = ctk.CTkEntry(form, placeholder_text="Nombre (ej. BBVA débito)")
        self.cta_nombre.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.cta_tipo = ctk.CTkSegmentedButton(form, values=list(TIPOS_CUENTA))
        self.cta_tipo.set("Débito")
        self.cta_tipo.grid(row=0, column=1, padx=4)
        self.cta_saldo = ctk.CTkEntry(form, width=150, placeholder_text="Saldo inicial / deuda")
        self.cta_saldo.grid(row=0, column=2, padx=4)
        ctk.CTkLabel(form, text="Solo crédito:", text_color="gray").grid(row=1, column=0, sticky="e", padx=8)
        self.cta_limite = ctk.CTkEntry(form, width=110, placeholder_text="Límite")
        self.cta_limite.grid(row=1, column=1, sticky="w", padx=4, pady=(0, 8))
        self.cta_corte = ctk.CTkEntry(form, width=90, placeholder_text="Día corte")
        self.cta_corte.grid(row=1, column=1, sticky="e", padx=4, pady=(0, 8))
        self.cta_pago = ctk.CTkEntry(form, width=90, placeholder_text="Día pago")
        self.cta_pago.grid(row=1, column=2, sticky="w", padx=4, pady=(0, 8))
        ctk.CTkButton(form, text="Crear cuenta", command=self.crear_cuenta).grid(row=0, column=3, padx=8)
        self.cta_msg = ctk.CTkLabel(form, text="")
        self.cta_msg.grid(row=2, column=0, columnspan=4, sticky="w", padx=8)
        form.grid_columnconfigure(0, weight=1)
        self.cta_lista = ctk.CTkScrollableFrame(tab)
        self.cta_lista.pack(fill="both", expand=True, pady=(8, 0))
        self.cta_lista.grid_columnconfigure(0, weight=1)

    def crear_cuenta(self):
        nombre = self.cta_nombre.get().strip()
        if nombre == "" or self.cuenta_por_nombre(nombre) is not None:
            self.cta_msg.configure(text="Escribe un nombre que no exista ya.", text_color="#e5a50a")
            return
        saldo = self.numero(self.cta_saldo, self.cta_msg, "El saldo") if self.cta_saldo.get().strip() else 0
        if saldo is None:
            return
        tipo = TIPOS_CUENTA[self.cta_tipo.get()]
        limite, corte, pago = 0, 1, 1
        if tipo == "credito":
            try:
                limite = float(self.cta_limite.get() or 0)
                corte = int(self.cta_corte.get() or 1)
                pago = int(self.cta_pago.get() or 1)
            except ValueError:
                self.cta_msg.configure(text="Límite y días deben ser números.", text_color="#e5a50a")
                return
        gastos.crear_cuenta(self.datos, nombre, tipo, saldo, limite, corte, pago)
        for entrada in (self.cta_nombre, self.cta_saldo, self.cta_limite, self.cta_corte, self.cta_pago):
            entrada.delete(0, "end")
        self.cta_msg.configure(text="Cuenta creada.", text_color=("gray10", "gray90"))
        self.refrescar_todo()

    def refrescar_cuentas(self):
        limpiar(self.cta_lista)
        hoy = date.today()
        for fila, cuenta in enumerate(self.datos["cuentas"]):
            saldo = gastos.saldo(self.datos, cuenta)
            if cuenta["tipo"] == "credito":
                info = gastos.info_credito(self.datos, cuenta, hoy)
                texto = cuenta["nombre"] + " (crédito)   Deuda " + dinero(info["deuda"])
                if info["disponible"] is not None:
                    texto += "   Disponible " + dinero(info["disponible"])
                texto += "\nCorte " + str(info["proximocorte"]) + "   Pago " + str(info["proximopago"]) + \
                         " (en " + str(info["diaspago"]) + " días)   A pagar " + dinero(info["facturado"])
            else:
                texto = cuenta["nombre"] + " (" + cuenta["tipo"] + ")   Saldo " + dinero(saldo)
            ctk.CTkLabel(self.cta_lista, text=texto, justify="left", anchor="w").grid(row=fila, column=0, sticky="ew", padx=6, pady=6)
            boton = ctk.CTkButton(self.cta_lista, text="Borrar", width=70, fg_color="#a33", hover_color="#822")
            boton.configure(command=lambda c=cuenta, b=boton: self.borrar_cuenta(c, b))
            boton.grid(row=fila, column=1, padx=4)
        if not self.datos["cuentas"]:
            ctk.CTkLabel(self.cta_lista, text="Crea tu primera cuenta arriba.", text_color="gray").grid(row=0, column=0, pady=20)

    def borrar_cuenta(self, cuenta, boton):
        if boton.cget("text") != "¿Seguro?":
            boton.configure(text="¿Seguro?")
            return
        gastos.borrar_cuenta(self.datos, cuenta["id"])
        self.refrescar_todo()

    # ---------- Recurrentes ----------
    def armar_recurrentes(self, tab):
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        form.grid_columnconfigure(0, weight=1)
        self.rec_nombre = ctk.CTkEntry(form, placeholder_text="Nombre (ej. Netflix)")
        self.rec_nombre.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self.rec_monto = ctk.CTkEntry(form, width=100, placeholder_text="Monto")
        self.rec_monto.grid(row=0, column=1, padx=4)
        self.rec_cuenta = ctk.CTkOptionMenu(form, values=self.nombres_cuentas(), width=140)
        self.rec_cuenta.grid(row=0, column=2, padx=4)
        self.rec_frec = ctk.CTkOptionMenu(form, values=FRECUENCIAS, width=120)
        self.rec_frec.grid(row=0, column=3, padx=(4, 8))
        self.rec_fecha = ctk.CTkEntry(form, width=110)
        self.rec_fecha.insert(0, date.today().strftime(gastos.DIA))
        self.rec_fecha.grid(row=1, column=1, padx=4, pady=(0, 8))
        self.rec_categoria = ctk.CTkComboBox(form, values=self.datos["categorias"], width=140)
        self.rec_categoria.set("Suscripciones")
        self.rec_categoria.grid(row=1, column=2, padx=4, pady=(0, 8))
        self.rec_auto = ctk.CTkCheckBox(form, text="Automático")
        self.rec_auto.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        ctk.CTkButton(form, text="Crear", width=120, command=self.crear_rec).grid(row=1, column=3, padx=(4, 8), pady=(0, 8))
        self.rec_msg = ctk.CTkLabel(form, text="")
        self.rec_msg.grid(row=2, column=0, columnspan=4, sticky="w", padx=8)
        self.rec_lista = ctk.CTkScrollableFrame(tab)
        self.rec_lista.pack(fill="both", expand=True, pady=(8, 0))
        self.rec_lista.grid_columnconfigure(0, weight=1)

    def crear_rec(self):
        cuenta = self.cuenta_por_nombre(self.rec_cuenta.get())
        nombre = self.rec_nombre.get().strip()
        if cuenta is None or nombre == "":
            self.rec_msg.configure(text="Pon un nombre y elige una cuenta.", text_color="#e5a50a")
            return
        monto = self.numero(self.rec_monto, self.rec_msg, "El monto")
        fecha = self.fecha(self.rec_fecha, self.rec_msg)
        if monto is None or fecha is None:
            return
        gastos.crear_recurrente(self.datos, nombre, monto, cuenta["id"], self.rec_frec.get(), fecha,
                                self.rec_categoria.get(), bool(self.rec_auto.get()))
        gastos.procesar_automaticos(self.datos, date.today())
        self.rec_nombre.delete(0, "end")
        self.rec_monto.delete(0, "end")
        self.rec_msg.configure(text="Pago recurrente creado.", text_color=("gray10", "gray90"))
        self.refrescar_todo()

    def refrescar_recurrentes(self):
        limpiar(self.rec_lista)
        for fila, rec in enumerate(self.datos["recurrentes"]):
            texto = rec["nombre"] + "   " + dinero(rec["monto"]) + "   " + rec["frecuencia"] + \
                    "   próximo: " + rec["proximafecha"]
            if rec["automatico"]:
                texto += "   (automático)"
            if not rec["activo"]:
                texto += "   — en pausa"
            ctk.CTkLabel(self.rec_lista, text=texto, anchor="w").grid(row=fila, column=0, sticky="ew", padx=6, pady=4)
            ctk.CTkButton(self.rec_lista, text="Registrar hoy", width=110,
                          command=lambda r=rec: self.registrar(r)).grid(row=fila, column=1, padx=2)
            ctk.CTkButton(self.rec_lista, text="Activar" if not rec["activo"] else "Pausar", width=80, fg_color="gray",
                          command=lambda r=rec: self.pausar(r)).grid(row=fila, column=2, padx=2)
            ctk.CTkButton(self.rec_lista, text="✕", width=30, fg_color="#a33", hover_color="#822",
                          command=lambda r=rec: self.borrar_rec(r)).grid(row=fila, column=3, padx=4)
        if not self.datos["recurrentes"]:
            ctk.CTkLabel(self.rec_lista, text="Sin pagos recurrentes.", text_color="gray").grid(row=0, column=0, pady=20)

    def registrar(self, rec):
        gastos.registrar_recurrente(self.datos, rec, date.today())
        self.refrescar_todo()

    def pausar(self, rec):
        gastos.alternar_recurrente(rec)
        self.refrescar_todo()

    def borrar_rec(self, rec):
        gastos.borrar_recurrente(self.datos, rec["id"])
        self.refrescar_todo()

    # ---------- Resumen ----------
    def armar_resumen(self, tab):
        ctk.CTkLabel(tab, text="Gastos de este mes por categoría", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")
        self.res_lista = ctk.CTkFrame(tab)
        self.res_lista.pack(fill="x", pady=8)
        self.res_lista.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tab, text="Próximos pagos (7 días)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(12, 0))
        self.res_pagos = ctk.CTkFrame(tab)
        self.res_pagos.pack(fill="x", pady=8)

    def refrescar_resumen(self):
        limpiar(self.res_lista)
        limpiar(self.res_pagos)
        hoy = date.today()
        filas = gastos.resumen_por_categoria(self.datos, date(hoy.year, hoy.month, 1), hoy)
        total = 0
        for fila in filas:
            total += fila[1]
        for i, fila in enumerate(filas):
            ctk.CTkLabel(self.res_lista, text=fila[0], anchor="w", width=150).grid(row=i, column=0, padx=8, pady=2, sticky="w")
            barra = ctk.CTkProgressBar(self.res_lista)
            barra.set(fila[1] / total if total else 0)
            barra.grid(row=i, column=1, sticky="ew", padx=8)
            ctk.CTkLabel(self.res_lista, text=dinero(fila[1]), width=110).grid(row=i, column=2, padx=8)
        ctk.CTkLabel(self.res_lista, text="Total: " + dinero(total), font=ctk.CTkFont(weight="bold")).grid(
            row=len(filas), column=2, padx=8, pady=6)
        pagos = gastos.proximos_pagos(self.datos, hoy)
        for i, pago in enumerate(pagos):
            dias = (pago[0] - hoy).days
            cuando = "hoy" if dias == 0 else ("atrasado" if dias < 0 else "en " + str(dias) + " días")
            ctk.CTkLabel(self.res_pagos, text=str(pago[0]) + "  " + pago[1] + "  " + dinero(pago[2]) + "  (" + cuando + ")",
                         anchor="w").grid(row=i, column=0, sticky="w", padx=8, pady=2)
        if not pagos:
            ctk.CTkLabel(self.res_pagos, text="Nada en los próximos 7 días.", text_color="gray").grid(row=0, column=0, padx=8, pady=6)
