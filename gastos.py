# gastos.py
# Cuentas (débito, crédito y efectivo), movimientos, pagos recurrentes
# y resumen por categoría. Todo vive en un diccionario "datos" en memoria.
import calendar
from datetime import date, datetime, timedelta
import uuid
import almacen

GASTOS = "gastos.json"
DIA = "%Y-%m-%d"
CATEGORIAS_BASE = ["Comida", "Supermercado", "Transporte", "Servicios", "Vivienda", "Suscripciones",
                   "Entretenimiento", "Salud", "Educación", "Ropa", "Compras", "Otros"]


def cargar():
    datos = almacen.leer_json(GASTOS, {})
    for clave in ["cuentas", "movimientos", "recurrentes"]:
        if clave not in datos:
            datos[clave] = []
    if "categorias" not in datos:
        datos["categorias"] = list(CATEGORIAS_BASE)
    return datos

def guardar_archivo(datos):
    almacen.escribir_json(GASTOS, datos)


# ---------- Fechas ----------

def a_fecha(texto):
    return datetime.strptime(texto, DIA).date()

def dia_valido(anio, mes, dia):
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(dia, ultimo))

def sumar_meses(fecha, meses, diabase):
    total = fecha.month - 1 + meses
    anio = fecha.year + total // 12
    mes = total % 12 + 1
    return dia_valido(anio, mes, diabase)

def proxima_fecha_con_dia(dia, desde):
    candidata = dia_valido(desde.year, desde.month, dia)
    if candidata < desde:
        candidata = sumar_meses(candidata, 1, dia)
    return candidata

def ultima_fecha_con_dia(dia, hasta):
    candidata = dia_valido(hasta.year, hasta.month, dia)
    if candidata > hasta:
        candidata = sumar_meses(candidata, -1, dia)
    return candidata


# ---------- Categorías ----------

def asegurar_categoria(datos, nombre):
    nombre = nombre.strip()
    if nombre == "":
        return "Otros"
    for existente in datos["categorias"]:
        if existente.lower() == nombre.lower():
            return existente
    datos["categorias"].append(nombre)
    return nombre


# ---------- Cuentas ----------

def crear_cuenta(datos, nombre, tipo, saldoinicial, limite=0, diacorte=1, diapago=1):
    cuenta = {
        "id": uuid.uuid4().hex,
        "nombre": nombre,
        "tipo": tipo,
        "saldoinicial": saldoinicial,
        "limite": limite,
        "diacorte": diacorte,
        "diapago": diapago,
    }
    datos["cuentas"].append(cuenta)
    return cuenta

def buscar_cuenta(datos, cuentaid):
    for cuenta in datos["cuentas"]:
        if cuenta["id"] == cuentaid:
            return cuenta
    return None

def borrar_cuenta(datos, cuentaid):
    cuenta = buscar_cuenta(datos, cuentaid)
    if cuenta is None:
        return False
    datos["cuentas"].remove(cuenta)
    movimientos = []
    for mov in datos["movimientos"]:
        if mov["cuentaid"] != cuentaid:
            movimientos.append(mov)
    datos["movimientos"] = movimientos
    recurrentes = []
    for rec in datos["recurrentes"]:
        if rec["cuentaid"] != cuentaid:
            recurrentes.append(rec)
    datos["recurrentes"] = recurrentes
    return True

def saldo(datos, cuenta):
    gastos = 0
    abonos = 0
    for mov in datos["movimientos"]:
        if mov["cuentaid"] == cuenta["id"]:
            if mov["tipo"] == "gasto":
                gastos += mov["monto"]
            else:
                abonos += mov["monto"]
    if cuenta["tipo"] == "credito":
        return round(cuenta["saldoinicial"] + gastos - abonos, 2)
    return round(cuenta["saldoinicial"] - gastos + abonos, 2)

def gastado_entre(datos, cuenta, inicio, fin):
    total = 0
    for mov in datos["movimientos"]:
        if mov["cuentaid"] == cuenta["id"] and mov["tipo"] == "gasto":
            fecha = a_fecha(mov["fecha"])
            if inicio <= fecha <= fin:
                total += mov["monto"]
    return round(total, 2)

def info_credito(datos, cuenta, hoy):
    ultimo_corte = ultima_fecha_con_dia(cuenta["diacorte"], hoy - timedelta(days=1))
    proximo_corte = proxima_fecha_con_dia(cuenta["diacorte"], hoy)
    corte_anterior = sumar_meses(ultimo_corte, -1, cuenta["diacorte"])
    pago = proxima_fecha_con_dia(cuenta["diapago"], ultimo_corte + timedelta(days=1))
    if pago < hoy:
        pago = proxima_fecha_con_dia(cuenta["diapago"], proximo_corte + timedelta(days=1))
        facturado = gastado_entre(datos, cuenta, ultimo_corte + timedelta(days=1), proximo_corte)
    else:
        facturado = gastado_entre(datos, cuenta, corte_anterior + timedelta(days=1), ultimo_corte)
    deuda = saldo(datos, cuenta)
    disponible = None
    if cuenta["limite"] > 0:
        disponible = round(cuenta["limite"] - deuda, 2)
    return {
        "deuda": deuda,
        "disponible": disponible,
        "proximocorte": proximo_corte,
        "proximopago": pago,
        "diaspago": (pago - hoy).days,
        "gastoperiodo": gastado_entre(datos, cuenta, ultimo_corte + timedelta(days=1), hoy),
        "facturado": facturado,
    }


# ---------- Movimientos ----------

def agregar_movimiento(datos, tipo, monto, cuentaid, fecha, descripcion="", categoria="", recurrenteid=None):
    if tipo == "gasto":
        categoria = asegurar_categoria(datos, categoria)
    else:
        categoria = ""
    mov = {
        "id": uuid.uuid4().hex,
        "tipo": tipo,
        "fecha": fecha.strftime(DIA),
        "descripcion": descripcion,
        "monto": round(float(monto), 2),
        "categoria": categoria,
        "cuentaid": cuentaid,
        "recurrenteid": recurrenteid,
    }
    datos["movimientos"].append(mov)
    return mov

def borrar_movimiento(datos, movid):
    for i, mov in enumerate(datos["movimientos"]):
        if mov["id"] == movid:
            datos["movimientos"].pop(i)
            return True
    return False

def fecha_de(mov):
    return mov["fecha"]

def filtrar(datos, desde=None, hasta=None, cuentaid=None, categoria=None, tipo=None, texto=""):
    texto = texto.strip().lower()
    resultado = []
    for mov in datos["movimientos"]:
        fecha = a_fecha(mov["fecha"])
        if desde is not None and fecha < desde:
            continue
        if hasta is not None and fecha > hasta:
            continue
        if cuentaid is not None and mov["cuentaid"] != cuentaid:
            continue
        if categoria is not None and mov["categoria"] != categoria:
            continue
        if tipo is not None and mov["tipo"] != tipo:
            continue
        if texto not in mov["descripcion"].lower() and texto not in mov["categoria"].lower():
            continue
        resultado.append(mov)
    resultado.sort(key=fecha_de, reverse=True)
    return resultado

def total_de(fila):
    return fila[1]

def resumen_por_categoria(datos, desde=None, hasta=None):
    totales = {}
    for mov in filtrar(datos, desde, hasta, tipo="gasto"):
        if mov["categoria"] not in totales:
            totales[mov["categoria"]] = 0
        totales[mov["categoria"]] += mov["monto"]
    filas = []
    for categoria in totales:
        filas.append([categoria, round(totales[categoria], 2)])
    filas.sort(key=total_de, reverse=True)
    return filas


# ---------- Pagos recurrentes ----------

def avanzar_fecha(fecha, frecuencia, diabase):
    if frecuencia == "semanal":
        return fecha + timedelta(days=7)
    if frecuencia == "quincenal":
        return fecha + timedelta(days=14)
    if frecuencia == "bimestral":
        return sumar_meses(fecha, 2, diabase)
    if frecuencia == "anual":
        return sumar_meses(fecha, 12, diabase)
    return sumar_meses(fecha, 1, diabase)

def crear_recurrente(datos, nombre, monto, cuentaid, frecuencia, proximafecha, categoria="", automatico=False):
    rec = {
        "id": uuid.uuid4().hex,
        "nombre": nombre,
        "monto": monto,
        "cuentaid": cuentaid,
        "frecuencia": frecuencia,
        "proximafecha": proximafecha.strftime(DIA),
        "diabase": proximafecha.day,
        "categoria": asegurar_categoria(datos, categoria),
        "automatico": automatico,
        "activo": True,
    }
    datos["recurrentes"].append(rec)
    return rec

def borrar_recurrente(datos, recid):
    for i, rec in enumerate(datos["recurrentes"]):
        if rec["id"] == recid:
            datos["recurrentes"].pop(i)
            return True
    return False

def alternar_recurrente(rec):
    rec["activo"] = not rec["activo"]

def registrar_recurrente(datos, rec, fecha):
    mov = agregar_movimiento(datos, "gasto", rec["monto"], rec["cuentaid"], fecha, rec["nombre"], rec["categoria"], rec["id"])
    siguiente = avanzar_fecha(a_fecha(rec["proximafecha"]), rec["frecuencia"], rec["diabase"])
    rec["proximafecha"] = siguiente.strftime(DIA)
    return mov

def procesar_automaticos(datos, hoy):
    creados = []
    for rec in datos["recurrentes"]:
        if rec["activo"] and rec["automatico"]:
            vueltas = 0
            while a_fecha(rec["proximafecha"]) <= hoy and vueltas < 60:
                creados.append(registrar_recurrente(datos, rec, a_fecha(rec["proximafecha"])))
                vueltas += 1
    return creados

def fecha_de_pago(pago):
    return pago[0]

def proximos_pagos(datos, hoy, dias=7):
    lista = []
    for rec in datos["recurrentes"]:
        fecha = a_fecha(rec["proximafecha"])
        if rec["activo"] and (fecha - hoy).days <= dias:
            lista.append([fecha, rec["nombre"], rec["monto"]])
    for cuenta in datos["cuentas"]:
        if cuenta["tipo"] == "credito":
            info = info_credito(datos, cuenta, hoy)
            if info["diaspago"] <= dias and info["deuda"] > 0:
                lista.append([info["proximopago"], "Pago tarjeta " + cuenta["nombre"], info["deuda"]])
    lista.sort(key=fecha_de_pago)
    return lista


if __name__ == "__main__":
    hoy = date(2026, 11, 5)
    datos = {"cuentas": [], "movimientos": [], "recurrentes": [], "categorias": list(CATEGORIAS_BASE)}
    deb = crear_cuenta(datos, "Débito", "debito", 1000)
    tdc = crear_cuenta(datos, "Tarjeta", "credito", 0, 5000, 20, 10)
    agregar_movimiento(datos, "gasto", 150, deb["id"], date(2026, 11, 1), "Tacos", "comida")
    agregar_movimiento(datos, "abono", 500, deb["id"], date(2026, 11, 2), "Pago de trabajo")
    agregar_movimiento(datos, "gasto", 800, tdc["id"], date(2026, 10, 18), "Tenis", "Ropa")
    agregar_movimiento(datos, "gasto", 200, tdc["id"], date(2026, 10, 25), "Cine", "Entretenimiento")
    print(saldo(datos, deb))
    print(saldo(datos, tdc))
    info = info_credito(datos, tdc, hoy)
    print(info["facturado"], info["gastoperiodo"], info["proximopago"])
    print(resumen_por_categoria(datos))
    rec = crear_recurrente(datos, "Netflix", 199, tdc["id"], "mensual", date(2026, 10, 3), "suscripciones", True)
    creados = procesar_automaticos(datos, hoy)
    print(len(creados), rec["proximafecha"])
    print(saldo(datos, tdc))
    print([pago[1] for pago in proximos_pagos(datos, hoy)])
    print(len(filtrar(datos, texto="netflix")))
    print(borrar_cuenta(datos, deb["id"]), len(datos["movimientos"]))
