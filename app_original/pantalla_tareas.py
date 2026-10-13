"""Pantalla de administración de tareas."""

from datetime import datetime, timedelta, date, time

import customtkinter as ctk

from modelos import tiempo_restante
from ui_comun import (C, fuente, boton, Pestanas, Encabezado, BarraAviso, SelectorFecha, HORAS,
                      leer_hora, crear_tabla, limpiar_tabla, Dialogo, confirmar, menu_contextual, limpiar_entrada)


class PantallaTareas(ctk.CTkFrame):

    def __init__(self, padre, app):
        super().__init__(padre, fg_color=C["fondo"], corner_radius=0)
        self.app = app
        self.store = app.tareas
        self.filtro = "pendiente"

        self.encabezado = Encabezado(self, "Tareas", app.mostrar_inicio)
        self.encabezado.pack(fill="x", padx=24, pady=(20, 14))

        self._crear_formulario()
        self._crear_lista()

        self.aviso = BarraAviso(self)
        self.aviso.pack(fill="x", padx=24, pady=(0, 10))

    # ---------------------------------------------------------- formulario

    def _crear_formulario(self):
        tarjeta = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=12)
        tarjeta.pack(fill="x", padx=24)

        fila1 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila1.pack(fill="x", padx=14, pady=(14, 6))

        self.e_nombre = ctk.CTkEntry(fila1, placeholder_text="¿Qué tienes que hacer?  (Enter para agregar)",
                                     height=38, font=fuente(14))
        self.e_nombre.pack(side="left", fill="x", expand=True)
        self.e_nombre.bind("<Return>", lambda e: self.agregar())

        self.e_fecha = SelectorFecha(fila1, date.today() + timedelta(days=1))
        self.e_fecha.pack(side="left", padx=(10, 6))

        self.e_hora = ctk.CTkComboBox(fila1, values=HORAS, width=90)
        self.e_hora.set("23:59")
        self.e_hora.pack(side="left")

        boton(fila1, "＋ Agregar", self.agregar, width=110, height=38).pack(side="left", padx=(10, 0))

        fila2 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        fila2.pack(fill="x", padx=14, pady=(0, 14))

        self.e_desc = ctk.CTkEntry(fila2, placeholder_text="Descripción (opcional)")
        self.e_desc.pack(side="left", fill="x", expand=True)
        self.e_desc.bind("<Return>", lambda e: self.agregar())

        ctk.CTkLabel(fila2, text="Rápido:", text_color=C["suave"], font=fuente(12)).pack(side="left", padx=(12, 4))
        for texto, dias in (("Hoy", 0), ("Mañana", 1), ("1 semana", 7)):
            ctk.CTkButton(fila2, text=texto, width=70, height=28, corner_radius=14, font=fuente(12),
                          fg_color=C["panel2"], hover_color=C["borde"], text_color=C["texto"],
                          command=lambda d=dias: self._fecha_rapida(d)).pack(side="left", padx=2)

    def _fecha_rapida(self, dias):
        self.e_fecha.set(date.today() + timedelta(days=dias))
        self.e_hora.set("23:59")
        self.e_nombre.focus_set()

    def _leer_fecha_hora(self, selector, combo):
        f = selector.get()
        h = leer_hora(combo.get())
        if f is None or h is None:
            return None
        return datetime.combine(f, time(h.hour, h.minute))

    def agregar(self):
        nombre = self.e_nombre.get().strip()
        if not nombre:
            self.aviso.mostrar("Escribe el nombre de la tarea.", "error")
            self.e_nombre.focus_set()
            return
        fecha = self._leer_fecha_hora(self.e_fecha, self.e_hora)
        if fecha is None:
            self.aviso.mostrar("Fecha u hora no válida. Usa el calendario 📅 y una hora como 18:30.", "error")
            return
        tarea = self.store.agregar(nombre, fecha, self.e_desc.get().strip())
        limpiar_entrada(self.e_nombre)
        limpiar_entrada(self.e_desc)
        self.e_nombre.focus_set()
        if tarea["estado"] == "expirada":
            self.aviso.mostrar(f"«{nombre}» se agregó, pero su fecha ya pasó: está en Expiradas.", "aviso")
        else:
            self.aviso.mostrar(f"✓ «{nombre}» agregada para el {fecha.strftime('%d/%m %H:%M')}.")
        self.refrescar()
        self.after(50, self.app.revisar_alertas)

    # ---------------------------------------------------------- lista

    def _crear_lista(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=24, pady=(16, 8))

        self.pestanas = Pestanas(barra, [("pendiente", "Pendientes"), ("completada", "Completadas"),
                                         ("expirada", "Expiradas")], self._cambiar_filtro)
        self.pestanas.pack(side="left")

        self.e_buscar = ctk.CTkEntry(barra, placeholder_text="🔍 Buscar…", width=220)
        self.e_buscar.pack(side="right")
        self.e_buscar.bind("<KeyRelease>", lambda e: self.refrescar())

        marco, self.tree = crear_tabla(self, [
            ("nombre", "Tarea", 240, "w", True),
            ("fecha", "Fecha límite", 150, "center", False),
            ("resta", "Tiempo restante", 130, "center", False),
            ("desc", "Descripción", 320, "w", True),
        ])
        marco.pack(fill="both", expand=True, padx=24)

        self.tree.bind("<Double-1>", lambda e: self.editar())
        self.tree.bind("<Delete>", lambda e: self.eliminar())
        self.tree.bind("<Return>", lambda e: self.completar_o_reabrir())
        self.tree.bind("<Button-3>", self._menu)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._actualizar_botones())

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.pack(fill="x", padx=24, pady=10)
        self.b_completar = boton(acciones, "✓ Completar", self.completar_o_reabrir, "ok", width=140)
        self.b_completar.pack(side="left")
        self.b_editar = boton(acciones, "✎ Editar", self.editar, "neutro", width=100)
        self.b_editar.pack(side="left", padx=8)
        self.b_eliminar = boton(acciones, "🗑 Eliminar", self.eliminar, "neutro", width=110)
        self.b_eliminar.pack(side="left")
        ctk.CTkLabel(acciones, text="Doble clic: editar · Supr: eliminar · Clic derecho: más opciones",
                     text_color=C["suave"], font=fuente(12)).pack(side="right")

    def _cambiar_filtro(self, clave):
        self.filtro = clave
        self.refrescar()

    def refrescar(self):
        self.store.actualizar_estados()
        texto = self.e_buscar.get().lower().strip()
        ahora = datetime.now()
        seleccion = self.tree.selection()
        limpiar_tabla(self.tree)

        tareas = [t for t in self.store.tareas if t.get("estado") == self.filtro]
        if texto:
            tareas = [t for t in tareas if texto in t.get("nombre", "").lower()
                      or texto in t.get("descripcion", "").lower()]
        lejana = datetime.max
        tareas.sort(key=lambda t: self.store.fecha_de(t) or lejana, reverse=(self.filtro != "pendiente"))

        for i, t in enumerate(tareas):
            fecha = self.store.fecha_de(t)
            etiquetas = ["par" if i % 2 == 0 else "impar"]
            if self.filtro == "pendiente" and fecha:
                resta = tiempo_restante(fecha, ahora)
                if fecha - ahora <= timedelta(hours=12):
                    etiquetas.append("urgente")
            elif self.filtro == "completada":
                resta = "Hecha ✓"
                etiquetas.append("apagado")
            else:
                resta = "Vencida"
                etiquetas.append("vencida")
            self.tree.insert("", "end", iid=t["id"], tags=etiquetas, values=(
                t.get("nombre", ""),
                fecha.strftime("%d/%m/%Y %H:%M") if fecha else t.get("fecha_limite", ""),
                resta,
                t.get("descripcion", "").replace("\n", " "),
            ))

        if seleccion and self.tree.exists(seleccion[0]):
            self.tree.selection_set(seleccion[0])

        nombres = {"pendiente": "Pendientes", "completada": "Completadas", "expirada": "Expiradas"}
        for clave, nombre in nombres.items():
            self.pestanas.texto(clave, f"{nombre}  {self.store.contar(clave)}")
        total = len(self.store.tareas)
        hechas = self.store.contar("completada")
        self.encabezado.derecha.configure(text=f"{hechas} de {total} completadas" if total else "")
        self._actualizar_botones()

    def _actualizar_botones(self):
        if self.filtro == "completada":
            self.b_completar.configure(text="↺ Reabrir", fg_color=C["neutro"], hover_color=C["neutro_hover"])
        else:
            self.b_completar.configure(text="✓ Completar", fg_color=C["ok"], hover_color=C["ok_hover"])
        estado = "normal" if self.tree.selection() else "disabled"
        for b in (self.b_completar, self.b_editar, self.b_eliminar):
            b.configure(state=estado)

    def _seleccion(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _menu(self, evento):
        fila = self.tree.identify_row(evento.y)
        if not fila:
            return
        self.tree.selection_set(fila)
        texto = "↺ Reabrir" if self.filtro == "completada" else "✓ Marcar completada"
        menu = menu_contextual(self.tree, [
            (texto, self.completar_o_reabrir),
            ("✎ Editar", self.editar),
            None,
            ("🗑 Eliminar", self.eliminar),
        ])
        menu.tk_popup(evento.x_root, evento.y_root)

    # ---------------------------------------------------------- acciones

    def completar_o_reabrir(self):
        tid = self._seleccion()
        if not tid:
            return
        tarea = self.store.buscar(tid)
        if self.filtro == "completada":
            self.store.cambiar_estado(tid, "pendiente")
            self.aviso.mostrar(f"«{tarea['nombre']}» se volvió a abrir.", "info")
        else:
            self.store.cambiar_estado(tid, "completada")
            self.aviso.mostrar(f"✓ «{tarea['nombre']}» completada. ¡Bien hecho!")
        self.refrescar()

    def eliminar(self):
        tid = self._seleccion()
        if not tid:
            return
        tarea = self.store.buscar(tid)
        if confirmar(self.winfo_toplevel(), "Eliminar tarea", f"¿Eliminar «{tarea['nombre']}»? No se puede deshacer."):
            self.store.eliminar(tid)
            self.aviso.mostrar("Tarea eliminada.", "info")
            self.refrescar()

    def editar(self):
        tid = self._seleccion()
        if not tid:
            return
        DialogoTarea(self, self.store.buscar(tid)).mostrar()


class DialogoTarea(Dialogo):

    def __init__(self, pantalla, tarea):
        super().__init__(pantalla.winfo_toplevel(), "Editar tarea")
        self.pantalla = pantalla
        self.tarea = tarea
        fecha = pantalla.store.fecha_de(tarea) or datetime.now()

        self.nombre = self.campo("Nombre", ctk.CTkEntry(self.cuerpo, width=340))
        self.nombre.insert(0, tarea["nombre"])

        fila = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.fecha = SelectorFecha(fila, fecha.date())
        self.fecha.pack(side="left")
        self.hora = ctk.CTkComboBox(fila, values=HORAS, width=90)
        self.hora.set(fecha.strftime("%H:%M"))
        self.hora.pack(side="left", padx=(8, 0))
        self.campo("Fecha límite", fila)

        self.desc = self.campo("Descripción", ctk.CTkTextbox(self.cuerpo, height=110, width=340))
        self.desc.insert("1.0", tarea.get("descripcion", ""))
        self.nombre.focus_set()

    def aceptar(self):
        nombre = self.nombre.get().strip()
        if not nombre:
            self.fallar("El nombre no puede estar vacío.")
            return False
        f = self.fecha.get()
        h = leer_hora(self.hora.get())
        if f is None or h is None:
            self.fallar("Fecha u hora no válida.")
            return False
        nueva = datetime.combine(f, time(h.hour, h.minute))
        self.pantalla.store.editar(self.tarea["id"], nombre, nueva, self.desc.get("1.0", "end").strip())
        self.pantalla.aviso.mostrar("✓ Cambios guardados.")
        self.pantalla.refrescar()
        return True
