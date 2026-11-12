# gastos.py
# Cuentas (débito, crédito y efectivo), movimientos, transferencias,
# pagos recurrentes, presupuestos y resumen por categoría.
# Todo vive en un diccionario "datos" en memoria.
import calendar
import csv
from datetime import date, datetime, timedelta
import uuid
from logica import almacen

GASTOS = "gastos.json"
DIA = "%Y-%m-%d"
CATEGORIAS_BASE = ["Comida", "Supermercado", "Transporte", "Servicios", "Vivienda", "Suscripciones",
                   "Entretenimiento", "Salud", "Educación", "Ropa", "Compras", "Otros"]
AVISO_PRESUPUESTO = 0.8   # avisar cuando se gasta el 80 % del presupuesto


def vacio():
    return {"cuentas": [], "movimientos": [], "recurrentes": [],
            "categorias": list(CATEGORIAS_BASE), "presupuestos": {}}

def cargar():
    datos = almacen.leer_json(GASTOS, {})
    base = vacio()
    for clave in base:
        if clave not in datos:
            datos[clave] = base[clave]
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

def inicio_mes(fecha):
    return date(fecha.year, fecha.month, 1)

def fin_mes(fecha):
    return dia_valido(fecha.year, fecha.month, 31)


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

def actualizar_cuenta(cuenta, nombre, tipo, saldoinicial, limite=0, diacorte=1, diapago=1):
    cuenta["nombre"] = nombre
    cuenta["tipo"] = tipo
    cuenta["saldoinicial"] = saldoinicial
    if tipo == "credito":
        cuenta["limite"] = limite
        cuenta["diacorte"] = diacorte
        cuenta["diapago"] = diapago
    else:
        cuenta["limite"] = 0
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
        if mov["cuentaid"] != cuentaid and mov.get("destinoid") != cuentaid:
            movimientos.append(mov)
    datos["movimientos"] = movimientos
    recurrentes = []
    for rec in datos["recurrentes"]:
        if rec["cuentaid"] != cuentaid:
            recurrentes.append(rec)
    datos["recurrentes"] = recurrentes
    return True

def saldo(datos, cuenta):
    # Una transferencia sale de "cuentaid" (como un gasto)
    # y entra a "destinoid" (como un abono).
    gastos = 0
    abonos = 0
    for mov in datos["movimientos"]:
        if mov["cuentaid"] == cuenta["id"]:
            if mov["tipo"] == "abono":
                abonos += mov["monto"]
            else:
                gastos += mov["monto"]
        elif mov.get("destinoid") == cuenta["id"]:
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
    uso = None
    if cuenta["limite"] > 0:
        disponible = round(cuenta["limite"] - deuda, 2)
        uso = max(0, deuda) / cuenta["limite"]
    return {
        "deuda": deuda,
        "disponible": disponible,
        "uso": uso,
        "proximocorte": proximo_corte,
        "proximopago": pago,
        "diaspago": (pago - hoy).days,
        "gastoperiodo": gastado_entre(datos, cuenta, ultimo_corte + timedelta(days=1), hoy),
        "facturado": min(facturado, max(0, deuda)),
    }

def total_disponible(datos):
    # Dinero real: saldos de débito y efectivo (sin contar las tarjetas).
    total = 0
    for cuenta in datos["cuentas"]:
        if cuenta["tipo"] != "credito":
            total += saldo(datos, cuenta)
    return round(total, 2)

def total_deuda(datos):
    total = 0
    for cuenta in datos["cuentas"]:
        if cuenta["tipo"] == "credito":
            total += max(0, saldo(datos, cuenta))
    return round(total, 2)


# ---------- Movimientos ----------
# tipo: "gasto", "abono" o "transferencia" (de cuentaid a destinoid)

def agregar_movimiento(datos, tipo, monto, cuentaid, fecha, descripcion="", categoria="",
                       recurrenteid=None, destinoid=None):
    mov = {"id": uuid.uuid4().hex, "recurrenteid": recurrenteid}
    llenar_movimiento(datos, mov, tipo, monto, cuentaid, fecha, descripcion, categoria, destinoid)
    datos["movimientos"].append(mov)
    return mov

def llenar_movimiento(datos, mov, tipo, monto, cuentaid, fecha, descripcion="", categoria="", destinoid=None):
    if tipo == "gasto":
        categoria = asegurar_categoria(datos, categoria)
    else:
        categoria = ""
    if tipo != "transferencia":
        destinoid = None
    mov["tipo"] = tipo
    mov["fecha"] = fecha.strftime(DIA)
    mov["descripcion"] = descripcion
    mov["monto"] = round(float(monto), 2)
    mov["categoria"] = categoria
    mov["cuentaid"] = cuentaid
    mov["destinoid"] = destinoid
    return mov

def categoria_sugerida(datos, descripcion):
    # Si ya escribiste esa descripción antes, reutiliza su categoría (la más reciente).
    texto = descripcion.strip().lower()
    if texto == "":
        return None
    for mov in filtrar(datos, tipo="gasto"):
        if mov["descripcion"].strip().lower() == texto:
            return mov["categoria"]
    return None

def transferir(datos, origenid, destinoid, monto, fecha, descripcion="Transferencia"):
    if origenid == destinoid:
        return None
    return agregar_movimiento(datos, "transferencia", monto, origenid, fecha, descripcion, destinoid=destinoid)

def buscar_movimiento(datos, movid):
    for mov in datos["movimientos"]:
        if mov["id"] == movid:
            return mov
    return None

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
        if cuentaid is not None and mov["cuentaid"] != cuentaid and mov.get("destinoid") != cuentaid:
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

def totales_mes(datos, fecha):
    # [gastado, ingresado] en el mes de "fecha" (las transferencias no cuentan)
    gastado = 0
    ingresado = 0
    for mov in filtrar(datos, inicio_mes(fecha), fin_mes(fecha)):
        if mov["tipo"] == "gasto":
            gastado += mov["monto"]
        elif mov["tipo"] == "abono":
            ingresado += mov["monto"]
    return [round(gastado, 2), round(ingresado, 2)]

def exportar_csv(datos, ruta):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(["fecha", "tipo", "monto", "cuenta", "destino", "categoria", "descripcion"])
        for mov in filtrar(datos):
            cuenta = buscar_cuenta(datos, mov["cuentaid"])
            destino = buscar_cuenta(datos, mov.get("destinoid"))
            escritor.writerow([mov["fecha"], mov["tipo"], mov["monto"],
                               cuenta["nombre"] if cuenta else "",
                               destino["nombre"] if destino else "",
                               mov["categoria"], mov["descripcion"]])
    return len(datos["movimientos"])


# ---------- Presupuestos (diccionario categoría -> límite mensual) ----------

def fijar_presupuesto(datos, categoria, monto):
    categoria = asegurar_categoria(datos, categoria)
    if monto <= 0:
        datos["presupuestos"].pop(categoria, None)
    else:
        datos["presupuestos"][categoria] = round(float(monto), 2)
    return categoria

def estado_presupuestos(datos, fecha):
    # Lista de [categoria, gastado, limite] del mes de "fecha".
    gastado = {}
    for fila in resumen_por_categoria(datos, inicio_mes(fecha), fin_mes(fecha)):
        gastado[fila[0]] = fila[1]
    filas = []
    for categoria in datos["presupuestos"]:
        filas.append([categoria, gastado.get(categoria, 0), datos["presupuestos"][categoria]])
    return filas

def aviso_presupuesto(datos, categoria, fecha):
    limite = datos["presupuestos"].get(categoria)
    if not limite:
        return None
    gastado = 0
    for fila in resumen_por_categoria(datos, inicio_mes(fecha), fin_mes(fecha)):
        if fila[0] == categoria:
            gastado = fila[1]
    if gastado > limite:
        return "Te pasaste del presupuesto de " + categoria + " por $" + format(gastado - limite, ",.2f") + "."
    if gastado >= limite * AVISO_PRESUPUESTO:
        return "Llevas " + str(round(gastado / limite * 100)) + " % del presupuesto de " + categoria + "."
    return None


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
            if info["diaspago"] <= dias and info["facturado"] > 0:
                lista.append([info["proximopago"], "Pago tarjeta " + cuenta["nombre"], info["facturado"]])
    lista.sort(key=fecha_de_pago)
    return lista


if __name__ == "__main__":
    hoy = date(2026, 11, 5)
    datos = vacio()
    deb = crear_cuenta(datos, "Débito", "debito", 1000)
    tdc = crear_cuenta(datos, "Tarjeta", "credito", 0, 5000, 20, 10)
    agregar_movimiento(datos, "gasto", 150, deb["id"], date(2026, 11, 1), "Tacos", "comida")
    agregar_movimiento(datos, "abono", 500, deb["id"], date(2026, 11, 2), "Pago de trabajo")
    agregar_movimiento(datos, "gasto", 800, tdc["id"], date(2026, 10, 18), "Tenis", "Ropa")
    agregar_movimiento(datos, "gasto", 200, tdc["id"], date(2026, 10, 25), "Cine", "Entretenimiento")
    print(saldo(datos, deb))
    print(saldo(datos, tdc))
    info = info_credito(datos, tdc, hoy)
    print(info["facturado"], info["gastoperiodo"], info["proximopago"], info["uso"])
    print(resumen_por_categoria(datos))
    rec = crear_recurrente(datos, "Netflix", 199, tdc["id"], "mensual", date(2026, 10, 3), "suscripciones", True)
    creados = procesar_automaticos(datos, hoy)
    print(len(creados), rec["proximafecha"])
    print(saldo(datos, tdc))
    print([pago[1] for pago in proximos_pagos(datos, hoy)])
    print(len(filtrar(datos, texto="netflix")))
    print(categoria_sugerida(datos, " tacos "), categoria_sugerida(datos, "nada"))
    # Transferencia: pagar 600 de la tarjeta desde el débito
    t = transferir(datos, deb["id"], tdc["id"], 600, hoy, "Pago tarjeta")
    print("transferencia:", saldo(datos, deb), saldo(datos, tdc), totales_mes(datos, hoy))
    print(transferir(datos, deb["id"], deb["id"], 10, hoy))
    # Editar el movimiento de la transferencia
    llenar_movimiento(datos, t, "transferencia", 700, deb["id"], hoy, "Pago tarjeta", destinoid=tdc["id"])
    print("editada:", saldo(datos, deb), saldo(datos, tdc))
    # Presupuestos
    fijar_presupuesto(datos, "comida", 180)
    print(estado_presupuestos(datos, hoy), aviso_presupuesto(datos, "Comida", hoy))
    agregar_movimiento(datos, "gasto", 50, deb["id"], hoy, "Café", "Comida")
    print(aviso_presupuesto(datos, "Comida", hoy))
    fijar_presupuesto(datos, "Comida", 0)
    print(datos["presupuestos"])
    print(total_disponible(datos), total_deuda(datos))
    import os, tempfile
    ruta = os.path.join(tempfile.gettempdir(), "prueba_gastos.csv")
    print(exportar_csv(datos, ruta), open(ruta, encoding="utf-8-sig").readline().strip())
    os.remove(ruta)
    actualizar_cuenta(tdc, "Tarjeta Nu", "credito", 0, 8000, 20, 10)
    print(info_credito(datos, tdc, hoy)["disponible"])
    print(borrar_cuenta(datos, deb["id"]), len(datos["movimientos"]))
