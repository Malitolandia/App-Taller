from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from storage import export_workbook_bytes, import_full_workbook_stream, storage_status

ROOT = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"No se pudo cargar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


control = load_module("apptaller_control", ROOT / "ControlTaller" / "app.py")
neveras = load_module("apptaller_neveras", ROOT / "Neveras" / "servidor.py")
peritaje = load_module("apptaller_peritaje", ROOT / "Peritaje" / "app.py")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

@app.get("/")
def menu():
    return send_file(ROOT / "menu.html")

@app.get("/api/health")
def health():
    status = storage_status()
    # En Google Sheets, "ok" exige una lectura real de metadatos de la hoja.
    # Así no se confunde una variable presente con una conexión utilizable.
    ok = bool(status.get("remote_connected") and status.get("required_sheets_present", True))
    return jsonify({"ok": ok, **status}), (200 if ok else 503)

@app.errorhandler(Exception)
def root_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.exception("Error no controlado en la aplicación raíz")
    return jsonify({
        "success": False,
        "error": f"{type(error).__name__}: {error}",
    }), 500

# Estas variables solo conservan la firma histórica del adaptador; no son
# rutas de archivos ni se abren durante el despliegue remoto.
ALL_FILES = ()
SHEET_OWNERS = {}

@app.get("/api/db/export")
def export_database():
    content = export_workbook_bytes(ALL_FILES)
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="APPTALLER_respaldo.xlsx",
    )

@app.post("/api/db/import")
def import_database():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "Selecciona un archivo .xlsx"}), 400
    if not uploaded.filename.lower().endswith((".xlsx", ".xlsm")):
        return jsonify({"success": False, "error": "El respaldo debe estar en formato .xlsx o .xlsm"}), 400
    try:
        imported = import_full_workbook_stream(uploaded.stream, ALL_FILES, SHEET_OWNERS)
        return jsonify({"success": True, "imported_sheets": imported})
    except Exception as exc:
        app.logger.exception("Error al importar respaldo")
        return jsonify({"success": False, "error": str(exc)}), 400

app.wsgi_app = DispatcherMiddleware(
    app.wsgi_app,
    {
        "/control": control.app,
        "/neveras": neveras.app,
        "/peritaje": peritaje.app,
    },
)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
