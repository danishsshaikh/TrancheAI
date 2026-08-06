from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Response

from app.ai.provider import FakeAIProvider
from app.ai.proposal_service import AIProposalService
from app.core.enums import Role, SanctionStatus, TrancheStatus
from app.exports.csv_export import project_master_csv, tranche_register_csv
from app.exports.rows import ProjectExportRecord, TrancheExportRecord
from app.exports.xlsx_export import project_master_xlsx, tranche_register_xlsx
from app.imports.csv_importer import template_csv
from app.services.audit import AuditRecorder
from app.services.domain import FundingSanction, Project, Tranche
from app.services.financials import calculate_project_financials
from app.services.permissions import Actor
from app.services.reconciliation import reconcile_project

router = APIRouter(prefix="/api/v1")


def _demo_records() -> tuple[list[Project], list[FundingSanction], list[Tranche]]:
    project = Project(id="p-001", project_code="TRAI-SYN-001", title="Low Cost Assistive Lab Prototype", school="Engineering", department="Mechanical Design")
    sanctions = [FundingSanction(project_id=project.id, sanction_reference="SYN-SAN-001", amount="500000", status=SanctionStatus.APPROVED)]
    tranches = [Tranche(project_id=project.id, sequence_number=1, requested_amount="250000", approved_amount="250000", disbursed_amount="250000", status=TrancheStatus.DISBURSED, payment_reference="UTR-SYN-001")]
    return [project], sanctions, tranches


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "trancheai-api"}


@router.get("/projects")
def list_projects() -> list[dict[str, object]]:
    projects, sanctions, tranches = _demo_records()
    return [_project_payload(project, sanctions, tranches) for project in projects]


@router.get("/projects/{project_id}/summary")
def project_summary(project_id: str) -> dict[str, str]:
    projects, sanctions, tranches = _demo_records()
    project = next(p for p in projects if p.id == project_id)
    summary = calculate_project_financials(sanctions, [], tranches)
    return {key: str(value) for key, value in asdict(summary).items()}


@router.get("/reports/project-master")
def project_master_report() -> list[dict[str, object]]:
    projects, sanctions, tranches = _demo_records()
    return [_project_payload(project, sanctions, tranches) for project in projects]


@router.get("/reports/tranche-register")
def tranche_register_report() -> list[dict[str, object]]:
    projects, sanctions, tranches = _demo_records()
    return [{"projectCode": projects[0].project_code, "projectTitle": projects[0].title, "tranche": asdict(tranche)} for tranche in tranches]


@router.get("/reports/reconciliation")
def reconciliation_report() -> list[dict[str, object]]:
    projects, sanctions, tranches = _demo_records()
    rows: list[dict[str, object]] = []
    for issue in reconcile_project(projects[0], sanctions, [], tranches):
        payload = asdict(issue)
        payload["projectCode"] = projects[0].project_code
        rows.append(payload)
    return rows


@router.get("/imports/templates/{import_type}.csv")
def import_template(import_type: str) -> Response:
    try:
        content = template_csv(import_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Import template not found.") from exc
    return Response(content, media_type="text/csv; charset=utf-8")


@router.get("/exports/project-master.csv")
def export_project_master_csv() -> Response:
    projects, sanctions, tranches = _demo_records()
    records = [ProjectExportRecord(projects[0], calculate_project_financials(sanctions, [], tranches))]
    return Response(project_master_csv(records), media_type="text/csv; charset=utf-8")


@router.get("/exports/tranche-register.csv")
def export_tranche_register_csv() -> Response:
    projects, sanctions, tranches = _demo_records()
    records = [TrancheExportRecord(projects[0], calculate_project_financials(sanctions, [], tranches), tranches)]
    return Response(tranche_register_csv(records), media_type="text/csv; charset=utf-8")


@router.get("/exports/project-master.xlsx")
def export_project_master_workbook() -> Response:
    projects, sanctions, tranches = _demo_records()
    records = [ProjectExportRecord(projects[0], calculate_project_financials(sanctions, [], tranches))]
    return Response(project_master_xlsx(records), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/exports/tranche-register.xlsx")
def export_tranche_register_workbook() -> Response:
    projects, sanctions, tranches = _demo_records()
    records = [TrancheExportRecord(projects[0], calculate_project_financials(sanctions, [], tranches), tranches)]
    return Response(tranche_register_xlsx(records), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/ai/preview")
def ai_preview() -> dict[str, object]:
    service = AIProposalService(FakeAIProvider(), AuditRecorder())
    preview = service.preview("Show active projects", Actor(id="dev-admin", roles={Role.ADMINISTRATOR}))
    return {"action": preview.proposal.action, "target": "projects", "allowed": preview.allowed, "errors": preview.errors, "warnings": preview.warnings, "proposedValues": preview.proposal.payload}


def _project_payload(project: Project, sanctions: list[FundingSanction], tranches: list[Tranche]) -> dict[str, object]:
    summary = calculate_project_financials(sanctions, [], tranches)
    return {
        "id": project.id,
        "projectCode": project.project_code,
        "title": project.title,
        "school": project.school,
        "department": project.department,
        "academicYear": project.academic_year,
        "status": project.project_status.value,
        "summary": {
            "initialSanctionedAmount": str(summary.initial_sanctioned_amount),
            "approvedFundingIncreases": str(summary.approved_funding_increases),
            "approvedFundingReductions": str(summary.approved_funding_reductions),
            "totalSanctionedAmount": str(summary.total_sanctioned_amount),
            "totalRequestedAmount": str(summary.total_requested_amount),
            "totalApprovedTrancheAmount": str(summary.total_approved_tranche_amount),
            "grossDisbursedAmount": str(summary.gross_disbursed_amount),
            "totalRefundedAmount": str(summary.total_refunded_amount),
            "netDisbursedAmount": str(summary.net_disbursed_amount),
            "totalUtilizedAmount": str(summary.total_utilized_amount),
            "availableSanctionedBalance": str(summary.available_sanctioned_balance),
            "unutilizedDisbursedBalance": str(summary.unutilized_disbursed_balance),
            "pendingApprovedAmount": str(summary.pending_approved_amount),
            "trancheCount": summary.tranche_count,
            "reconciliationStatus": summary.reconciliation_status,
        },
    }
