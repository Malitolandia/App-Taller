from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.exceptions import HTTPException
import os
import io
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from storage import load_workbook_for_app, workbook_to_bytes

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            static_url_path='/static')

@app.errorhandler(Exception)
def api_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Error no controlado en ControlTaller")
    return jsonify({"success": False, "error": f"{type(error).__name__}: {error}"}), 500

EXCEL_FILE = "google-sheets://ControlTaller"

COMISION_DEFAULT = 50  # % de la mano de obra que se paga al mecánico (editable)

CATEGORIAS_GASTO_DEFAULT = ["Gasolina", "Repuestos", "Almuerzos", "Herramientas", "Servicios", "Otros"]

SHEET_HEADERS = {
    "Mecanicos": ["ID", "Nombre", "Teléfono", "% Comisión", "Activo", "Fecha Ingreso"],
    "Equipos": ["ID", "Nombre", "Integrante 1", "Integrante 2", "% Comisión Total", "Activo"],
    "Trabajos": ["ID", "Fecha", "Semana", "Mecánico", "Equipo", "Placa", "Vehículo",
                 "Descripción", "Monto Mano de Obra", "% Comisión", "Monto Mecánico",
                 "Factura Cancelada", "Estado", "Fecha Pago", "Grupo"],
    "Gastos": ["ID", "Fecha", "Categoría", "Descripción", "Monto", "Responsable", "Método de Pago"],
    "Pagos": ["ID", "Fecha Pago", "Mecánico", "Semana", "N° Trabajos",
              "Total Mano de Obra", "Total Comisión", "Total Descuentos", "Neto Pagado"],
    "Prestamos": ["ID", "Fecha", "Mecánico", "Monto Original", "Cuota Sugerida",
                  "Total Descontado", "Saldo Pendiente", "Estado", "Observaciones"],
    "Descuentos Nomina": ["ID", "Fecha Aplicación", "Mecánico", "Semana", "Concepto",
                          "Monto", "Préstamo ID", "Observaciones"],
    "Herramientas": ["ID", "Herramienta", "Prestada A", "Entregada Por", "Fecha Préstamo",
                      "Fecha Devolución", "Estado", "Observaciones"],
}

# ---------------------------------------------------------------------------
# Las pestañas y encabezados remotos se preparan en storage.py.
# Este módulo solo trabaja sobre la instantánea recibida de Google Sheets.

def get_wb():
    """Carga una instantánea actual desde Google Sheets."""
    return load_workbook_for_app(EXCEL_FILE)


def next_id(ws):
    max_id = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None:
            try:
                max_id = max(max_id, int(row[0]))
            except (TypeError, ValueError):
                pass
    return max_id + 1


def append_row(ws, headers, row_values, id_val, zebra=True):
    row_num = ws.max_row + 1
    fill_color = "F9EBEA" if zebra and row_num % 2 == 0 else "FFFFFF"
    for col, header in enumerate(headers, 1):
        value = row_values.get(header, "")
        cell = ws.cell(row=row_num, column=col, value=value)
        cell.fill = PatternFill("solid", fgColor=fill_color)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                              top=Side(style='thin'), bottom=Side(style='thin'))
        if col == 1:
            cell.font = Font(bold=True, color="C0392B")
    return row_num


def sheet_to_dicts(ws, headers):
    result = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None:
            result.append(dict(zip(headers, row)))
    return result


def find_row_by_id(ws, target_id):
    for row in ws.iter_rows(min_row=2):
        if row[0].value is not None and str(row[0].value) == str(target_id):
            return row
    return None


def week_key(fecha_str):
    """fecha_str = 'YYYY-MM-DD' -> 'YYYY-Wnn' (semana ISO)"""
    d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def money(value):
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def normalize_name(value):
    return " ".join(str(value or "").strip().split()).casefold()


def _row_values(row, headers):
    return {headers[i]: row[i].value for i in range(min(len(headers), len(row)))}


def _loan_records(wb):
    """Devuelve préstamos con saldo calculado y no altera la hoja."""
    ws = wb["Prestamos"]
    headers = SHEET_HEADERS["Prestamos"]
    records = []
    for row in ws.iter_rows(min_row=2):
        if row[0].value is None:
            continue
        values = _row_values(row, headers)
        original = money(values.get("Monto Original"))
        discounted = money(values.get("Total Descontado"))
        saldo = max(round(original - discounted, 2), 0.0)
        estado = "Pagado" if saldo <= 0.009 else "Pendiente"
        records.append({
            "id": int(values.get("ID") or 0),
            "fecha": values.get("Fecha") or "",
            "mecanico": values.get("Mecánico") or "",
            "monto_original": original,
            "cuota_sugerida": money(values.get("Cuota Sugerida")),
            "total_descontado": discounted,
            "saldo_pendiente": saldo,
            "estado": estado,
            "observaciones": values.get("Observaciones") or "",
        })
    return records


def _discount_records(wb):
    ws = wb["Descuentos Nomina"]
    headers = SHEET_HEADERS["Descuentos Nomina"]
    records = []
    for row in ws.iter_rows(min_row=2):
        if row[0].value is None:
            continue
        values = _row_values(row, headers)
        records.append({
            "id": int(values.get("ID") or 0),
            "fecha_aplicacion": values.get("Fecha Aplicación") or "",
            "mecanico": values.get("Mecánico") or "",
            "semana": values.get("Semana") or "",
            "concepto": values.get("Concepto") or "",
            "monto": money(values.get("Monto")),
            "prestamo_id": int(values["Préstamo ID"]) if str(values.get("Préstamo ID") or "").strip().isdigit() else None,
            "observaciones": values.get("Observaciones") or "",
        })
    return records


def _nomina_calculada(wb, semana=None, mecanico=None):
    """Calcula bruto pendiente, descuentos aplicados y neto por mecánico."""
    ws = wb["Trabajos"]
    headers = SHEET_HEADERS["Trabajos"]
    resumen = {}
    for row in ws.iter_rows(min_row=2):
        if row[0].value is None:
            continue
        values = _row_values(row, headers)
        if semana and values.get("Semana") != semana:
            continue
        if mecanico and values.get("Mecánico") != mecanico:
            continue
        if values.get("Factura Cancelada") != "Sí":
            continue
        mec = values.get("Mecánico") or "Sin asignar"
        item = resumen.setdefault(mec, {
            "mecanico": mec, "n_trabajos": 0, "total_mo": 0.0,
            "total_comision": 0.0, "pendiente": 0.0, "pagado": 0.0,
            "bruto_pendiente": 0.0, "descuentos": 0.0, "neto_pagar": 0.0,
        })
        monto_mo = money(values.get("Monto Mano de Obra"))
        monto_mec = money(values.get("Monto Mecánico"))
        item["n_trabajos"] += 1
        item["total_mo"] += monto_mo
        item["total_comision"] += monto_mec
        if values.get("Estado") == "Pagado":
            item["pagado"] += monto_mec
        else:
            item["pendiente"] += monto_mec

    discounts = _discount_records(wb)
    for item in resumen.values():
        if semana:
            item["descuentos"] = sum(
                d["monto"] for d in discounts
                if d["mecanico"] == item["mecanico"] and d["semana"] == semana
            )
        else:
            item["descuentos"] = sum(
                d["monto"] for d in discounts if d["mecanico"] == item["mecanico"]
            )
        item["bruto_pendiente"] = round(item["pendiente"], 2)
        item["descuentos"] = round(item["descuentos"], 2)
        item["neto_pagar"] = round(max(item["bruto_pendiente"] - item["descuentos"], 0), 2)
        for key in ("total_mo", "total_comision", "pendiente", "pagado"):
            item[key] = round(item[key], 2)
    return list(resumen.values())


def _nomina_response(wb, semana=None, mecanico=None):
    resumen = _nomina_calculada(wb, semana=semana, mecanico=mecanico)
    ws = wb["Trabajos"]
    headers = SHEET_HEADERS["Trabajos"]
    semanas = sorted({
        _row_values(row, headers).get("Semana")
        for row in ws.iter_rows(min_row=2)
        if row[0].value is not None and _row_values(row, headers).get("Semana")
    }, reverse=True)
    totales = {
        "bruto_pendiente": round(sum(r["bruto_pendiente"] for r in resumen), 2),
        "descuentos": round(sum(r["descuentos"] for r in resumen), 2),
        "neto_pagar": round(sum(r["neto_pagar"] for r in resumen), 2),
    }
    return {"resumen": resumen, "semanas_disponibles": semanas, "totales": totales}


# ---------------------------------------------------------------------------
# Rutas de página
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html', comision_default=COMISION_DEFAULT,
                            categorias=CATEGORIAS_GASTO_DEFAULT)


# ---------------------------------------------------------------------------
# API Mecánicos
# ---------------------------------------------------------------------------

@app.route('/api/mecanicos', methods=['GET'])
def list_mecanicos():
    wb = get_wb()
    ws = wb["Mecanicos"]
    return jsonify(sheet_to_dicts(ws, SHEET_HEADERS["Mecanicos"]))


@app.route('/api/mecanicos', methods=['POST'])
def create_mecanico():
    data = request.json
    wb = get_wb()
    ws = wb["Mecanicos"]
    mid = next_id(ws)
    append_row(ws, SHEET_HEADERS["Mecanicos"], {
        "ID": mid,
        "Nombre": data.get("nombre", "").strip(),
        "Teléfono": data.get("telefono", ""),
        "% Comisión": float(data.get("comision", COMISION_DEFAULT)),
        "Activo": "Sí",
        "Fecha Ingreso": data.get("fecha_ingreso", datetime.now().strftime("%Y-%m-%d")),
    }, mid)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "id": mid})


@app.route('/api/mecanicos/<int:mid>', methods=['PUT'])
def update_mecanico(mid):
    data = request.json
    wb = get_wb()
    ws = wb["Mecanicos"]
    row = find_row_by_id(ws, mid)
    if not row:
        return jsonify({"success": False, "error": "No encontrado"}), 404
    headers = SHEET_HEADERS["Mecanicos"]
    field_map = {"nombre": "Nombre", "telefono": "Teléfono",
                 "comision": "% Comisión", "activo": "Activo"}
    for key, header in field_map.items():
        if key in data:
            col = headers.index(header) + 1
            val = data[key]
            if key == "comision":
                val = float(val)
            ws.cell(row=row[0].row, column=col, value=val)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/mecanicos/<int:mid>', methods=['DELETE'])
def delete_mecanico(mid):
    wb = get_wb()
    ws = wb["Mecanicos"]
    row = find_row_by_id(ws, mid)
    if row:
        ws.delete_rows(row[0].row, 1)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# API Equipos (mecánicos en pareja)
# ---------------------------------------------------------------------------

@app.route('/api/equipos', methods=['GET'])
def list_equipos():
    wb = get_wb()
    ws = wb["Equipos"]
    return jsonify(sheet_to_dicts(ws, SHEET_HEADERS["Equipos"]))


@app.route('/api/equipos', methods=['POST'])
def create_equipo():
    data = request.json
    m1 = (data.get("integrante1") or "").strip()
    m2 = (data.get("integrante2") or "").strip()
    if not m1 or not m2 or m1 == m2:
        return jsonify({"success": False, "error": "Selecciona dos mecánicos distintos"}), 400
    wb = get_wb()
    ws = wb["Equipos"]
    eid = next_id(ws)
    append_row(ws, SHEET_HEADERS["Equipos"], {
        "ID": eid,
        "Nombre": f"{m1} + {m2}",
        "Integrante 1": m1,
        "Integrante 2": m2,
        "% Comisión Total": float(data.get("comision_total", COMISION_DEFAULT)),
        "Activo": "Sí",
    }, eid)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "id": eid})


@app.route('/api/equipos/<int:eid>', methods=['PUT'])
def update_equipo(eid):
    data = request.json
    wb = get_wb()
    ws = wb["Equipos"]
    row = find_row_by_id(ws, eid)
    if not row:
        return jsonify({"success": False, "error": "No encontrado"}), 404
    headers = SHEET_HEADERS["Equipos"]
    field_map = {"comision_total": "% Comisión Total", "activo": "Activo"}
    for key, header in field_map.items():
        if key in data:
            col = headers.index(header) + 1
            val = data[key]
            if key == "comision_total":
                val = float(val)
            ws.cell(row=row[0].row, column=col, value=val)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/equipos/<int:eid>', methods=['DELETE'])
def delete_equipo(eid):
    wb = get_wb()
    ws = wb["Equipos"]
    row = find_row_by_id(ws, eid)
    if row:
        ws.delete_rows(row[0].row, 1)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# API Trabajos / Nómina
# ---------------------------------------------------------------------------

@app.route('/api/trabajos', methods=['GET'])
def list_trabajos():
    wb = get_wb()
    ws = wb["Trabajos"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Trabajos"])
    semana = request.args.get('semana')
    mecanico = request.args.get('mecanico')
    if semana:
        data = [d for d in data if d.get("Semana") == semana]
    if mecanico:
        data = [d for d in data if d.get("Mecánico") == mecanico]
    data.sort(key=lambda d: (d.get("Fecha") or "", d.get("ID") or 0), reverse=True)
    return jsonify(data)


@app.route('/api/trabajo', methods=['POST'])
def create_trabajo():
    data = request.json
    fecha = data.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    monto_mo = float(data.get("monto_mo", 0) or 0)
    semana = week_key(fecha)
    placa = (data.get("placa", "") or "").upper()
    vehiculo = data.get("vehiculo", "")
    descripcion = data.get("descripcion", "")
    factura_cancelada = "Sí" if data.get("factura_cancelada") else "No"

    print(f"\n[DEBUG] POST /api/trabajo recibido: {data}")
    print(f"[DEBUG] data.get('factura_cancelada') = {data.get('factura_cancelada')!r} (tipo {type(data.get('factura_cancelada')).__name__}) -> se guardará como: {factura_cancelada!r}\n")

    wb = get_wb()
    ws = wb["Trabajos"]

    base = {
        "Fecha": fecha, "Semana": semana, "Placa": placa, "Vehículo": vehiculo,
        "Descripción": descripcion, "Monto Mano de Obra": monto_mo,
        "Factura Cancelada": factura_cancelada,
        "Estado": "Pendiente", "Fecha Pago": "",
    }

    if data.get("modo") == "equipo":
        # --- Trabajo en pareja: se reparte el % total entre los dos integrantes ---
        equipo_id = data.get("equipo_id")
        ws_eq = wb["Equipos"]
        row_eq = find_row_by_id(ws_eq, equipo_id)
        if not row_eq:
            return jsonify({"success": False, "error": "Equipo no encontrado"}), 404
        eq_headers = SHEET_HEADERS["Equipos"]
        eq_vals = {eq_headers[i]: row_eq[i].value for i in range(len(eq_headers))}

        comision_total = float(data.get("comision_pct", eq_vals.get("% Comisión Total", COMISION_DEFAULT)) or COMISION_DEFAULT)
        comision_individual = round(comision_total / 2, 4)
        monto_individual = round(monto_mo * comision_individual / 100, 2)
        nombre_equipo = eq_vals.get("Nombre", "")
        integrantes = [eq_vals.get("Integrante 1"), eq_vals.get("Integrante 2")]

        grupo_id = next_id(ws)
        for i, mec in enumerate(integrantes):
            tid = grupo_id if i == 0 else next_id(ws)
            row_data = dict(base)
            row_data.update({
                "ID": tid, "Mecánico": mec, "Equipo": nombre_equipo,
                "% Comisión": comision_individual, "Monto Mecánico": monto_individual,
                "Grupo": grupo_id,
            })
            append_row(ws, SHEET_HEADERS["Trabajos"], row_data, tid)

        wb.save(EXCEL_FILE)
        return jsonify({"success": True, "monto_mecanico": monto_individual, "equipo": nombre_equipo,
                         "comision_individual": comision_individual})

    else:
        # --- Trabajo individual ---
        mecanico = data.get("mecanico", "")
        comision_pct = float(data.get("comision_pct", COMISION_DEFAULT) or COMISION_DEFAULT)
        monto_mecanico = round(monto_mo * comision_pct / 100, 2)
        tid = next_id(ws)
        row_data = dict(base)
        row_data.update({
            "ID": tid, "Mecánico": mecanico, "Equipo": "",
            "% Comisión": comision_pct, "Monto Mecánico": monto_mecanico, "Grupo": "",
        })
        append_row(ws, SHEET_HEADERS["Trabajos"], row_data, tid)
        wb.save(EXCEL_FILE)
        return jsonify({"success": True, "id": tid, "monto_mecanico": monto_mecanico})


@app.route('/api/trabajo/<int:tid>', methods=['PUT'])
def update_trabajo(tid):
    data = request.json
    wb = get_wb()
    ws = wb["Trabajos"]
    row = find_row_by_id(ws, tid)
    if not row:
        return jsonify({"success": False, "error": "No encontrado"}), 404
    headers = SHEET_HEADERS["Trabajos"]
    r = row[0].row

    def set_val(header, value):
        ws.cell(row=r, column=headers.index(header) + 1, value=value)

    if "monto_mo" in data or "comision_pct" in data:
        monto_mo = float(data.get("monto_mo", ws.cell(row=r, column=headers.index("Monto Mano de Obra")+1).value or 0))
        comision_pct = float(data.get("comision_pct", ws.cell(row=r, column=headers.index("% Comisión")+1).value or COMISION_DEFAULT))
        set_val("Monto Mano de Obra", monto_mo)
        set_val("% Comisión", comision_pct)
        set_val("Monto Mecánico", round(monto_mo * comision_pct / 100, 2))
    for key, header in {"descripcion": "Descripción", "placa": "Placa",
                         "vehiculo": "Vehículo"}.items():
        if key in data:
            set_val(header, data[key])
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/trabajo/<int:tid>/factura', methods=['POST'])
def marcar_factura_cancelada(tid):
    wb = get_wb()
    ws = wb["Trabajos"]
    headers = SHEET_HEADERS["Trabajos"]
    row = find_row_by_id(ws, tid)
    if not row:
        return jsonify({"success": False, "error": "No encontrado"}), 404

    # Si el trabajo es de un equipo (Grupo), se marca para ambos integrantes a la vez.
    grupo = row[headers.index("Grupo")].value
    filas_a_marcar = [row[0].row]
    if grupo:
        for r in ws.iter_rows(min_row=2):
            if r[0].value is None or r[0].row == row[0].row:
                continue
            if r[headers.index("Grupo")].value == grupo:
                filas_a_marcar.append(r[0].row)

    col = headers.index("Factura Cancelada") + 1
    for r_num in filas_a_marcar:
        ws.cell(row=r_num, column=col, value="Sí")

    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/trabajo/<int:tid>', methods=['DELETE'])
def delete_trabajo(tid):
    wb = get_wb()
    ws = wb["Trabajos"]
    headers = SHEET_HEADERS["Trabajos"]
    row = find_row_by_id(ws, tid)
    if not row:
        wb.save(EXCEL_FILE)
        return jsonify({"success": True})

    grupo = row[headers.index("Grupo")].value
    rows_to_delete = [row[0].row]

    if grupo:
        for r in ws.iter_rows(min_row=2):
            if r[0].value is None or r[0].row == row[0].row:
                continue
            if r[headers.index("Grupo")].value == grupo:
                rows_to_delete.append(r[0].row)

    for r_num in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(r_num, 1)

    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/nomina/resumen', methods=['GET'])
def nomina_resumen():
    semana = request.args.get('semana')
    wb = get_wb()
    return jsonify(_nomina_response(wb, semana=semana))


# ---------------------------------------------------------------------------
# API Préstamos y descuentos de Nómina
# ---------------------------------------------------------------------------

@app.route('/api/prestamos', methods=['GET'])
def list_prestamos():
    wb = get_wb()
    mecanico = request.args.get('mecanico')
    prestamos = _loan_records(wb)
    descuentos = _discount_records(wb)
    if mecanico:
        prestamos = [p for p in prestamos if p['mecanico'] == mecanico]
        descuentos = [d for d in descuentos if d['mecanico'] == mecanico]
    return jsonify({'prestamos': prestamos, 'descuentos': descuentos})


@app.route('/api/prestamos/panel', methods=['GET'])
def prestamos_panel():
    semana = request.args.get('semana')
    wb = get_wb()
    return jsonify({
        'nomina': _nomina_response(wb, semana=semana),
        'prestamos': _loan_records(wb),
        'descuentos': _discount_records(wb),
    })


@app.route('/api/prestamo', methods=['POST'])
def create_prestamo():
    data = request.json or {}
    mecanico = ' '.join(str(data.get('mecanico') or '').strip().split())
    try:
        monto = round(float(data.get('monto_original') or 0), 2)
        cuota = round(float(data.get('cuota_sugerida') or 0), 2)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'El monto y la cuota deben ser numéricos'}), 400
    if not mecanico or monto <= 0 or cuota <= 0:
        return jsonify({'success': False, 'error': 'Mecánico, monto y cuota son obligatorios y deben ser mayores que cero'}), 400
    if cuota > monto:
        cuota = monto

    wb = get_wb()
    ws_mec = wb['Mecanicos']
    if not any(normalize_name(row[1].value) == normalize_name(mecanico) and row[4].value != 'No'
               for row in ws_mec.iter_rows(min_row=2) if row[0].value is not None):
        return jsonify({'success': False, 'error': 'El mecánico no existe o está inactivo'}), 400
    ws = wb['Prestamos']
    pid = next_id(ws)
    fecha = data.get('fecha') or datetime.now().strftime('%Y-%m-%d')
    append_row(ws, SHEET_HEADERS['Prestamos'], {
        'ID': pid, 'Fecha': fecha, 'Mecánico': mecanico,
        'Monto Original': monto, 'Cuota Sugerida': cuota,
        'Total Descontado': 0.0, 'Saldo Pendiente': monto,
        'Estado': 'Pendiente', 'Observaciones': (data.get('observaciones') or '').strip(),
    }, pid)
    wb.save(EXCEL_FILE)
    return jsonify({'success': True, 'id': pid, 'saldo_pendiente': monto})


@app.route('/api/prestamo/<int:pid>', methods=['PUT'])
def update_prestamo(pid):
    data = request.json or {}
    wb = get_wb()
    ws = wb['Prestamos']
    row = find_row_by_id(ws, pid)
    if not row:
        return jsonify({'success': False, 'error': 'Préstamo no encontrado'}), 404
    headers = SHEET_HEADERS['Prestamos']
    original = money(row[headers.index('Monto Original')].value)
    descontado = money(row[headers.index('Total Descontado')].value)
    if 'cuota_sugerida' in data:
        try:
            cuota = round(float(data.get('cuota_sugerida') or 0), 2)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'La cuota debe ser numérica'}), 400
        if cuota <= 0 or cuota > max(round(original - descontado, 2), 0):
            return jsonify({'success': False, 'error': 'La cuota debe ser mayor que cero y no superar el saldo pendiente'}), 400
        ws.cell(row=row[0].row, column=headers.index('Cuota Sugerida') + 1, value=cuota)
    if 'observaciones' in data:
        ws.cell(row=row[0].row, column=headers.index('Observaciones') + 1, value=(data.get('observaciones') or '').strip())
    wb.save(EXCEL_FILE)
    return jsonify({'success': True})


@app.route('/api/prestamo/<int:pid>', methods=['DELETE'])
def delete_prestamo(pid):
    wb = get_wb()
    ws = wb['Prestamos']
    row = find_row_by_id(ws, pid)
    if not row:
        return jsonify({'success': False, 'error': 'Préstamo no encontrado'}), 404
    if any(d['prestamo_id'] == pid for d in _discount_records(wb)):
        return jsonify({'success': False, 'error': 'No se puede eliminar un préstamo que ya tiene descuentos aplicados'}), 409
    ws.delete_rows(row[0].row, 1)
    wb.save(EXCEL_FILE)
    return jsonify({'success': True})


@app.route('/api/nomina/descuento', methods=['POST'])
def aplicar_descuento_nomina():
    data = request.json or {}
    mecanico = ' '.join(str(data.get('mecanico') or '').strip().split())
    semana = str(data.get('semana') or '').strip()
    concepto = ' '.join(str(data.get('concepto') or '').strip().split())
    try:
        monto = round(float(data.get('monto') or 0), 2)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'El descuento debe ser numérico'}), 400
    if not mecanico or not semana or not concepto or monto <= 0:
        return jsonify({'success': False, 'error': 'Mecánico, semana, concepto y monto son obligatorios'}), 400

    raw_loan = data.get('prestamo_id')
    loan_id = None
    if raw_loan not in (None, '', 0, '0'):
        try:
            loan_id = int(raw_loan)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'El préstamo seleccionado no es válido'}), 400

    wb = get_wb()
    loans = _loan_records(wb)
    loan = next((p for p in loans if p['id'] == loan_id), None) if loan_id else None
    if loan_id and not loan:
        return jsonify({'success': False, 'error': 'Préstamo no encontrado'}), 404
    if loan and loan['mecanico'] != mecanico:
        return jsonify({'success': False, 'error': 'El préstamo no pertenece al mecánico seleccionado'}), 400
    if loan and monto > loan['saldo_pendiente']:
        return jsonify({'success': False, 'error': 'El descuento supera el saldo pendiente del préstamo'}), 400

    nomina = next((r for r in _nomina_calculada(wb, semana=semana, mecanico=mecanico)), None)
    bruto = nomina['bruto_pendiente'] if nomina else 0.0
    descuentos = _discount_records(wb)
    ya_aplicado = sum(d['monto'] for d in descuentos if d['mecanico'] == mecanico and d['semana'] == semana)
    disponible = max(round(bruto - ya_aplicado, 2), 0.0)
    if monto > disponible:
        return jsonify({'success': False, 'error': f'El descuento supera el saldo de nómina disponible ({disponible:.2f})'}), 400

    ws_d = wb['Descuentos Nomina']
    did = next_id(ws_d)
    fecha = data.get('fecha') or datetime.now().strftime('%Y-%m-%d')
    append_row(ws_d, SHEET_HEADERS['Descuentos Nomina'], {
        'ID': did, 'Fecha Aplicación': fecha, 'Mecánico': mecanico,
        'Semana': semana, 'Concepto': concepto, 'Monto': monto,
        'Préstamo ID': loan_id or '', 'Observaciones': (data.get('observaciones') or '').strip(),
    }, did)

    if loan:
        ws_l = wb['Prestamos']
        row_l = find_row_by_id(ws_l, loan_id)
        headers_l = SHEET_HEADERS['Prestamos']
        total_descontado = round(loan['total_descontado'] + monto, 2)
        saldo = max(round(loan['monto_original'] - total_descontado, 2), 0.0)
        ws_l.cell(row=row_l[0].row, column=headers_l.index('Total Descontado') + 1, value=total_descontado)
        ws_l.cell(row=row_l[0].row, column=headers_l.index('Saldo Pendiente') + 1, value=saldo)
        ws_l.cell(row=row_l[0].row, column=headers_l.index('Estado') + 1, value='Pagado' if saldo <= 0.009 else 'Pendiente')

    wb.save(EXCEL_FILE)
    return jsonify({'success': True, 'id': did, 'monto': monto, 'saldo_prestamo': loan['saldo_pendiente'] - monto if loan else None,
                    'nomina': _nomina_response(wb, semana=semana)})


@app.route('/api/nomina/pagar', methods=['POST'])
def pagar_nomina():
    data = request.json
    mecanico = data.get("mecanico")
    semana = data.get("semana")
    if not mecanico or not semana:
        return jsonify({"success": False, "error": "Falta mecánico o semana"}), 400

    wb = get_wb()
    ws = wb["Trabajos"]
    headers = SHEET_HEADERS["Trabajos"]
    fecha_pago = datetime.now().strftime("%Y-%m-%d")
    n_trabajos, total_mo, total_comision = 0, 0.0, 0.0

    for row in ws.iter_rows(min_row=2):
        if row[0].value is None:
            continue
        vals = {headers[i]: row[i].value for i in range(len(headers))}
        if (vals.get("Mecánico") == mecanico and vals.get("Semana") == semana
                and vals.get("Estado") != "Pagado" and vals.get("Factura Cancelada") == "Sí"):
            n_trabajos += 1
            total_mo += float(vals.get("Monto Mano de Obra") or 0)
            total_comision += float(vals.get("Monto Mecánico") or 0)
            row[headers.index("Estado")].value = "Pagado"
            row[headers.index("Fecha Pago")].value = fecha_pago

    descuentos_periodo = sum(
        d['monto'] for d in _discount_records(wb)
        if d['mecanico'] == mecanico and d['semana'] == semana
    )
    # Si existía un pago anterior de la misma semana, sus descuentos ya fueron
    # aplicados y no deben restarse otra vez sobre trabajos nuevos.
    pagos_previos = 0.0
    ws_pagos = wb['Pagos']
    headers_pagos = SHEET_HEADERS['Pagos']
    for row_pago in ws_pagos.iter_rows(min_row=2):
        if row_pago[0].value is None:
            continue
        vals_pago = _row_values(row_pago, headers_pagos)
        if vals_pago.get('Mecánico') == mecanico and vals_pago.get('Semana') == semana:
            pagos_previos += money(vals_pago.get('Total Descuentos'))
    total_descuentos = round(max(descuentos_periodo - pagos_previos, 0.0), 2)
    total_descuentos = min(total_descuentos, round(total_comision, 2))
    neto_pagado = round(max(total_comision - total_descuentos, 0), 2)

    if n_trabajos > 0:
        ws_pagos = wb["Pagos"]
        pid = next_id(ws_pagos)
        append_row(ws_pagos, SHEET_HEADERS["Pagos"], {
            "ID": pid, "Fecha Pago": fecha_pago, "Mecánico": mecanico,
            "Semana": semana, "N° Trabajos": n_trabajos,
            "Total Mano de Obra": round(total_mo, 2), "Total Comisión": round(total_comision, 2),
            "Total Descuentos": total_descuentos, "Neto Pagado": neto_pagado,
        }, pid)

    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "n_trabajos": n_trabajos,
                    "total_comision": round(total_comision, 2),
                    "total_descuentos": total_descuentos,
                    "neto_pagado": neto_pagado})


@app.route('/api/pagos', methods=['GET'])
def list_pagos():
    wb = get_wb()
    ws = wb["Pagos"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Pagos"])
    data.sort(key=lambda d: d.get("ID") or 0, reverse=True)
    return jsonify(data)


# ---------------------------------------------------------------------------
# API Gastos
# ---------------------------------------------------------------------------

@app.route('/api/gastos', methods=['GET'])
def list_gastos():
    wb = get_wb()
    ws = wb["Gastos"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Gastos"])
    fecha = request.args.get('fecha')
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    categoria = request.args.get('categoria')
    if fecha:
        data = [d for d in data if d.get("Fecha") == fecha]
    if desde:
        data = [d for d in data if (d.get("Fecha") or "") >= desde]
    if hasta:
        data = [d for d in data if (d.get("Fecha") or "") <= hasta]
    if categoria:
        data = [d for d in data if d.get("Categoría") == categoria]
    data.sort(key=lambda d: (d.get("Fecha") or "", d.get("ID") or 0), reverse=True)
    return jsonify(data)


@app.route('/api/gasto', methods=['POST'])
def create_gasto():
    data = request.json
    wb = get_wb()
    ws = wb["Gastos"]
    gid = next_id(ws)
    append_row(ws, SHEET_HEADERS["Gastos"], {
        "ID": gid,
        "Fecha": data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
        "Categoría": data.get("categoria", "Otros"),
        "Descripción": data.get("descripcion", ""),
        "Monto": float(data.get("monto", 0) or 0),
        "Responsable": data.get("responsable", ""),
        "Método de Pago": data.get("metodo_pago", ""),
    }, gid)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "id": gid})


@app.route('/api/gasto/<int:gid>', methods=['DELETE'])
def delete_gasto(gid):
    wb = get_wb()
    ws = wb["Gastos"]
    row = find_row_by_id(ws, gid)
    if row:
        ws.delete_rows(row[0].row, 1)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/gastos/resumen', methods=['GET'])
def resumen_gastos():
    fecha = request.args.get('fecha', datetime.now().strftime("%Y-%m-%d"))
    wb = get_wb()
    ws = wb["Gastos"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Gastos"])

    hoy = [d for d in data if d.get("Fecha") == fecha]
    total_hoy = sum(float(d.get("Monto") or 0) for d in hoy)
    por_categoria = {}
    for d in hoy:
        cat = d.get("Categoría", "Otros")
        por_categoria[cat] = por_categoria.get(cat, 0) + float(d.get("Monto") or 0)

    mes = fecha[:7]
    del_mes = [d for d in data if (d.get("Fecha") or "").startswith(mes)]
    total_mes = sum(float(d.get("Monto") or 0) for d in del_mes)

    return jsonify({
        "fecha": fecha, "total_hoy": round(total_hoy, 2),
        "por_categoria": por_categoria, "total_mes": round(total_mes, 2),
    })


# ---------------------------------------------------------------------------
# API Herramientas
# ---------------------------------------------------------------------------

@app.route('/api/herramientas', methods=['GET'])
def list_herramientas():
    wb = get_wb()
    ws = wb["Herramientas"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Herramientas"])
    estado = request.args.get('estado')
    if estado:
        data = [d for d in data if d.get("Estado") == estado]
    data.sort(key=lambda d: (d.get("Fecha Préstamo") or "", d.get("ID") or 0), reverse=True)
    return jsonify(data)


@app.route('/api/herramienta', methods=['POST'])
def create_herramienta():
    data = request.json
    wb = get_wb()
    ws = wb["Herramientas"]
    hid = next_id(ws)
    append_row(ws, SHEET_HEADERS["Herramientas"], {
        "ID": hid,
        "Herramienta": (data.get("herramienta") or "").strip(),
        "Prestada A": (data.get("prestada_a") or "").strip(),
        "Entregada Por": (data.get("entregada_por") or "").strip(),
        "Fecha Préstamo": data.get("fecha_prestamo", datetime.now().strftime("%Y-%m-%d")),
        "Fecha Devolución": "",
        "Estado": "Prestada",
        "Observaciones": data.get("observaciones", ""),
    }, hid)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "id": hid})


@app.route('/api/herramienta/<int:hid>', methods=['PUT'])
def update_herramienta(hid):
    data = request.json
    wb = get_wb()
    ws = wb["Herramientas"]
    row = find_row_by_id(ws, hid)
    if not row:
        return jsonify({"success": False, "error": "No encontrado"}), 404
    headers = SHEET_HEADERS["Herramientas"]

    def set_val(header, value):
        ws.cell(row=row[0].row, column=headers.index(header) + 1, value=value)

    if data.get("devolver"):
        set_val("Fecha Devolución", datetime.now().strftime("%Y-%m-%d"))
        set_val("Estado", "Devuelta")
    field_map = {"herramienta": "Herramienta", "prestada_a": "Prestada A",
                 "entregada_por": "Entregada Por", "observaciones": "Observaciones"}
    for key, header in field_map.items():
        if key in data:
            set_val(header, data[key])
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


@app.route('/api/herramienta/<int:hid>', methods=['DELETE'])
def delete_herramienta(hid):
    wb = get_wb()
    ws = wb["Herramientas"]
    row = find_row_by_id(ws, hid)
    if row:
        ws.delete_rows(row[0].row, 1)
    wb.save(EXCEL_FILE)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@app.route('/api/excel', methods=['GET'])
def download_excel():
    content = workbook_to_bytes(EXCEL_FILE)
    return send_file(io.BytesIO(content),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name='Control_Taller_VeneAutos.xlsx')


# Vercel carga este módulo desde el WSGI unificado de ../app.py.
