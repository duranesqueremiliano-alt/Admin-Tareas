# pantalla_gastos.py
# Cuatro pestañas: Movimientos, Cuentas, Recurrentes y Resumen.
from datetime import date, timedelta
from tkinter import filedialog
import customtkinter as ctk
import gastos

TIPOS_CUENTA = {"Débito": "debito", "Crédito": "credito", "Efectivo": "efectivo"}
NOMBRE_TIPO = {"debito": "débito", "credito": "crédito", "efectivo": "efectivo"}
ETIQUETA_SALDO = {"Débito": "Saldo actual", "Crédito": "Deuda actual", "Efectivo": "Dinero que tienes"}
FRECUENCIAS = ["mensual", "semanal", "quincenal", "bimestral", "anual"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
PERIODOS = ["Todo", "Este mes", "Mes pasado"]
TODAS = "Todas las cuentas"
ROJO, VERDE, AMARILLO, AZUL = "#e01b24", "#2ec27e", "#e5a50a", "#3584e4"
NORMAL = ("gray10", "gray90")


def dinero(monto):
    if monto < 0:
        return "-${:,.2f}".format(-monto)
    return "${:,.2f}".format(monto)


def limpiar(marco):
    for hijo in marco.winfo_children():
        hijo.destroy()


def nombre_mes(fecha):
    return MESES[fecha.month - 1] + " " + str(fecha.year)


class PantallaGastos(ctk.CTkFrame):
    def __init__(self, padre, app):
        super().__init__(padre, fg_color="transparent")
        self.app = app
        self.datos = app.gastos
        self.editando_mov = None
        self.editando_cta = None
        self.mes_resumen = gastos.inicio_mes(date.today())
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
    def nombres_cuentas(self, solo=None):
        nombres = []
        for cuenta in self.datos["cuentas"]:
            if solo is None or cuenta["tipo"] in solo:
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
            return float(entrada.get().replace(",", "").replace("$", "").strip())
        except ValueError:
            mensaje.configure(text=nombre + " debe ser un número.", text_color=AMARILLO)
            return None

    def fecha(self, entrada, mensaje):
        try:
            return gastos.a_fecha(entrada.get().strip())
        except ValueError:
            mensaje.configure(text="La fecha va así: 2026-11-05", text_color=AMARILLO)
            return None

    def poner_texto(self, entrada, texto):
        entrada.delete(0, "end")
        entrada.insert(0, texto)

    def ajustar_menu(self, menu, valores):
        menu.configure(values=valores)
        if menu.get() not in valores:
            menu.set(valores[0])

    def refrescar_todo(self):
        todas = self.nombres_cuentas()
        for menu in (self.mov_cuenta, self.mov_destino, self.rec_cuenta):
            self.ajustar_menu(menu, todas)
        self.ajustar_menu(self.filtro_cuenta, [TODAS] + [c["nombre"] for c in self.datos["cuentas"]])
        for combo in (self.mov_categoria, self.rec_categoria, self.pre_categoria):
            combo.configure(values=self.datos["categorias"])
        self.refrescar_movimientos()
        self.refrescar_cuentas()
        self.refrescar_recurrentes()
        self.refrescar_resumen()

    # ================= Movimientos =================
    def armar_movimientos(self, tab):
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        form.grid_columnconfigure(5, weight=1)
        self.mov_tipo = ctk.CTkSegmentedButton(form, values=["gasto", "abono", "transferencia"],
                                               command=self.cambiar_tipo_mov)
        self.mov_tipo.set("gasto")
        self.mov_tipo.grid(row=0, column=0, columnspan=2, padx=8, pady=8, sticky="w")
        self.mov_monto = ctk.CTkEntry(form, width=100, placeholder_text="Monto")
        self.mov_monto.grid(row=0, column=2, padx=4)
        self.mov_de = ctk.CTkLabel(form, text="Cuenta:")
        self.mov_de.grid(row=0, column=3, padx=(8, 2))
        self.mov_cuenta = ctk.CTkOptionMenu(form, values=self.nombres_cuentas(), width=140)
        self.mov_cuenta.grid(row=0, column=4, padx=4)
        self.mov_hacia = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(self.mov_hacia, text="a:").pack(side="left", padx=(4, 4))
        self.mov_destino = ctk.CTkOptionMenu(self.mov_hacia, values=self.nombres_cuentas(), width=140)
        self.mov_destino.pack(side="left")
        self.mov_desc = ctk.CTkEntry(form, placeholder_text="Descripción (ej. Tacos)")
        self.mov_desc.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        self.mov_desc.bind("<FocusOut>", lambda e: self.sugerir_categoria())
        self.mov_categoria = ctk.CTkComboBox(form, values=self.datos["categorias"], width=140)
        self.mov_categoria.set("Otros")
        self.mov_categoria.grid(row=1, column=4, padx=4, pady=(0, 8))
        fechas = ctk.CTkFrame(form, fg_color="transparent")
        fechas.grid(row=1, column=5, sticky="w", padx=4, pady=(0, 8))
        self.mov_fecha = ctk.CTkEntry(fechas, width=105)
        self.mov_fecha.insert(0, date.today().strftime(gastos.DIA))
        self.mov_fecha.pack(side="left")
        ctk.CTkButton(fechas, text="Hoy", width=44, fg_color="gray",
                      command=lambda: self.poner_texto(self.mov_fecha, date.today().strftime(gastos.DIA))).pack(side="left", padx=(4, 0))
        ctk.CTkButton(fechas, text="Ayer", width=44, fg_color="gray",
                      command=lambda: self.poner_texto(self.mov_fecha, (date.today() - timedelta(days=1)).strftime(gastos.DIA))).pack(side="left", padx=(4, 0))
        self.mov_boton = ctk.CTkButton(form, text="Agregar", width=100, command=self.agregar_mov)
        self.mov_boton.grid(row=0, column=6, padx=8)
        self.mov_cancelar = ctk.CTkButton(form, text="Cancelar", width=100, fg_color="gray", command=self.cancelar_mov)
        self.mov_msg = ctk.CTkLabel(form, text="Consejo: Enter agrega el movimiento.", text_color="gray")
        self.mov_msg.grid(row=2, column=0, columnspan=7, sticky="w", padx=8)
        for entrada in (self.mov_monto, self.mov_desc, self.mov_fecha):
            entrada.bind("<Return>", lambda e: self.agregar_mov())

        filtros = ctk.CTkFrame(tab, fg_color="transparent")
        filtros.pack(fill="x", pady=8)
        self.mov_buscar = ctk.CTkEntry(filtros, placeholder_text="Buscar por descripción o categoría")
        self.mov_buscar.pack(side="left", fill="x", expand=True)
        self.mov_buscar.bind("<KeyRelease>", lambda e: self.refrescar_movimientos())
        self.filtro_cuenta = ctk.CTkOptionMenu(filtros, values=[TODAS], width=150,
                                               command=lambda v: self.refrescar_movimientos())
        self.filtro_cuenta.pack(side="left", padx=4)
        self.filtro_periodo = ctk.CTkOptionMenu(filtros, values=PERIODOS, width=110,
                                                command=lambda v: self.refrescar_movimientos())
        self.filtro_periodo.pack(side="left", padx=4)
        ctk.CTkButton(filtros, text="Exportar CSV", width=110, fg_color="gray", command=self.exportar).pack(side="left", padx=(4, 0))
        self.mov_total = ctk.CTkLabel(tab, text="", anchor="w", text_color="gray")
        self.mov_total.pack(fill="x")
        self.mov_lista = ctk.CTkScrollableFrame(tab)
        self.mov_lista.pack(fill="both", expand=True)
        self.mov_lista.grid_columnconfigure(1, weight=1)

    def cambiar_tipo_mov(self, tipo):
        # Gasto: categoría. Abono: nada extra. Transferencia: cuenta destino.
        if tipo == "transferencia":
            self.mov_de.configure(text="De:")
            self.mov_hacia.grid(row=0, column=5, sticky="w")
        else:
            self.mov_de.configure(text="Cuenta:")
            self.mov_hacia.grid_remove()
        if tipo == "gasto":
            self.mov_categoria.grid()
        else:
            self.mov_categoria.grid_remove()

    def sugerir_categoria(self):
        if self.mov_tipo.get() != "gasto" or self.mov_categoria.get() not in ("", "Otros"):
            return
        sugerida = gastos.categoria_sugerida(self.datos, self.mov_desc.get())
        if sugerida:
            self.mov_categoria.set(sugerida)

    def agregar_mov(self):
        tipo = self.mov_tipo.get()
        cuenta = self.cuenta_por_nombre(self.mov_cuenta.get())
        if cuenta is None:
            self.mov_msg.configure(text="Primero crea una cuenta.", text_color=AMARILLO)
            return
        monto = self.numero(self.mov_monto, self.mov_msg, "El monto")
        fecha = self.fecha(self.mov_fecha, self.mov_msg)
        if monto is None or fecha is None:
            return
        if monto <= 0:
            self.mov_msg.configure(text="El monto debe ser mayor que 0.", text_color=AMARILLO)
            return
        destinoid = None
        if tipo == "transferencia":
            destino = self.cuenta_por_nombre(self.mov_destino.get())
            if destino is None or destino["id"] == cuenta["id"]:
                self.mov_msg.configure(text="Elige dos cuentas diferentes.", text_color=AMARILLO)
                return
            destinoid = destino["id"]
        self.sugerir_categoria()
        descripcion = self.mov_desc.get().strip()
        if tipo == "transferencia" and descripcion == "":
            descripcion = "Transferencia"
        if self.editando_mov is not None:
            gastos.llenar_movimiento(self.datos, self.editando_mov, tipo, monto, cuenta["id"], fecha,
                                     descripcion, self.mov_categoria.get(), destinoid)
            mov = self.editando_mov
            texto = "Movimiento actualizado."
        else:
            mov = gastos.agregar_movimiento(self.datos, tipo, monto, cuenta["id"], fecha, descripcion,
                                            self.mov_categoria.get(), destinoid=destinoid)
            texto = "Movimiento agregado."
        self.cancelar_mov()
        color = NORMAL
        if tipo == "gasto":
            aviso = gastos.aviso_presupuesto(self.datos, mov["categoria"], fecha)
            if aviso:
                texto += "  " + aviso
                color = AMARILLO
        self.mov_msg.configure(text=texto, text_color=color)
        self.refrescar_todo()
        self.mov_monto.focus_set()

    def cancelar_mov(self):
        # Limpia el formulario pero recuerda la última cuenta y categoría.
        self.editando_mov = None
        self.mov_monto.delete(0, "end")
        self.mov_desc.delete(0, "end")
        self.mov_boton.configure(text="Agregar")
        self.mov_cancelar.grid_remove()
        self.mov_msg.configure(text="")

    def editar_mov(self, mov):
        self.pestanas.set("Movimientos")
        self.editando_mov = mov
        self.mov_tipo.set(mov["tipo"])
        self.cambiar_tipo_mov(mov["tipo"])
        self.poner_texto(self.mov_monto, str(mov["monto"]))
        self.poner_texto(self.mov_desc, mov["descripcion"])
        self.poner_texto(self.mov_fecha, mov["fecha"])
        cuenta = gastos.buscar_cuenta(self.datos, mov["cuentaid"])
        if cuenta:
            self.mov_cuenta.set(cuenta["nombre"])
        destino = gastos.buscar_cuenta(self.datos, mov.get("destinoid"))
        if destino:
            self.mov_destino.set(destino["nombre"])
        if mov["categoria"]:
            self.mov_categoria.set(mov["categoria"])
        self.mov_boton.configure(text="Guardar")
        self.mov_cancelar.grid(row=1, column=6, padx=8, pady=(0, 8))
        self.mov_msg.configure(text="Editando: cambia lo que quieras y pulsa Guardar.", text_color=AZUL)

    def repetir_mov(self, mov):
        # Copia el movimiento con la fecha de hoy (útil para gastos de todos los días).
        gastos.agregar_movimiento(self.datos, mov["tipo"], mov["monto"], mov["cuentaid"], date.today(),
                                  mov["descripcion"], mov["categoria"], destinoid=mov.get("destinoid"))
        self.mov_msg.configure(text="Repetido con fecha de hoy.", text_color=NORMAL)
        self.refrescar_todo()

    def periodo_elegido(self):
        hoy = date.today()
        if self.filtro_periodo.get() == "Este mes":
            return gastos.inicio_mes(hoy), gastos.fin_mes(hoy)
        if self.filtro_periodo.get() == "Mes pasado":
            pasado = gastos.inicio_mes(hoy) - timedelta(days=1)
            return gastos.inicio_mes(pasado), gastos.fin_mes(pasado)
        return None, None

    def refrescar_movimientos(self):
        limpiar(self.mov_lista)
        desde, hasta = self.periodo_elegido()
        filtro = self.cuenta_por_nombre(self.filtro_cuenta.get())
        cuentaid = filtro["id"] if filtro else None
        movimientos = gastos.filtrar(self.datos, desde, hasta, cuentaid=cuentaid, texto=self.mov_buscar.get())
        gastado = 0
        ingresado = 0
        for mov in movimientos:
            if mov["tipo"] == "gasto":
                gastado += mov["monto"]
            elif mov["tipo"] == "abono":
                ingresado += mov["monto"]
        self.mov_total.configure(text=str(len(movimientos)) + " movimientos   ·   gastos " + dinero(gastado) +
                                 "   ·   ingresos " + dinero(ingresado) + "   ·   clic en uno para editarlo")
        for fila, mov in enumerate(movimientos[:200]):
            cuenta = gastos.buscar_cuenta(self.datos, mov["cuentaid"])
            nombre = cuenta["nombre"] if cuenta else "(sin cuenta)"
            if mov["tipo"] == "transferencia":
                destino = gastos.buscar_cuenta(self.datos, mov.get("destinoid"))
                texto = mov["descripcion"] + "   ·   " + nombre + " → " + (destino["nombre"] if destino else "?")
                signo, color = "⇄", AZUL
            else:
                texto = (mov["descripcion"] or "(sin descripción)") + "   ·   " + (mov["categoria"] or "ingreso") + "   ·   " + nombre
                signo, color = ("-", ROJO) if mov["tipo"] == "gasto" else ("+", VERDE)
            if self.editando_mov is mov:
                texto = "✎ " + texto
            etiquetas = [
                ctk.CTkLabel(self.mov_lista, text=mov["fecha"], width=90),
                ctk.CTkLabel(self.mov_lista, text=texto, anchor="w", cursor="hand2"),
                ctk.CTkLabel(self.mov_lista, text=signo + dinero(mov["monto"]), text_color=color, width=110),
            ]
            for columna, etiqueta in enumerate(etiquetas):
                etiqueta.grid(row=fila, column=columna, padx=4, pady=2, sticky="ew" if columna == 1 else "")
                etiqueta.bind("<Button-1>", lambda e, m=mov: self.editar_mov(m))
            ctk.CTkButton(self.mov_lista, text="↻", width=30, fg_color="gray",
                          command=lambda m=mov: self.repetir_mov(m)).grid(row=fila, column=3, padx=2)
            ctk.CTkButton(self.mov_lista, text="✕", width=30, fg_color="#a33", hover_color="#822",
                          command=lambda m=mov: self.borrar_mov(m)).grid(row=fila, column=4, padx=4)
        if not movimientos:
            ctk.CTkLabel(self.mov_lista, text="Sin movimientos con estos filtros.", text_color="gray").grid(row=0, column=1, pady=20)

    def borrar_mov(self, mov):
        if self.editando_mov is mov:
            self.cancelar_mov()
        gastos.borrar_movimiento(self.datos, mov["id"])
        self.refrescar_todo()

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="movimientos.csv",
                                            filetypes=[("CSV (Excel)", "*.csv")])
        if not ruta:
            return
        cantidad = gastos.exportar_csv(self.datos, ruta)
        self.mov_msg.configure(text="Exportados " + str(cantidad) + " movimientos.", text_color=NORMAL)

    # ================= Cuentas =================
    def armar_cuentas(self, tab):
        self.cta_totales = ctk.CTkLabel(tab, text="", anchor="w", font=ctk.CTkFont(weight="bold"))
        self.cta_totales.pack(fill="x", pady=(0, 6))
        form = ctk.CTkFrame(tab)
        form.pack(fill="x")
        form.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(form, text="Nombre", text_color="gray").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 0))
        ctk.CTkLabel(form, text="Tipo", text_color="gray").grid(row=0, column=1, sticky="w", padx=4, pady=(6, 0))
        self.cta_saldo_txt = ctk.CTkLabel(form, text="Saldo actual", text_color="gray")
        self.cta_saldo_txt.grid(row=0, column=2, sticky="w", padx=4, pady=(6, 0))
        self.cta_nombre = ctk.CTkEntry(form, placeholder_text="ej. BBVA débito")
        self.cta_nombre.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self.cta_tipo = ctk.CTkSegmentedButton(form, values=list(TIPOS_CUENTA), command=self.cambiar_tipo_cuenta)
        self.cta_tipo.set("Débito")
        self.cta_tipo.grid(row=1, column=1, padx=4, pady=(0, 8))
        self.cta_saldo = ctk.CTkEntry(form, width=130, placeholder_text="0")
        self.cta_saldo.grid(row=1, column=2, padx=4, pady=(0, 8))
        self.cta_boton = ctk.CTkButton(form, text="Crear cuenta", width=130, command=self.guardar_cuenta)
        self.cta_boton.grid(row=1, column=3, padx=8, pady=(0, 8))
        self.cta_cancelar = ctk.CTkButton(form, text="Cancelar", width=130, fg_color="gray", command=self.cancelar_cuenta)

        # Solo para crédito: se muestra u oculta según el tipo elegido.
        self.cta_credito = ctk.CTkFrame(form, fg_color="transparent")
        campos = [("Límite de crédito", "ej. 8000", 130), ("Día de corte", "1 a 31", 90), ("Día de pago", "1 a 31", 90)]
        self.cta_extra = []
        for columna, (titulo, ejemplo, ancho) in enumerate(campos):
            ctk.CTkLabel(self.cta_credito, text=titulo, text_color="gray").grid(row=0, column=columna, sticky="w", padx=(8 if columna == 0 else 4, 4))
            entrada = ctk.CTkEntry(self.cta_credito, width=ancho, placeholder_text=ejemplo)
            entrada.grid(row=1, column=columna, sticky="w", padx=(8 if columna == 0 else 4, 4), pady=(0, 8))
            self.cta_extra.append(entrada)
        self.cta_limite, self.cta_corte, self.cta_pago = self.cta_extra
        ctk.CTkLabel(self.cta_credito, text="El corte cierra el periodo; el pago es la fecha límite para pagar sin intereses.",
                     text_color="gray").grid(row=1, column=3, sticky="w", padx=8, pady=(0, 8))
        self.cta_msg = ctk.CTkLabel(form, text="")
        self.cta_msg.grid(row=3, column=0, columnspan=4, sticky="w", padx=8)
        self.cta_lista = ctk.CTkScrollableFrame(tab)
        self.cta_lista.pack(fill="both", expand=True, pady=(8, 0))
        self.cta_lista.grid_columnconfigure(0, weight=1)
        self.cambiar_tipo_cuenta("Débito")

    def cambiar_tipo_cuenta(self, tipo):
        self.cta_saldo_txt.configure(text=ETIQUETA_SALDO[tipo])
        if tipo == "Crédito":
            self.cta_credito.grid(row=2, column=0, columnspan=4, sticky="ew")
        else:
            self.cta_credito.grid_remove()

    def guardar_cuenta(self):
        nombre = self.cta_nombre.get().strip()
        otra = self.cuenta_por_nombre(nombre)
        if nombre == "" or (otra is not None and otra is not self.editando_cta):
            self.cta_msg.configure(text="Escribe un nombre que no exista ya.", text_color=AMARILLO)
            return
        saldo = self.numero(self.cta_saldo, self.cta_msg, "El saldo") if self.cta_saldo.get().strip() else 0
        if saldo is None:
            return
        tipo = TIPOS_CUENTA[self.cta_tipo.get()]
        limite, corte, pago = 0, 1, 1
        if tipo == "credito":
            try:
                limite = float(self.cta_limite.get().replace(",", "") or 0)
                corte = int(self.cta_corte.get() or 1)
                pago = int(self.cta_pago.get() or 1)
            except ValueError:
                self.cta_msg.configure(text="Límite y días deben ser números.", text_color=AMARILLO)
                return
            if not (1 <= corte <= 31 and 1 <= pago <= 31):
                self.cta_msg.configure(text="Los días van del 1 al 31.", text_color=AMARILLO)
                return
        if self.editando_cta is not None:
            gastos.actualizar_cuenta(self.editando_cta, nombre, tipo, saldo, limite, corte, pago)
            texto = "Cuenta actualizada."
        else:
            gastos.crear_cuenta(self.datos, nombre, tipo, saldo, limite, corte, pago)
            texto = "Cuenta creada."
        self.cancelar_cuenta()
        self.cta_msg.configure(text=texto, text_color=NORMAL)
        self.refrescar_todo()

    def cancelar_cuenta(self):
        self.editando_cta = None
        for entrada in [self.cta_nombre, self.cta_saldo] + self.cta_extra:
            entrada.delete(0, "end")
        self.cta_boton.configure(text="Crear cuenta")
        self.cta_cancelar.grid_remove()
        self.cta_msg.configure(text="")

    def editar_cuenta(self, cuenta):
        self.cancelar_cuenta()
        self.editando_cta = cuenta
        tipo = "Débito"
        for nombre in TIPOS_CUENTA:
            if TIPOS_CUENTA[nombre] == cuenta["tipo"]:
                tipo = nombre
        self.cta_tipo.set(tipo)
        self.cambiar_tipo_cuenta(tipo)
        self.cta_nombre.insert(0, cuenta["nombre"])
        self.cta_saldo.insert(0, str(cuenta["saldoinicial"]))
        if cuenta["tipo"] == "credito":
            self.cta_limite.insert(0, str(cuenta["limite"]))
            self.cta_corte.insert(0, str(cuenta["diacorte"]))
            self.cta_pago.insert(0, str(cuenta["diapago"]))
        self.cta_boton.configure(text="Guardar cambios")
        self.cta_cancelar.grid(row=0, column=3, padx=8, pady=(6, 0))
        self.cta_msg.configure(text="Editando " + cuenta["nombre"] + ". El saldo/deuda es el que tenía al crearla.", text_color=AZUL)

    def pagar_tarjeta(self, cuenta):
        # Prepara una transferencia desde débito/efectivo hacia la tarjeta.
        info = gastos.info_credito(self.datos, cuenta, date.today())
        self.cancelar_mov()
        self.pestanas.set("Movimientos")
        self.mov_tipo.set("transferencia")
        self.cambiar_tipo_mov("transferencia")
        origenes = self.nombres_cuentas(solo=("debito", "efectivo"))
        self.mov_cuenta.set(origenes[0])
        self.mov_destino.set(cuenta["nombre"])
        monto = info["facturado"] if info["facturado"] > 0 else max(0, info["deuda"])
        self.poner_texto(self.mov_monto, "{:.2f}".format(monto))
        self.poner_texto(self.mov_desc, "Pago tarjeta " + cuenta["nombre"])
        self.poner_texto(self.mov_fecha, date.today().strftime(gastos.DIA))
        self.mov_msg.configure(text="Revisa el monto y la cuenta de origen, luego pulsa Agregar.", text_color=AZUL)

    def refrescar_cuentas(self):
        limpiar(self.cta_lista)
        self.cta_totales.configure(text="Tienes " + dinero(gastos.total_disponible(self.datos)) +
                                   " en débito y efectivo   ·   Debes " + dinero(gastos.total_deuda(self.datos)) + " en tarjetas")
        hoy = date.today()
        for fila, cuenta in enumerate(self.datos["cuentas"]):
            caja = ctk.CTkFrame(self.cta_lista)
            caja.grid(row=fila, column=0, sticky="ew", padx=4, pady=4)
            caja.grid_columnconfigure(0, weight=1)
            titulo = cuenta["nombre"] + "  ·  " + NOMBRE_TIPO.get(cuenta["tipo"], cuenta["tipo"])
            ctk.CTkLabel(caja, text=titulo, anchor="w", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
            botones = ctk.CTkFrame(caja, fg_color="transparent")
            botones.grid(row=0, column=1, rowspan=3, padx=8)
            if cuenta["tipo"] == "credito":
                info = gastos.info_credito(self.datos, cuenta, hoy)
                linea = "Deuda " + dinero(info["deuda"])
                if info["disponible"] is not None:
                    linea += "   ·   Límite " + dinero(cuenta["limite"]) + "   ·   Disponible " + dinero(info["disponible"])
                ctk.CTkLabel(caja, text=linea, anchor="w").grid(row=1, column=0, sticky="w", padx=10)
                fechas = "Próximo corte " + str(info["proximocorte"]) + "   ·   "
                if info["facturado"] > 0:
                    fechas += "Pagar " + dinero(info["facturado"]) + " antes del " + str(info["proximopago"]) + \
                              " (en " + str(info["diaspago"]) + " días)"
                else:
                    fechas += "Nada pendiente del corte pasado"
                ctk.CTkLabel(caja, text=fechas, anchor="w", text_color="gray").grid(row=2, column=0, sticky="w", padx=10)
                if info["uso"] is not None:
                    uso = min(info["uso"], 1)
                    color = VERDE if uso < 0.3 else (AMARILLO if uso < 0.7 else ROJO)
                    barra = ctk.CTkProgressBar(caja, progress_color=color)
                    barra.set(uso)
                    barra.grid(row=3, column=0, sticky="ew", padx=10, pady=(4, 2))
                    ctk.CTkLabel(caja, text="Usas " + str(round(info["uso"] * 100)) + " % de tu límite (menos de 30 % es lo sano)",
                                 text_color="gray", anchor="w").grid(row=4, column=0, sticky="w", padx=10, pady=(0, 6))
                ctk.CTkButton(botones, text="Pagar", width=70, command=lambda c=cuenta: self.pagar_tarjeta(c)).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(caja, text="Saldo " + dinero(gastos.saldo(self.datos, cuenta)), anchor="w").grid(
                    row=1, column=0, sticky="w", padx=10, pady=(0, 6))
            ctk.CTkButton(botones, text="Editar", width=70, fg_color="gray",
                          command=lambda c=cuenta: self.editar_cuenta(c)).pack(side="left", padx=2)
            boton = ctk.CTkButton(botones, text="Borrar", width=70, fg_color="#a33", hover_color="#822")
            boton.configure(command=lambda c=cuenta, b=boton: self.borrar_cuenta(c, b))
            boton.pack(side="left", padx=2)
        if not self.datos["cuentas"]:
            ctk.CTkLabel(self.cta_lista, text="Crea tu primera cuenta arriba.", text_color="gray").grid(row=0, column=0, pady=20)

    def borrar_cuenta(self, cuenta, boton):
        if boton.cget("text") != "¿Seguro?":
            boton.configure(text="¿Seguro?")
            return
        if self.editando_cta is cuenta:
            self.cancelar_cuenta()
        gastos.borrar_cuenta(self.datos, cuenta["id"])
        self.refrescar_todo()

    # ================= Recurrentes =================
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
        self.rec_auto = ctk.CTkCheckBox(form, text="Automático (se registra solo en su fecha)")
        self.rec_auto.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        ctk.CTkButton(form, text="Crear", width=120, command=self.crear_rec).grid(row=1, column=3, padx=(4, 8), pady=(0, 8))
        self.rec_msg = ctk.CTkLabel(form, text="")
        self.rec_msg.grid(row=2, column=0, columnspan=4, sticky="w", padx=8)
        self.rec_total = ctk.CTkLabel(tab, text="", anchor="w", text_color="gray")
        self.rec_total.pack(fill="x", pady=(8, 0))
        self.rec_lista = ctk.CTkScrollableFrame(tab)
        self.rec_lista.pack(fill="both", expand=True, pady=(4, 0))
        self.rec_lista.grid_columnconfigure(0, weight=1)

    def crear_rec(self):
        cuenta = self.cuenta_por_nombre(self.rec_cuenta.get())
        nombre = self.rec_nombre.get().strip()
        if cuenta is None or nombre == "":
            self.rec_msg.configure(text="Pon un nombre y elige una cuenta.", text_color=AMARILLO)
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
        self.rec_msg.configure(text="Pago recurrente creado.", text_color=NORMAL)
        self.refrescar_todo()

    def costo_mensual(self, rec):
        veces = {"mensual": 1, "semanal": 52 / 12, "quincenal": 26 / 12, "bimestral": 0.5, "anual": 1 / 12}
        return rec["monto"] * veces.get(rec["frecuencia"], 1)

    def refrescar_recurrentes(self):
        limpiar(self.rec_lista)
        total = 0
        for rec in self.datos["recurrentes"]:
            if rec["activo"]:
                total += self.costo_mensual(rec)
        self.rec_total.configure(text="Tus pagos activos cuestan unos " + dinero(total) + " al mes (" +
                                 dinero(total * 12) + " al año).")
        for fila, rec in enumerate(self.datos["recurrentes"]):
            texto = rec["nombre"] + "   " + dinero(rec["monto"]) + "   " + rec["frecuencia"] + \
                    "   próximo: " + rec["proximafecha"]
            if rec["automatico"]:
                texto += "   (automático)"
            if not rec["activo"]:
                texto += "   — en pausa"
            ctk.CTkLabel(self.rec_lista, text=texto, anchor="w",
                         text_color=NORMAL if rec["activo"] else "gray").grid(row=fila, column=0, sticky="ew", padx=6, pady=4)
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

    # ================= Resumen =================
    def armar_resumen(self, tab):
        zona = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        zona.pack(fill="both", expand=True)
        navegar = ctk.CTkFrame(zona, fg_color="transparent")
        navegar.pack(fill="x")
        ctk.CTkButton(navegar, text="◀", width=36, command=lambda: self.mover_mes(-1)).pack(side="left")
        self.res_mes = ctk.CTkLabel(navegar, text="", width=170, font=ctk.CTkFont(size=16, weight="bold"))
        self.res_mes.pack(side="left", padx=6)
        ctk.CTkButton(navegar, text="▶", width=36, command=lambda: self.mover_mes(1)).pack(side="left")
        ctk.CTkButton(navegar, text="Este mes", width=80, fg_color="gray", command=lambda: self.mover_mes(0)).pack(side="left", padx=8)
        self.res_totales = ctk.CTkLabel(zona, text="", anchor="w", justify="left")
        self.res_totales.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(zona, text="Gastos por categoría", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(12, 0))
        self.res_lista = ctk.CTkFrame(zona)
        self.res_lista.pack(fill="x", pady=8)
        self.res_lista.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(zona, text="Presupuestos del mes", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(12, 0))
        forma = ctk.CTkFrame(zona, fg_color="transparent")
        forma.pack(fill="x", pady=(4, 0))
        self.pre_categoria = ctk.CTkComboBox(forma, values=self.datos["categorias"], width=160)
        self.pre_categoria.set("Comida")
        self.pre_categoria.pack(side="left")
        self.pre_monto = ctk.CTkEntry(forma, width=110, placeholder_text="Límite al mes")
        self.pre_monto.pack(side="left", padx=4)
        self.pre_monto.bind("<Return>", lambda e: self.fijar_presupuesto())
        ctk.CTkButton(forma, text="Fijar", width=70, command=self.fijar_presupuesto).pack(side="left", padx=4)
        self.pre_msg = ctk.CTkLabel(forma, text="0 quita el presupuesto.", text_color="gray")
        self.pre_msg.pack(side="left", padx=8)
        self.res_presupuestos = ctk.CTkFrame(zona)
        self.res_presupuestos.pack(fill="x", pady=8)
        self.res_presupuestos.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(zona, text="Próximos pagos (7 días)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(12, 0))
        self.res_pagos = ctk.CTkFrame(zona)
        self.res_pagos.pack(fill="x", pady=8)

    def mover_mes(self, paso):
        if paso == 0:
            self.mes_resumen = gastos.inicio_mes(date.today())
        else:
            self.mes_resumen = gastos.sumar_meses(self.mes_resumen, paso, 1)
        self.refrescar_resumen()

    def fijar_presupuesto(self):
        monto = self.numero(self.pre_monto, self.pre_msg, "El límite")
        if monto is None:
            return
        categoria = gastos.fijar_presupuesto(self.datos, self.pre_categoria.get(), monto)
        self.pre_monto.delete(0, "end")
        texto = "Presupuesto de " + categoria + " quitado." if monto <= 0 else "Presupuesto de " + categoria + " guardado."
        self.pre_msg.configure(text=texto, text_color=NORMAL)
        self.refrescar_todo()

    def refrescar_resumen(self):
        for marco in (self.res_lista, self.res_presupuestos, self.res_pagos):
            limpiar(marco)
        mes = self.mes_resumen
        self.res_mes.configure(text=nombre_mes(mes))
        gastado, ingresado = gastos.totales_mes(self.datos, mes)
        anterior = gastos.sumar_meses(mes, -1, 1)
        gastado_antes = gastos.totales_mes(self.datos, anterior)[0]
        texto = "Gastaste " + dinero(gastado) + "   ·   Ingresaste " + dinero(ingresado) + \
                "   ·   Balance " + dinero(ingresado - gastado)
        if gastado_antes > 0:
            cambio = round((gastado - gastado_antes) / gastado_antes * 100)
            texto += "\n" + ("+" if cambio > 0 else "") + str(cambio) + " % de gasto comparado con " + MESES[anterior.month - 1]
        self.res_totales.configure(text=texto)

        filas = gastos.resumen_por_categoria(self.datos, gastos.inicio_mes(mes), gastos.fin_mes(mes))
        for i, fila in enumerate(filas):
            ctk.CTkLabel(self.res_lista, text=fila[0], anchor="w", width=150).grid(row=i, column=0, padx=8, pady=2, sticky="w")
            barra = ctk.CTkProgressBar(self.res_lista)
            barra.set(fila[1] / gastado if gastado else 0)
            barra.grid(row=i, column=1, sticky="ew", padx=8)
            porcentaje = round(fila[1] / gastado * 100) if gastado else 0
            ctk.CTkLabel(self.res_lista, text=dinero(fila[1]) + "  (" + str(porcentaje) + " %)", width=150, anchor="e").grid(row=i, column=2, padx=8)
        if not filas:
            ctk.CTkLabel(self.res_lista, text="Sin gastos este mes.", text_color="gray").grid(row=0, column=0, padx=8, pady=6)

        presupuestos = gastos.estado_presupuestos(self.datos, mes)
        for i, (categoria, usado, limite) in enumerate(presupuestos):
            proporcion = usado / limite
            color = VERDE if proporcion < gastos.AVISO_PRESUPUESTO else (AMARILLO if proporcion <= 1 else ROJO)
            ctk.CTkLabel(self.res_presupuestos, text=categoria, anchor="w", width=150).grid(row=i, column=0, padx=8, pady=2, sticky="w")
            barra = ctk.CTkProgressBar(self.res_presupuestos, progress_color=color)
            barra.set(min(proporcion, 1))
            barra.grid(row=i, column=1, sticky="ew", padx=8)
            if usado <= limite:
                queda = "quedan " + dinero(limite - usado)
            else:
                queda = "te pasaste " + dinero(usado - limite)
            ctk.CTkLabel(self.res_presupuestos, text=dinero(usado) + " de " + dinero(limite) + " · " + queda,
                         text_color=color if proporcion > 1 else NORMAL, width=260, anchor="e").grid(row=i, column=2, padx=8)
        if not presupuestos:
            ctk.CTkLabel(self.res_presupuestos, text="Pon un límite mensual a una categoría y aquí verás cuánto te queda.",
                         text_color="gray").grid(row=0, column=0, columnspan=3, padx=8, pady=6, sticky="w")

        hoy = date.today()
        pagos = gastos.proximos_pagos(self.datos, hoy)
        for i, pago in enumerate(pagos):
            dias = (pago[0] - hoy).days
            cuando = "hoy" if dias == 0 else ("atrasado" if dias < 0 else "en " + str(dias) + " días")
            ctk.CTkLabel(self.res_pagos, text=str(pago[0]) + "  " + pago[1] + "  " + dinero(pago[2]) + "  (" + cuando + ")",
                         anchor="w", text_color=ROJO if dias < 0 else NORMAL).grid(row=i, column=0, sticky="w", padx=8, pady=2)
        if not pagos:
            ctk.CTkLabel(self.res_pagos, text="Nada en los próximos 7 días.", text_color="gray").grid(row=0, column=0, padx=8, pady=6)
