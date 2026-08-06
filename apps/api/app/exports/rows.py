from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.services.financials import ProjectFinancialSummary

PROJECT_MASTER_HEADERS = [
    "Project Code",
    "Project Title",
    "Institution",
    "School",
    "Department",
    "Academic Year",
    "Cohort",
    "Project Status",
    "Start Date",
    "Completion Date",
    "Principal Investigator",
    "Initial Sanction",
    "Funding Increases",
    "Funding Reductions",
    "Total Sanctioned",
    "Total Requested",
    "Total Approved",
    "Gross Disbursed",
    "Refund",
    "Net Disbursed",
    "Utilized",
    "Available Balance",
    "Unutilized Disbursed Balance",
    "Tranche Count",
    "Latest Disbursement Date",
    "Reconciliation Status",
    "TRL",
    "Prototype Status",
    "Publication Status",
    "Patent Status",
    "Startup Status",
]

TRANCHE_REGISTER_HEADERS = [
    "Serial Number",
    "Project Code",
    "Project Title",
    "School",
    "Department",
    "Academic Year",
    "Cohort",
    "Principal Investigator",
    "Total Sanctioned",
    "Tranche Sequence",
    "Transaction Type",
    "Purchase-Order Number",
    "PO Received Date",
    "Requested Amount",
    "Approved Amount",
    "Disbursed Amount",
    "Refund",
    "Utilized Amount",
    "Payment Reference",
    "Status",
    "Remarks",
]


@dataclass(frozen=True)
class ProjectExportRecord:
    project: Any
    summary: ProjectFinancialSummary
    principal_investigator: str = ""


@dataclass(frozen=True)
class TrancheExportRecord:
    project: Any
    summary: ProjectFinancialSummary
    tranches: list[Any]
    principal_investigator: str = ""


def project_master_row(record: ProjectExportRecord) -> list[object]:
    p, s = record.project, record.summary
    return [
        getattr(p, "project_code", getattr(p, "projectCode", "")),
        p.title,
        p.institution,
        p.school,
        p.department,
        p.academic_year,
        p.cohort,
        _label(p.project_status),
        p.start_date,
        p.actual_completion_date or p.expected_completion_date,
        record.principal_investigator,
        s.initial_sanctioned_amount,
        s.approved_funding_increases,
        s.approved_funding_reductions,
        s.total_sanctioned_amount,
        s.total_requested_amount,
        s.total_approved_tranche_amount,
        s.gross_disbursed_amount,
        s.total_refunded_amount,
        s.net_disbursed_amount,
        s.total_utilized_amount,
        s.available_sanctioned_balance,
        s.unutilized_disbursed_balance,
        s.tranche_count,
        s.latest_disbursement_date,
        s.reconciliation_status,
        p.technology_readiness_level,
        p.prototype_status,
        p.publication_status,
        p.patent_status,
        p.startup_status,
    ]


def is_money_column(header: str) -> bool:
    return any(word in header.lower() for word in ["amount", "sanction", "disbursed", "refund", "utilized", "balance", "approved", "requested"])


def serialize_csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def _label(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw).replace("_", " ").title()
