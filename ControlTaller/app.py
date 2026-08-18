from flask import Flask, render_template, request, jsonify, send_file
import os
import io
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from storage import load_workbook_for_app, workbook_to_bytes, sheets_enabled

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'),
            static_url_path='/static')

EXCEL_FILE = os.path.join(os.path.dirname(__file__), 'data', 'taller_control.xlsx')

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
              "Total Mano de Obra", "Total Comisión"],
    "Herramientas": ["ID", "Herramienta", "Prestada A", "Entregada Por", "Fecha Préstamo",
                      "Fecha Devolución", "Estado", "Observaciones"],
}

# ---------------------------------------------------------------------------
# Excel helpers
# ---------------------------------------------------------------------------

def style_header_row(ws, headers):
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="C0392B")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'),
                              top=Side(style='thin'), bottom=Side(style='thin'))
    ws.row_dimensions[1].height = 32
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    ws.column_dimensions['A'].width = 8


def init_excel():
    if sheets_enabled() or os.path.exists(EXCEL_FILE):
        return
    wb = Workbook()
    first = True
    for sheet_name, headers in SHEET_HEADERS.items():
        ws = wb.active if first else wb.create_sheet(sheet_name)
        ws.title = sheet_name
        style_header_row(ws, headers)
        first = False
    wb.save(EXCEL_FILE)


def migrate_sheet(wb, sheet_name, target_headers):
    """Reconstruye una hoja si sus encabezados no coinciden con los actuales,
    preservando todos los datos existentes (columnas nuevas quedan vacías)."""
    if sheet_name not in wb.sheetnames:
        return False
    ws = wb[sheet_name]
    current_headers = [c.value for c in ws[1] if c.value is not None]
    if current_headers == target_headers:
        return False
    print(f"\n[DEBUG] Migrando hoja '{sheet_name}':")
    print(f"[DEBUG]   headers actuales: {current_headers}")
    print(f"[DEBUG]   headers nuevos:   {target_headers}\n")

    old_data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row and row[0] is not None:
            old_data.append(dict(zip(current_headers, row)))

    idx = wb.sheetnames.index(sheet_name)
    del wb[sheet_name]
    new_ws = wb.create_sheet(sheet_name, idx)
    style_header_row(new_ws, target_headers)
    for d in old_data:
        row_values = {h: d.get(h, "") for h in target_headers}
        if sheet_name == "Trabajos" and not row_values.get("Factura Cancelada"):
            # Trabajos registrados antes de este cambio: se asumen con factura ya cancelada
            # (de lo contrario, todo el historial existente desaparecería del resumen de nómina).
            row_values["Factura Cancelada"] = "Sí"
        append_row(new_ws, target_headers, row_values, d.get("ID"))
    return True


def ensure_sheets(wb):
    changed = False
    for name, headers in SHEET_HEADERS.items():
        if name not in wb.sheetnames:
            ws = wb.create_sheet(name)
            style_header_row(ws, headers)
            changed = True
        elif migrate_sheet(wb, name, headers):
            changed = True
    return changed


def get_wb():
    init_excel()
    wb = load_workbook_for_app(EXCEL_FILE)
    if ensure_sheets(wb):
        wb.save(EXCEL_FILE)
    return wb


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
    ws = wb["Trabajos"]
    data = sheet_to_dicts(ws, SHEET_HEADERS["Trabajos"])
    if semana:
        data = [d for d in data if d.get("Semana") == semana]

    resumen = {}
    for d in data:
        if d.get("Factura Cancelada") != "Sí":
            print(f"[DEBUG] nomina_resumen: excluyendo trabajo ID={d.get('ID')} Placa={d.get('Placa')} (Factura Cancelada={d.get('Factura Cancelada')!r})")
            continue  # la factura del cliente aún no está cancelada: no se suma a lo que se le debe al mecánico
        mec = d.get("Mecánico", "Sin asignar")
        if mec not in resumen:
            resumen[mec] = {"mecanico": mec, "n_trabajos": 0, "total_mo": 0,
                             "total_comision": 0, "pendiente": 0, "pagado": 0}
        r = resumen[mec]
        r["n_trabajos"] += 1
        r["total_mo"] += float(d.get("Monto Mano de Obra") or 0)
        monto_mec = float(d.get("Monto Mecánico") or 0)
        r["total_comision"] += monto_mec
        if d.get("Estado") == "Pagado":
            r["pagado"] += monto_mec
        else:
            r["pendiente"] += monto_mec

    semanas = sorted({d.get("Semana") for d in sheet_to_dicts(ws, SHEET_HEADERS["Trabajos"]) if d.get("Semana")}, reverse=True)
    return jsonify({"resumen": list(resumen.values()), "semanas_disponibles": semanas})


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

    if n_trabajos > 0:
        ws_pagos = wb["Pagos"]
        pid = next_id(ws_pagos)
        append_row(ws_pagos, SHEET_HEADERS["Pagos"], {
            "ID": pid, "Fecha Pago": fecha_pago, "Mecánico": mecanico,
            "Semana": semana, "N° Trabajos": n_trabajos,
            "Total Mano de Obra": round(total_mo, 2), "Total Comisión": round(total_comision, 2),
        }, pid)

    wb.save(EXCEL_FILE)
    return jsonify({"success": True, "n_trabajos": n_trabajos, "total_comision": round(total_comision, 2)})


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


if __name__ == '__main__':
    get_wb()
    print("\n" + "=" * 55)
    print("  VENE AUTOS - Control de Nómina y Gastos")
    print("  Servidor corriendo en: http://localhost:5002")
    print("=" * 55 + "\n")
    app.run(debug=True, port=5002)
