from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RevisionType, TrancheStatus
from app.core.money import ZERO, format_inr, money
from app.models.domain import AuditEventModel, FundingRevisionModel, FundingSanctionModel, ProjectModel, TrancheModel, UserModel
from app.services.financials import ProjectFinancialSummary, calculate_project_financials
from app.services.reconciliation import reconcile_project

SECRET_KEYS = {"password", "password_hash", "token", "token_hash", "api_key", "secret"}


class WorkflowError(ValueError):
    pass


def uuid() -> str:
    return str(uuid4())


def project_records(session: Session, project_id: str) -> tuple[ProjectModel, list[FundingSanctionModel], list[FundingRevisionModel], list[TrancheModel]]:
    project = session.get(ProjectModel, project_id)
    if project is None:
        raise WorkflowError("Project not found.")
    sanctions = list(session.scalars(select(FundingSanctionModel).where(FundingSanctionModel.project_id == project_id)))
    revisions = list(session.scalars(select(FundingRevisionModel).where(FundingRevisionModel.project_id == project_id)))
    tranches = list(session.scalars(select(TrancheModel).where(TrancheModel.project_id == project_id)))
    return project, sanctions, revisions, tranches


def project_summary(session: Session, project_id: str) -> ProjectFinancialSummary:
    _, sanctions, revisions, tranches = project_records(session, project_id)
    return calculate_project_financials(sanctions, revisions, tranches)


def audit(session: Session, *, actor: UserModel, entity_type: str, entity_id: str, action: str, previous: dict | None = None, new: dict | None = None, reason: str | None = None) -> None:
    session.add(
        AuditEventModel(
            id=uuid(),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor.id,
            previous_values=_safe(previous or {}),
            new_values=_safe(new or {}),
            reason=reason,
            source="api",
        )
    )


def approve_sanction(session: Session, sanction: FundingSanctionModel, actor: UserModel) -> FundingSanctionModel:
    if sanction.status not in {"draft", "submitted"}:
        raise WorkflowError("Only draft or submitted sanctions can be approved.")
    existing = session.scalar(
        select(FundingSanctionModel).where(
            FundingSanctionModel.project_id == sanction.project_id,
            FundingSanctionModel.status == "approved",
            FundingSanctionModel.id != sanction.id,
        )
    )
    if existing is not None:
        raise WorkflowError("This project already has an approved original sanction.")
    old = {"status": sanction.status}
    sanction.status = "approved"
    sanction.approved_by = actor.id
    sanction.approved_at = datetime.now(timezone.utc)
    sanction.version += 1
    audit(session, actor=actor, entity_type="funding_sanction", entity_id=sanction.id, action="approve", previous=old, new={"status": sanction.status})
    return sanction


def approve_revision(session: Session, revision: FundingRevisionModel, actor: UserModel) -> FundingRevisionModel:
    if revision.status not in {"draft", "submitted"}:
        raise WorkflowError("Only draft or submitted funding revisions can be approved.")
    if revision.revision_type not in {RevisionType.INCREASE.value, RevisionType.REDUCTION.value}:
        raise WorkflowError("Only increase and reduction revisions are supported in this workflow.")
    old = {"status": revision.status}
    revision.status = "approved"
    revision.approved_by = actor.id
    revision.approved_at = datetime.now(timezone.utc)
    revision.version += 1
    audit(session, actor=actor, entity_type="funding_revision", entity_id=revision.id, action="approve", previous=old, new={"status": revision.status})
    return revision


def submit_tranche(session: Session, tranche: TrancheModel, actor: UserModel) -> TrancheModel:
    if tranche.status != "draft":
        raise WorkflowError("Only draft tranches can be submitted.")
    old = {"status": tranche.status}
    tranche.status = "submitted"
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="submit", previous=old, new={"status": tranche.status})
    return tranche


def approve_tranche(session: Session, tranche: TrancheModel, actor: UserModel) -> TrancheModel:
    if tranche.status not in {"submitted", "under_review"}:
        raise WorkflowError("Only submitted tranches can be approved.")
    session.execute(select(ProjectModel).where(ProjectModel.id == tranche.project_id).with_for_update()).scalar_one()
    _, sanctions, revisions, tranches = project_records(session, tranche.project_id)
    other_tranches = [item for item in tranches if item.id != tranche.id]
    summary = calculate_project_financials(sanctions, revisions, other_tranches)
    available = summary.available_sanctioned_balance - summary.pending_approved_amount
    if tranche.approved_amount > available:
        raise WorkflowError(f"This tranche exceeds the project's available sanctioned balance by {format_inr(tranche.approved_amount - available)}.")
    _validate_amounts(tranche)
    old = {"status": tranche.status}
    tranche.status = "approved"
    tranche.approval_date = tranche.approval_date or date.today()
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="approve", previous=old, new={"status": tranche.status, "approved_amount": str(tranche.approved_amount)})
    return tranche


def reject_tranche(session: Session, tranche: TrancheModel, actor: UserModel, reason: str | None = None) -> TrancheModel:
    if tranche.status not in {"submitted", "under_review", "approved"}:
        raise WorkflowError("Only submitted, under-review or approved tranches can be rejected.")
    old = {"status": tranche.status}
    tranche.status = "rejected"
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="reject", previous=old, new={"status": tranche.status}, reason=reason)
    return tranche


def record_disbursement(session: Session, tranche: TrancheModel, actor: UserModel, amount: Decimal, payment_reference: str, payment_date: date, payment_mode: str | None = None) -> TrancheModel:
    if tranche.status not in {"approved", "scheduled", "partially_disbursed", "disbursed"}:
        raise WorkflowError("Only approved or scheduled tranches can be disbursed.")
    amount = money(amount)
    if amount > tranche.approved_amount:
        raise WorkflowError("Disbursed amount cannot exceed approved amount.")
    duplicate = session.scalar(select(TrancheModel).where(TrancheModel.payment_reference == payment_reference, TrancheModel.id != tranche.id))
    if duplicate is not None:
        raise WorkflowError(f"Payment reference {payment_reference} is already used.")
    old = {"status": tranche.status, "disbursed_amount": str(tranche.disbursed_amount), "payment_reference": tranche.payment_reference}
    tranche.disbursed_amount = amount
    tranche.payment_reference = payment_reference
    tranche.actual_disbursement_date = payment_date
    tranche.payment_mode = payment_mode or tranche.payment_mode
    tranche.status = "disbursed" if amount == tranche.approved_amount else "partially_disbursed"
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="record_disbursement", previous=old, new={"status": tranche.status, "disbursed_amount": str(amount), "payment_reference": payment_reference})
    return tranche


def record_refund(session: Session, tranche: TrancheModel, actor: UserModel, amount: Decimal) -> TrancheModel:
    amount = money(amount)
    if amount > tranche.disbursed_amount:
        raise WorkflowError("Refund amount cannot exceed this tranche's disbursed amount.")
    old = {"refund_amount": str(tranche.refund_amount)}
    tranche.refund_amount = amount
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="record_refund", previous=old, new={"refund_amount": str(amount)})
    return tranche


def record_utilization(session: Session, tranche: TrancheModel, actor: UserModel, amount: Decimal) -> TrancheModel:
    amount = money(amount)
    if amount > tranche.disbursed_amount - tranche.refund_amount:
        raise WorkflowError("Utilized amount cannot exceed this tranche's net disbursed amount.")
    old = {"utilized_amount": str(tranche.utilized_amount)}
    tranche.utilized_amount = amount
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="record_utilization", previous=old, new={"utilized_amount": str(amount)})
    return tranche


def cancel_tranche(session: Session, tranche: TrancheModel, actor: UserModel, reason: str | None = None) -> TrancheModel:
    if tranche.status in {TrancheStatus.CANCELLED.value, TrancheStatus.REJECTED.value}:
        raise WorkflowError("This tranche is already closed.")
    old = {"status": tranche.status}
    tranche.status = "cancelled"
    tranche.version += 1
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="cancel", previous=old, new={"status": tranche.status}, reason=reason)
    return tranche


def reconciliation_rows(session: Session) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    projects = list(session.scalars(select(ProjectModel).order_by(ProjectModel.project_code)))
    for project in projects:
        _, sanctions, revisions, tranches = project_records(session, project.id)
        for issue in reconcile_project(project, sanctions, revisions, tranches):
            rows.append({**issue.__dict__, "projectCode": project.project_code, "projectTitle": project.title})
    return rows


def _validate_amounts(tranche: TrancheModel) -> None:
    if min(tranche.requested_amount, tranche.approved_amount, tranche.disbursed_amount, tranche.refund_amount, tranche.utilized_amount) < ZERO:
        raise WorkflowError("Amount fields cannot be negative.")
    if tranche.approved_amount > tranche.requested_amount:
        raise WorkflowError("Approved amount cannot exceed requested amount.")
    if tranche.disbursed_amount > tranche.approved_amount:
        raise WorkflowError("Disbursed amount cannot exceed approved amount.")
    if tranche.refund_amount > tranche.disbursed_amount:
        raise WorkflowError("Refund amount cannot exceed this tranche's disbursed amount.")
    if tranche.utilized_amount > tranche.disbursed_amount - tranche.refund_amount:
        raise WorkflowError("Utilized amount cannot exceed this tranche's net disbursed amount.")


def _safe(values: dict) -> dict:
    return {key: value for key, value in values.items() if key.lower() not in SECRET_KEYS}
