from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import PurePath
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ProjectStatus, RevisionStatus, RevisionType, Role, SanctionStatus, TrancheStatus, TransactionType
from app.core.money import ZERO, money
from app.imports.csv_importer import TEMPLATES, ImportRowPreview, preview_csv
from app.imports.normalization import normalize_text
from app.models.domain import (
    FundingRevisionModel,
    FundingSanctionModel,
    ImportBatchModel,
    ImportRowModel,
    ProjectModel,
    ProjectParticipantModel,
    TrancheModel,
    UserModel,
)
from app.services.workflow import (
    WorkflowError,
    approve_revision,
    approve_sanction,
    approve_tranche,
    audit,
    cancel_tranche,
    record_disbursement,
    record_refund,
    record_utilization,
    reject_tranche,
    submit_revision,
    submit_sanction,
    submit_tranche,
    uuid,
)

MAX_IMPORT_BYTES = 2 * 1024 * 1024
IMPORT_EXTENSION = ".csv"

PROJECT_STATUSES = {status.value for status in ProjectStatus}
SANCTION_STATUSES = {SanctionStatus.DRAFT.value, SanctionStatus.SUBMITTED.value, SanctionStatus.APPROVED.value}
REVISION_STATUSES = {RevisionStatus.DRAFT.value, RevisionStatus.SUBMITTED.value, RevisionStatus.APPROVED.value}
REVISION_TYPES = {RevisionType.INCREASE.value, RevisionType.REDUCTION.value}
TRANCHE_STATUSES = {
    TrancheStatus.DRAFT.value,
    TrancheStatus.SUBMITTED.value,
    TrancheStatus.APPROVED.value,
    TrancheStatus.PARTIALLY_DISBURSED.value,
    TrancheStatus.DISBURSED.value,
    TrancheStatus.REJECTED.value,
    TrancheStatus.CANCELLED.value,
}
TRANSACTION_TYPES = {transaction_type.value for transaction_type in TransactionType}


def create_import_preview(
    session: Session,
    *,
    import_type: str,
    filename: str,
    content_type: str | None,
    content: bytes,
    actor: UserModel,
) -> ImportBatchModel:
    _validate_upload(import_type, filename, content)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise WorkflowError("Import file must be UTF-8 CSV.") from exc

    existing_fingerprints = set(session.scalars(select(ImportRowModel.row_fingerprint).where(ImportRowModel.status == "committed")))
    try:
        preview = preview_csv(import_type, text, existing_fingerprints)
    except ValueError as exc:
        raise WorkflowError(str(exc)) from exc

    batch = ImportBatchModel(
        id=uuid(),
        import_type=import_type,
        filename=PurePath(filename).name,
        content_type=content_type,
        file_fingerprint=preview.file_fingerprint,
        file_size_bytes=len(content),
        status="previewed",
        created_by=actor.id,
    )
    session.add(batch)

    seen_natural_keys: set[tuple[object, ...]] = set()
    for preview_row in preview.rows:
        reviewed = _review_row(session, import_type, preview_row, actor, seen_natural_keys)
        batch.rows.append(
            ImportRowModel(
                id=uuid(),
                batch_id=batch.id,
                row_number=preview_row.row_number,
                row_fingerprint=preview_row.row_fingerprint,
                raw_values=_jsonable(preview_row.raw_values),
                normalized_values=_jsonable(preview_row.normalized_values),
                status=reviewed["status"],
                proposed_action=reviewed["proposed_action"],
                duplicate=reviewed["duplicate"],
                entity_type=reviewed["entity_type"],
                existing_entity_id=reviewed["existing_entity_id"],
                errors=reviewed["errors"],
                warnings=reviewed["warnings"],
            )
        )
    _recount(batch)
    session.commit()
    return batch


def commit_import_batch(session: Session, batch_id: str, actor: UserModel) -> ImportBatchModel:
    batch = session.get(ImportBatchModel, batch_id)
    if batch is None:
        raise WorkflowError("Import batch not found.")
    if batch.status in {"committed", "partial_failed", "failed"}:
        return batch

    rows = sorted(batch.rows, key=lambda row: row.row_number)
    for row in rows:
        if row.status != "valid" or row.proposed_action != "create":
            row.status = "skipped"
            row.result = {"status": "skipped", "reason": "Row was not eligible for commit."}
            continue
        try:
            with session.begin_nested():
                entity_type, entity_id = _commit_row(session, batch.import_type, row, actor)
        except (IntegrityError, ValueError, WorkflowError) as exc:
            row.status = "failed"
            row.errors = [*row.errors, str(exc)]
            row.result = {"status": "failed", "error": str(exc)}
            continue
        row.status = "committed"
        row.entity_type = entity_type
        row.entity_id = entity_id
        row.result = {"status": "committed", "entity_type": entity_type, "entity_id": entity_id}

    batch.committed_by = actor.id
    batch.committed_at = datetime.now(timezone.utc)
    _recount(batch)
    if batch.failed_count:
        batch.status = "partial_failed" if batch.committed_count else "failed"
    else:
        batch.status = "committed"
    audit(
        session,
        actor=actor,
        entity_type="import_batch",
        entity_id=batch.id,
        action="commit_import",
        new={"import_type": batch.import_type, "committed_count": batch.committed_count, "failed_count": batch.failed_count},
    )
    session.commit()
    return batch


def import_batch_payload(batch: ImportBatchModel, *, include_rows: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": batch.id,
        "importType": batch.import_type,
        "filename": batch.filename,
        "contentType": batch.content_type,
        "fileFingerprint": batch.file_fingerprint,
        "fileSizeBytes": batch.file_size_bytes,
        "status": batch.status,
        "rowsDetected": batch.row_count,
        "validRows": batch.valid_count,
        "invalidRows": batch.invalid_count,
        "duplicateRows": batch.duplicate_count,
        "existingRecordsMatched": batch.existing_match_count,
        "proposedCreates": batch.create_count,
        "proposedUpdates": batch.update_count,
        "committedRows": batch.committed_count,
        "failedRows": batch.failed_count,
        "skippedRows": batch.skipped_count,
        "createdAt": batch.created_at,
        "committedAt": batch.committed_at,
    }
    if include_rows:
        payload["rows"] = [import_row_payload(row) for row in sorted(batch.rows, key=lambda item: item.row_number)]
    return payload


def import_row_payload(row: ImportRowModel) -> dict[str, object]:
    return {
        "id": row.id,
        "rowNumber": row.row_number,
        "rowFingerprint": row.row_fingerprint,
        "rawValues": row.raw_values,
        "normalizedValues": row.normalized_values,
        "status": row.status,
        "proposedAction": row.proposed_action,
        "duplicate": row.duplicate,
        "entityType": row.entity_type,
        "entityId": row.entity_id,
        "existingEntityId": row.existing_entity_id,
        "errors": row.errors,
        "warnings": row.warnings,
        "result": row.result,
    }


def _validate_upload(import_type: str, filename: str, content: bytes) -> None:
    if import_type not in TEMPLATES:
        raise WorkflowError(f"Unsupported import type: {import_type}")
    if not filename.lower().endswith(IMPORT_EXTENSION):
        raise WorkflowError("Only .csv import files are supported.")
    if len(content) > MAX_IMPORT_BYTES:
        raise WorkflowError(f"Import file exceeds the {MAX_IMPORT_BYTES} byte limit.")
    if not content.strip():
        raise WorkflowError("Import file is empty.")


def _review_row(
    session: Session,
    import_type: str,
    preview_row: ImportRowPreview,
    actor: UserModel,
    seen_natural_keys: set[tuple[object, ...]],
) -> dict[str, Any]:
    values = preview_row.normalized_values
    raw_values = preview_row.raw_values
    errors = list(preview_row.errors)
    warnings = list(preview_row.warnings)
    duplicate = preview_row.duplicate
    proposed_action = "create"
    entity_type = _entity_type(import_type)
    existing_entity_id: str | None = None

    key = _natural_key(import_type, values)
    if key is not None:
        if key in seen_natural_keys:
            duplicate = True
            warnings.append("A row with the same natural key appears earlier in this file.")
        seen_natural_keys.add(key)

    if import_type == "projects":
        existing_entity_id = _review_project(session, values, errors, warnings)
    elif import_type == "funding_sanctions":
        existing_entity_id = _review_sanction(session, values, raw_values, actor, errors, warnings)
    elif import_type == "funding_revisions":
        existing_entity_id = _review_revision(session, values, raw_values, actor, errors, warnings)
    elif import_type == "tranches":
        existing_entity_id = _review_tranche(session, values, raw_values, actor, errors, warnings)

    if existing_entity_id:
        duplicate = True
        proposed_action = "duplicate"
    status = "invalid" if errors else "duplicate" if duplicate else "valid"
    return {
        "status": status,
        "proposed_action": proposed_action,
        "duplicate": duplicate,
        "entity_type": entity_type,
        "existing_entity_id": existing_entity_id,
        "errors": errors,
        "warnings": warnings,
    }


def _review_project(session: Session, values: dict[str, Any], errors: list[str], warnings: list[str]) -> str | None:
    code = values.get("project_code")
    if not values.get("project_title"):
        errors.append("project_title is required.")
    status = values.get("project_status")
    if status and status not in PROJECT_STATUSES:
        errors.append(f"project_status must be one of: {', '.join(sorted(PROJECT_STATUSES))}.")
    if not code:
        return None
    existing = session.scalar(select(ProjectModel).where(ProjectModel.project_code == code))
    if existing is not None:
        warnings.append(f"Project code {code} already exists; commit will not create another project.")
        return existing.id
    return None


def _review_sanction(session: Session, values: dict[str, Any], raw_values: dict[str, Any], actor: UserModel, errors: list[str], warnings: list[str]) -> str | None:
    project = _project_for_import(session, values, errors)
    if not values.get("sanction_reference"):
        errors.append("sanction_reference is required.")
    _require_positive_money(raw_values, values, "sanction_amount", errors)
    status = values.get("status") or SanctionStatus.DRAFT.value
    if status not in SANCTION_STATUSES:
        errors.append("status must be draft, submitted or approved.")
    if status == SanctionStatus.APPROVED.value and not _can_approve(actor):
        errors.append("Importing approved sanctions requires administrator or fund reviewer permission.")
    if project is None or not values.get("sanction_reference"):
        return None
    existing = session.scalar(
        select(FundingSanctionModel).where(
            FundingSanctionModel.project_id == project.id,
            FundingSanctionModel.sanction_reference == values["sanction_reference"],
        )
    )
    if existing is not None:
        warnings.append("A sanction with this project and reference already exists.")
        return existing.id
    return None


def _review_revision(session: Session, values: dict[str, Any], raw_values: dict[str, Any], actor: UserModel, errors: list[str], warnings: list[str]) -> str | None:
    project = _project_for_import(session, values, errors)
    if values.get("revision_number") is None:
        errors.append("revision_number is required.")
    revision_type = values.get("revision_type")
    if revision_type not in REVISION_TYPES:
        errors.append("revision_type must be increase or reduction.")
    _require_positive_money(raw_values, values, "amount", errors)
    status = values.get("status") or SanctionStatus.DRAFT.value
    if status not in REVISION_STATUSES:
        errors.append("status must be draft, submitted or approved.")
    if status == SanctionStatus.APPROVED.value and not _can_approve(actor):
        errors.append("Importing approved funding revisions requires administrator or fund reviewer permission.")
    if project is None or values.get("revision_number") is None:
        return None
    existing = session.scalar(
        select(FundingRevisionModel).where(
            FundingRevisionModel.project_id == project.id,
            FundingRevisionModel.revision_number == values["revision_number"],
        )
    )
    if existing is not None:
        warnings.append("A funding revision with this project and revision number already exists.")
        return existing.id
    return None


def _review_tranche(session: Session, values: dict[str, Any], raw_values: dict[str, Any], actor: UserModel, errors: list[str], warnings: list[str]) -> str | None:
    project = _project_for_import(session, values, errors)
    if values.get("tranche_sequence") is None:
        errors.append("tranche_sequence is required.")
    transaction_type = values.get("transaction_type") or TransactionType.ADVANCE.value
    if transaction_type not in TRANSACTION_TYPES:
        errors.append(f"transaction_type must be one of: {', '.join(sorted(TRANSACTION_TYPES))}.")
    _require_money(raw_values, "requested_amount", errors)
    _require_money(raw_values, "approved_amount", errors)
    requested = money(values.get("requested_amount", ZERO))
    approved = money(values.get("approved_amount", ZERO))
    disbursed = money(values.get("disbursed_amount", ZERO))
    refunded = money(values.get("refund_amount", ZERO))
    utilized = money(values.get("utilized_amount", ZERO))
    if approved > requested:
        errors.append("approved_amount cannot exceed requested_amount.")
    if disbursed > approved:
        errors.append("disbursed_amount cannot exceed approved_amount.")
    if refunded > disbursed:
        errors.append("refund_amount cannot exceed disbursed_amount.")
    if utilized > disbursed - refunded:
        errors.append("utilized_amount cannot exceed net disbursed amount.")
    target_status = values.get("tranche_status") or TrancheStatus.DRAFT.value
    if target_status not in TRANCHE_STATUSES:
        errors.append("tranche_status must be draft, submitted, approved, partially_disbursed, disbursed, rejected or cancelled.")
    if target_status in {TrancheStatus.APPROVED.value, TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value, TrancheStatus.REJECTED.value} and not _can_approve(actor):
        errors.append("Importing approved, disbursed or rejected tranches requires administrator or fund reviewer permission.")
    if target_status in {TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value}:
        if disbursed <= ZERO:
            errors.append("disbursed tranches require disbursed_amount.")
        if not values.get("disbursement_date"):
            errors.append("disbursed tranches require disbursement_date.")
        if not values.get("payment_reference"):
            errors.append("disbursed tranches require payment_reference.")
    if target_status in {TrancheStatus.DRAFT.value, TrancheStatus.SUBMITTED.value, TrancheStatus.APPROVED.value} and any(amount > ZERO for amount in [disbursed, refunded, utilized]):
        errors.append("disbursed, refund and utilized amounts require a disbursed tranche status.")
    existing_id = None
    if project is not None and values.get("tranche_sequence") is not None:
        existing = session.scalar(select(TrancheModel).where(TrancheModel.project_id == project.id, TrancheModel.sequence_number == values["tranche_sequence"]))
        if existing is not None:
            warnings.append("A tranche with this project and sequence already exists.")
            existing_id = existing.id
    if values.get("payment_reference"):
        duplicate_payment = session.scalar(select(TrancheModel).where(TrancheModel.payment_reference == values["payment_reference"]))
        if duplicate_payment is not None:
            errors.append(f"payment_reference {values['payment_reference']} is already used.")
    return existing_id


def _commit_row(session: Session, import_type: str, row: ImportRowModel, actor: UserModel) -> tuple[str, str]:
    values = row.normalized_values
    if import_type == "projects":
        return _commit_project(session, values, actor)
    if import_type == "funding_sanctions":
        return _commit_sanction(session, values, actor)
    if import_type == "funding_revisions":
        return _commit_revision(session, values, actor)
    if import_type == "tranches":
        return _commit_tranche(session, values, actor)
    raise WorkflowError(f"Unsupported import type: {import_type}")


def _commit_project(session: Session, values: dict[str, Any], actor: UserModel) -> tuple[str, str]:
    if session.scalar(select(ProjectModel).where(ProjectModel.project_code == values["project_code"])) is not None:
        raise WorkflowError(f"Project code {values['project_code']} already exists.")
    project = ProjectModel(
        id=uuid(),
        project_code=values["project_code"],
        title=values["project_title"],
        institution=values.get("institution"),
        school=values.get("school"),
        department=values.get("department"),
        academic_year=values.get("academic_year"),
        cohort=values.get("cohort"),
        domain=values.get("domain"),
        technology_readiness_level=values.get("trl"),
        prototype_status=values.get("prototype_status"),
        project_status=values.get("project_status") or ProjectStatus.DRAFT.value,
        start_date=_date(values.get("start_date")),
        expected_completion_date=_date(values.get("expected_completion_date")),
        remarks=values.get("remarks"),
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(project)
    audit(session, actor=actor, entity_type="project", entity_id=project.id, action="create", new={"project_code": project.project_code, "source": "import"})
    _add_project_participants(session, project, values)
    return "project", project.id


def _commit_sanction(session: Session, values: dict[str, Any], actor: UserModel) -> tuple[str, str]:
    project = _project_by_code_or_error(session, values)
    if session.scalar(select(FundingSanctionModel).where(FundingSanctionModel.project_id == project.id, FundingSanctionModel.sanction_reference == values["sanction_reference"])) is not None:
        raise WorkflowError("A sanction with this project and reference already exists.")
    sanction = FundingSanctionModel(
        id=uuid(),
        project_id=project.id,
        sanction_reference=values["sanction_reference"],
        sanction_date=_date(values.get("sanction_date")),
        amount=money(values["sanction_amount"]),
        funding_source=values.get("funding_source"),
        financial_year=values.get("financial_year"),
        status=SanctionStatus.DRAFT.value,
        remarks=values.get("remarks"),
    )
    session.add(sanction)
    audit(session, actor=actor, entity_type="funding_sanction", entity_id=sanction.id, action="create", new={"amount": str(sanction.amount), "source": "import"})
    target = values.get("status") or SanctionStatus.DRAFT.value
    if target in {SanctionStatus.SUBMITTED.value, SanctionStatus.APPROVED.value}:
        submit_sanction(session, sanction, actor)
    if target == SanctionStatus.APPROVED.value:
        _ensure_can_approve(actor, "approved sanctions")
        approve_sanction(session, sanction, actor)
    return "funding_sanction", sanction.id


def _commit_revision(session: Session, values: dict[str, Any], actor: UserModel) -> tuple[str, str]:
    project = _project_by_code_or_error(session, values)
    if session.scalar(select(FundingRevisionModel).where(FundingRevisionModel.project_id == project.id, FundingRevisionModel.revision_number == values["revision_number"])) is not None:
        raise WorkflowError("A funding revision with this project and revision number already exists.")
    revision = FundingRevisionModel(
        id=uuid(),
        project_id=project.id,
        revision_number=int(values["revision_number"]),
        revision_type=values["revision_type"],
        revision_date=_date(values.get("revision_date")),
        amount=money(values["amount"]),
        approval_reference=values.get("approval_reference"),
        reason=values.get("reason"),
        status=SanctionStatus.DRAFT.value,
        remarks=values.get("remarks"),
    )
    session.add(revision)
    audit(session, actor=actor, entity_type="funding_revision", entity_id=revision.id, action="create", new={"amount": str(revision.amount), "revision_type": revision.revision_type, "source": "import"})
    target = values.get("status") or SanctionStatus.DRAFT.value
    if target in {SanctionStatus.SUBMITTED.value, SanctionStatus.APPROVED.value}:
        submit_revision(session, revision, actor)
    if target == SanctionStatus.APPROVED.value:
        _ensure_can_approve(actor, "approved funding revisions")
        approve_revision(session, revision, actor)
    return "funding_revision", revision.id


def _commit_tranche(session: Session, values: dict[str, Any], actor: UserModel) -> tuple[str, str]:
    project = _project_by_code_or_error(session, values)
    if session.scalar(select(TrancheModel).where(TrancheModel.project_id == project.id, TrancheModel.sequence_number == values["tranche_sequence"])) is not None:
        raise WorkflowError("A tranche with this project and sequence already exists.")
    tranche = TrancheModel(
        id=uuid(),
        project_id=project.id,
        sequence_number=int(values["tranche_sequence"]),
        transaction_type=values.get("transaction_type") or TransactionType.ADVANCE.value,
        purchase_order_number=values.get("purchase_order_number"),
        purchase_order_received_date=_date(values.get("purchase_order_received_date")),
        request_date=_date(values.get("request_date")),
        requested_amount=money(values["requested_amount"]),
        approved_amount=money(values["approved_amount"]),
        approval_date=_date(values.get("approval_date")),
        payment_mode=values.get("payment_mode"),
        payment_reference=values.get("payment_reference"),
        bill_status=values.get("bill_status"),
        utilization_certificate_status=values.get("utilization_certificate_status"),
        status=TrancheStatus.DRAFT.value,
        remarks=values.get("remarks"),
    )
    session.add(tranche)
    audit(session, actor=actor, entity_type="tranche", entity_id=tranche.id, action="create", new={"sequence_number": tranche.sequence_number, "source": "import"})
    target = values.get("tranche_status") or TrancheStatus.DRAFT.value
    if target in {TrancheStatus.SUBMITTED.value, TrancheStatus.APPROVED.value, TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value, TrancheStatus.REJECTED.value}:
        submit_tranche(session, tranche, actor)
    if target in {TrancheStatus.APPROVED.value, TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value}:
        _ensure_can_approve(actor, "approved or disbursed tranches")
        approve_tranche(session, tranche, actor)
    if target in {TrancheStatus.PARTIALLY_DISBURSED.value, TrancheStatus.DISBURSED.value}:
        record_disbursement(
            session,
            tranche,
            actor,
            money(values["disbursed_amount"]),
            str(values["payment_reference"]),
            _date(values.get("disbursement_date")) or date.today(),
            values.get("payment_mode"),
        )
    if money(values.get("refund_amount", ZERO)) > ZERO:
        record_refund(session, tranche, actor, money(values["refund_amount"]))
    if money(values.get("utilized_amount", ZERO)) > ZERO:
        record_utilization(session, tranche, actor, money(values["utilized_amount"]))
    if target == TrancheStatus.REJECTED.value:
        _ensure_can_approve(actor, "rejected tranches")
        reject_tranche(session, tranche, actor, "Imported as rejected.")
    if target == TrancheStatus.CANCELLED.value:
        cancel_tranche(session, tranche, actor, "Imported as cancelled.")
    return "tranche", tranche.id


def _add_project_participants(session: Session, project: ProjectModel, values: dict[str, Any]) -> None:
    names: list[tuple[str, str, bool]] = []
    principal = values.get("principal_investigator")
    if principal:
        names.append(("principal_investigator", str(principal), True))
    raw_participants = values.get("participant_names")
    if raw_participants:
        for item in str(raw_participants).split(";"):
            name = normalize_text(item)
            if name and name != principal:
                names.append(("participant", name, False))
    seen: set[str] = set()
    for role, name, primary in names:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        session.add(ProjectParticipantModel(id=uuid(), project_id=project.id, role=role, full_name=name, is_primary=primary))


def _project_for_import(session: Session, values: dict[str, Any], errors: list[str]) -> ProjectModel | None:
    code = values.get("project_code")
    if not code:
        return None
    project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == code))
    if project is None:
        errors.append(f"Unknown project_code {code}.")
    return project


def _project_by_code_or_error(session: Session, values: dict[str, Any]) -> ProjectModel:
    project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == values.get("project_code")))
    if project is None:
        raise WorkflowError(f"Unknown project_code {values.get('project_code')}.")
    return project


def _require_positive_money(raw_values: dict[str, Any], values: dict[str, Any], field: str, errors: list[str]) -> None:
    _require_money(raw_values, field, errors)
    if money(values.get(field, ZERO)) <= ZERO:
        errors.append(f"{field} must be greater than zero.")


def _require_money(raw_values: dict[str, Any], field: str, errors: list[str]) -> None:
    if normalize_text(raw_values.get(field)) is None:
        errors.append(f"{field} is required.")


def _natural_key(import_type: str, values: dict[str, Any]) -> tuple[object, ...] | None:
    if import_type == "projects" and values.get("project_code"):
        return ("project", values["project_code"])
    if import_type == "funding_sanctions" and values.get("project_code") and values.get("sanction_reference"):
        return ("sanction", values["project_code"], values["sanction_reference"])
    if import_type == "funding_revisions" and values.get("project_code") and values.get("revision_number") is not None:
        return ("revision", values["project_code"], values["revision_number"])
    if import_type == "tranches" and values.get("project_code") and values.get("tranche_sequence") is not None:
        return ("tranche", values["project_code"], values["tranche_sequence"])
    return None


def _entity_type(import_type: str) -> str:
    return {
        "projects": "project",
        "funding_sanctions": "funding_sanction",
        "funding_revisions": "funding_revision",
        "tranches": "tranche",
    }[import_type]


def _can_approve(actor: UserModel) -> bool:
    return Role(actor.role) in {Role.ADMINISTRATOR, Role.FUND_REVIEWER}


def _ensure_can_approve(actor: UserModel, target: str) -> None:
    if not _can_approve(actor):
        raise WorkflowError(f"Importing {target} requires administrator or fund reviewer permission.")


def _date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _recount(batch: ImportBatchModel) -> None:
    rows = list(batch.rows)
    batch.row_count = len(rows)
    batch.valid_count = len([row for row in rows if row.status == "valid"])
    batch.invalid_count = len([row for row in rows if row.status == "invalid"])
    batch.duplicate_count = len([row for row in rows if row.duplicate or row.status == "duplicate"])
    batch.existing_match_count = len([row for row in rows if row.existing_entity_id])
    batch.create_count = len([row for row in rows if row.proposed_action == "create" and row.status == "valid"])
    batch.update_count = len([row for row in rows if row.proposed_action == "update"])
    batch.committed_count = len([row for row in rows if row.status == "committed"])
    batch.failed_count = len([row for row in rows if row.status == "failed"])
    batch.skipped_count = len([row for row in rows if row.status == "skipped"])
