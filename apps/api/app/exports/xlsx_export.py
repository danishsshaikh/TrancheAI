from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from app.exports.rows import PROJECT_MASTER_HEADERS, TRANCHE_REGISTER_HEADERS, ProjectExportRecord, TrancheExportRecord, is_money_column, project_master_row


def project_master_xlsx(records: list[ProjectExportRecord]) -> bytes:
    rows = [["TrancheAI Project Master Register"], [f"Generated: {datetime.now(timezone.utc).isoformat()}"], [], PROJECT_MASTER_HEADERS]
    rows.extend(project_master_row(record) for record in records)
    return _minimal_xlsx("Project Master", rows, metadata={"Export Type": "project_master", "Record Count": str(len(records))}, freeze_pane="A5")


def tranche_register_xlsx(records: list[TrancheExportRecord]) -> bytes:
    rows: list[list[object]] = [["TrancheAI Tranche Register"], [f"Generated: {datetime.now(timezone.utc).isoformat()}"], [], TRANCHE_REGISTER_HEADERS]
    serial = 1
    for record in records:
        ordered = sorted(record.tranches, key=lambda t: (t.sequence_number, t.request_date or t.actual_disbursement_date or ""))
        if not ordered:
            rows.append([serial, record.project.project_code, record.project.title, record.project.school, record.project.department, record.project.academic_year, record.project.cohort, record.principal_investigator, record.summary.total_sanctioned_amount])
        for index, tranche in enumerate(ordered):
            first = index == 0
            rows.append(
                [
                    serial if first else "",
                    record.project.project_code if first else "",
                    record.project.title if first else "",
                    record.project.school if first else "",
                    record.project.department if first else "",
                    record.project.academic_year if first else "",
                    record.project.cohort if first else "",
                    record.principal_investigator if first else "",
                    record.summary.total_sanctioned_amount if first else "",
                    tranche.sequence_number,
                    tranche.transaction_type.label,
                    tranche.purchase_order_number,
                    tranche.purchase_order_received_date,
                    tranche.requested_amount,
                    tranche.approved_amount,
                    tranche.disbursed_amount,
                    tranche.refund_amount,
                    tranche.utilized_amount,
                    tranche.payment_reference,
                    tranche.status.label,
                    tranche.remarks,
                ]
            )
        serial += 1
    return _minimal_xlsx("Tranche Register", rows, metadata={"Export Type": "tranche_register", "Record Count": str(len(records))}, freeze_pane="A5")


def _minimal_xlsx(sheet_name: str, rows: list[list[object]], metadata: dict[str, str], freeze_pane: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types())
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows, freeze_pane))
        archive.writestr("xl/worksheets/sheet2.xml", _sheet_xml([["Key", "Value"], *metadata.items()], "A2"))
    return buffer.getvalue()


def _cell(value: object, row: int, col: int, header: str | None = None) -> str:
    ref = f"{_col(col)}{row}"
    style = ' s="1"' if row == 4 or row == 1 else ""
    if isinstance(value, Decimal):
        return f'<c r="{ref}" s="2"><v>{value}</v></c>'
    if isinstance(value, int) and not isinstance(value, bool):
        return f'<c r="{ref}"><v>{value}</v></c>'
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return f'<c r="{ref}" s="3"><v>{escape(value.isoformat())}</v></c>'
    text = "" if value is None else str(value)
    return f'<c r="{ref}" t="inlineStr"{style}><is><t>{escape(text)}</t></is></c>'


def _sheet_xml(rows: list[list[object]], freeze_pane: str) -> str:
    xml_rows = []
    for row_number, row in enumerate(rows, start=1):
        cells = "".join(_cell(value, row_number, col) for col, value in enumerate(row, start=1))
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')
    max_col = max((len(r) for r in rows), default=1)
    cols = "".join(f'<col min="{i}" max="{i}" width="{18 if i < 10 else 14}" customWidth="1"/>' for i in range(1, max_col + 1))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols}</cols>"
        f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="{freeze_pane}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f'<mergeCells count="1"><mergeCell ref="A1:{_col(max_col)}1"/></mergeCells>'
        '<sheetData>'
        + "".join(xml_rows)
        + "</sheetData>"
        f'<autoFilter ref="A4:{_col(max_col)}{len(rows)}"/>'
        '<pageSetup orientation="landscape"/>'
        "</worksheet>"
    )


def _col(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>"""


def _root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""


def _workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""


def _workbook_xml(sheet_name: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/><sheet name="Metadata" sheetId="2" r:id="rId2"/></sheets></workbook>"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="2"><numFmt numFmtId="164" formatCode="₹#,##0.00"/><numFmt numFmtId="165" formatCode="yyyy-mm-dd"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><sz val="11"/><name val="Aptos"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs></styleSheet>"""
