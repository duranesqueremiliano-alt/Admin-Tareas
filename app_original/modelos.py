"""
Lógica y datos de la aplicación (sin interfaz gráfica).

- TareasStore: tareas guardadas en tareas.json (mismo formato de siempre).
- GastosStore: cuentas, movimientos, pagos recurrentes y categorías en gastos.json.
"""

import calendar
from collections import Counter
import json
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
ARCHIVO_TAREAS = CARPETA / "tareas.json"
ARCHIVO_GASTOS = CARPETA / "gastos.json"

FORMATO_FECHA = "%Y-%m-%d %H:%M"
FORMATO_DIA = "%Y-%m-%d"

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
MESES_CORTOS = [m[:3] for m in MESES]
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ==============================================================
# UTILIDADES
# ==============================================================

def nuevo_id():
    return str(uuid.uuid4())


def leer_json(ruta, por_defecto):
    """Lee un JSON; si no existe o está dañado devuelve el valor por defecto."""
    if not ruta.exists():
        return por_defecto
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except (json.JSONDecodeError, OSError):
        return por_defecto


def escribir_json(ruta, datos):
    """Guarda primero en un temporal y luego lo reemplaza (evita archivos a medias)."""
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=4)
    os.replace(temporal, ruta)


def a_fecha(texto):
    """'2026-10-06' -> date. Devuelve None si no es válida."""
    try:
        return datetime.strptime(str(texto).strip(), FORMATO_DIA).date()
    except ValueError:
        return None


def dia_valido(anio, mes, dia):
    """Ajusta el día al último del mes si no existe (ej. 31 de febrero -> 28/29)."""
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(max(1, int(dia)), ultimo))


def sumar_meses(fecha, meses, dia_base=None):
    total = fecha.month - 1 + meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    return dia_valido(anio, mes, dia_base or fecha.day)


def proxima_fecha_con_dia(dia, desde):
    """Próxima fecha (>= desde) cuyo día del mes sea `dia`."""
    candidata = dia_valido(desde.year, desde.month, dia)
    if candidata < desde:
        candidata = sumar_meses(candidata, 1, dia)
    return candidata


def ultima_fecha_con_dia(dia, hasta):
    """Última fecha (<= hasta) cuyo día del mes sea `dia`."""
    candidata = dia_valido(hasta.year, hasta.month, dia)
    if candidata > hasta:
        candidata = sumar_meses(candidata, -1, dia)
    return candidata


def fecha_larga(fecha):
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def fecha_corta(fecha):
    return f"{fecha.day} {MESES_CORTOS[fecha.month - 1]}"


def texto_dias(dias):
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "mañana"
    if dias == -1:
        return "ayer"
    if dias < 0:
        return f"hace {-dias} días"
    return f"en {dias} días"


def tiempo_restante(fecha_limite, ahora=None):
    ahora = ahora or datetime.now()
    segundos = (fecha_limite - ahora).total_seconds()
    if segundos <= 0:
        return "Vencida"
    minutos = int(segundos // 60)
    dias, resto = divmod(minutos, 60 * 24)
    horas, minutos = divmod(resto, 60)
    if dias > 0:
        return f"{dias} d {horas} h"
    if horas > 0:
        return f"{horas} h {minutos} min"
    return f"{minutos} min"


def moneda(valor):
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.2f}"


def leer_monto(texto):
    """Acepta '1,250.50', '$300', '300'. Devuelve float > 0 o None."""
    limpio = str(texto).replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        valor = round(float(limpio), 2)
    except ValueError:
        return None
    return valor if valor > 0 else None


# ==============================================================
# TAREAS
# ==============================================================

class TareasStore:

    def __init__(self, ruta=ARCHIVO_TAREAS):
        self.ruta = ruta
        self.tareas = []
        self.error_carga = False
        self.cargar()

    def cargar(self):
        datos = leer_json(self.ruta, None)
        if datos is None and self.ruta.exists() and self.ruta.stat().st_size > 0:
            self.error_carga = True
        self.tareas = datos if isinstance(datos, list) else []
        for tarea in self.tareas:
            tarea.setdefault("id", nuevo_id())
            tarea.setdefault("descripcion", "")
            tarea.setdefault("estado", "pendiente")
            tarea.setdefault("alerta_12h_enviada", False)

    def guardar(self):
        escribir_json(self.ruta, self.tareas)

    @staticmethod
    def fecha_de(tarea):
        try:
            return datetime.strptime(tarea["fecha_limite"], FORMATO_FECHA)
        except (KeyError, ValueError):
            return None

    def buscar(self, tarea_id):
        return next((t for t in self.tareas if t["id"] == tarea_id), None)

    def contar(self, estado):
        return sum(1 for t in self.tareas if t.get("estado") == estado)

    def agregar(self, nombre, fecha_limite, descripcion=""):
        estado = "expirada" if fecha_limite <= datetime.now() else "pendiente"
        tarea = {
            "id": nuevo_id(),
            "nombre": nombre,
            "descripcion": descripcion,
            "fecha_limite": fecha_limite.strftime(FORMATO_FECHA),
            "estado": estado,
            "alerta_12h_enviada": False,
        }
        self.tareas.append(tarea)
        self.guardar()
        return tarea

    def editar(self, tarea_id, nombre, fecha_limite, descripcion):
        tarea = self.buscar(tarea_id)
        if tarea is None:
            return
        tarea["nombre"] = nombre
        tarea["descripcion"] = descripcion
        tarea["fecha_limite"] = fecha_limite.strftime(FORMATO_FECHA)
        tarea["alerta_12h_enviada"] = False
        if tarea["estado"] != "completada":
            tarea["estado"] = "expirada" if fecha_limite <= datetime.now() else "pendiente"
        self.guardar()

    def cambiar_estado(self, tarea_id, estado):
        tarea = self.buscar(tarea_id)
        if tarea is None:
            return
        if estado == "pendiente":
            # Al reabrir: si la fecha ya pasó queda como expirada
            fecha = self.fecha_de(tarea)
            if fecha and fecha <= datetime.now():
                estado = "expirada"
            tarea["alerta_12h_enviada"] = False
        tarea["estado"] = estado
        self.guardar()

    def eliminar(self, tarea_id):
        self.tareas = [t for t in self.tareas if t["id"] != tarea_id]
        self.guardar()

    def actualizar_estados(self):
        """Pasa a 'expirada' las pendientes vencidas. Devuelve True si hubo cambios."""
        ahora = datetime.now()
        cambios = False
        for tarea in self.tareas:
            if tarea.get("estado") != "pendiente":
                continue
            fecha = self.fecha_de(tarea)
            if fecha and fecha <= ahora:
                tarea["estado"] = "expirada"
                cambios = True
        if cambios:
            self.guardar()
        return cambios

    def nuevas_alertas(self, horas=12):
        """Pendientes que vencen dentro de `horas` y aún no se avisaron."""
        ahora = datetime.now()
        limite = ahora + timedelta(hours=horas)
        avisar = []
        for tarea in self.tareas:
            if tarea.get("estado") != "pendiente" or tarea.get("alerta_12h_enviada"):
                continue
            fecha = self.fecha_de(tarea)
            if fecha and ahora < fecha <= limite:
                tarea["alerta_12h_enviada"] = True
                avisar.append(tarea)
        if avisar:
            self.guardar()
        return avisar

    def proximas(self, cantidad=3):
        pendientes = [t for t in self.tareas if t.get("estado") == "pendiente" and self.fecha_de(t)]
        pendientes.sort(key=self.fecha_de)
        return pendientes[:cantidad]


# ==============================================================
# GASTOS
# ==============================================================

TIPOS_CUENTA = {
    "debito": "Débito",
    "credito": "Crédito",
    "efectivo": "Efectivo",
}

FRECUENCIAS = {
    "semanal": "Semanal",
    "quincenal": "Quincenal",
    "mensual": "Mensual",
    "bimestral": "Bimestral",
    "anual": "Anual",
}

CATEGORIAS_BASE = [
    "Comida", "Supermercado", "Transporte", "Servicios", "Vivienda",
    "Suscripciones", "Entretenimiento", "Salud", "Educación", "Ropa",
    "Compras", "Otros",
]

COLORES_CUENTA = ["#3b82f6", "#22c55e", "#a855f7", "#f97316", "#ec4899", "#14b8a6", "#eab308", "#64748b"]


def avanzar_fecha(fecha, frecuencia, dia_base=None):
    if frecuencia == "semanal":
        return fecha + timedelta(days=7)
    if frecuencia == "quincenal":
        return fecha + timedelta(days=14)
    if frecuencia == "bimestral":
        return sumar_meses(fecha, 2, dia_base)
    if frecuencia == "anual":
        return sumar_meses(fecha, 12, dia_base)
    return sumar_meses(fecha, 1, dia_base)


class GastosStore:

    def __init__(self, ruta=ARCHIVO_GASTOS):
        self.ruta = ruta
        self.cuentas = []
        self.movimientos = []
        self.recurrentes = []
        self.categorias = list(CATEGORIAS_BASE)
        self.cargar()

    # ---------------- archivo ----------------

    def cargar(self):
        datos = leer_json(self.ruta, {})
        if not isinstance(datos, dict):
            datos = {}
        self.cuentas = datos.get("cuentas", [])
        self.movimientos = datos.get("movimientos", [])
        self.recurrentes = datos.get("recurrentes", [])
        self.categorias = datos.get("categorias") or list(CATEGORIAS_BASE)

    def guardar(self):
        escribir_json(self.ruta, {
            "cuentas": self.cuentas,
            "movimientos": self.movimientos,
            "recurrentes": self.recurrentes,
            "categorias": self.categorias,
        })

    # ---------------- categorías ----------------

    def asegurar_categoria(self, nombre):
        nombre = nombre.strip()
        if not nombre:
            return "Otros"
        for existente in self.categorias:
            if existente.lower() == nombre.lower():
                return existente
        self.categorias.append(nombre)
        return nombre

    # ---------------- cuentas ----------------

    def cuenta(self, cuenta_id):
        return next((c for c in self.cuentas if c["id"] == cuenta_id), None)

    def nombre_cuenta(self, cuenta_id):
        cuenta = self.cuenta(cuenta_id)
        return cuenta["nombre"] if cuenta else "(cuenta eliminada)"

    def guardar_cuenta(self, datos, cuenta_id=None):
        """Crea o actualiza una cuenta. `datos` trae nombre, tipo, saldo_inicial, limite, dia_corte, dia_pago, color."""
        if cuenta_id:
            cuenta = self.cuenta(cuenta_id)
            cuenta.update(datos)
        else:
            cuenta = {"id": nuevo_id(), "creada": date.today().strftime(FORMATO_DIA)}
            cuenta.update(datos)
            self.cuentas.append(cuenta)
        self.guardar()
        return cuenta

    def nombre_disponible(self, nombre, excepto_id=None):
        return not any(
            c["nombre"].lower() == nombre.lower() and c["id"] != excepto_id
            for c in self.cuentas
        )

    def uso_de_cuenta(self, cuenta_id):
        movs = sum(1 for m in self.movimientos if m["cuenta_id"] == cuenta_id)
        recs = sum(1 for r in self.recurrentes if r["cuenta_id"] == cuenta_id)
        return movs, recs

    def eliminar_cuenta(self, cuenta_id):
        self.cuentas = [c for c in self.cuentas if c["id"] != cuenta_id]
        self.movimientos = [m for m in self.movimientos if m["cuenta_id"] != cuenta_id]
        self.recurrentes = [r for r in self.recurrentes if r["cuenta_id"] != cuenta_id]
        self.guardar()

    def saldo(self, cuenta):
        """
        Débito / efectivo: dinero disponible = saldo inicial - gastos + ingresos.
        Crédito: deuda = deuda inicial + gastos - pagos.
        """
        gastos = sum(m["monto"] for m in self.movimientos
                     if m["cuenta_id"] == cuenta["id"] and m["tipo"] == "gasto")
        abonos = sum(m["monto"] for m in self.movimientos
                     if m["cuenta_id"] == cuenta["id"] and m["tipo"] == "abono")
        inicial = float(cuenta.get("saldo_inicial", 0) or 0)
        if cuenta["tipo"] == "credito":
            return round(inicial + gastos - abonos, 2)
        return round(inicial - gastos + abonos, 2)

    def info_credito(self, cuenta, hoy=None):
        """Fechas y montos útiles de una tarjeta de crédito."""
        hoy = hoy or date.today()
        dia_corte = int(cuenta.get("dia_corte") or 1)
        dia_pago = int(cuenta.get("dia_pago") or 1)

        ultimo_corte = ultima_fecha_con_dia(dia_corte, hoy - timedelta(days=1))
        proximo_corte = proxima_fecha_con_dia(dia_corte, hoy)
        corte_anterior = sumar_meses(ultimo_corte, -1, dia_corte)

        # El pago corresponde al último corte: primera fecha con dia_pago después de ese corte
        pago_del_corte = proxima_fecha_con_dia(dia_pago, ultimo_corte + timedelta(days=1))
        if pago_del_corte < hoy:
            # Ya pasó; el siguiente pago es el del próximo corte
            pago_del_corte = proxima_fecha_con_dia(dia_pago, proximo_corte + timedelta(days=1))
            periodo_facturado = (ultimo_corte + timedelta(days=1), proximo_corte)
        else:
            periodo_facturado = (corte_anterior + timedelta(days=1), ultimo_corte)

        def gastado_entre(inicio, fin):
            total = 0.0
            for m in self.movimientos:
                if m["cuenta_id"] != cuenta["id"] or m["tipo"] != "gasto":
                    continue
                f = a_fecha(m["fecha"])
                if f and inicio <= f <= fin:
                    total += m["monto"]
            return round(total, 2)

        deuda = self.saldo(cuenta)
        limite = float(cuenta.get("limite", 0) or 0)
        return {
            "deuda": deuda,
            "limite": limite,
            "disponible": round(limite - deuda, 2) if limite else None,
            "uso": (deuda / limite) if limite else 0,
            "proximo_corte": proximo_corte,
            "dias_corte": (proximo_corte - hoy).days,
            "proximo_pago": pago_del_corte,
            "dias_pago": (pago_del_corte - hoy).days,
            "gasto_periodo_actual": gastado_entre(ultimo_corte + timedelta(days=1), hoy),
            "gasto_facturado": gastado_entre(*periodo_facturado),
        }

    # ---------------- movimientos ----------------

    def movimiento(self, mov_id):
        return next((m for m in self.movimientos if m["id"] == mov_id), None)

    def agregar_movimiento(self, tipo, monto, cuenta_id, fecha, descripcion="", categoria="", recurrente_id=None, guardar=True):
        mov = {
            "id": nuevo_id(),
            "tipo": tipo,
            "fecha": fecha.strftime(FORMATO_DIA),
            "descripcion": descripcion,
            "monto": round(float(monto), 2),
            "categoria": self.asegurar_categoria(categoria) if tipo == "gasto" else "",
            "cuenta_id": cuenta_id,
        }
        if recurrente_id:
            mov["recurrente_id"] = recurrente_id
        self.movimientos.append(mov)
        if guardar:
            self.guardar()
        return mov

    def editar_movimiento(self, mov_id, **cambios):
        mov = self.movimiento(mov_id)
        if mov is None:
            return
        if "fecha" in cambios and isinstance(cambios["fecha"], date):
            cambios["fecha"] = cambios["fecha"].strftime(FORMATO_DIA)
        if "categoria" in cambios:
            tipo = cambios.get("tipo", mov["tipo"])
            cambios["categoria"] = self.asegurar_categoria(cambios["categoria"]) if tipo == "gasto" else ""
        mov.update(cambios)
        self.guardar()

    def eliminar_movimiento(self, mov_id):
        self.movimientos = [m for m in self.movimientos if m["id"] != mov_id]
        self.guardar()

    def movimientos_filtrados(self, desde=None, hasta=None, cuenta_id=None, categoria=None, texto="", tipo=None):
        texto = texto.lower().strip()
        resultado = []
        for m in self.movimientos:
            f = a_fecha(m["fecha"])
            if f is None:
                continue
            if desde and f < desde:
                continue
            if hasta and f > hasta:
                continue
            if cuenta_id and m["cuenta_id"] != cuenta_id:
                continue
            if categoria and m.get("categoria") != categoria:
                continue
            if tipo and m["tipo"] != tipo:
                continue
            if texto and texto not in m.get("descripcion", "").lower() and texto not in m.get("categoria", "").lower():
                continue
            resultado.append(m)
        orden = {id(m): i for i, m in enumerate(self.movimientos)}
        resultado.sort(key=lambda m: (m["fecha"], orden[id(m)]), reverse=True)
        return resultado

    def meses_con_datos(self):
        meses = {m["fecha"][:7] for m in self.movimientos if len(m.get("fecha", "")) >= 7}
        meses.add(date.today().strftime("%Y-%m"))
        return sorted(meses, reverse=True)

    def gasto_total(self, desde, hasta, cuenta_id=None):
        return round(sum(m["monto"] for m in self.movimientos_filtrados(desde, hasta, cuenta_id, tipo="gasto")), 2)

    def resumen_por_categoria(self, desde=None, hasta=None, cuenta_id=None):
        """Lista [(categoria, total, cantidad)] ordenada de mayor a menor."""
        totales = {}
        for m in self.movimientos_filtrados(desde, hasta, cuenta_id, tipo="gasto"):
            cat = m.get("categoria") or "Otros"
            total, cantidad = totales.get(cat, (0.0, 0))
            totales[cat] = (total + m["monto"], cantidad + 1)
        filas = [(cat, round(t, 2), n) for cat, (t, n) in totales.items()]
        filas.sort(key=lambda fila: fila[1], reverse=True)
        return filas

    # ---------------- pagos recurrentes ----------------

    def recurrente(self, rec_id):
        return next((r for r in self.recurrentes if r["id"] == rec_id), None)

    def guardar_recurrente(self, datos, rec_id=None):
        if isinstance(datos.get("proxima_fecha"), date):
            datos["dia_base"] = datos["proxima_fecha"].day
            datos["proxima_fecha"] = datos["proxima_fecha"].strftime(FORMATO_DIA)
        datos["categoria"] = self.asegurar_categoria(datos.get("categoria", ""))
        if rec_id:
            rec = self.recurrente(rec_id)
            rec.update(datos)
        else:
            rec = {"id": nuevo_id(), "activo": True}
            rec.update(datos)
            self.recurrentes.append(rec)
        self.guardar()
        return rec

    def eliminar_recurrente(self, rec_id):
        self.recurrentes = [r for r in self.recurrentes if r["id"] != rec_id]
        self.guardar()

    def alternar_recurrente(self, rec_id):
        rec = self.recurrente(rec_id)
        if rec:
            rec["activo"] = not rec.get("activo", True)
            self.guardar()

    def _avanzar(self, rec):
        actual = a_fecha(rec["proxima_fecha"]) or date.today()
        siguiente = avanzar_fecha(actual, rec["frecuencia"], rec.get("dia_base"))
        rec["proxima_fecha"] = siguiente.strftime(FORMATO_DIA)

    def registrar_recurrente(self, rec_id, fecha=None):
        """Registra el gasto de un pago recurrente y mueve su próxima fecha."""
        rec = self.recurrente(rec_id)
        if rec is None:
            return None
        mov = self.agregar_movimiento(
            "gasto", rec["monto"], rec["cuenta_id"], fecha or date.today(),
            rec["nombre"], rec["categoria"], recurrente_id=rec["id"], guardar=False,
        )
        self._avanzar(rec)
        self.guardar()
        return mov

    def procesar_automaticos(self, hoy=None):
        """Registra los recurrentes automáticos cuya fecha ya llegó. Devuelve los movimientos creados."""
        hoy = hoy or date.today()
        creados = []
        for rec in self.recurrentes:
            if not rec.get("activo", True) or not rec.get("automatico"):
                continue
            if not self.cuenta(rec["cuenta_id"]):
                continue
            vueltas = 0
            while vueltas < 60:
                proxima = a_fecha(rec["proxima_fecha"])
                if proxima is None or proxima > hoy:
                    break
                creados.append(self.agregar_movimiento(
                    "gasto", rec["monto"], rec["cuenta_id"], proxima,
                    rec["nombre"], rec["categoria"], recurrente_id=rec["id"], guardar=False,
                ))
                self._avanzar(rec)
                vueltas += 1
        if creados:
            self.guardar()
        return creados

    def proximos_pagos(self, dias=7, hoy=None):
        """Recurrentes y fechas de pago de tarjeta dentro de los próximos `dias` (incluye atrasados)."""
        hoy = hoy or date.today()
        lista = []
        for rec in self.recurrentes:
            if not rec.get("activo", True):
                continue
            f = a_fecha(rec["proxima_fecha"])
            if f and (f - hoy).days <= dias:
                lista.append({"fecha": f, "nombre": rec["nombre"], "monto": rec["monto"], "tipo": "recurrente",
                              "automatico": rec.get("automatico", False)})
        for cuenta in self.cuentas:
            if cuenta["tipo"] != "credito":
                continue
            info = self.info_credito(cuenta, hoy)
            if info["dias_pago"] <= dias and info["deuda"] > 0:
                lista.append({"fecha": info["proximo_pago"], "nombre": f"Pago tarjeta {cuenta['nombre']}",
                              "monto": info["deuda"], "tipo": "tarjeta", "automatico": False})
        lista.sort(key=lambda x: x["fecha"])
        return lista


# ==============================================================
# NOTAS DE CLASE
# ==============================================================

ARCHIVO_NOTAS = CARPETA / "notas.json"


def normalizar(texto):
    """Minúsculas y sin acentos, para buscar 'funcion' y encontrar 'Función'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(texto))
                   if unicodedata.category(c) != "Mn").lower()


class NotasStore:

    def __init__(self, ruta=ARCHIVO_NOTAS):
        self.ruta = ruta
        self.notas = []
        self.materias = []
        self.cargar()

    def cargar(self):
        datos = leer_json(self.ruta, {})
        if not isinstance(datos, dict):
            datos = {}
        self.notas = datos.get("notas", [])
        self.materias = datos.get("materias", [])
        for n in self.notas:
            n.setdefault("palabras_clave", [])
            n.setdefault("fuente", "local")
            n.setdefault("titulo", "")

    def guardar(self):
        escribir_json(self.ruta, {"materias": self.materias, "notas": self.notas})

    def asegurar_materia(self, nombre):
        nombre = " ".join(nombre.split())
        if not nombre:
            return "General"
        for m in self.materias:
            if m.lower() == nombre.lower():
                return m
        self.materias.append(nombre)
        return nombre

    @staticmethod
    def titulo_de(nota):
        if nota.get("titulo"):
            return nota["titulo"]
        primera = nota.get("texto", "").strip().split("\n")[0]
        return primera[:60] + ("…" if len(primera) > 60 else "") or "(sin título)"

    def nota(self, nota_id):
        return next((n for n in self.notas if n["id"] == nota_id), None)

    def agregar(self, materia, titulo, texto):
        nota = {
            "id": nuevo_id(),
            "materia": self.asegurar_materia(materia),
            "titulo": titulo.strip(),
            "texto": texto.strip(),
            "fecha": datetime.now().strftime(FORMATO_FECHA),
            "palabras_clave": [],
            "fuente": "pendiente",
        }
        self.notas.append(nota)
        self.guardar()
        return nota

    def editar(self, nota_id, materia, titulo, texto, palabras=None):
        nota = self.nota(nota_id)
        if nota is None:
            return None
        nota["materia"] = self.asegurar_materia(materia)
        nota["titulo"] = titulo.strip()
        nota["texto"] = texto.strip()
        if palabras is not None:
            nota["palabras_clave"] = palabras
            nota["fuente"] = "manual"
        self.guardar()
        return nota

    def poner_palabras(self, nota_id, palabras, fuente):
        nota = self.nota(nota_id)
        if nota is not None:
            nota["palabras_clave"] = palabras
            nota["fuente"] = fuente
            self.guardar()

    def eliminar(self, nota_id):
        self.notas = [n for n in self.notas if n["id"] != nota_id]
        # Quita de la lista las materias que ya no tienen ninguna nota
        self.materias = self.materias_en_uso()
        self.guardar()

    def materias_en_uso(self):
        usadas = {n["materia"] for n in self.notas}
        return [m for m in self.materias if m in usadas]

    def otros_textos(self, nota_id):
        return [n["texto"] for n in self.notas if n["id"] != nota_id]

    def buscar(self, texto="", materia=None):
        """
        Todas las palabras buscadas deben aparecer en la nota (título, texto, materia o palabras clave).
        Ordena primero las que coinciden con palabras clave, luego por fecha.
        """
        terminos = normalizar(texto).split()
        resultado = []
        for n in self.notas:
            if materia and n["materia"] != materia:
                continue
            claves = normalizar(" | ".join(n.get("palabras_clave", [])))
            titulo = normalizar(self.titulo_de(n))
            cuerpo = normalizar(n.get("texto", "")) + " " + normalizar(n.get("materia", ""))
            puntos = 0
            valida = True
            for t in terminos:
                if t in claves:
                    puntos += 3
                elif t in titulo:
                    puntos += 2
                elif t in cuerpo:
                    puntos += 1
                else:
                    valida = False
                    break
            if valida:
                resultado.append((puntos, n["fecha"], n))
        resultado.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [n for _, _, n in resultado]

    def palabras_frecuentes(self, materia=None, cantidad=10):
        conteo = Counter()
        forma = {}
        for n in self.notas:
            if materia and n["materia"] != materia:
                continue
            for p in n.get("palabras_clave", []):
                clave = normalizar(p)
                conteo[clave] += 1
                forma.setdefault(clave, p)
        return [(forma[c], k) for c, k in conteo.most_common(cantidad)]

    def recientes(self, cantidad=3):
        return sorted(self.notas, key=lambda n: n["fecha"], reverse=True)[:cantidad]
