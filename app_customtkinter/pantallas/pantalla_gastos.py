# pantalla_gastos.py
# Tres pestañas: Cuentas, Movimientos (con los pagos recurrentes) y Resumen.
from datetime import date, timedelta
from tkinter import filedialog
import customtkinter as ctk
from m import gastos
from pantallas.colores import ROJO, ROJO_HOVER, ROJO_SUAVE, TEXTO, GRIS, GRIS_FUERTE, BOTON_GRIS, BOTON_GRIS_HOVER

TIPOS_CUENTA = {"Débito": "debito", "Crédito": "credito", "Efectivo": "efectivo"}
NOMBRE_TIPO = {"debito": "débito", "credito": "crédito", "efectivo": "efectivo"}
ETIQUETA_SALDO = {"Débito": "Saldo actual", "Crédito": "Deuda actual", "Efectivo": "Dinero que tienes"}
NO_REPETIR = "No se repite"
REPETIR = {NO_REPETIR: None, "Cada semana": "semanal", "Cada quincena": "quincenal",
           "Cada mes": "mensual", "Cada 2 meses": "bimestral", "Cada año": "anual"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
PERIODOS = ["Todo", "Este mes", "Mes pasado"]
TODAS = "Todas las cuentas"


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
        self.editando_rec = None
        self.prog_abierto = True
        self.mes_resumen = gastos.inicio_mes(date.today())
        self.pestanas = ctk.CTkTabview(self, command=self.refrescar_todo)
        self.pestanas.pack(fill="both", expand=True)
        for nombre in ["Cuentas", "Movimientos", "Resumen"]:
            self.pestanas.add(nombre)
        self.armar_cuentas(self.pestanas.tab("Cuentas"))
        self.armar_movimientos(self.pestanas.tab("Movimientos"))
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
            mensaje.configure(text=nombre + " debe ser un número.", text_color=ROJO_SUAVE)
            return None

    def fecha(self, entrada, mensaje):
        try:
            return gastos.a_fecha(entrada.get().strip())
        except ValueError:
            mensaje.configure(text="La fecha va así: 2026-11-05", text_color=ROJO_SUAVE)
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
        for menu in (self.mov_cuenta, self.mov_destino):
            self.ajustar_menu(menu, todas)
        self.ajustar_menu(self.filtro_cuenta, [TODAS] + [c["nombre"] for c in self.datos["cuentas"]])
        for combo in (self.mov_categoria, self.pre_categoria):
            combo.configure(values=self.datos["categorias"])
        self.refrescar_movimientos()
        self.refrescar_cuentas()
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
        ctk.CTkButton(fechas, text="Hoy", width=44, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER,
                      command=lambda: self.poner_texto(self.mov_fecha, date.today().strftime(gastos.DIA))).pack(side="left", padx=(4, 0))
        ctk.CTkButton(fechas, text="Ayer", width=44, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER,
                      command=lambda: self.poner_texto(self.mov_fecha, (date.today() - timedelta(days=1)).strftime(gastos.DIA))).pack(side="left", padx=(4, 0))
        self.mov_boton = ctk.CTkButton(form, text="Agregar", width=100, command=self.agregar_mov)
        self.mov_boton.grid(row=0, column=6, padx=8)
        self.mov_cancelar = ctk.CTkButton(form, text="Cancelar", width=100, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER, command=self.cancelar_mov)
        # Repetir: convierte el movimiento en un pago (o ingreso) recurrente.
        self.mov_rep = ctk.CTkFrame(form, fg_color="transparent")
        self.mov_rep.grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 6))
        ctk.CTkLabel(self.mov_rep, text="Repetir:").pack(side="left")
        self.mov_repetir = ctk.CTkOptionMenu(self.mov_rep, values=list(REPETIR), width=140,
                                             command=lambda v: self.cambiar_repetir())
        self.mov_repetir.pack(side="left", padx=6)
        self.mov_auto = ctk.CTkCheckBox(self.mov_rep, text="Registrar solo en su fecha (automático)")
        self.mov_msg = ctk.CTkLabel(form, text="Consejo: Enter agrega el movimiento.", text_color="gray")
        self.mov_msg.grid(row=3, column=0, columnspan=7, sticky="w", padx=8)
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
        ctk.CTkButton(filtros, text="Exportar CSV", width=110, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER, command=self.exportar).pack(side="left", padx=(4, 0))
        self.prog_caja = ctk.CTkFrame(tab)
        self.prog_caja.pack(fill="x", pady=(0, 8))
        self.prog_caja.grid_columnconfigure(0, weight=1)
        self.prog_titulo = ctk.CTkButton(self.prog_caja, text="", anchor="w", fg_color="transparent",
                                         hover_color=("gray80", "gray25"), command=self.alternar_programados)
        self.prog_titulo.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.prog_lista = ctk.CTkFrame(self.prog_caja, fg_color="transparent")
        self.prog_lista.grid_columnconfigure(1, weight=1)
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
        # Las transferencias no se repiten (solo gastos e ingresos).
        if tipo == "transferencia":
            self.mov_rep.grid_remove()
        else:
            self.mov_rep.grid()

    def cambiar_repetir(self):
        if self.mov_repetir.get() == NO_REPETIR:
            self.mov_auto.pack_forget()
        else:
            self.mov_auto.pack(side="left", padx=(6, 0))

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
            self.mov_msg.configure(text="Primero crea una cuenta.", text_color=ROJO_SUAVE)
            return
        monto = self.numero(self.mov_monto, self.mov_msg, "El monto")
        fecha = self.fecha(self.mov_fecha, self.mov_msg)
        if monto is None or fecha is None:
            return
        if monto <= 0:
            self.mov_msg.configure(text="El monto debe ser mayor que 0.", text_color=ROJO_SUAVE)
            return
        destinoid = None
        if tipo == "transferencia":
            destino = self.cuenta_por_nombre(self.mov_destino.get())
            if destino is None or destino["id"] == cuenta["id"]:
                self.mov_msg.configure(text="Elige dos cuentas diferentes.", text_color=ROJO_SUAVE)
                return
            destinoid = destino["id"]
        frecuencia = None if tipo == "transferencia" else REPETIR[self.mov_repetir.get()]
        automatico = bool(self.mov_auto.get())
        if self.editando_rec is not None and frecuencia is None:
            self.mov_msg.configure(text="Un pago recurrente debe ser gasto o abono y repetirse. "
                                        "Para quitarlo usa Pausar o ✕.", text_color=ROJO_SUAVE)
            return
        self.sugerir_categoria()
        descripcion = self.mov_desc.get().strip()
        if tipo == "transferencia" and descripcion == "":
            descripcion = "Transferencia"
        if frecuencia and descripcion == "":
            descripcion = "Pago recurrente" if tipo == "gasto" else "Ingreso recurrente"
        categoria = self.mov_categoria.get()
        mov = None
        if self.editando_rec is not None:
            rec = self.editando_rec
            gastos.llenar_recurrente(self.datos, rec, descripcion, monto, cuenta["id"], frecuencia, fecha,
                                     categoria, automatico, tipo)
            creados = gastos.ponerse_al_dia(self.datos, rec, date.today())
            texto = "Pago recurrente actualizado. Próximo: " + rec["proximafecha"] + "."
            if creados:
                texto = str(len(creados)) + " registrado(s) automáticamente. " + texto
        elif self.editando_mov is not None:
            mov = self.editando_mov
            gastos.llenar_movimiento(self.datos, mov, tipo, monto, cuenta["id"], fecha,
                                     descripcion, categoria, destinoid)
            texto = "Movimiento actualizado."
            if frecuencia and gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is None:
                rec, _ = gastos.repetir_desde(self.datos, mov, frecuencia, automatico)
                texto += " Se repetirá; próximo: " + rec["proximafecha"] + "."
        elif frecuencia:
            rec, creados = gastos.programar(self.datos, tipo, monto, cuenta["id"], frecuencia, fecha,
                                            descripcion, categoria, automatico)
            if creados:
                mov = creados[0]
                texto = "Registrado y programado. Próximo: " + rec["proximafecha"] + "."
                if len(creados) > 1:
                    texto = str(len(creados)) + " fechas pasadas registradas. Próximo: " + rec["proximafecha"] + "."
            else:
                texto = "Programado para el " + rec["proximafecha"] + "."
        else:
            mov = gastos.agregar_movimiento(self.datos, tipo, monto, cuenta["id"], fecha, descripcion,
                                            categoria, destinoid=destinoid)
            texto = "Movimiento agregado."
        self.cancelar_mov()
        color = TEXTO
        if mov is not None and tipo == "gasto":
            aviso = gastos.aviso_presupuesto(self.datos, mov["categoria"], fecha)
            if aviso:
                texto += "  " + aviso
                color = ROJO_SUAVE
        self.mov_msg.configure(text=texto, text_color=color)
        self.refrescar_todo()
        self.mov_monto.focus_set()

    def cancelar_mov(self):
        # Limpia el formulario pero recuerda la última cuenta y categoría.
        self.editando_mov = None
        self.editando_rec = None
        self.mov_monto.delete(0, "end")
        self.mov_desc.delete(0, "end")
        self.mov_repetir.set(NO_REPETIR)
        self.mov_auto.deselect()
        self.cambiar_repetir()
        self.cambiar_tipo_mov(self.mov_tipo.get())
        self.mov_boton.configure(text="Agregar")
        self.mov_cancelar.grid_remove()
        self.mov_msg.configure(text="")

    def editar_mov(self, mov):
        self.cancelar_mov()
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
        texto = "Editando: cambia lo que quieras y pulsa Guardar."
        if gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is None and mov["tipo"] != "transferencia":
            texto += " Elige «Repetir» para que se repita."
        else:
            self.mov_rep.grid_remove()
        self.mov_msg.configure(text=texto, text_color=GRIS)

    def editar_rec(self, rec):
        self.cancelar_mov()
        self.pestanas.set("Movimientos")
        self.editando_rec = rec
        tipo = gastos.tipo_recurrente(rec)
        self.mov_tipo.set(tipo)
        self.cambiar_tipo_mov(tipo)
        self.poner_texto(self.mov_monto, str(rec["monto"]))
        self.poner_texto(self.mov_desc, rec["nombre"])
        self.poner_texto(self.mov_fecha, rec["proximafecha"])
        cuenta = gastos.buscar_cuenta(self.datos, rec["cuentaid"])
        if cuenta:
            self.mov_cuenta.set(cuenta["nombre"])
        if rec["categoria"]:
            self.mov_categoria.set(rec["categoria"])
        for etiqueta in REPETIR:
            if REPETIR[etiqueta] == rec["frecuencia"]:
                self.mov_repetir.set(etiqueta)
        if rec["automatico"]:
            self.mov_auto.select()
        self.cambiar_repetir()
        self.mov_boton.configure(text="Guardar")
        self.mov_cancelar.grid(row=1, column=6, padx=8, pady=(0, 8))
        self.mov_msg.configure(text="Editando el pago recurrente «" + rec["nombre"] + "». La fecha es la del próximo cobro.",
                               text_color=GRIS)

    def repetir_mov(self, mov):
        # Copia el movimiento con la fecha de hoy (útil para gastos de todos los días).
        gastos.agregar_movimiento(self.datos, mov["tipo"], mov["monto"], mov["cuentaid"], date.today(),
                                  mov["descripcion"], mov["categoria"], destinoid=mov.get("destinoid"))
        self.mov_msg.configure(text="Repetido con fecha de hoy.", text_color=TEXTO)
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
        self.refrescar_programados(cuentaid)
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
                signo, color = "⇄", GRIS
            else:
                texto = (mov["descripcion"] or "(sin descripción)") + "   ·   " + (mov["categoria"] or "ingreso") + "   ·   " + nombre
                signo, color = ("-", ROJO) if mov["tipo"] == "gasto" else ("+", GRIS_FUERTE)
            if gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is not None:
                texto = "↺ " + texto
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
            ctk.CTkButton(self.mov_lista, text="↻", width=30, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER,
                          command=lambda m=mov: self.repetir_mov(m)).grid(row=fila, column=3, padx=2)
            ctk.CTkButton(self.mov_lista, text="✕", width=30, fg_color=ROJO, hover_color=ROJO_HOVER,
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
        self.mov_msg.configure(text="Exportados " + str(cantidad) + " movimientos.", text_color=TEXTO)

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
        self.cta_cancelar = ctk.CTkButton(form, text="Cancelar", width=130, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER, command=self.cancelar_cuenta)

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
            self.cta_msg.configure(text="Escribe un nombre que no exista ya.", text_color=ROJO_SUAVE)
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
                self.cta_msg.configure(text="Límite y días deben ser números.", text_color=ROJO_SUAVE)
                return
            if not (1 <= corte <= 31 and 1 <= pago <= 31):
                self.cta_msg.configure(text="Los días van del 1 al 31.", text_color=ROJO_SUAVE)
                return
        if self.editando_cta is not None:
            gastos.actualizar_cuenta(self.editando_cta, nombre, tipo, saldo, limite, corte, pago)
            texto = "Cuenta actualizada."
        else:
            gastos.crear_cuenta(self.datos, nombre, tipo, saldo, limite, corte, pago)
            texto = "Cuenta creada."
        self.cancelar_cuenta()
        self.cta_msg.configure(text=texto, text_color=TEXTO)
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
        self.cta_msg.configure(text="Editando " + cuenta["nombre"] + ". El saldo/deuda es el que tenía al crearla.", text_color=GRIS)

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
        self.mov_msg.configure(text="Revisa el monto y la cuenta de origen, luego pulsa Agregar.", text_color=GRIS)

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
                    color = GRIS_FUERTE if uso < 0.3 else (ROJO_SUAVE if uso < 0.7 else ROJO)
                    barra = ctk.CTkProgressBar(caja, progress_color=color)
                    barra.set(uso)
                    barra.grid(row=3, column=0, sticky="ew", padx=10, pady=(4, 2))
                    ctk.CTkLabel(caja, text="Usas " + str(round(info["uso"] * 100)) + " % de tu límite (menos de 30 % es lo sano)",
                                 text_color="gray", anchor="w").grid(row=4, column=0, sticky="w", padx=10, pady=(0, 6))
                ctk.CTkButton(botones, text="Pagar", width=70, command=lambda c=cuenta: self.pagar_tarjeta(c)).pack(side="left", padx=2)
            else:
                ctk.CTkLabel(caja, text="Saldo " + dinero(gastos.saldo(self.datos, cuenta)), anchor="w").grid(
                    row=1, column=0, sticky="w", padx=10, pady=(0, 6))
            ctk.CTkButton(botones, text="Editar", width=70, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER,
                          command=lambda c=cuenta: self.editar_cuenta(c)).pack(side="left", padx=2)
            boton = ctk.CTkButton(botones, text="Borrar", width=70, fg_color=ROJO, hover_color=ROJO_HOVER)
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

    # ---------- Programados (pagos e ingresos recurrentes) ----------
    def alternar_programados(self):
        self.prog_abierto = not self.prog_abierto
        self.refrescar_movimientos()

    def refrescar_programados(self, cuentaid):
        limpiar(self.prog_lista)
        hoy = date.today()
        recurrentes = gastos.recurrentes_de(self.datos, cuentaid, self.mov_buscar.get())
        if not self.datos["recurrentes"]:
            self.prog_titulo.configure(text="↺ Sin pagos recurrentes: elige «Repetir» al agregar un movimiento "
                                            "(Netflix, renta, sueldo…).", text_color="gray")
            self.prog_lista.grid_remove()
            return
        fijo_gasto = 0
        fijo_ingreso = 0
        pendientes = 0
        for rec in recurrentes:
            if not rec["activo"]:
                continue
            if gastos.tipo_recurrente(rec) == "gasto":
                fijo_gasto += gastos.costo_mensual(rec)
            else:
                fijo_ingreso += gastos.costo_mensual(rec)
            if gastos.a_fecha(rec["proximafecha"]) <= hoy:
                pendientes += 1
        titulo = ("▾ " if self.prog_abierto else "▸ ") + "Programados (" + str(len(recurrentes)) + ")"
        titulo += "   ·   gastos fijos ~" + dinero(fijo_gasto) + "/mes"
        if fijo_ingreso:
            titulo += "   ·   ingresos fijos ~" + dinero(fijo_ingreso) + "/mes"
        if pendientes:
            titulo += "   ·   " + str(pendientes) + " por registrar"
        self.prog_titulo.configure(text=titulo, text_color=ROJO_SUAVE if pendientes else TEXTO)
        if not self.prog_abierto or not recurrentes:
            self.prog_lista.grid_remove()
            return
        self.prog_lista.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))
        for fila, rec in enumerate(recurrentes):
            dias = (gastos.a_fecha(rec["proximafecha"]) - hoy).days
            if not rec["activo"]:
                cuando, color_fecha = "en pausa", "gray"
            elif dias < 0:
                cuando, color_fecha = "atrasado " + str(-dias) + " días", ROJO
            elif dias == 0:
                cuando, color_fecha = "hoy", ROJO_SUAVE
            else:
                cuando, color_fecha = "en " + str(dias) + " días", TEXTO
            cuenta = gastos.buscar_cuenta(self.datos, rec["cuentaid"])
            texto = rec["nombre"] + "   ·   " + rec["frecuencia"] + "   ·   " + (cuenta["nombre"] if cuenta else "?")
            if rec["automatico"]:
                texto += "   ·   automático"
            texto += "   ·   " + cuando
            if self.editando_rec is rec:
                texto = "✎ " + texto
            es_gasto = gastos.tipo_recurrente(rec) == "gasto"
            etiquetas = [
                ctk.CTkLabel(self.prog_lista, text=rec["proximafecha"], width=90, text_color=color_fecha),
                ctk.CTkLabel(self.prog_lista, text=texto, anchor="w", cursor="hand2",
                             text_color=TEXTO if rec["activo"] else "gray"),
                ctk.CTkLabel(self.prog_lista, text=("-" if es_gasto else "+") + dinero(rec["monto"]),
                             text_color=(ROJO if es_gasto else GRIS_FUERTE) if rec["activo"] else "gray", width=110),
            ]
            for columna, etiqueta in enumerate(etiquetas):
                etiqueta.grid(row=fila, column=columna, padx=4, pady=2, sticky="ew" if columna == 1 else "")
                etiqueta.bind("<Button-1>", lambda e, r=rec: self.editar_rec(r))
            if rec["activo"]:
                ctk.CTkButton(self.prog_lista, text="Registrar", width=80,
                              command=lambda r=rec: self.registrar(r)).grid(row=fila, column=3, padx=2)
            ctk.CTkButton(self.prog_lista, text="Activar" if not rec["activo"] else "Pausar", width=70, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER,
                          command=lambda r=rec: self.pausar(r)).grid(row=fila, column=4, padx=2)
            boton = ctk.CTkButton(self.prog_lista, text="✕", width=30, fg_color=ROJO, hover_color=ROJO_HOVER)
            boton.configure(command=lambda r=rec, b=boton: self.borrar_rec(r, b))
            boton.grid(row=fila, column=5, padx=4)

    def registrar(self, rec):
        # Registra el cobro con fecha de hoy y avanza a la siguiente fecha.
        mov = gastos.registrar_recurrente(self.datos, rec, date.today())
        texto = rec["nombre"] + " registrado. Próximo: " + rec["proximafecha"] + "."
        aviso = None
        if mov["tipo"] == "gasto":
            aviso = gastos.aviso_presupuesto(self.datos, mov["categoria"], date.today())
        self.mov_msg.configure(text=texto + ("  " + aviso if aviso else ""), text_color=ROJO_SUAVE if aviso else TEXTO)
        self.refrescar_todo()

    def pausar(self, rec):
        gastos.alternar_recurrente(rec)
        self.refrescar_todo()

    def borrar_rec(self, rec, boton):
        if boton.cget("text") != "¿Seguro?":
            boton.configure(text="¿Seguro?", width=70)
            return
        if self.editando_rec is rec:
            self.cancelar_mov()
        gastos.borrar_recurrente(self.datos, rec["id"])
        self.mov_msg.configure(text="Ya no se repite. Los movimientos que ya registraste se quedan.", text_color=TEXTO)
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
        ctk.CTkButton(navegar, text="Este mes", width=80, fg_color=BOTON_GRIS, hover_color=BOTON_GRIS_HOVER, command=lambda: self.mover_mes(0)).pack(side="left", padx=8)
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
        self.pre_msg.configure(text=texto, text_color=TEXTO)
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
            color = GRIS_FUERTE if proporcion < gastos.AVISO_PRESUPUESTO else (ROJO_SUAVE if proporcion <= 1 else ROJO)
            ctk.CTkLabel(self.res_presupuestos, text=categoria, anchor="w", width=150).grid(row=i, column=0, padx=8, pady=2, sticky="w")
            barra = ctk.CTkProgressBar(self.res_presupuestos, progress_color=color)
            barra.set(min(proporcion, 1))
            barra.grid(row=i, column=1, sticky="ew", padx=8)
            if usado <= limite:
                queda = "quedan " + dinero(limite - usado)
            else:
                queda = "te pasaste " + dinero(usado - limite)
            ctk.CTkLabel(self.res_presupuestos, text=dinero(usado) + " de " + dinero(limite) + " · " + queda,
                         text_color=color if proporcion > 1 else TEXTO, width=260, anchor="e").grid(row=i, column=2, padx=8)
        if not presupuestos:
            ctk.CTkLabel(self.res_presupuestos, text="Pon un límite mensual a una categoría y aquí verás cuánto te queda.",
                         text_color="gray").grid(row=0, column=0, columnspan=3, padx=8, pady=6, sticky="w")

        hoy = date.today()
        pagos = gastos.proximos_pagos(self.datos, hoy)
        for i, pago in enumerate(pagos):
            dias = (pago[0] - hoy).days
            cuando = "hoy" if dias == 0 else ("atrasado" if dias < 0 else "en " + str(dias) + " días")
            ctk.CTkLabel(self.res_pagos, text=str(pago[0]) + "  " + pago[1] + "  " + dinero(pago[2]) + "  (" + cuando + ")",
                         anchor="w", text_color=ROJO if dias < 0 else TEXTO).grid(row=i, column=0, sticky="w", padx=8, pady=2)
        if not pagos:
            ctk.CTkLabel(self.res_pagos, text="Nada en los próximos 7 días.", text_color="gray").grid(row=0, column=0, padx=8, pady=6)
