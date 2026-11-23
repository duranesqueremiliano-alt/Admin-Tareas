# pantalla_gastos.py
# Tres pestañas: Cuentas, Movimientos (con los pagos recurrentes) y Resumen.
from datetime import date, datetime
import flet as ft
import flet.canvas as cv
import flet_shadcn_ui as shad
from m import gastos
from pantallas.colores import ROJO, ROJO_SUAVE, TEXTO, GRIS, GRIS_FUERTE
from pantallas.comun import texto, gris, caja, opciones, avisar, pedir_texto, confirmar

TIPOS_CUENTA = {"Débito": "debito", "Crédito": "credito", "Efectivo": "efectivo", "Inversión": "inversion"}
NOMBRE_TIPO = {"debito": "débito", "credito": "crédito", "efectivo": "efectivo", "inversion": "inversión"}
ETIQUETA_SALDO = {"Débito": "Saldo actual", "Crédito": "Deuda actual", "Efectivo": "Dinero que tienes",
                  "Inversión": "Monto invertido"}
REPETIR = {"Cada semana": "semanal", "Cada quincena": "quincenal", "Cada mes": "mensual",
           "Cada 2 meses": "bimestral", "Cada año": "anual"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
TODAS = "Todas las cuentas"
SUBE = "#9A9AA5"     # color de la línea de la gráfica cuando sube (cuando baja va en ROJO)
SIN_CUENTAS = "(crea una cuenta)"
NUEVA_CATEGORIA = "+ Nueva categoría"
PESTANAS = ["Cuentas", "Movimientos", "Resumen"]


def dinero(monto):
    if monto < 0:
        return "-${:,.2f}".format(-monto)
    return "${:,.2f}".format(monto)


def nombre_mes(fecha):
    return MESES[fecha.month - 1] + " " + str(fecha.year)


def boton_chico(etiqueta, al_pulsar, variante=shad.ButtonVariant.SECONDARY):
    return shad.Button(etiqueta, variant=variante, size=shad.ButtonSize.SM, on_click=al_pulsar)


def boton_borrar(al_pulsar):
    return shad.IconButton(icon=shad.LucideIcons.X, variant=shad.ButtonVariant.GHOST, color=ROJO, on_click=al_pulsar)


def clicable(control, al_pulsar):
    # Hace que un texto se pueda pulsar (lo que antes era label.bind("<Button-1>", ...)).
    return ft.Container(control, expand=True, on_click=al_pulsar)


def a_dia(valor):
    # El calendario devuelve un datetime (medianoche UTC); nosotros solo queremos el día.
    if isinstance(valor, datetime):
        return valor.date()
    return valor


def monto_texto(monto, negativo=False):
    # 120.0 -> "120", 99.5 -> "99.5"; con negativo=True -> "-120"
    limpio = ("%.2f" % monto).rstrip("0").rstrip(".")
    return "-" + limpio if negativo else limpio


class PantallaGastos:
    def __init__(self, app):
        self.app = app
        self.datos = app.gastos
        self.editando_mov = None
        self.editando_cta = None
        self.editando_rec = None
        self.prog_abierto = True
        self.meses_abiertos = None   # meses que dejaste abiertos en la lista; None = solo el más reciente
        self.mes_resumen = gastos.inicio_mes(date.today())
        self.selector = ft.FilePicker()   # ventana de Windows para guardar el CSV

        # Las pestañas de arriba solo eligen; debajo, cada contenido se muestra u oculta.
        self.pestanas = shad.Tabs(value="Cuentas", tabs=[shad.Tab(value=p, label=p) for p in PESTANAS],
                                  on_change=lambda e: self.ir_a(self.pestanas.value))
        self.contenidos = {
            "Cuentas": self.armar_cuentas(),
            "Movimientos": self.armar_movimientos(),
            "Resumen": self.armar_resumen(),
        }
        # Las pestañas de shadcn necesitan un ancho fijo; sin él no se dibujan.
        self.vista = ft.Column([ft.Container(self.pestanas, width=420),
                                ft.Stack([self.contenidos[p] for p in PESTANAS], expand=True)], expand=True)
        self.ir_a("Cuentas")

    # ---------- Ayudantes ----------
    def ir_a(self, nombre):
        self.pestanas.value = nombre
        for p in PESTANAS:
            self.contenidos[p].visible = p == nombre
        self.refrescar_todo()

    def nombres_cuentas(self, solo=None):
        nombres = []
        for cuenta in self.datos["cuentas"]:
            if solo is None or cuenta["tipo"] in solo:
                nombres.append(cuenta["nombre"])
        if not nombres:
            nombres = [SIN_CUENTAS]
        return nombres

    def cuenta_por_nombre(self, nombre):
        for cuenta in self.datos["cuentas"]:
            if cuenta["nombre"] == nombre:
                return cuenta
        return None

    def numero(self, entrada, mensaje, nombre):
        try:
            return float(entrada.value.replace(",", "").replace("$", "").strip())
        except ValueError:
            avisar(mensaje, nombre + " debe ser un número.", ROJO_SUAVE)
            return None

    def fecha(self, entrada, mensaje):
        try:
            return gastos.a_fecha(entrada.value.strip())
        except ValueError:
            avisar(mensaje, "La fecha va así: 2026-11-05", ROJO_SUAVE)
            return None

    def ajustar_menu(self, menu, valores):
        menu.options = opciones(valores)
        if menu.value not in valores:
            menu.value = valores[0]

    def opciones_categoria(self):
        return list(self.datos["categorias"]) + [NUEVA_CATEGORIA]

    def elegir_categoria(self, e):
        # El Select no deja escribir, así que una categoría nueva se pide en una ventanita.
        menu = e.control
        if menu.value != NUEVA_CATEGORIA:
            return

        def al_terminar(nombre):
            if nombre and nombre.strip():
                menu.value = gastos.asegurar_categoria(self.datos, nombre)
            else:
                menu.value = "Otros"
            for otro in (self.mov_categoria, self.pre_categoria):
                otro.options = opciones(self.opciones_categoria())

        pedir_texto(self.app.page, "Nueva categoría", "ej. Mascotas", al_terminar)

    def refrescar_todo(self):
        todas = self.nombres_cuentas()
        for menu in (self.mov_cuenta, self.mov_destino):
            self.ajustar_menu(menu, todas)
        self.ajustar_menu(self.filtro_cuenta, [TODAS] + [c["nombre"] for c in self.datos["cuentas"]])
        for menu in (self.mov_categoria, self.pre_categoria):
            self.ajustar_menu(menu, self.opciones_categoria())
        self.refrescar_movimientos()
        self.refrescar_cuentas()
        self.refrescar_resumen()

    # ================= Movimientos =================
    def armar_movimientos(self):
        # Ya no hay pestañas Gasto/Abono/Transferencia: el signo del monto decide
        # (negativo = gasto, positivo = abono) y una casilla marca las transferencias.
        self.mov_desc = shad.Input(placeholder="Descripción", expand=True,
                                   on_blur=lambda e: self.sugerir_categoria(), on_submit=lambda e: self.agregar_mov())
        self.mov_monto = shad.Input(placeholder="-120 / 120", width=110,
                                    on_change=lambda e: self.cambiar_tipo_mov(), on_submit=lambda e: self.agregar_mov())
        self.mov_de = texto("Cuenta:")
        self.mov_cuenta = shad.Select(options=opciones(self.nombres_cuentas()), value=self.nombres_cuentas()[0],
                                      min_width=140)
        self.mov_transfer = shad.Checkbox(label="Transferencia", on_change=lambda e: self.cambiar_tipo_mov())
        self.mov_destino = shad.Select(options=opciones(self.nombres_cuentas()), value=self.nombres_cuentas()[0],
                                       min_width=140)
        self.mov_hacia = ft.Row([texto("a:"), self.mov_destino], tight=True)
        self.mov_categoria = shad.Select(options=opciones(self.opciones_categoria()), value="Otros",
                                         min_width=140, on_change=self.elegir_categoria)
        self.mov_fecha = shad.DatePicker(value=date.today(), width=200)
        # Se repite: casilla; al marcarla aparecen cada cuánto y "automático".
        self.mov_repite = shad.Checkbox(label="Se repite", on_change=lambda e: self.cambiar_repetir())
        self.mov_repetir = shad.Select(options=opciones(list(REPETIR)), value="Cada mes", min_width=140)
        self.mov_auto = shad.Checkbox(label="Registrar solo en su fecha (automático)")
        self.mov_rep = ft.Row([self.mov_repetir, self.mov_auto], tight=True)
        self.mov_boton = shad.Button("Agregar", width=100, on_click=lambda e: self.agregar_mov())
        self.mov_cancelar = shad.Button("Cancelar", width=100, variant=shad.ButtonVariant.SECONDARY,
                                        visible=False, on_click=lambda e: self.cancelar_mov())
        self.mov_msg = gris("Monto negativo = gasto, positivo = abono. Enter agrega el movimiento.")
        # Orden: descripción, monto, cuenta, fecha, se repite y Agregar al final.
        form = caja(ft.Column([
            # Esta fila NO usa wrap: la descripción tiene expand=True y necesita una fila normal para estirarse.
            ft.Row([self.mov_desc, self.mov_monto, self.mov_de, self.mov_cuenta, self.mov_transfer,
                    self.mov_hacia, self.mov_categoria]),
            # Esta sí usa wrap: si no cabe todo, Agregar baja de renglón pero sigue al final.
            ft.Row([self.mov_fecha, self.mov_repite, self.mov_rep, self.mov_cancelar, self.mov_boton], wrap=True,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.mov_msg,
        ]))

        # Buscar: solo el icono; al pulsarlo aparece el campo de texto.
        self.mov_buscar = shad.Input(placeholder="Buscar por descripción o categoría", expand=True, visible=False,
                                     on_change=lambda e: self.refrescar_movimientos())
        self.boton_buscar = shad.Tooltip(message="Buscar", content=shad.IconButton(
            icon=shad.LucideIcons.SEARCH, variant=shad.ButtonVariant.OUTLINE, on_click=lambda e: self.alternar_buscar()))
        self.hueco = ft.Container(expand=True)   # empuja lo demás a la derecha mientras no se busca
        self.filtro_cuenta = shad.Select(options=opciones([TODAS]), value=TODAS, min_width=150,
                                         on_change=lambda e: self.refrescar_movimientos())
        # CSV: un icono; al hacer clic se abre un menú flotante (Popover) con Importar y Exportar.
        self.menu_csv = shad.Popover(
            content=shad.Tooltip(message="Importar o exportar CSV", content=shad.IconButton(
                icon=shad.LucideIcons.FILE_SPREADSHEET, variant=shad.ButtonVariant.OUTLINE,
                on_click=lambda e: self.alternar_csv())),
            popover=ft.Column([
                shad.Button("Importar CSV", leading=shad.LucideIcons.UPLOAD, variant=shad.ButtonVariant.GHOST,
                            on_click=self.importar),
                shad.Button("Exportar CSV", leading=shad.LucideIcons.DOWNLOAD, variant=shad.ButtonVariant.GHOST,
                            on_click=self.exportar),
            ], tight=True, spacing=2))
        filtros = ft.Row([self.boton_buscar, self.mov_buscar, self.hueco, self.filtro_cuenta, self.menu_csv])

        self.prog_titulo = texto("")
        self.prog_lista = ft.Column(spacing=2)
        prog_caja = caja(ft.Column([ft.Container(self.prog_titulo, padding=4, on_click=lambda e: self.alternar_programados()),
                                    self.prog_lista], spacing=4))
        self.mov_total = gris("")
        self.mov_lista = ft.ListView(expand=True, spacing=2)

        self.cambiar_tipo_mov()
        return ft.Column([form, filtros, prog_caja, self.mov_total, caja(self.mov_lista, expand=True)], expand=True)

    def tipo_mov(self):
        # Lo decide el formulario: la casilla de transferencia o el signo del monto.
        if self.mov_transfer.value:
            return "transferencia"
        escrito = (self.mov_monto.value or "").strip()
        if escrito and not escrito.startswith("-"):
            return "abono"
        return "gasto"

    def cambiar_tipo_mov(self):
        # Gasto: categoría. Abono: nada extra. Transferencia: cuenta destino y no se repite.
        tipo = self.tipo_mov()
        self.mov_de.value = "De:" if tipo == "transferencia" else "Cuenta:"
        self.mov_hacia.visible = tipo == "transferencia"
        self.mov_categoria.visible = tipo == "gasto"
        self.mov_repite.visible = tipo != "transferencia"
        self.cambiar_repetir()

    def cambiar_repetir(self):
        self.mov_rep.visible = self.mov_repite.visible and bool(self.mov_repite.value)

    def alternar_buscar(self):
        self.mov_buscar.visible = not self.mov_buscar.visible
        self.hueco.visible = not self.mov_buscar.visible
        if self.mov_buscar.visible:
            self.app.page.run_task(self.mov_buscar.focus)
        else:
            self.mov_buscar.value = ""
            self.refrescar_movimientos()

    def alternar_csv(self):
        self.menu_csv.open = not self.menu_csv.open

    def sugerir_categoria(self):
        if self.tipo_mov() != "gasto" or self.mov_categoria.value not in ("", "Otros"):
            return
        sugerida = gastos.categoria_sugerida(self.datos, self.mov_desc.value)
        if sugerida:
            self.mov_categoria.value = sugerida

    def agregar_mov(self):
        tipo = self.tipo_mov()
        cuenta = self.cuenta_por_nombre(self.mov_cuenta.value)
        if cuenta is None:
            avisar(self.mov_msg, "Primero crea una cuenta.", ROJO_SUAVE)
            return
        monto = self.numero(self.mov_monto, self.mov_msg, "El monto")
        if monto is None:
            return
        fecha = a_dia(self.mov_fecha.value)
        if fecha is None:
            avisar(self.mov_msg, "Elige la fecha en el calendario.", ROJO_SUAVE)
            return
        if monto == 0:
            avisar(self.mov_msg, "El monto no puede ser 0.", ROJO_SUAVE)
            return
        monto = abs(monto)   # en los datos se guarda positivo; el tipo dice si es gasto o abono
        destinoid = None
        if tipo == "transferencia":
            destino = self.cuenta_por_nombre(self.mov_destino.value)
            if destino is None or destino["id"] == cuenta["id"]:
                avisar(self.mov_msg, "Elige dos cuentas diferentes.", ROJO_SUAVE)
                return
            destinoid = destino["id"]
        frecuencia = None
        if tipo != "transferencia" and self.mov_repite.value:
            frecuencia = REPETIR[self.mov_repetir.value]
        automatico = bool(self.mov_auto.value)
        if self.editando_rec is not None and frecuencia is None:
            avisar(self.mov_msg, "Un pago recurrente debe ser gasto o abono y repetirse. "
                                 "Para quitarlo usa Pausar o ✕.", ROJO_SUAVE)
            return
        self.sugerir_categoria()
        descripcion = self.mov_desc.value.strip()
        if tipo == "transferencia" and descripcion == "":
            descripcion = "Transferencia"
        if frecuencia and descripcion == "":
            descripcion = "Pago recurrente" if tipo == "gasto" else "Ingreso recurrente"
        categoria = self.mov_categoria.value
        if categoria == NUEVA_CATEGORIA:
            categoria = "Otros"
        mov = None
        if self.editando_rec is not None:
            rec = self.editando_rec
            gastos.llenar_recurrente(self.datos, rec, descripcion, monto, cuenta["id"], frecuencia, fecha,
                                     categoria, automatico, tipo)
            creados = gastos.ponerse_al_dia(self.datos, rec, date.today())
            mensaje = "Pago recurrente actualizado. Próximo: " + rec["proximafecha"] + "."
            if creados:
                mensaje = str(len(creados)) + " registrado(s) automáticamente. " + mensaje
        elif self.editando_mov is not None:
            mov = self.editando_mov
            gastos.llenar_movimiento(self.datos, mov, tipo, monto, cuenta["id"], fecha,
                                     descripcion, categoria, destinoid)
            mensaje = "Movimiento actualizado."
            if frecuencia and gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is None:
                rec, _ = gastos.repetir_desde(self.datos, mov, frecuencia, automatico)
                mensaje += " Se repetirá; próximo: " + rec["proximafecha"] + "."
        elif frecuencia:
            rec, creados = gastos.programar(self.datos, tipo, monto, cuenta["id"], frecuencia, fecha,
                                            descripcion, categoria, automatico)
            if creados:
                mov = creados[0]
                mensaje = "Registrado y programado. Próximo: " + rec["proximafecha"] + "."
                if len(creados) > 1:
                    mensaje = str(len(creados)) + " fechas pasadas registradas. Próximo: " + rec["proximafecha"] + "."
            else:
                mensaje = "Programado para el " + rec["proximafecha"] + "."
        else:
            mov = gastos.agregar_movimiento(self.datos, tipo, monto, cuenta["id"], fecha, descripcion,
                                            categoria, destinoid=destinoid)
            mensaje = "Movimiento agregado."
        self.cancelar_mov()
        color = TEXTO
        if mov is not None and tipo == "gasto":
            aviso = gastos.aviso_presupuesto(self.datos, mov["categoria"], fecha)
            if aviso:
                mensaje += "  " + aviso
                color = ROJO_SUAVE
        avisar(self.mov_msg, mensaje, color)
        self.refrescar_todo()
        self.app.page.run_task(self.mov_desc.focus)

    def cancelar_mov(self):
        # Limpia el formulario pero recuerda la última cuenta, categoría y fecha.
        self.editando_mov = None
        self.editando_rec = None
        self.mov_monto.value = ""
        self.mov_desc.value = ""
        self.mov_transfer.value = False
        self.mov_repite.value = False
        self.mov_repetir.value = "Cada mes"
        self.mov_auto.value = False
        self.cambiar_tipo_mov()
        self.mov_boton.content = "Agregar"
        self.mov_cancelar.visible = False
        avisar(self.mov_msg, "")

    def poner_en_formulario(self, tipo, monto, descripcion, fecha, cuentaid, categoria):
        self.mov_transfer.value = tipo == "transferencia"
        self.mov_monto.value = monto_texto(monto, negativo=tipo == "gasto")
        self.mov_desc.value = descripcion
        self.mov_fecha.value = gastos.a_fecha(fecha)
        cuenta = gastos.buscar_cuenta(self.datos, cuentaid)
        if cuenta:
            self.mov_cuenta.value = cuenta["nombre"]
        if categoria:
            self.mov_categoria.value = categoria
        self.cambiar_tipo_mov()

    def editar_mov(self, mov):
        self.cancelar_mov()
        self.editando_mov = mov
        self.poner_en_formulario(mov["tipo"], mov["monto"], mov["descripcion"], mov["fecha"],
                                 mov["cuentaid"], mov["categoria"])
        destino = gastos.buscar_cuenta(self.datos, mov.get("destinoid"))
        if destino:
            self.mov_destino.value = destino["nombre"]
        self.mov_boton.content = "Guardar"
        self.mov_cancelar.visible = True
        mensaje = "Editando: cambia lo que quieras y pulsa Guardar."
        if gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is None and mov["tipo"] != "transferencia":
            mensaje += " Marca «Se repite» para que se repita."
        else:
            self.mov_repite.visible = False
            self.cambiar_repetir()
        avisar(self.mov_msg, mensaje, GRIS)
        self.ir_a("Movimientos")

    def editar_rec(self, rec):
        self.cancelar_mov()
        self.editando_rec = rec
        self.poner_en_formulario(gastos.tipo_recurrente(rec), rec["monto"], rec["nombre"], rec["proximafecha"],
                                 rec["cuentaid"], rec["categoria"])
        self.mov_repite.value = True
        for etiqueta in REPETIR:
            if REPETIR[etiqueta] == rec["frecuencia"]:
                self.mov_repetir.value = etiqueta
        self.mov_auto.value = bool(rec["automatico"])
        self.cambiar_repetir()
        self.mov_boton.content = "Guardar"
        self.mov_cancelar.visible = True
        avisar(self.mov_msg, "Editando el pago recurrente «" + rec["nombre"] + "». La fecha es la del próximo cobro.", GRIS)
        self.ir_a("Movimientos")

    def repetir_mov(self, mov):
        # Copia el movimiento con la fecha de hoy (útil para gastos de todos los días).
        gastos.agregar_movimiento(self.datos, mov["tipo"], mov["monto"], mov["cuentaid"], date.today(),
                                  mov["descripcion"], mov["categoria"], destinoid=mov.get("destinoid"))
        avisar(self.mov_msg, "Repetido con fecha de hoy.", TEXTO)
        self.refrescar_todo()

    def refrescar_movimientos(self):
        self.mov_lista.controls.clear()
        filtro = self.cuenta_por_nombre(self.filtro_cuenta.value)
        cuentaid = filtro["id"] if filtro else None
        self.refrescar_programados(cuentaid)
        movimientos = gastos.filtrar(self.datos, cuentaid=cuentaid, texto=self.mov_buscar.value)
        # Agrupar por mes: "2026-11" -> movimientos de ese mes (ya vienen del más nuevo al más viejo).
        meses = {}
        for mov in movimientos:
            clave = mov["fecha"][:7]
            if clave not in meses:
                meses[clave] = []
            meses[clave].append(mov)
        self.mov_total.value = str(len(movimientos)) + " movimientos   ·   clic en uno para editarlo"
        if not meses:
            self.mov_lista.controls.append(ft.Container(gris("Sin movimientos con estos filtros."), padding=20,
                                                        alignment=ft.Alignment.CENTER))
            return
        claves = list(meses)
        if self.meses_abiertos is None:
            abiertos = [claves[0]]          # al principio solo el mes más reciente
        else:
            abiertos = [c for c in self.meses_abiertos if c in meses]
        secciones = []
        for clave in claves:
            gastado, ingresado = 0, 0
            for mov in meses[clave]:
                if mov["tipo"] == "gasto":
                    gastado += mov["monto"]
                elif mov["tipo"] == "abono":
                    ingresado += mov["monto"]
            mes = date(int(clave[:4]), int(clave[5:]), 1)
            titulo = (nombre_mes(mes).capitalize() + "   ·   " + str(len(meses[clave])) + " mov.   ·   gastos " +
                      dinero(gastado) + "   ·   ingresos " + dinero(ingresado))
            filas = ft.Column([self.fila_mov(mov) for mov in meses[clave]], spacing=2)
            secciones.append(shad.AccordionItem(value=clave, title=titulo, content=filas))
        self.mov_lista.controls.append(shad.Accordion(items=secciones, value=abiertos, multiple=True,
                                                      on_change=self.cambiar_meses))

    def cambiar_meses(self, e):
        # Recuerda qué meses abriste para no cerrarlos al refrescar la lista.
        self.meses_abiertos = list(e.control.value)

    def fila_mov(self, mov):
        cuenta = gastos.buscar_cuenta(self.datos, mov["cuentaid"])
        nombre = cuenta["nombre"] if cuenta else "(sin cuenta)"
        if mov["tipo"] == "transferencia":
            destino = gastos.buscar_cuenta(self.datos, mov.get("destinoid"))
            linea = mov["descripcion"] + "   ·   " + nombre + " → " + (destino["nombre"] if destino else "?")
            signo, color = "⇄", GRIS
        else:
            linea = (mov["descripcion"] or "(sin descripción)") + "   ·   " + (mov["categoria"] or "ingreso") + "   ·   " + nombre
            signo, color = ("-", ROJO) if mov["tipo"] == "gasto" else ("+", GRIS_FUERTE)
        if gastos.buscar_recurrente(self.datos, mov.get("recurrenteid")) is not None:
            linea = "↺ " + linea
        if self.editando_mov is mov:
            linea = "✎ " + linea
        return ft.Row([
            ft.Container(texto(mov["fecha"]), width=90),
            clicable(texto(linea), lambda e: self.editar_mov(mov)),
            ft.Container(texto(signo + dinero(mov["monto"]), color=color), width=110, alignment=ft.Alignment.CENTER_RIGHT),
            shad.IconButton(icon=shad.LucideIcons.ROTATE_CW, variant=shad.ButtonVariant.GHOST,
                            on_click=lambda e: self.repetir_mov(mov)),
            boton_borrar(lambda e: self.borrar_mov(mov)),
        ])

    def borrar_mov(self, mov):
        if self.editando_mov is mov:
            self.cancelar_mov()
        gastos.borrar_movimiento(self.datos, mov["id"])
        self.refrescar_todo()

    async def exportar(self, e):
        self.menu_csv.open = False
        ruta = await self.selector.save_file(dialog_title="Exportar movimientos", file_name="movimientos.csv",
                                             file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["csv"])
        if not ruta:
            return
        if not ruta.lower().endswith(".csv"):
            ruta += ".csv"
        cantidad = gastos.exportar_csv(self.datos, ruta)
        avisar(self.mov_msg, "Exportados " + str(cantidad) + " movimientos.", TEXTO)
        self.app.page.update()

    async def importar(self, e):
        self.menu_csv.open = False
        archivos = await self.selector.pick_files(dialog_title="Importar movimientos",
                                                  file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["csv"])
        if not archivos:
            return
        try:
            nuevos, repetidos, errores = gastos.importar_csv(self.datos, archivos[0].path)
        except (OSError, UnicodeDecodeError) as err:
            avisar(self.mov_msg, "No se pudo leer el archivo: " + str(err), ROJO_SUAVE)
            self.app.page.update()
            return
        mensaje = "Importados " + str(nuevos) + " movimientos."
        if repetidos:
            mensaje += " " + str(repetidos) + " ya existían."
        if errores:
            mensaje += " " + str(errores) + " filas con error (fecha AAAA-MM-DD y monto numérico)."
        avisar(self.mov_msg, mensaje, ROJO_SUAVE if errores else TEXTO)
        self.refrescar_todo()
        self.app.page.update()

    # ================= Cuentas =================
    def armar_cuentas(self):
        self.cta_totales = texto("", negrita=True)
        self.cta_nombre = shad.Input(label="Nombre", placeholder="ej. BBVA débito", expand=True)
        self.cta_tipo = shad.Tabs(value="Débito", tabs=[shad.Tab(value=t, label=t) for t in TIPOS_CUENTA],
                                  on_change=lambda e: self.cambiar_tipo_cuenta(self.cta_tipo.value))
        self.cta_saldo = shad.Input(label="Saldo actual", placeholder="0", width=140)
        self.cta_boton = shad.Button("Crear cuenta", width=140, on_click=lambda e: self.guardar_cuenta())
        self.cta_cancelar = shad.Button("Cancelar", width=140, variant=shad.ButtonVariant.SECONDARY,
                                        visible=False, on_click=lambda e: self.cancelar_cuenta())
        # Solo para crédito: se muestra u oculta según el tipo elegido.
        self.cta_limite = shad.Input(label="Límite de crédito", placeholder="ej. 8000", width=140)
        self.cta_corte = shad.Input(label="Día de corte", placeholder="1 a 31", width=100)
        self.cta_pago = shad.Input(label="Día de pago", placeholder="1 a 31", width=100)
        self.cta_extra = [self.cta_limite, self.cta_corte, self.cta_pago]
        self.cta_credito = ft.Row(self.cta_extra + [
            gris("El corte cierra el periodo; el pago es la fecha límite para pagar sin intereses.", expand=True)],
            vertical_alignment=ft.CrossAxisAlignment.END)
        # Solo para inversión: cuánto crece al año.
        self.cta_tasa = shad.Input(label="Crece % al año", placeholder="ej. 10", width=140)
        self.cta_inversion = ft.Row([self.cta_tasa, gris(
            "Crece con interés compuesto. Cuando sepas el valor real, pulsa «Registrar valor» en su tarjeta; "
            "aportes y retiros son movimientos normales.", expand=True)], vertical_alignment=ft.CrossAxisAlignment.END)
        self.cta_msg = texto("")
        form = caja(ft.Column([
            ft.Row([self.cta_nombre, ft.Column([gris("Tipo"), ft.Container(self.cta_tipo, width=380)], spacing=4), self.cta_saldo,
                    ft.Column([self.cta_cancelar, self.cta_boton], spacing=4)],
                   vertical_alignment=ft.CrossAxisAlignment.END),
            self.cta_credito,
            self.cta_inversion,
            self.cta_msg,
        ]))
        self.cta_lista = ft.ListView(expand=True, spacing=8)
        self.cambiar_tipo_cuenta("Débito")
        return ft.Column([self.cta_totales, form, self.cta_lista], expand=True)

    def cambiar_tipo_cuenta(self, tipo):
        self.cta_saldo.label = ETIQUETA_SALDO[tipo]
        self.cta_credito.visible = tipo == "Crédito"
        self.cta_inversion.visible = tipo == "Inversión"

    def guardar_cuenta(self):
        nombre = self.cta_nombre.value.strip()
        otra = self.cuenta_por_nombre(nombre)
        if nombre == "" or (otra is not None and otra is not self.editando_cta):
            avisar(self.cta_msg, "Escribe un nombre que no exista ya.", ROJO_SUAVE)
            return
        saldo = self.numero(self.cta_saldo, self.cta_msg, "El saldo") if self.cta_saldo.value.strip() else 0
        if saldo is None:
            return
        tipo = TIPOS_CUENTA[self.cta_tipo.value]
        limite, corte, pago, tasa = 0, 1, 1, 0
        if tipo == "inversion":
            tasa = self.numero(self.cta_tasa, self.cta_msg, "El %") if self.cta_tasa.value.strip() else 0
            if tasa is None:
                return
        if tipo == "credito":
            try:
                limite = float(self.cta_limite.value.replace(",", "") or 0)
                corte = int(self.cta_corte.value or 1)
                pago = int(self.cta_pago.value or 1)
            except ValueError:
                avisar(self.cta_msg, "Límite y días deben ser números.", ROJO_SUAVE)
                return
            if not (1 <= corte <= 31 and 1 <= pago <= 31):
                avisar(self.cta_msg, "Los días van del 1 al 31.", ROJO_SUAVE)
                return
        if self.editando_cta is not None:
            gastos.actualizar_cuenta(self.editando_cta, nombre, tipo, saldo, limite, corte, pago, tasa)
            mensaje = "Cuenta actualizada."
        else:
            gastos.crear_cuenta(self.datos, nombre, tipo, saldo, limite, corte, pago, tasa)
            mensaje = "Cuenta creada."
        self.cancelar_cuenta()
        avisar(self.cta_msg, mensaje, TEXTO)
        self.refrescar_todo()

    def cancelar_cuenta(self):
        self.editando_cta = None
        for entrada in [self.cta_nombre, self.cta_saldo, self.cta_tasa] + self.cta_extra:
            entrada.value = ""
        self.cta_boton.content = "Crear cuenta"
        self.cta_cancelar.visible = False
        avisar(self.cta_msg, "")

    def editar_cuenta(self, cuenta):
        self.cancelar_cuenta()
        self.editando_cta = cuenta
        tipo = "Débito"
        for nombre in TIPOS_CUENTA:
            if TIPOS_CUENTA[nombre] == cuenta["tipo"]:
                tipo = nombre
        self.cta_tipo.value = tipo
        self.cambiar_tipo_cuenta(tipo)
        self.cta_nombre.value = cuenta["nombre"]
        self.cta_saldo.value = str(cuenta["saldoinicial"])
        if cuenta["tipo"] == "credito":
            self.cta_limite.value = str(cuenta["limite"])
            self.cta_corte.value = str(cuenta["diacorte"])
            self.cta_pago.value = str(cuenta["diapago"])
        if cuenta["tipo"] == "inversion":
            self.cta_tasa.value = monto_texto(cuenta.get("tasa", 0))
        self.cta_boton.content = "Guardar cambios"
        self.cta_cancelar.visible = True
        avisar(self.cta_msg, "Editando " + cuenta["nombre"] + ". El saldo/deuda es el que tenía al crearla.", GRIS)

    def pagar_tarjeta(self, cuenta):
        # Prepara una transferencia desde débito/efectivo hacia la tarjeta.
        info = gastos.info_credito(self.datos, cuenta, date.today())
        self.cancelar_mov()
        self.mov_transfer.value = True
        self.cambiar_tipo_mov()
        self.ir_a("Movimientos")
        self.mov_cuenta.value = self.nombres_cuentas(solo=("debito", "efectivo"))[0]
        self.mov_destino.value = cuenta["nombre"]
        monto = info["facturado"] if info["facturado"] > 0 else max(0, info["deuda"])
        self.mov_monto.value = "{:.2f}".format(monto)
        self.mov_desc.value = "Pago tarjeta " + cuenta["nombre"]
        self.mov_fecha.value = date.today()
        avisar(self.mov_msg, "Revisa el monto y la cuenta de origen, luego pulsa Agregar.", GRIS)

    def refrescar_cuentas(self):
        self.cta_lista.controls.clear()
        self.cta_totales.value = ("Tienes " + dinero(gastos.total_disponible(self.datos)) +
                                  " en débito y efectivo   ·   Invertido " + dinero(gastos.total_invertido(self.datos)) +
                                  "   ·   Debes " + dinero(gastos.total_deuda(self.datos)) + " en tarjetas")
        hoy = date.today()
        for cuenta in self.datos["cuentas"]:
            self.cta_lista.controls.append(self.tarjeta_cuenta(cuenta, hoy))
        if not self.datos["cuentas"]:
            self.cta_lista.controls.append(ft.Container(gris("Crea tu primera cuenta arriba."), padding=20,
                                                        alignment=ft.Alignment.CENTER))

    def tarjeta_cuenta(self, cuenta, hoy):
        lineas = []
        botones = []
        if cuenta["tipo"] == "credito":
            info = gastos.info_credito(self.datos, cuenta, hoy)
            linea = "Deuda " + dinero(info["deuda"])
            if info["disponible"] is not None:
                linea += "   ·   Límite " + dinero(cuenta["limite"]) + "   ·   Disponible " + dinero(info["disponible"])
            lineas.append(texto(linea))
            fechas = "Próximo corte " + str(info["proximocorte"]) + "   ·   "
            if info["facturado"] > 0:
                fechas += ("Pagar " + dinero(info["facturado"]) + " antes del " + str(info["proximopago"]) +
                           " (en " + str(info["diaspago"]) + " días)")
            else:
                fechas += "Nada pendiente del corte pasado"
            lineas.append(gris(fechas))
            if info["uso"] is not None:
                uso = min(info["uso"], 1)
                color = GRIS_FUERTE if uso < 0.3 else (ROJO_SUAVE if uso < 0.7 else ROJO)
                lineas.append(shad.Progress(value=uso, color=color))
                lineas.append(gris("Usas " + str(round(info["uso"] * 100)) + " % de tu límite (menos de 30 % es lo sano)"))
            botones.append(boton_chico("Pagar", lambda e: self.pagar_tarjeta(cuenta), shad.ButtonVariant.PRIMARY))
        elif cuenta["tipo"] == "inversion":
            valor = gastos.valor_inversion(self.datos, cuenta, hoy)
            puesto = gastos.aportado(self.datos, cuenta)
            diferencia = valor - puesto
            palabra = "Ganancia " if diferencia >= 0 else "Pérdida "
            lineas.append(texto("Valor hoy " + dinero(valor) + "   ·   Aportado " + dinero(puesto) + "   ·   " +
                                palabra + dinero(abs(diferencia)), color=ROJO if diferencia < 0 else TEXTO))
            detalle = monto_texto(cuenta.get("tasa", 0)) + " % al año"
            if cuenta.get("valores"):
                ultimo = cuenta["valores"][-1]
                detalle += "   ·   último valor anotado: " + dinero(ultimo["valor"]) + " el " + ultimo["fecha"]
            lineas.append(gris(detalle))
            lineas.append(self.grafica(gastos.historial_inversion(self.datos, cuenta, hoy)))
            botones.append(boton_chico("Registrar valor", lambda e: self.registrar_valor(cuenta),
                                       shad.ButtonVariant.PRIMARY))
        else:
            lineas.append(texto("Saldo " + dinero(gastos.saldo(self.datos, cuenta))))
        botones.append(boton_chico("Editar", lambda e: self.editar_cuenta(cuenta)))
        botones.append(boton_chico("Borrar", lambda e: self.borrar_cuenta(cuenta), shad.ButtonVariant.DESTRUCTIVE))
        titulo = cuenta["nombre"] + "  ·  " + NOMBRE_TIPO.get(cuenta["tipo"], cuenta["tipo"])
        return shad.Card(title=titulo, content=ft.Column(lineas, spacing=4), trailing=ft.Row(botones, tight=True),
                         padding=12)

    def registrar_valor(self, cuenta):
        # Anota cuánto vale hoy la inversión (lo ves en la app de tu banco o broker).
        def al_terminar(escrito):
            if escrito is None:
                return
            try:
                valor = float(escrito.replace(",", "").replace("$", "").strip())
            except ValueError:
                avisar(self.cta_msg, "El valor debe ser un número.", ROJO_SUAVE)
                return
            gastos.registrar_valor(cuenta, date.today(), valor)
            avisar(self.cta_msg, "Valor de " + cuenta["nombre"] + " anotado: " + dinero(valor) + ".", TEXTO)
            self.refrescar_todo()

        pedir_texto(self.app.page, "Valor actual de " + cuenta["nombre"], "ej. 10500", al_terminar)

    def grafica(self, puntos, ancho=560, alto=140):
        # Gráfica de línea dibujada a mano en un Canvas: cada tramo va gris si sube y rojo si baja.
        if len(puntos) < 2:
            return gris("La gráfica aparece cuando la inversión tenga más de un día.")
        valores = [p[1] for p in puntos]
        minimo, maximo = min(valores), max(valores)
        if maximo == minimo:
            maximo = minimo + 1
        margen = 8

        def x_de(i):
            return margen + i * (ancho - 2 * margen) / (len(puntos) - 1)

        def y_de(valor):
            # En pantalla "y" crece hacia abajo, por eso se resta desde abajo.
            return alto - margen - (valor - minimo) / (maximo - minimo) * (alto - 2 * margen)

        formas = []
        for i in range(1, len(puntos)):
            color = ROJO if valores[i] < valores[i - 1] else SUBE
            formas.append(cv.Line(x_de(i - 1), y_de(valores[i - 1]), x_de(i), y_de(valores[i]),
                                  paint=ft.Paint(color=color, stroke_width=3)))
        for i in range(len(puntos)):
            formas.append(cv.Circle(x_de(i), y_de(valores[i]), 3, paint=ft.Paint(color=SUBE)))
        return ft.Column([
            cv.Canvas(formas, width=ancho, height=alto),
            ft.Row([gris(str(puntos[0][0]), tamano=12), ft.Container(expand=True),
                    gris("mín " + dinero(min(valores)) + "  ·  máx " + dinero(max(valores)), tamano=12),
                    ft.Container(expand=True), gris(str(puntos[-1][0]), tamano=12)], width=ancho),
        ], spacing=2)

    def borrar_cuenta(self, cuenta):
        def si():
            if self.editando_cta is cuenta:
                self.cancelar_cuenta()
            gastos.borrar_cuenta(self.datos, cuenta["id"])
            self.refrescar_todo()

        confirmar(self.app.page, "¿Borrar la cuenta «" + cuenta["nombre"] + "»?", "No se puede deshacer.", si)

    # ---------- Programados (pagos e ingresos recurrentes) ----------
    def alternar_programados(self):
        self.prog_abierto = not self.prog_abierto
        self.refrescar_movimientos()

    def refrescar_programados(self, cuentaid):
        self.prog_lista.controls.clear()
        hoy = date.today()
        recurrentes = gastos.recurrentes_de(self.datos, cuentaid, self.mov_buscar.value)
        if not self.datos["recurrentes"]:
            self.prog_titulo.value = ("↺ Sin pagos recurrentes: elige «Repetir» al agregar un movimiento "
                                      "(Netflix, renta, sueldo…).")
            self.prog_titulo.color = GRIS
            self.prog_lista.visible = False
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
        self.prog_titulo.value = titulo
        self.prog_titulo.color = ROJO_SUAVE if pendientes else TEXTO
        self.prog_lista.visible = self.prog_abierto and bool(recurrentes)
        if not self.prog_lista.visible:
            return
        for rec in recurrentes:
            self.prog_lista.controls.append(self.fila_rec(rec, hoy))

    def fila_rec(self, rec, hoy):
        dias = (gastos.a_fecha(rec["proximafecha"]) - hoy).days
        if not rec["activo"]:
            cuando, color_fecha = "en pausa", GRIS
        elif dias < 0:
            cuando, color_fecha = "atrasado " + str(-dias) + " días", ROJO
        elif dias == 0:
            cuando, color_fecha = "hoy", ROJO_SUAVE
        else:
            cuando, color_fecha = "en " + str(dias) + " días", TEXTO
        cuenta = gastos.buscar_cuenta(self.datos, rec["cuentaid"])
        linea = rec["nombre"] + "   ·   " + rec["frecuencia"] + "   ·   " + (cuenta["nombre"] if cuenta else "?")
        if rec["automatico"]:
            linea += "   ·   automático"
        linea += "   ·   " + cuando
        if self.editando_rec is rec:
            linea = "✎ " + linea
        es_gasto = gastos.tipo_recurrente(rec) == "gasto"
        color_monto = (ROJO if es_gasto else GRIS_FUERTE) if rec["activo"] else GRIS
        fila = [
            ft.Container(texto(rec["proximafecha"], color=color_fecha), width=90),
            clicable(texto(linea, color=TEXTO if rec["activo"] else GRIS), lambda e: self.editar_rec(rec)),
            ft.Container(texto(("-" if es_gasto else "+") + dinero(rec["monto"]), color=color_monto), width=110,
                         alignment=ft.Alignment.CENTER_RIGHT),
        ]
        if rec["activo"]:
            fila.append(boton_chico("Registrar", lambda e: self.registrar(rec), shad.ButtonVariant.PRIMARY))
        fila.append(boton_chico("Pausar" if rec["activo"] else "Activar", lambda e: self.pausar(rec)))
        fila.append(boton_borrar(lambda e: self.borrar_rec(rec)))
        return ft.Row(fila)

    def registrar(self, rec):
        # Registra el cobro con fecha de hoy y avanza a la siguiente fecha.
        mov = gastos.registrar_recurrente(self.datos, rec, date.today())
        mensaje = rec["nombre"] + " registrado. Próximo: " + rec["proximafecha"] + "."
        aviso = None
        if mov["tipo"] == "gasto":
            aviso = gastos.aviso_presupuesto(self.datos, mov["categoria"], date.today())
        avisar(self.mov_msg, mensaje + ("  " + aviso if aviso else ""), ROJO_SUAVE if aviso else TEXTO)
        self.refrescar_todo()

    def pausar(self, rec):
        gastos.alternar_recurrente(rec)
        self.refrescar_todo()

    def borrar_rec(self, rec):
        def si():
            if self.editando_rec is rec:
                self.cancelar_mov()
            gastos.borrar_recurrente(self.datos, rec["id"])
            avisar(self.mov_msg, "Ya no se repite. Los movimientos que ya registraste se quedan.", TEXTO)
            self.refrescar_todo()

        confirmar(self.app.page, "¿Dejar de repetir «" + rec["nombre"] + "»?",
                  "Los movimientos que ya registraste se quedan.", si)

    # ================= Resumen =================
    def armar_resumen(self):
        self.res_mes = texto("", tamano=16, negrita=True, width=170, text_align=ft.TextAlign.CENTER)
        navegar = ft.Row([
            shad.IconButton(icon=shad.LucideIcons.CHEVRON_LEFT, variant=shad.ButtonVariant.OUTLINE,
                            on_click=lambda e: self.mover_mes(-1)),
            self.res_mes,
            shad.IconButton(icon=shad.LucideIcons.CHEVRON_RIGHT, variant=shad.ButtonVariant.OUTLINE,
                            on_click=lambda e: self.mover_mes(1)),
            boton_chico("Este mes", lambda e: self.mover_mes(0)),
        ])
        self.res_totales = texto("")
        self.res_lista = ft.Column(spacing=4)
        self.pre_categoria = shad.Select(options=opciones(self.opciones_categoria()), value="Comida",
                                         min_width=160, on_change=self.elegir_categoria)
        self.pre_monto = shad.Input(placeholder="Límite al mes", width=130, on_submit=lambda e: self.fijar_presupuesto())
        self.pre_msg = gris("0 quita el presupuesto.")
        forma = ft.Row([self.pre_categoria, self.pre_monto,
                        shad.Button("Fijar", on_click=lambda e: self.fijar_presupuesto()), self.pre_msg])
        self.res_presupuestos = ft.Column(spacing=4)
        self.res_pagos = ft.Column(spacing=4)
        return ft.Column([
            navegar,
            self.res_totales,
            texto("Gastos por categoría", tamano=16, negrita=True),
            caja(self.res_lista),
            texto("Presupuestos del mes", tamano=16, negrita=True),
            forma,
            caja(self.res_presupuestos),
            texto("Próximos pagos (7 días)", tamano=16, negrita=True),
            caja(self.res_pagos),
        ], expand=True, scroll=ft.ScrollMode.AUTO, spacing=10)

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
        categoria_elegida = self.pre_categoria.value
        if categoria_elegida == NUEVA_CATEGORIA:
            avisar(self.pre_msg, "Elige una categoría.", ROJO_SUAVE)
            return
        categoria = gastos.fijar_presupuesto(self.datos, categoria_elegida, monto)
        self.pre_monto.value = ""
        mensaje = "Presupuesto de " + categoria + " quitado." if monto <= 0 else "Presupuesto de " + categoria + " guardado."
        avisar(self.pre_msg, mensaje, TEXTO)
        self.refrescar_todo()

    def fila_barra(self, nombre, proporcion, derecha, color=None, color_texto=None, ancho=150):
        return ft.Row([
            ft.Container(texto(nombre), width=150),
            ft.Container(shad.Progress(value=proporcion, color=color), expand=True),
            ft.Container(texto(derecha, color=color_texto), width=ancho, alignment=ft.Alignment.CENTER_RIGHT),
        ])

    def refrescar_resumen(self):
        for marco in (self.res_lista, self.res_presupuestos, self.res_pagos):
            marco.controls.clear()
        mes = self.mes_resumen
        self.res_mes.value = nombre_mes(mes)
        gastado, ingresado = gastos.totales_mes(self.datos, mes)
        anterior = gastos.sumar_meses(mes, -1, 1)
        gastado_antes = gastos.totales_mes(self.datos, anterior)[0]
        resumen = ("Gastaste " + dinero(gastado) + "   ·   Ingresaste " + dinero(ingresado) +
                   "   ·   Balance " + dinero(ingresado - gastado))
        if gastado_antes > 0:
            cambio = round((gastado - gastado_antes) / gastado_antes * 100)
            resumen += "\n" + ("+" if cambio > 0 else "") + str(cambio) + " % de gasto comparado con " + MESES[anterior.month - 1]
        self.res_totales.value = resumen

        filas = gastos.resumen_por_categoria(self.datos, gastos.inicio_mes(mes), gastos.fin_mes(mes))
        for fila in filas:
            porcentaje = round(fila[1] / gastado * 100) if gastado else 0
            self.res_lista.controls.append(self.fila_barra(fila[0], fila[1] / gastado if gastado else 0,
                                                           dinero(fila[1]) + "  (" + str(porcentaje) + " %)"))
        if not filas:
            self.res_lista.controls.append(gris("Sin gastos este mes."))

        presupuestos = gastos.estado_presupuestos(self.datos, mes)
        for categoria, usado, limite in presupuestos:
            proporcion = usado / limite
            color = GRIS_FUERTE if proporcion < gastos.AVISO_PRESUPUESTO else (ROJO_SUAVE if proporcion <= 1 else ROJO)
            if usado <= limite:
                queda = "quedan " + dinero(limite - usado)
            else:
                queda = "te pasaste " + dinero(usado - limite)
            self.res_presupuestos.controls.append(self.fila_barra(
                categoria, min(proporcion, 1), dinero(usado) + " de " + dinero(limite) + " · " + queda,
                color=color, color_texto=color if proporcion > 1 else TEXTO, ancho=260))
        if not presupuestos:
            self.res_presupuestos.controls.append(gris("Pon un límite mensual a una categoría y aquí verás cuánto te queda."))

        hoy = date.today()
        pagos = gastos.proximos_pagos(self.datos, hoy)
        for pago in pagos:
            dias = (pago[0] - hoy).days
            cuando = "hoy" if dias == 0 else ("atrasado" if dias < 0 else "en " + str(dias) + " días")
            self.res_pagos.controls.append(texto(str(pago[0]) + "  " + pago[1] + "  " + dinero(pago[2]) + "  (" + cuando + ")",
                                                 color=ROJO if dias < 0 else TEXTO))
        if not pagos:
            self.res_pagos.controls.append(gris("Nada en los próximos 7 días."))
