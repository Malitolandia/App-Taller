"""Persistencia híbrida para APPTALLER.

En desarrollo local conserva el comportamiento original basado en XLSX. En
producción, cuando existen GOOGLE_SHEETS_ID y credenciales de cuenta de
servicio, cada libro se sincroniza con pestañas de un único Google Sheet.
"""
from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Iterable

from openpyxl import Workbook, load_workbook


SHEETS_ID_ENV = "GOOGLE_SHEETS_ID"
SERVICE_JSON_ENV = "GOOGLE_SERVICE_ACCOUNT_JSON"
SERVICE_FILE_ENV = "GOOGLE_SERVICE_ACCOUNT_FILE"


def sheets_enabled() -> bool:
    return bool(os.getenv(SHEETS_ID_ENV) and _credentials_info())


def _credentials_info() -> dict | None:
    raw = os.getenv(SERVICE_JSON_ENV)
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON no contiene JSON válido") from exc
    path = os.getenv(SERVICE_FILE_ENV)
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


@lru_cache(maxsize=1)
def _sheets_service():
    info = _credentials_info()
    if not info:
        raise RuntimeError(
            "Faltan credenciales de Google. Configura GOOGLE_SERVICE_ACCOUNT_JSON "
            "o GOOGLE_SERVICE_ACCOUNT_FILE."
        )
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Instala google-api-python-client y google-auth para usar Google Sheets"
        ) from exc
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _title_range(title: str) -> str:
    return "'" + title.replace("'", "''") + "'!A:ZZ"


def _sheet_properties() -> list[dict]:
    response = (
        _sheets_service()
        .spreadsheets()
        .get(spreadsheetId=os.environ[SHEETS_ID_ENV], includeGridData=False, fields="sheets.properties")
        .execute()
    )
    return [sheet["properties"] for sheet in response.get("sheets", [])]


def _remote_workbook() -> Workbook:
    service = _sheets_service()
    wb = Workbook()
    default = wb.active
    default.title = "APPTALLER"
    wb.remove(default)

    for props in _sheet_properties():
        title = props["title"]
        values = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=os.environ[SHEETS_ID_ENV],
                range=_title_range(title),
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
            .get("values", [])
        )
        ws = wb.create_sheet(title)
        for row_index, row_values in enumerate(values, start=1):
            for col_index, value in enumerate(row_values, start=1):
                ws.cell(row=row_index, column=col_index, value=value)
    if not wb.sheetnames:
        wb.create_sheet("APPTALLER")
    return wb


def _copy_local_sheet_values(source_ws, target_ws) -> None:
    for row in source_ws.iter_rows():
        for cell in row:
            target_ws.cell(row=cell.row, column=cell.column, value=cell.value)


def _is_blank_sheet(ws) -> bool:
    return ws.max_row == 1 and ws.max_column == 1 and ws.cell(1, 1).value in (None, "")


def _merge_local_seed(remote_wb: Workbook, local_path: str) -> bool:
    """Añade las pestañas locales que todavía no existen en la hoja remota."""
    path = Path(local_path)
    if not path.exists():
        return False
    try:
        local_wb = load_workbook(path, data_only=True)
    except Exception:
        return False
    changed = False
    try:
        for title in local_wb.sheetnames:
            source = local_wb[title]
            if title not in remote_wb.sheetnames:
                target = remote_wb.create_sheet(title)
                _copy_local_sheet_values(source, target)
                changed = True
            elif _is_blank_sheet(remote_wb[title]) and source.max_row >= 1:
                _copy_local_sheet_values(source, remote_wb[title])
                changed = True
    finally:
        local_wb.close()
    return changed


class RemoteWorkbook:
    """Proxy mínimo de openpyxl que sincroniza al ejecutarse ``save``."""

    def __init__(self, workbook: Workbook):
        self._workbook = workbook

    def __getitem__(self, key):
        return self._workbook[key]

    def __getattr__(self, name):
        return getattr(self._workbook, name)

    def save(self, _path: str | None = None) -> dict[str, dict[str, int]]:
        return save_workbook_to_sheets(self._workbook)

    def close(self) -> None:
        self._workbook.close()


def load_workbook_for_app(local_path: str, data_only: bool = False, read_only: bool = False):
    if not sheets_enabled():
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if not Path(local_path).exists():
            wb = Workbook()
            wb.save(local_path)
            wb.close()
        return load_workbook(local_path, data_only=data_only, read_only=read_only)

    wb = _remote_workbook()
    _merge_local_seed(wb, local_path)
    return RemoteWorkbook(wb)


def _trimmed_values(ws) -> list[list]:
    values = []
    for row in ws.iter_rows(values_only=True):
        row_values = list(row)
        while row_values and row_values[-1] in (None, ""):
            row_values.pop()
        if row_values:
            values.append(["" if value is None else value for value in row_values])
    return values


def _ensure_remote_sheet(title: str) -> None:
    if title in {p["title"] for p in _sheet_properties()}:
        return
    body = {"requests": [{"addSheet": {"properties": {"title": title}}}]}
    _sheets_service().spreadsheets().batchUpdate(
        spreadsheetId=os.environ[SHEETS_ID_ENV], body=body
    ).execute()


def save_workbook_to_sheets(wb: Workbook) -> dict[str, dict[str, int]]:
    """Sincroniza el libro completo y confirma que Google aceptó cada escritura.

    La API de Google responde con el número de filas y celdas actualizadas. Si
    una escritura no devuelve el mínimo esperado, se interrumpe la petición en
    vez de informar éxito sin que los datos hayan llegado a la hoja remota.
    """
    service = _sheets_service()
    spreadsheet_id = os.environ[SHEETS_ID_ENV]
    existing = {p["title"] for p in _sheet_properties()}
    results: dict[str, dict[str, int]] = {}
    for title in wb.sheetnames:
        if title not in existing:
            _ensure_remote_sheet(title)
            existing.add(title)
        range_name = _title_range(title)
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name, body={}
        ).execute()
        values = _trimmed_values(wb[title])
        if not values:
            results[title] = {"rows": 0, "cells": 0}
            continue
        expected_cells = sum(len(row) for row in values)
        response = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title.replace(chr(39), chr(39) + chr(39))}'!A1",
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
        updated_cells = int(response.get("updatedCells", 0))
        updated_rows = int(response.get("updatedRows", 0))
        if updated_cells < expected_cells or updated_rows < len(values):
            raise RuntimeError(
                f"Google Sheets no confirmó la escritura completa de la pestaña '{title}' "
                f"({updated_rows}/{len(values)} filas, {updated_cells}/{expected_cells} celdas)."
            )
        results[title] = {"rows": updated_rows, "cells": updated_cells}
    return results


def workbook_to_bytes(local_path: str) -> bytes:
    workbook = load_workbook_for_app(local_path)
    raw = workbook._workbook if isinstance(workbook, RemoteWorkbook) else workbook
    stream = io.BytesIO()
    raw.save(stream)
    if hasattr(workbook, "close"):
        workbook.close()
    return stream.getvalue()


def _replace_workbook_contents(target: Workbook, incoming: Workbook, allowed_sheets: Iterable[str] | None) -> None:
    allowed = set(allowed_sheets) if allowed_sheets else None
    incoming_names = [name for name in incoming.sheetnames if allowed is None or name in allowed]
    for title in incoming_names:
        if title in target.sheetnames:
            target.remove(target[title])
        target.create_sheet(title)
        _copy_local_sheet_values(incoming[title], target[title])
    if not target.sheetnames:
        target.create_sheet("APPTALLER")


def export_workbook_bytes(local_paths: Iterable[str]) -> bytes:
    paths = list(local_paths)
    if sheets_enabled():
        workbook = _remote_workbook()
        for path in paths:
            _merge_local_seed(workbook, path)
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)
        for path in paths:
            local_path = Path(path)
            if not local_path.exists():
                continue
            source = load_workbook(local_path, data_only=True)
            try:
                for title in source.sheetnames:
                    if title in workbook.sheetnames:
                        continue
                    target = workbook.create_sheet(title)
                    _copy_local_sheet_values(source[title], target)
            finally:
                source.close()
        if not workbook.sheetnames:
            workbook.create_sheet("APPTALLER")
    stream = io.BytesIO()
    workbook.save(stream)
    if hasattr(workbook, "close"):
        workbook.close()
    return stream.getvalue()


def import_full_workbook_stream(
    stream: BinaryIO,
    local_paths: Iterable[str],
    sheet_owners: dict[str, str],
) -> list[str]:
    incoming = load_workbook(io.BytesIO(stream.read()), data_only=True)
    try:
        if sheets_enabled():
            first_path = next(iter(local_paths), "")
            current = load_workbook_for_app(first_path)
            raw = current._workbook if isinstance(current, RemoteWorkbook) else current
            _replace_workbook_contents(raw, incoming, None)
            if isinstance(current, RemoteWorkbook):
                current.save(first_path)
            else:
                raw.save(first_path)
            return list(incoming.sheetnames)

        imported = []
        paths_by_owner: dict[str, list[str]] = {}
        for title, owner in sheet_owners.items():
            paths_by_owner.setdefault(owner, []).append(title)
        for owner, titles in paths_by_owner.items():
            current = load_workbook_for_app(owner)
            raw = current._workbook if isinstance(current, RemoteWorkbook) else current
            _replace_local_sheets(raw, incoming, titles)
            if isinstance(current, RemoteWorkbook):
                current.save(owner)
            else:
                Path(owner).parent.mkdir(parents=True, exist_ok=True)
                raw.save(owner)
            imported.extend(title for title in titles if title in incoming.sheetnames)
        return imported
    finally:
        incoming.close()


def _replace_local_sheets(target: Workbook, incoming: Workbook, titles: Iterable[str]) -> None:
    for title in titles:
        if title not in incoming.sheetnames:
            continue
        if title in target.sheetnames:
            target.remove(target[title])
        target.create_sheet(title)
        _copy_local_sheet_values(incoming[title], target[title])


def import_workbook_stream(stream: BinaryIO, local_path: str, allowed_sheets: Iterable[str] | None = None) -> list[str]:
    incoming = load_workbook(io.BytesIO(stream.read()), data_only=True)
    try:
        current = load_workbook_for_app(local_path)
        raw = current._workbook if isinstance(current, RemoteWorkbook) else current
        _replace_workbook_contents(raw, incoming, allowed_sheets)
        if isinstance(current, RemoteWorkbook):
            current.save(local_path)
        else:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            raw.save(local_path)
        return [name for name in incoming.sheetnames if not allowed_sheets or name in set(allowed_sheets)]
    finally:
        incoming.close()


def sync_seed_workbooks(local_paths: Iterable[str]) -> None:
    if not sheets_enabled():
        return
    workbook = _remote_workbook()
    changed = any(_merge_local_seed(workbook, path) for path in local_paths)
    if changed:
        save_workbook_to_sheets(workbook)


def storage_status() -> dict:
    """Devuelve el estado verificado sin exponer ninguna credencial."""
    spreadsheet_id = os.getenv(SHEETS_ID_ENV, "").strip()
    configured = bool(spreadsheet_id)
    try:
        enabled = sheets_enabled()
    except Exception as exc:
        return {
            "backend": "google_sheets",
            "spreadsheet_configured": configured,
            "remote_connected": False,
            "error": str(exc),
        }
    if not enabled:
        return {
            "backend": "excel_local",
            "spreadsheet_configured": configured,
            "remote_connected": False,
        }
    try:
        titles = [item["title"] for item in _sheet_properties()]
        return {
            "backend": "google_sheets",
            "spreadsheet_configured": True,
            "remote_connected": True,
            "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
            "sheet_titles": titles,
        }
    except Exception as exc:
        return {
            "backend": "google_sheets",
            "spreadsheet_configured": True,
            "remote_connected": False,
            "error": str(exc),
        }
