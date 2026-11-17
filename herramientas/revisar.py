# revisar.py
# Ventana para confirmar cada renglón antes de entrenar: ves el recorte de tu foto, el texto propuesto
# (corregido por Claude o leído por el modelo) y lo arreglas si hace falta.
#   Enter  = Aceptar (queda "ok" y se usa para entrenar)
#   Ctrl+D = Descartar (recorte malo: no se usa)
#   Ctrl+← = Anterior
# Cada cambio se guarda al momento en labels.csv: puedes cerrar y seguir después.
#
# Uso:  python herramientas/revisar.py            (solo los que faltan por confirmar)
#       python herramientas/revisar.py --todos    (también los ya aceptados o descartados)
#       python herramientas/revisar.py --descartados pagina_18 pagina_19
#                                   (los descartados de esas fotos, para escribirles tú el texto)
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import customtkinter as ctk  # noqa: E402
from PIL import Image  # noqa: E402
import etiquetas  # noqa: E402

ANCHO_IMAGEN = 1000
ALTO_MAX_IMAGEN = 220
COLOR_ESTADO = {"pendiente": "#e5a50a", "claude": "#3584e4", "ok": "#2ec27e", "descartado": "#c01c28"}
TEXTO_ESTADO = {"pendiente": "Leído solo por el modelo", "claude": "Corregido por Claude",
                "ok": "Aceptado", "descartado": "Descartado"}


class Revisor(ctk.CTk):
    def __init__(self, todos=False, descartados=None):
        super().__init__()
        self.title("Revisar renglones")
        self.geometry("1080x520")
        self.datos = etiquetas.todas()
        def entra(fila):
            if descartados is not None:   # solo descartados (de las fotos indicadas, si se dieron)
                return fila["estado"] == "descartado" and (
                    not descartados or any(fila["filename"].startswith(f + "_") for f in descartados))
            return todos or fila["estado"] in etiquetas.SIN_CONFIRMAR

        self.lista = [(parte, fila) for parte, filas in self.datos.items() for fila in filas if entra(fila)]
        self.i = 0
        self.grid_columnconfigure(0, weight=1)

        self.progreso = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.progreso.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        self.imagen = ctk.CTkLabel(self, text="")
        self.imagen.grid(row=1, column=0, padx=16, pady=6)
        self.estado = ctk.CTkLabel(self, text="")
        self.estado.grid(row=2, column=0, sticky="w", padx=16)
        self.texto = ctk.CTkEntry(self, font=ctk.CTkFont(size=18), height=40)
        self.texto.grid(row=3, column=0, sticky="ew", padx=16, pady=6)
        self.original = ctk.CTkLabel(self, text="", text_color="gray", anchor="w", justify="left", wraplength=1000)
        self.original.grid(row=4, column=0, sticky="ew", padx=16)

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.grid(row=5, column=0, sticky="ew", padx=16, pady=12)
        ctk.CTkButton(botones, text="← Anterior", width=110, command=self.anterior).pack(side="left")
        ctk.CTkButton(botones, text="Descartar (Ctrl+D)", width=150, fg_color="#c01c28", hover_color="#a51d2d",
                      command=self.descartar).pack(side="left", padx=8)
        ctk.CTkButton(botones, text="Aceptar (Enter)", width=150, fg_color="#26a269", hover_color="#1f8a59",
                      command=self.aceptar).pack(side="right")
        self.bind("<Return>", lambda e: self.aceptar())
        self.bind("<Control-d>", lambda e: self.descartar())
        self.bind("<Control-Left>", lambda e: self.anterior())
        self.mostrar()

    def mostrar(self):
        if not self.lista:
            self.terminar("No hay renglones por revisar.")
            return
        if self.i >= len(self.lista):
            self.terminar()
            return
        parte, fila = self.lista[self.i]
        self.progreso.configure(text=f"Renglón {self.i + 1} de {len(self.lista)}   ·   {parte}/{fila['filename']}")
        img = Image.open(etiquetas.ruta_imagen(parte, fila)).convert("RGB")
        escala = min(ANCHO_IMAGEN / img.width, ALTO_MAX_IMAGEN / img.height, 2.0)
        tam = (max(1, int(img.width * escala)), max(1, int(img.height * escala)))
        self.foto = ctk.CTkImage(light_image=img, dark_image=img, size=tam)   # guardar referencia o desaparece
        self.imagen.configure(image=self.foto)
        self.estado.configure(text="● " + TEXTO_ESTADO.get(fila["estado"], fila["estado"]),
                              text_color=COLOR_ESTADO.get(fila["estado"], "gray"))
        self.texto.delete(0, "end")
        if not (fila["estado"] == "descartado" and fila["words"] == fila.get("ocr")):
            self.texto.insert(0, fila["words"])   # un descartado sin corregir empieza vacío: lo escribes tú
        self.texto.focus_set()
        self.texto.icursor("end")
        self.original.configure(text="Lo que leyó el modelo: " + (fila.get("ocr") or "—"))

    def guardar(self, parte, fila, texto, estado):
        """Vuelve a leer el CSV y cambia solo este renglón: si otra herramienta agregó renglones
        mientras la ventana estaba abierta, no se pierden."""
        fila["words"], fila["estado"] = texto, estado
        en_disco = etiquetas.leer(parte)
        for f in en_disco:
            if f["filename"] == fila["filename"]:
                f["words"], f["estado"] = texto, estado
                break
        etiquetas.escribir(parte, en_disco)

    def guardar_y_seguir(self, parte, fila, texto, estado):
        try:
            self.guardar(parte, fila, texto, estado)
        except OSError as e:   # p. ej. labels.csv abierto en Excel
            self.estado.configure(text=f"⚠ No se pudo guardar ({e.__class__.__name__}). "
                                       "¿Tienes labels.csv abierto en otro programa? Ciérralo y vuelve a intentar.",
                                  text_color="#c01c28")
            return
        self.i += 1
        self.mostrar()

    def aceptar(self):
        if self.i >= len(self.lista):
            return
        parte, fila = self.lista[self.i]
        texto = self.texto.get().strip()
        self.guardar_y_seguir(parte, fila, texto or fila["words"], "ok" if texto else "descartado")

    def descartar(self):
        if self.i >= len(self.lista):
            return
        parte, fila = self.lista[self.i]
        self.guardar_y_seguir(parte, fila, fila["words"], "descartado")

    def anterior(self):
        if self.i > 0:
            self.i -= 1
            self.mostrar()

    def terminar(self, mensaje=None):
        for hijo in self.winfo_children():
            hijo.destroy()
        conteo = {}
        for filas in self.datos.values():
            for f in filas:
                conteo[f["estado"]] = conteo.get(f["estado"], 0) + 1
        resumen = "\n".join(f"{TEXTO_ESTADO.get(k, k)}: {v}" for k, v in sorted(conteo.items()))
        texto = (mensaje or "¡Listo! Revisaste todos los renglones.") + "\n\n" + resumen
        texto += "\n\nPara entrenar con los aceptados:\npython herramientas/entrenar.py --epocas 10"
        ctk.CTkLabel(self, text=texto, font=ctk.CTkFont(size=16), justify="left").pack(padx=30, pady=30, anchor="w")
        ctk.CTkButton(self, text="Cerrar", command=self.destroy).pack(pady=10)


if __name__ == "__main__":
    ctk.set_appearance_mode("system")
    if "--descartados" in sys.argv:
        Revisor(descartados=sys.argv[sys.argv.index("--descartados") + 1:]).mainloop()
    else:
        Revisor(todos="--todos" in sys.argv).mainloop()
