# pantalla_notas.py
# Menú de notas a la izquierda (con buscador) y editor a la derecha.
import asyncio
import flet as ft
import flet_shadcn_ui as shad
from m import notas
from m import ocr
from m import materias
from m import palabras_clave
from m import obsidian
from pantallas.colores import ROJO, BORDE, TEXTO
from pantallas.comun import texto, gris, caja, opciones, avisar, pedir_texto

AGREGAR = "+ Agregar materia"
EXTENSIONES_FOTO = ["png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"]


class PantallaNotas:
    def __init__(self, app):
        self.app = app
        self.nota = None
        self.selector = ft.FilePicker()   # ventana de Windows para elegir la foto

        # ----- Menú de notas -----
        self.buscador = shad.Input(placeholder="Buscar en notas y palabras clave",
                                   leading=shad.LucideIcons.SEARCH, on_change=lambda e: self.refrescar())
        self.lista = ft.ListView(expand=True, spacing=6)
        self.izq = caja(ft.Column([
            self.buscador,
            shad.Button("Nueva nota", leading=shad.LucideIcons.PLUS, on_click=lambda e: self.nueva()),
            shad.Button("Exportar a Obsidian", leading=shad.LucideIcons.BOOK_OPEN,
                        variant=shad.ButtonVariant.OUTLINE, on_click=self.exportar_obsidian),
            self.lista,
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), expand=2)

        # ----- Editor -----
        # Botón para ocultar/mostrar la lista. Cuando la lista se oculta (visible=False) no ocupa espacio,
        # así que el editor (expand=3) se queda solo en la fila y crece hasta ocupar todo el ancho.
        self.boton_panel = shad.Tooltip(message="Ocultar / mostrar la lista de notas", content=shad.IconButton(
            icon=shad.LucideIcons.PANEL_LEFT_CLOSE, variant=shad.ButtonVariant.OUTLINE,
            on_click=lambda e: self.alternar_panel()))
        self.materia = shad.Select(options=opciones(self.opciones_materia()), value=self.opciones_materia()[0],
                                   min_width=150, on_change=self.elegir_materia)
        self.boton_foto = shad.Button("Foto → texto", leading=shad.LucideIcons.CAMERA,
                                      variant=shad.ButtonVariant.OUTLINE, on_click=self.foto_a_texto)
        self.editor = shad.Textarea(placeholder="Escribe tu nota…", expand=True, min_height=340,
                                    max_height=4000, resizable=False)
        self.info = gris("")
        self.mensaje = texto("")
        der = caja(ft.Column([
            ft.Row([self.boton_panel, texto("Materia:"), self.materia, ft.Container(expand=True), self.boton_foto]),
            gris("La primera línea es el título."),
            self.editor,
            self.info,
            ft.Row([shad.Button("Guardar nota", leading=shad.LucideIcons.SAVE, on_click=lambda e: self.guardar()),
                    self.mensaje]),
        ], expand=True), expand=3)

        self.vista = ft.Row([self.izq, der], expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        self.nueva()
        self.refrescar()

    def alternar_panel(self):
        self.izq.visible = not self.izq.visible
        boton = self.boton_panel.content
        boton.icon = shad.LucideIcons.PANEL_LEFT_CLOSE if self.izq.visible else shad.LucideIcons.PANEL_LEFT_OPEN

    # ----- Materias (compartidas con Tareas) -----
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

        pedir_texto(self.app.page, "Agregar materia", "Nombre de la materia", al_terminar)

    # ----- Menú -----
    def refrescar(self):
        self.lista.controls.clear()
        for nota in notas.buscar(self.app.notas, self.buscador.value):
            self.lista.controls.append(self.tarjeta(nota))

    def tarjeta(self, nota):
        lineas = nota["texto"].strip().splitlines()
        vista = " ".join(lineas[1:])[:70]
        detalle = vista + "\n" + nota["materia"] + " · " + nota["fechacreacion"]
        if nota["palabrasclave"]:
            detalle += "\n# " + "  # ".join(nota["palabrasclave"])
        textos = ft.Column([texto(notas.titulo(nota), tamano=15, negrita=True), gris(detalle, tamano=12)],
                           spacing=2, expand=True)
        botones = ft.Column([
            shad.IconButton(icon=shad.LucideIcons.ARROW_UP, variant=shad.ButtonVariant.GHOST,
                            on_click=lambda e: self.subir(nota)),
            shad.IconButton(icon=shad.LucideIcons.X, variant=shad.ButtonVariant.GHOST, color=ROJO,
                            on_click=lambda e: self.borrar(nota)),
        ], spacing=0)
        elegida = nota is self.nota
        return ft.Container(ft.Row([textos, botones]), padding=8, border_radius=8,
                            border=ft.Border.all(2 if elegida else 1, TEXTO if elegida else BORDE),
                            on_click=lambda e: self.abrir(nota))

    # ----- Acciones -----
    def nueva(self):
        self.nota = notas.crear(self.materia.value)
        self.editor.value = ""
        self.info.value = "Nota nueva"
        avisar(self.mensaje, "")

    def abrir(self, nota):
        self.nota = nota
        self.editor.value = nota["texto"]
        if nota["materia"] in self.app.materias:
            self.materia.value = nota["materia"]
        self.info.value = "Creada: " + nota["fechacreacion"] + "   Palabras clave: " + ", ".join(nota["palabrasclave"])
        avisar(self.mensaje, "")
        self.refrescar()

    def guardar(self):
        texto_nota = self.editor.value.rstrip("\n")
        self.nota["texto"] = texto_nota
        materia = self.materia.value
        if materia != AGREGAR:
            self.nota["materia"] = materia
        self.nota["palabrasclave"] = palabras_clave.extraer(texto_nota)
        tipo = notas.guardar(self.app.notas, self.nota)
        mensajes = {"creacion": "La nota se creó.", "actualizacion": "La nota se actualizó.",
                    "borrada": "La nota estaba vacía: no se guardó."}
        avisar(self.mensaje, mensajes[tipo])
        if tipo == "borrada":
            self.nota = notas.crear(self.materia.value)
        else:
            self.info.value = "Creada: " + self.nota["fechacreacion"] + "   Palabras clave: " + ", ".join(self.nota["palabrasclave"])
        self.refrescar()

    # ----- Foto -> texto -----
    async def foto_a_texto(self, e):
        # "async": mientras se lee la foto, la ventana sigue respondiendo.
        archivos = await self.selector.pick_files(dialog_title="Elige una foto",
                                                  file_type=ft.FilePickerFileType.CUSTOM,
                                                  allowed_extensions=EXTENSIONES_FOTO)
        if not archivos:
            return
        self.boton_foto.disabled = True
        self.boton_foto.content = "Leyendo…"
        aviso = "Leyendo la foto…" if ocr.listo() else "Cargando el modelo de letra a mano (la primera vez lo descarga, ~1.4 GB)…"
        avisar(self.mensaje, aviso)
        self.app.page.update()   # mostrar "Leyendo…" antes de empezar a esperar
        try:
            # to_thread: el trabajo pesado corre en otro hilo y aquí solo esperamos el resultado
            valor = await asyncio.to_thread(ocr.foto_a_texto, archivos[0].path)
            error = None
        except ocr.OCRNoInstalado as err:
            valor, error = "", str(err)
        except Exception as err:
            valor, error = "", "No se pudo leer la foto: " + str(err)
        self.boton_foto.disabled = False
        self.boton_foto.content = "Foto → texto"
        if error:
            avisar(self.mensaje, error)
        elif not valor.strip():
            avisar(self.mensaje, "No encontré texto en la foto.")
        else:
            actual = self.editor.value
            if actual and not actual.endswith("\n"):
                actual += "\n"
            self.editor.value = actual + valor + "\n"   # se agrega al final de la nota
            avisar(self.mensaje, "Texto agregado. Revísalo y guarda la nota.")
        self.app.page.update()

    # ----- Exportar a Obsidian -----
    async def exportar_obsidian(self, e):
        carpeta = await self.selector.get_directory_path(dialog_title="Carpeta de tu bóveda de Obsidian")
        if not carpeta:
            return
        try:
            cantidad = obsidian.exportar(self.app.notas, carpeta)
            avisar(self.mensaje, "Exportadas " + str(cantidad) + " notas a " + carpeta)
        except OSError as err:
            avisar(self.mensaje, "No se pudo exportar: " + str(err), ROJO)
        self.app.page.update()

    def subir(self, nota):
        notas.mover(self.app.notas, nota["id"], 0)
        self.refrescar()

    def borrar(self, nota):
        notas.borrar(self.app.notas, nota["id"])
        if nota is self.nota:
            self.nueva()
        self.refrescar()
