#!/usr/bin/env python3
"""Backend del módulo Neveras, montado bajo /neveras en Vercel."""

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException
import io
from flask_cors import CORS
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from copy import copy
from storage import load_workbook_for_app, workbook_to_bytes, google_error_status
from datetime import datetime
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.errorhandler(Exception)
def api_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Error no controlado en Neveras")
    quota_status = google_error_status(error)
    if quota_status:
        return jsonify({
            "ok": False,
            "error": "Google Sheets está temporalmente limitado por cuota. Espera unos segundos y vuelve a intentar.",
            "retry_after_seconds": 10,
        }), quota_status
    return jsonify({"ok": False, "error": f"{type(error).__name__}: {error}"}), 500

# Solo se conserva el directorio de recursos de la interfaz. Los datos viven
# exclusivamente en Google Sheets y nunca se buscan en un Excel local.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = "google-sheets://Neveras"

# ─────────────────────────────────────────────────────────────
# COLUMNAS DE LA HOJA "Ventas"
#
#  A(1)  #             ← FORMULA  — NO TOCAR
#  B(2)  Fecha         ← escribir
#  C(3)  Hora          ← escribir
#  D(4)  Cliente       ← escribir
#  E(5)  Producto      ← escribir
#  F(6)  Cantidad      ← escribir
#  G(7)  Precio Unit.  ← FORMULA  — NO TOCAR
#  H(8)  Total         ← FORMULA  — NO TOCAR
#  I(9)  Método Pago   ← escribir
#  J(10) Pagó          ← escribir
#  K(11) Estado Pago   ← escribir
#  L(12) Ganancia      ← FORMULA  — NO TOCAR
#
# La fila vacía se detecta mirando la columna B (no la A).
# ─────────────────────────────────────────────────────────────
COLS_DATOS    = [2, 3, 4, 5, 6, 9, 10, 11]   # B C D E F I J K
COLS_FORMULA  = [1, 7, 8, 12]                  # A G H L  — intocables


def _at(row, index, default=None):
    """Acceso tolerante a filas remotas con celdas vacías finales."""
    return row[index] if index < len(row) else default


def _as_float(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=0):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return default


# ── UTILIDAD: copiar formato de una celda a otra ─────────────

def _copiar_formato(origen, destino):
    """Copia font, fill, border, alignment y number_format de origen a destino."""
    if origen.font:
        destino.font       = copy(origen.font)
    if origen.fill:
        destino.fill       = copy(origen.fill)
    if origen.border:
        destino.border     = copy(origen.border)
    if origen.alignment:
        destino.alignment  = copy(origen.alignment)
    destino.number_format  = origen.number_format


# ── LECTURA ──────────────────────────────────────────────────

def _precio_de_inventario(producto):
    """Devuelve (precio, ganUnit) desde la hoja Inventario."""
    try:
        wb = load_workbook_for_app(EXCEL_PATH, data_only=True, read_only=True)
        ws = wb['Inventario']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if _at(row, 0) and str(_at(row, 0)) == producto:
                precio = _as_float(_at(row, 2))
                costo  = _as_float(_at(row, 1))
                wb.close()
                return precio, precio - costo
        wb.close()
    except Exception:
        pass
    return 0, 0


def leer_ventas(prods_base=None):
    """
    Lee la hoja Ventas.
    Para filas donde Total=0 (fórmula aún sin calcular) rellena
    precio y total desde el inventario base para que el dashboard
    muestre valores correctos inmediatamente.
    """
    wb     = load_workbook_for_app(EXCEL_PATH, data_only=True, read_only=True)
    ws     = wb['Ventas']
    ventas = []

    # Índice rápido precio → para rellenar filas recién escritas
    precio_idx = {}
    if prods_base:
        for p in prods_base:
            precio_idx[p['producto']] = (p['precio'], p['precio'] - p['costo'])

    for row in ws.iter_rows(min_row=2, values_only=True):
        # Detectar fila vacía por columna B (índice 1)
        if not _at(row, 1):
            continue
        num      = _at(row, 0)
        cantidad = _as_int(_at(row, 5))
        producto = str(_at(row, 4) or '')
        precio   = _as_float(_at(row, 6))
        total    = _as_float(_at(row, 7))
        ganancia = _as_float(_at(row, 11))

        # Si las fórmulas aún no tienen valor cacheado, calcular desde inventario
        if precio == 0 and producto in precio_idx:
            precio, ganUnit = precio_idx[producto]
            total    = cantidad * precio
            ganancia = round(cantidad * ganUnit, 2)

        ventas.append({
            'num':      int(num) if num else len(ventas) + 1,
                        'fecha':     str(_at(row, 1) or '')[:10],

                        'hora':      str(_at(row, 2) or ''),
            'cliente':   str(_at(row, 3) or '').upper(),

            'producto': producto,
            'cantidad': cantidad,
            'precio':   precio,
            'total':    total,
                        'metodo':    str(_at(row, 8) or ''),
            'pago':      'SI' if str(_at(row, 9) or '').upper() == 'SI' else 'NO',
            'estado':    str(_at(row, 10) or ''),

            'ganancia': ganancia,
        })

    wb.close()
    return ventas


def leer_inventario_base():
    wb       = load_workbook_for_app(EXCEL_PATH, data_only=True, read_only=True)
    ws       = wb['Inventario']
    prods    = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not _at(row, 0):
            continue
        prods.append({
            'producto': str(_at(row, 0)),
            'costo':    _as_float(_at(row, 1)),
            'precio':   _as_float(_at(row, 2)),
            'stockIni': _as_float(_at(row, 4)),
            'stockMin': _as_float(_at(row, 5)),
        })
    wb.close()
    return prods


def _primera_fila_vacia_inventario(ws):
    """Devuelve la primera fila libre de Inventario según la columna A."""
    max_row = max(int(ws.max_row or 1), 1)
    for row_number in range(2, max_row + 1):
        value = ws.cell(row=row_number, column=1).value
        if value is None or str(value).strip() == '':
            return row_number
    return max_row + 1


def _numero_no_negativo(value, campo, entero=False):
    """Valida importes y cantidades recibidos desde el formulario web."""
    if value is None or str(value).strip() == '':
        raise ValueError(f'El campo {campo} es obligatorio')
    try:
        numero = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'El campo {campo} debe ser numérico') from exc
    if numero != numero or numero in (float('inf'), float('-inf')) or numero < 0:
        raise ValueError(f'El campo {campo} debe ser un número no negativo')
    if entero and not numero.is_integer():
        raise ValueError(f'El campo {campo} debe ser un número entero')
    return int(numero) if entero else round(numero, 2)


def agregar_producto(producto, costo, precio, stock_inicial, stock_minimo):
    """Agrega un producto nuevo a Inventario y confirma la sincronización remota."""
    wb = None
    try:
        nombre = str(producto or '').strip()
        if not nombre:
            raise ValueError('El nombre del producto es obligatorio')

        costo = _numero_no_negativo(costo, 'Costo')
        precio = _numero_no_negativo(precio, 'Precio de venta')
        stock_inicial = _numero_no_negativo(stock_inicial, 'Stock inicial', entero=True)
        stock_minimo = _numero_no_negativo(stock_minimo, 'Stock mínimo', entero=True)

        wb = load_workbook_for_app(EXCEL_PATH)
        ws = wb['Inventario']
        nombres_existentes = {
            str(ws.cell(row=row_number, column=1).value).strip().casefold()
            for row_number in range(2, max(int(ws.max_row or 1), 1) + 1)
            if ws.cell(row=row_number, column=1).value not in (None, '')
        }
        if nombre.casefold() in nombres_existentes:
            return False, 'Ya existe un producto con ese nombre', None

        fila = _primera_fila_vacia_inventario(ws)
        ganancia_unitaria = round(precio - costo, 2)
        stock_actual = stock_inicial
        estado = '🚫 AGOTADO' if stock_actual <= 0 else ('⚠ SURTIR' if stock_actual <= stock_minimo else '✅ OK')
        valores = [
            nombre,
            costo,
            precio,
            ganancia_unitaria,
            stock_inicial,
            stock_minimo,
            0,
            stock_actual,
            estado,
            round(costo * stock_inicial, 2),
            round(ganancia_unitaria * stock_inicial, 2),
        ]
        for column, value in enumerate(valores, start=1):
            ws.cell(row=fila, column=column, value=value)

        resultado = wb.save(EXCEL_PATH)
        confirmado = bool(resultado and resultado.get('Inventario'))
        if not confirmado:
            raise RuntimeError('Google Sheets no confirmó la actualización de Inventario')

        return True, None, {
            'producto': nombre,
            'costo': costo,
            'precio': precio,
            'ganUnit': ganancia_unitaria,
            'stockIni': stock_inicial,
            'stockMin': stock_minimo,
            'vendidos': 0,
            'stockAct': stock_actual,
            'estado': estado,
        }
    finally:
        if wb is not None:
            wb.close()


def calcular_inventario_y_clientes(ventas, prods_base):
    inventario = []
    for p in prods_base:
        vendidos  = sum(v['cantidad'] for v in ventas if v['producto'] == p['producto'])
        stock_act = p['stockIni'] - vendidos
        ganUnit   = p['precio'] - p['costo']
        if stock_act <= 0:
            estado = '🚫 AGOTADO'
        elif stock_act <= p['stockMin']:
            estado = '⚠ SURTIR'
        else:
            estado = '✅ OK'
        inventario.append({
            'producto': p['producto'],
            'costo':    p['costo'],
            'precio':   p['precio'],
            'ganUnit':  ganUnit,
            'stockIni': p['stockIni'],
            'stockMin': p['stockMin'],
            'vendidos': vendidos,
            'stockAct': stock_act,
            'estado':   estado,
        })

    cli_dict = {}
    for v in ventas:
        cli = v['cliente']
        if not cli:
            continue
        if cli not in cli_dict:
            cli_dict[cli] = {'comprado': 0, 'pagado': 0, 'compras': 0}
        cli_dict[cli]['comprado'] += v['total']
        if v['pago'] == 'SI':
            cli_dict[cli]['pagado'] += v['total']
        cli_dict[cli]['compras'] += 1

    clientes = [{
        'cliente':  cli,
        'comprado': v['comprado'],
        'pagado':   v['pagado'],
        'deuda':    v['comprado'] - v['pagado'],
        'compras':  v['compras'],
    } for cli, v in cli_dict.items()]

    return inventario, clientes


# ── ESCRITURA ─────────────────────────────────────────────────

def _primera_fila_vacia(ws):
    """
    Devuelve el número de la primera fila donde la columna B esté vacía.
    Se ignora la columna A porque tiene fórmula y puede tener valor
    incluso si la fila no fue rellenada manualmente.
    """
    fila = 2
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        celda = row[0]
        if celda.value is None or str(celda.value).strip() == '':
            return celda.row
        fila = celda.row + 1
    return fila


def agregar_fila_venta(cliente, producto, cantidad, metodo, pago):
    """
    Agrega una fila en la hoja 'Ventas'.

    REGLAS:
    - Solo escribe en cols B C D E F I J K (índices 2 3 4 5 6 9 10 11).
    - Nunca toca A (formula #), G (Precio), H (Total), L (Ganancia).
    - La fila vacía se localiza mirando la columna B.
    - Copia el formato visual de la fila anterior a las celdas nuevas.
    """
    try:
        # Cargar SIN data_only para preservar las fórmulas existentes
        wb = load_workbook_for_app(EXCEL_PATH)
        ws = wb['Ventas']

        fila      = _primera_fila_vacia(ws)
        fila_ref  = fila - 1   # fila de referencia para copiar formato

        ahora  = datetime.now()
        estado = '✅ PAGADO' if pago.upper() == 'SI' else '🔴 PENDIENTE'

        # Valores a escribir indexados por número de columna
        valores = {
            2:  ahora.strftime('%Y-%m-%d'),   # Fecha
            3:  ahora.strftime('%H:%M'),       # Hora
            4:  cliente.upper(),              # Cliente
            5:  producto,                     # Producto
            6:  cantidad,                     # Cantidad
            9:  metodo,                       # Método Pago
            10: pago.upper(),                 # Pagó
            11: estado,                       # Estado Pago
        }

        for col, valor in valores.items():
            celda_nueva = ws.cell(row=fila,     column=col)
            celda_ref   = ws.cell(row=fila_ref, column=col)

            # Escribir valor
            celda_nueva.value = valor

            # Copiar formato de la fila anterior (si existe)
            if fila_ref >= 2:
                _copiar_formato(celda_ref, celda_nueva)

        wb.save(EXCEL_PATH)
        wb.close()
        return True, None

    except PermissionError:
        return False, ('El archivo Excel está abierto. '
                       'Ciérralo en Excel y vuelve a intentarlo.')
    except Exception as e:
        return False, str(e)


def agregar_filas_venta(cliente, items, metodo, pago):
    """
    Agrega varias filas en la hoja 'Ventas' (una por cada producto de la
    compra), todas con el mismo cliente, método de pago, estado de pago,
    fecha y hora — para representar una sola compra con varios productos.

    items: lista de tuplas (producto, cantidad).
    Misma lógica/columnas que agregar_fila_venta, pero abre y guarda el
    Excel una sola vez para todas las filas.
    """
    try:
        wb = load_workbook_for_app(EXCEL_PATH)
        ws = wb['Ventas']

        ahora  = datetime.now()
        estado = '✅ PAGADO' if pago.upper() == 'SI' else '🔴 PENDIENTE'

        for producto, cantidad in items:
            fila     = _primera_fila_vacia(ws)
            fila_ref = fila - 1

            valores = {
                2:  ahora.strftime('%Y-%m-%d'),   # Fecha
                3:  ahora.strftime('%H:%M'),       # Hora
                4:  cliente.upper(),              # Cliente
                5:  producto,                     # Producto
                6:  cantidad,                     # Cantidad
                9:  metodo,                       # Método Pago
                10: pago.upper(),                 # Pagó
                11: estado,                       # Estado Pago
            }

            for col, valor in valores.items():
                celda_nueva = ws.cell(row=fila,     column=col)
                celda_ref   = ws.cell(row=fila_ref, column=col)
                celda_nueva.value = valor
                if fila_ref >= 2:
                    _copiar_formato(celda_ref, celda_nueva)

        wb.save(EXCEL_PATH)
        wb.close()
        return True, None

    except PermissionError:
        return False, ('El archivo Excel está abierto. '
                       'Ciérralo en Excel y vuelve a intentarlo.')
    except Exception as e:
        return False, str(e)


def marcar_venta_pagada(num):
    """Marca la venta como pagada. Solo toca cols J y K."""
    try:
        wb = load_workbook_for_app(EXCEL_PATH)
        ws = wb['Ventas']

        # ── CORRECCIÓN ────────────────────────────────────────────
        # La col A tiene una fórmula (p. ej. =ROW()-1).
        # Al abrir sin data_only=True, row[0].value devuelve el STRING
        # de la fórmula, nunca el número → la comparación siempre fallaba.
        #
        # Solución: calcular la fila directamente.
        # Fila 1 = encabezado → venta #N siempre está en fila N + 1.
        # ─────────────────────────────────────────────────────────
        fila = int(num) + 1

        # Verificar que la fila tiene datos (col B = Fecha)
        if ws.cell(row=fila, column=2).value is None:
            wb.close()
            return False, f'Venta #{num} no encontrada'

        ws.cell(row=fila, column=10).value = 'SI'
        ws.cell(row=fila, column=11).value = '✅ PAGADO'
        wb.save(EXCEL_PATH)
        wb.close()
        return True, None

    except PermissionError:
        return False, 'El archivo Excel está abierto. Ciérralo e intenta de nuevo.'
    except Exception as e:
        return False, str(e)


# ── HELPER: archivos estáticos en ambas carpetas ─────────────

def _static(nombre):
    return os.path.join(BASE_DIR, nombre)


# ── RUTAS ─────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_file(_static('dashboard_neveras.html'))

@app.route('/styles.css')
def styles():
    return send_file(_static('styles.css'))

@app.route('/app.js')
def appjs():
    return send_file(_static('app.js'))


@app.route('/api/datos')
def get_datos():
    try:
        prods  = leer_inventario_base()
        ventas = leer_ventas(prods)
        inv, cli = calcular_inventario_y_clientes(ventas, prods)
        return jsonify({'ventas': ventas, 'inventario': inv, 'clientes': cli})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/nueva-venta', methods=['POST'])
def nueva_venta():
    data    = request.json
    cliente = data.get('cliente', '').strip()
    metodo  = data.get('metodo', 'Efectivo')
    pago    = data.get('pago', 'NO').upper()

    # Nuevo formato: varios productos en una sola compra.
    # Se mantiene compatibilidad con el formato anterior (un solo producto).
    items_in = data.get('items')
    if items_in:
        items = [(it.get('producto', ''), int(it.get('cantidad', 0) or 0)) for it in items_in]
    else:
        items = [(data.get('producto', ''), int(data.get('cantidad', 1) or 0))]
    items = [(p, c) for p, c in items if p and c >= 1]

    if not cliente or not items:
        return jsonify({'error': 'Datos inválidos'}), 400

    ok, err = agregar_filas_venta(cliente, items, metodo, pago)
    if not ok:
        return jsonify({'error': err}), 500

    prods  = leer_inventario_base()
    ventas = leer_ventas(prods)
    inv, cli = calcular_inventario_y_clientes(ventas, prods)
    resumen = ', '.join(f'{p} x{c}' for p, c in items)
    return jsonify({
        'ok':         True,
        'mensaje':    f'✅ Venta guardada: {cliente} — {resumen}',
        'ventas':     ventas,
        'inventario': inv,
        'clientes':   cli,
    })


@app.route('/api/marcar-pagado', methods=['POST'])
def marcar_pagado():
    data = request.json
    num  = data.get('num')
    if not num:
        return jsonify({'error': 'Número de venta requerido'}), 400

    ok, err = marcar_venta_pagada(int(num))
    if not ok:
        return jsonify({'error': err}), 500

    prods  = leer_inventario_base()
    ventas = leer_ventas(prods)
    inv, cli = calcular_inventario_y_clientes(ventas, prods)
    return jsonify({
        'ok':         True,
        'mensaje':    f'✅ Venta #{num} marcada como pagada',
        'ventas':     ventas,
        'inventario': inv,
        'clientes':   cli,
    })


@app.route('/api/productos')
def get_productos():
    try:
        prods  = leer_inventario_base()
        ventas = leer_ventas(prods)
        inv, _ = calcular_inventario_y_clientes(ventas, prods)
        return jsonify([{
            'nombre':  p['producto'],
            'precio':  p['precio'],
            'ganUnit': p['ganUnit'],
            'stock':   p['stockAct'],
        } for p in inv])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/nuevo-producto', methods=['POST'])
def nuevo_producto():
    data = request.get_json(silent=True) or {}
    try:
        ok, error, producto = agregar_producto(
            data.get('producto'),
            data.get('costo'),
            data.get('precio'),
            data.get('stockInicial'),
            data.get('stockMin'),
        )
        if not ok:
            return jsonify({'ok': False, 'error': error}), 409
        return jsonify({
            'ok': True,
            'mensaje': f"✅ Producto '{producto['producto']}' guardado en Google Sheets",
            'producto': producto,
        })
    except Exception as exc:
        quota_status = google_error_status(exc)
        if quota_status:
            return jsonify({
                'ok': False,
                'error': 'Google Sheets está temporalmente limitado por cuota. Espera unos segundos y vuelve a intentar.',
                'retry_after_seconds': 10,
            }), quota_status
        return jsonify({'ok': False, 'error': str(exc)}), 400


@app.route('/api/lista-clientes')
def lista_clientes():
    """
    Lee TODA la columna A de la hoja 'Clientes' desde la fila 2.
    No usa read_only para evitar que openpyxl corte el max_row antes de tiempo.
    """
    try:
        wb = load_workbook_for_app(EXCEL_PATH, data_only=True)
        ws = wb['Clientes']
        nombres = []
        for row in ws.iter_rows(min_row=2, min_col=1, max_col=1):
            val = row[0].value
            if val is not None and str(val).strip() != '':
                nombres.append(str(val).strip().upper())
        wb.close()
        return jsonify(nombres)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/excel')
def download_excel():
    content = workbook_to_bytes(EXCEL_PATH)
    return send_file(io.BytesIO(content),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name='INVENTARIO_NEVERAS.xlsx')


# Vercel carga este módulo desde el WSGI unificado de ../app.py.
