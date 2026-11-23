# pantalla_tareas.py
# Formulario arriba, filtro y lista de tareas abajo.
from datetime import date, datetime, time, timedelta
import flet as ft
import flet_shadcn_ui as shad
from m import tareas
from m import materias
from pantallas.colores import ROJO, ROJO_SUAVE, TEXTO, GRIS
from pantallas.comun import texto, gris, caja, opciones, avisar, pedir_texto

AGREGAR = "+ Agregar materia"
FILTROS = ["Activas", "Vencidas", "Completadas", "Todas"]
HORA_POR_DEFECTO = time(23, 59)


def a_dia(valor):
    # El calendario devuelve un datetime (medianoche UTC); nosotros solo queremos el día.
    if isinstance(valor, datetime):
        return valor.date()
    return valor


class PantallaTareas:
    def __init__(self, app):
        self.app = app
        self.tarea = None   # None = creando una nueva; si no, la tarea que se está editando

        # ----- Formulario -----
        self.titulo = shad.Input(placeholder="¿Qué hay que hacer?", expand=True, on_submit=lambda e: self.guardar())
        self.materia = shad.Select(options=opciones(self.opciones_materia()), value=self.opciones_materia()[0],
                                   min_width=150, on_change=self.elegir_materia)
        # El calendario da el día y el reloj la hora; al guardar se juntan en "2026-11-20 23:59".
        self.dia = shad.DatePicker(placeholder="Elige el día", label="Fecha límite")
        self.hora = shad.TimePicker(label="Hora", hour_label="h", minute_label="min")
        # Un solo botón: "Agregar" al crear y "Guardar cambios" al editar. Cancelar solo aparece al editar.
        self.boton = shad.Button("Agregar", leading=shad.LucideIcons.PLUS, width=170, on_click=lambda e: self.guardar())
        self.cancelar = shad.Button("Cancelar", variant=shad.ButtonVariant.SECONDARY, visible=False,
                                    on_click=lambda e: self.nueva())
        self.mensaje = texto("")
        form = caja(ft.Column([
            ft.Row([self.titulo, self.materia]),
            ft.Row([self.dia, self.hora, ft.Container(expand=True), self.cancelar, self.boton],
                   vertical_alignment=ft.CrossAxisAlignment.END),
            self.mensaje,
        ]))

        # ----- Filtro y lista -----
        self.filtro = shad.Tabs(value="Activas", tabs=[shad.Tab(value=f, label=f) for f in FILTROS],
                                on_change=lambda e: self.refrescar())
        self.lista = ft.ListView(expand=True, spacing=2)

        # Las pestañas de shadcn necesitan un ancho fijo; sin él no se dibujan.
        self.vista = ft.Column([form, ft.Container(self.filtro, width=460), caja(self.lista, expand=True)], expand=True)
        self.nueva()
        self.refrescar()

    # ----- Materias (compartidas con Notas) -----
    def opciones_materia(self):
        lista = list(self.app.materias)
        if not lista:
            lista = ["General"]
        lista.append(AGREGAR)
        return lista

    def actualizar_materias(self):
        # La llama la app cuando otra pantalla agrega una materia.
        valores = self.opciones_materia()
        self.materia.options = opciones(valores)
        if self.materia.value not in valores or self.materia.value == AGREGAR:
            self.materia.value = valores[0]

    def elegir_materia(self, e):
        if self.materia.value != AGREGAR:
            return

        def al_terminar(nombre):
            if nombre and materias.agregar(self.app.materias, nombre):
                self.app.materias_cambiaron()
                self.materia.value = nombre.strip()
            else:
                self.materia.value = self.opciones_materia()[0]

        pedir_texto(self.app.page, "Agregar materia", "Nombre de la materia o categoría", al_terminar)

    # ----- Formulario -----
    def nueva(self):
        self.tarea = None
        self.titulo.value = ""
        self.dia.value = date.today() + timedelta(days=1)
        self.hora.value = HORA_POR_DEFECTO
        self.boton.content = "Agregar"
        self.boton.leading = shad.LucideIcons.PLUS
        self.cancelar.visible = False
        avisar(self.mensaje, "")
        self.refrescar()

    def editar(self, tarea):
        self.tarea = tarea
        self.titulo.value = tarea["titulo"]
        limite = datetime.strptime(tarea["fechalimite"], tareas.FECHA)
        self.dia.value = limite.date()
        self.hora.value = limite.time()
        if tarea["materia"] in self.app.materias:
            self.materia.value = tarea["materia"]
        self.boton.content = "Guardar cambios"
        self.boton.leading = shad.LucideIcons.SAVE
        self.cancelar.visible = True
        avisar(self.mensaje, "Editando «" + tarea["titulo"] + "». Cambia lo que quieras y pulsa Guardar cambios.", GRIS)
        self.refrescar()

    def fecha_elegida(self):
        dia = a_dia(self.dia.value)
        if dia is None:
            return None
        hora = self.hora.value or HORA_POR_DEFECTO
        return datetime.combine(dia, hora).strftime(tareas.FECHA)

    def guardar(self):
        limite = self.fecha_elegida()
        if limite is None:
            avisar(self.mensaje, "Elige el día en el calendario.", ROJO_SUAVE)
            return
        materia = self.materia.value
        if materia == AGREGAR:
            materia = ""
        if self.tarea is None:
            tarea = tareas.crear(self.titulo.value, limite, materia)
        else:
            tarea = self.tarea
            tarea["titulo"] = self.titulo.value
            tarea["fechalimite"] = limite
            tarea["materia"] = materia
        tipo = tareas.guardar(self.app.tareas, tarea)
        mensajes = {"creacion": "La tarea se creó.", "actualizacion": "La tarea se actualizó.",
                    "borrada": "Sin título no se guarda."}
        self.nueva()
        avisar(self.mensaje, mensajes[tipo])

    # ----- Lista -----
    def estado_de(self, tarea):
        if tarea["estado"] == "completada":
            return "Completada"
        if tareas.esta_vencida(tarea):
            return "Vencida"
        return "Activa"

    def refrescar(self):
        # En Flet no se destruyen los widgets: se vacía la lista de controles y se llena de nuevo.
        self.lista.controls.clear()
        filtro = self.filtro.value
        for tarea in self.app.tareas:
            estado = self.estado_de(tarea)
            if filtro == "Activas" and estado != "Activa":
                continue
            if filtro == "Vencidas" and estado != "Vencida":
                continue
            if filtro == "Completadas" and estado != "Completada":
                continue
            self.lista.controls.append(self.fila(tarea, estado))
        if not self.lista.controls:
            self.lista.controls.append(ft.Container(gris("No hay tareas aquí."), padding=20,
                                                    alignment=ft.Alignment.CENTER))

    def fila(self, tarea, estado):
        marca = shad.Checkbox(value=estado == "Completada", on_change=lambda e: self.alternar(tarea))
        # Toda la fila se puede pulsar para editarla; el lápiz lo hace más evidente.
        datos = ft.Container(
            ft.Column([texto(tarea["titulo"]), gris(tarea["materia"] + " · límite " + tarea["fechalimite"], tamano=12)],
                      spacing=0),
            expand=True, on_click=lambda e: self.editar(tarea))
        variante = {"Vencida": shad.BadgeVariant.DESTRUCTIVE, "Completada": shad.BadgeVariant.SECONDARY,
                    "Activa": shad.BadgeVariant.OUTLINE}[estado]
        lapiz = shad.Tooltip(message="Editar", content=shad.IconButton(
            icon=shad.LucideIcons.PENCIL, variant=shad.ButtonVariant.GHOST, on_click=lambda e: self.editar(tarea)))
        borrar = shad.IconButton(icon=shad.LucideIcons.X, variant=shad.ButtonVariant.GHOST, color=ROJO,
                                 on_click=lambda e: self.borrar(tarea))
        editando = tarea is self.tarea
        return ft.Container(ft.Row([marca, datos, shad.Badge(estado, variant=variante), lapiz, borrar]),
                            padding=ft.Padding.symmetric(horizontal=4, vertical=2), border_radius=8,
                            border=ft.Border.all(2 if editando else 1, TEXTO if editando else ft.Colors.TRANSPARENT))

    def alternar(self, tarea):
        if tarea["estado"] == "completada":
            tareas.reabrir(tarea)
        else:
            tareas.completar(tarea)
        self.refrescar()

    def borrar(self, tarea):
        tareas.borrar(self.app.tareas, tarea["id"])
        if tarea is self.tarea:
            self.nueva()
        self.refrescar()
