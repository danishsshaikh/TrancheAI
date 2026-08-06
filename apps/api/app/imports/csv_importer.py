from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

from app.imports.normalization import fingerprint, normalize_code, normalize_date, normalize_enum, normalize_money, normalize_text

PROJECT_HEADERS = [
    "project_code",
    "project_title",
    "institution",
    "school",
    "department",
    "academic_year",
    "cohort",
    "project_status",
    "start_date",
    "expected_completion_date",
    "principal_investigator",
    "participant_names",
    "domain",
    "trl",
    "prototype_status",
    "remarks",
]
SANCTION_HEADERS = ["project_code", "sanction_reference", "sanction_date", "sanction_amount", "funding_source", "financial_year", "status", "remarks"]
REVISION_HEADERS = ["project_code", "revision_number", "revision_type", "revision_date", "amount", "approval_reference", "reason", "status", "remarks"]
TRANCHE_HEADERS = [
    "project_code",
    "tranche_sequence",
    "transaction_type",
    "purchase_order_number",
    "purchase_order_received_date",
    "requested_amount",
    "approved_amount",
    "disbursed_amount",
    "refund_amount",
    "utilized_amount",
    "request_date",
    "approval_date",
    "disbursement_date",
    "payment_mode",
    "payment_reference",
    "tranche_status",
    "bill_status",
    "utilization_certificate_status",
    "remarks",
]
TEMPLATES = {
    "projects": PROJECT_HEADERS,
    "funding_sanctions": SANCTION_HEADERS,
    "funding_revisions": REVISION_HEADERS,
    "tranches": TRANCHE_HEADERS,
}


@dataclass(frozen=True)
class ImportRowPreview:
    row_number: int
    raw_values: dict[str, Any]
    normalized_values: dict[str, Any]
    row_fingerprint: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate: bool = False


@dataclass(frozen=True)
class ImportPreview:
    import_type: str
    headers: list[str]
    rows: list[ImportRowPreview]
    file_fingerprint: str

    @property
    def valid(self) -> bool:
        return all(not row.errors for row in self.rows)


def template_csv(import_type: str) -> str:
    output = StringIO()
    csv.writer(output).writerow(TEMPLATES[import_type])
    return output.getvalue()


def preview_csv(import_type: str, content: str, existing_row_fingerprints: set[str] | None = None) -> ImportPreview:
    if import_type not in TEMPLATES:
        raise ValueError(f"Unsupported import type: {import_type}")
    existing = existing_row_fingerprints or set()
    reader = csv.DictReader(StringIO(content))
    actual_headers = reader.fieldnames or []
    expected = TEMPLATES[import_type]
    if actual_headers != expected:
        missing = [h for h in expected if h not in actual_headers]
        extra = [h for h in actual_headers if h not in expected]
        raise ValueError(f"Invalid headers. Missing: {missing}. Extra: {extra}.")
    seen: set[str] = set()
    rows: list[ImportRowPreview] = []
    for idx, raw in enumerate(reader, start=2):
        normalized, errors, warnings = _normalize_row(import_type, raw)
        row_fingerprint = fingerprint(raw)
        duplicate = row_fingerprint in seen or row_fingerprint in existing
        if duplicate:
            warnings.append("This row fingerprint was already imported or appears more than once in this file.")
        seen.add(row_fingerprint)
        rows.append(ImportRowPreview(idx, raw, normalized, row_fingerprint, errors, warnings, duplicate))
    return ImportPreview(import_type, actual_headers, rows, fingerprint({"content": content}))


def _normalize_row(import_type: str, raw: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, Any] = {}
    date_fields = {"start_date", "expected_completion_date", "sanction_date", "revision_date", "purchase_order_received_date", "request_date", "approval_date", "disbursement_date"}
    money_fields = {"sanction_amount", "amount", "requested_amount", "approved_amount", "disbursed_amount", "refund_amount", "utilized_amount"}
    enum_fields = {"project_status", "status", "revision_type", "transaction_type", "tranche_status", "bill_status", "utilization_certificate_status"}
    for key, value in raw.items():
        try:
            if key == "project_code":
                normalized[key] = normalize_code(value)
            elif key in date_fields:
                normalized[key] = normalize_date(value)
            elif key in money_fields:
                normalized[key] = normalize_money(value)
            elif key in enum_fields:
                normalized[key] = normalize_enum(value)
            elif key in {"tranche_sequence", "revision_number"}:
                text = normalize_text(value)
                normalized[key] = int(text) if text else None
            else:
                normalized[key] = normalize_text(value)
        except ValueError as exc:
            errors.append(f"{key}: {exc}")
    if not normalized.get("project_code"):
        errors.append("project_code is required.")
    if import_type == "projects" and not normalized.get("project_title"):
        errors.append("project_title is required.")
    if import_type == "tranches" and normalized.get("tranche_sequence") is None:
        warnings.append("tranche_sequence is blank; the server can propose the next sequence during commit.")
    return normalized, errors, warnings

