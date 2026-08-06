from __future__ import annotations

import csv
from io import StringIO

from app.exports.rows import PROJECT_MASTER_HEADERS, TRANCHE_REGISTER_HEADERS, ProjectExportRecord, TrancheExportRecord, project_master_row, serialize_csv_value


def project_master_csv(records: list[ProjectExportRecord]) -> str:
    return _write_csv(PROJECT_MASTER_HEADERS, [project_master_row(record) for record in records])


def tranche_register_csv(records: list[TrancheExportRecord]) -> str:
    rows: list[list[object]] = []
    serial = 1
    for record in records:
        for index, tranche in enumerate(sorted(record.tranches, key=lambda t: (t.sequence_number, t.request_date or t.actual_disbursement_date or ""))):
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
    return _write_csv(TRANCHE_REGISTER_HEADERS, rows)


def _write_csv(headers: list[str], rows: list[list[object]]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([serialize_csv_value(value) for value in row])
    return output.getvalue()

