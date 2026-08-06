from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.db.session import get_session
from app.exports.csv_export import project_master_csv, tranche_register_csv
from app.exports.rows import ProjectExportRecord, TrancheExportRecord
from app.exports.xlsx_export import project_master_xlsx, tranche_register_xlsx
from app.imports.csv_importer import template_csv
from app.models.domain import (
    AuditEventModel,
    AuthSessionModel,
    FundingRevisionModel,
    FundingSanctionModel,
    ProjectModel,
    TrancheModel,
    UserModel,
)
from app.schemas.domain import (
    AmountAction,
    DisbursementCreate,
    LoginRequest,
    LoginResponse,
    ProjectCreate,
    ProjectUpdate,
    RevisionCreate,
    SanctionCreate,
    StatusAction,
    TrancheCreate,
)
from app.services.financials import calculate_project_financials
from app.services.security import hash_token, new_token, verify_password
from app.services.workflow import (
    WorkflowError,
    approve_revision,
    approve_sanction,
    approve_tranche,
    audit,
    cancel_tranche,
    project_records,
    reconciliation_rows,
    record_disbursement,
    record_refund,
    record_utilization,
    reject_tranche,
    submit_tranche,
    uuid,
)

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)


def _current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> UserModel:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    token_hash = hash_token(credentials.credentials)
    auth_session = session.scalar(
        select(AuthSessionModel).where(
            AuthSessionModel.token_hash == token_hash,
            AuthSessionModel.revoked_at.is_(None),
            AuthSessionModel.expires_at > datetime.now(timezone.utc),
        )
    )
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    user = session.get(UserModel, auth_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")
    return user


@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(select(1)).scalar_one()
    return {"status": "ok", "service": "trancheai-api"}


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = session.scalar(select(UserModel).where(UserModel.email == payload.email.lower(), UserModel.is_active.is_(True)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token, token_hash, expires_at = new_token()
    session.add(AuthSessionModel(id=uuid(), user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    session.commit()
    return LoginResponse(access_token=token, user=_user_payload(user))


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if credentials:
        auth_session = session.scalar(select(AuthSessionModel).where(AuthSessionModel.token_hash == hash_token(credentials.credentials)))
        if auth_session is not None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            session.commit()
    return {"status": "ok"}


@router.get("/auth/me")
def me(user: UserModel = Depends(_current_user)) -> dict[str, str]:
    return _user_payload(user)


@router.get("/projects")
def list_projects(
    q: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    school: str | None = None,
    department: str | None = None,
    academic_year: str | None = None,
    cohort: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    user: UserModel = Depends(_current_user),
) -> list[dict[str, object]]:
    _require(user, "read")
    statement = select(ProjectModel).order_by(ProjectModel.project_code).offset(offset).limit(limit)
    if q:
        needle = f"%{q}%"
        statement = statement.where(or_(ProjectModel.project_code.ilike(needle), ProjectModel.title.ilike(needle)))
    if status_filter:
        statement = statement.where(ProjectModel.project_status == status_filter)
    if school:
        statement = statement.where(ProjectModel.school == school)
    if department:
        statement = statement.where(ProjectModel.department == department)
    if academic_year:
        statement = statement.where(ProjectModel.academic_year == academic_year)
    if cohort:
        statement = statement.where(ProjectModel.cohort == cohort)
    projects = list(session.scalars(statement))
    return [_project_payload(session, project) for project in projects]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    project = ProjectModel(id=uuid(), project_code=payload.project_code.strip(), title=payload.title, institution=payload.institution, school=payload.school, department=payload.department, academic_year=payload.academic_year, cohort=payload.cohort, project_status=payload.project_status, funding_status=payload.funding_status, start_date=payload.start_date, expected_completion_date=payload.expected_completion_date, remarks=payload.remarks, created_by=user.id, updated_by=user.id)
    session.add(project)
    audit(session, actor=user, entity_type="project", entity_id=project.id, action="create", new={"project_code": project.project_code, "title": project.title})
    return _commit_payload(session, lambda: _project_payload(session, project))


@router.get("/projects/{project_id}")
def get_project(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "read")
    project = _project_or_404(session, project_id)
    payload = _project_payload(session, project)
    payload["sanctions"] = [_sanction_payload(item) for item in project_records(session, project_id)[1]]
    payload["fundingRevisions"] = [_revision_payload(item) for item in project_records(session, project_id)[2]]
    payload["tranches"] = [_tranche_payload(item) for item in project_records(session, project_id)[3]]
    return payload


@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    project = _project_or_404(session, project_id)
    if project.version != payload.version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project was updated by another user. Refresh and try again.")
    previous = {"title": project.title, "project_status": project.project_status, "version": project.version}
    for field, value in payload.model_dump(exclude_unset=True, exclude={"version"}).items():
        setattr(project, field, value)
    project.updated_by = user.id
    project.version += 1
    audit(session, actor=user, entity_type="project", entity_id=project.id, action="update", previous=previous, new={"version": project.version})
    return _commit_payload(session, lambda: _project_payload(session, project))


@router.get("/projects/{project_id}/summary")
def get_project_summary(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "read")
    _project_or_404(session, project_id)
    return _summary_payload(calculate_project_financials(*project_records(session, project_id)[1:]))


@router.get("/projects/{project_id}/audit")
def get_project_audit(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "audit_read")
    _project_or_404(session, project_id)
    entity_ids = [project_id]
    _, sanctions, revisions, tranches = project_records(session, project_id)
    entity_ids.extend(item.id for item in sanctions + revisions + tranches)
    events = session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id.in_(entity_ids)).order_by(AuditEventModel.timestamp.desc()))
    return [_audit_payload(event) for event in events]


@router.get("/projects/{project_id}/timeline")
def get_project_timeline(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    return get_project_audit(project_id, session, user)


@router.get("/projects/{project_id}/sanctions")
def list_sanctions(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    _project_or_404(session, project_id)
    return [_sanction_payload(item) for item in session.scalars(select(FundingSanctionModel).where(FundingSanctionModel.project_id == project_id).order_by(FundingSanctionModel.created_at))]


@router.post("/projects/{project_id}/sanctions", status_code=status.HTTP_201_CREATED)
def create_sanction(project_id: str, payload: SanctionCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    _project_or_404(session, project_id)
    sanction = FundingSanctionModel(id=uuid(), project_id=project_id, sanction_reference=payload.sanction_reference, sanction_date=payload.sanction_date, amount=payload.amount, funding_source=payload.funding_source, financial_year=payload.financial_year, status="draft", remarks=payload.remarks)
    session.add(sanction)
    audit(session, actor=user, entity_type="funding_sanction", entity_id=sanction.id, action="create", new={"amount": str(sanction.amount)})
    return _commit_payload(session, lambda: _sanction_payload(sanction), status.HTTP_400_BAD_REQUEST)


@router.post("/sanctions/{sanction_id}/submit")
def submit_sanction(sanction_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    sanction = _sanction_or_404(session, sanction_id)
    if sanction.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft sanctions can be submitted.")
    previous = {"status": sanction.status}
    sanction.status = "submitted"
    sanction.version += 1
    audit(session, actor=user, entity_type="funding_sanction", entity_id=sanction.id, action="submit", previous=previous, new={"status": sanction.status})
    return _commit_payload(session, lambda: _sanction_payload(sanction))


@router.post("/sanctions/{sanction_id}/approve")
def approve_sanction_route(sanction_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "approve")
    try:
        return _commit_payload(session, lambda: _sanction_payload(approve_sanction(session, _sanction_or_404(session, sanction_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/funding-revisions")
def list_revisions(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    _project_or_404(session, project_id)
    return [_revision_payload(item) for item in session.scalars(select(FundingRevisionModel).where(FundingRevisionModel.project_id == project_id).order_by(FundingRevisionModel.revision_number))]


@router.post("/projects/{project_id}/funding-revisions", status_code=status.HTTP_201_CREATED)
def create_revision(project_id: str, payload: RevisionCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    _project_or_404(session, project_id)
    revision = FundingRevisionModel(id=uuid(), project_id=project_id, revision_number=payload.revision_number, revision_type=payload.revision_type, revision_date=payload.revision_date, amount=payload.amount, status="draft", reason=payload.reason)
    session.add(revision)
    audit(session, actor=user, entity_type="funding_revision", entity_id=revision.id, action="create", new={"amount": str(revision.amount), "revision_type": revision.revision_type})
    return _commit_payload(session, lambda: _revision_payload(revision), status.HTTP_400_BAD_REQUEST)


@router.post("/funding-revisions/{revision_id}/submit")
def submit_revision(revision_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    revision = _revision_or_404(session, revision_id)
    if revision.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft funding revisions can be submitted.")
    previous = {"status": revision.status}
    revision.status = "submitted"
    revision.version += 1
    audit(session, actor=user, entity_type="funding_revision", entity_id=revision.id, action="submit", previous=previous, new={"status": revision.status})
    return _commit_payload(session, lambda: _revision_payload(revision))


@router.post("/funding-revisions/{revision_id}/approve")
def approve_revision_route(revision_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "approve")
    try:
        return _commit_payload(session, lambda: _revision_payload(approve_revision(session, _revision_or_404(session, revision_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/tranches")
def list_project_tranches(project_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    _project_or_404(session, project_id)
    return [_tranche_payload(item) for item in session.scalars(select(TrancheModel).where(TrancheModel.project_id == project_id).order_by(TrancheModel.sequence_number))]


@router.post("/projects/{project_id}/tranches", status_code=status.HTTP_201_CREATED)
def create_tranche(project_id: str, payload: TrancheCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    _project_or_404(session, project_id)
    tranche = TrancheModel(id=uuid(), project_id=project_id, sequence_number=payload.sequence_number, transaction_type=payload.transaction_type, requested_amount=payload.requested_amount, approved_amount=payload.approved_amount, request_date=payload.request_date, payment_reference=payload.payment_reference, remarks=payload.remarks)
    if tranche.approved_amount > tranche.requested_amount:
        raise HTTPException(status_code=400, detail="Approved amount cannot exceed requested amount.")
    session.add(tranche)
    audit(session, actor=user, entity_type="tranche", entity_id=tranche.id, action="create", new={"sequence_number": tranche.sequence_number, "requested_amount": str(tranche.requested_amount)})
    return _commit_payload(session, lambda: _tranche_payload(tranche), status.HTTP_400_BAD_REQUEST)


@router.get("/tranches")
def list_tranches(status_filter: str | None = Query(default=None, alias="status"), session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    statement = select(TrancheModel).order_by(TrancheModel.created_at.desc())
    if status_filter:
        statement = statement.where(TrancheModel.status == status_filter)
    return [_tranche_payload(item) for item in session.scalars(statement)]


@router.get("/tranches/{tranche_id}")
def read_tranche(tranche_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "read")
    return _tranche_payload(_tranche_or_404(session, tranche_id))


@router.post("/tranches/{tranche_id}/submit")
def submit_tranche_route(tranche_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _tranche_payload(submit_tranche(session, _tranche_or_404(session, tranche_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/approve")
def approve_tranche_route(tranche_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "approve")
    try:
        return _commit_payload(session, lambda: _tranche_payload(approve_tranche(session, _tranche_or_404(session, tranche_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/reject")
def reject_tranche_route(tranche_id: str, payload: StatusAction, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "approve")
    try:
        return _commit_payload(session, lambda: _tranche_payload(reject_tranche(session, _tranche_or_404(session, tranche_id), user, payload.reason)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/disburse")
def disburse_tranche_route(tranche_id: str, payload: DisbursementCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _tranche_payload(record_disbursement(session, _tranche_or_404(session, tranche_id), user, payload.amount, payload.payment_reference, payload.payment_date, payload.payment_mode)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/record-refund")
def refund_tranche_route(tranche_id: str, payload: AmountAction, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _tranche_payload(record_refund(session, _tranche_or_404(session, tranche_id), user, payload.amount)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/record-utilization")
def utilize_tranche_route(tranche_id: str, payload: AmountAction, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _tranche_payload(record_utilization(session, _tranche_or_404(session, tranche_id), user, payload.amount)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tranches/{tranche_id}/cancel")
def cancel_tranche_route(tranche_id: str, payload: StatusAction, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _tranche_payload(cancel_tranche(session, _tranche_or_404(session, tranche_id), user, payload.reason)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports/project-master")
def project_master_report(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    return [_project_payload(session, project) for project in session.scalars(select(ProjectModel).order_by(ProjectModel.project_code))]


@router.get("/reports/tranche-register")
def tranche_register_report(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    rows: list[dict[str, object]] = []
    for tranche in session.scalars(select(TrancheModel).order_by(TrancheModel.project_id, TrancheModel.sequence_number)):
        project = session.get(ProjectModel, tranche.project_id)
        if project is None:
            continue
        rows.append({"project": _project_payload(session, project), "tranche": _tranche_payload(tranche)})
    return rows


@router.get("/reports/reconciliation")
def reconciliation_report(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    return reconciliation_rows(session)


@router.get("/imports/templates/{import_type}.csv")
def import_template(import_type: str, user: UserModel = Depends(_current_user)) -> Response:
    _require(user, "read")
    try:
        content = template_csv(import_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Import template not found.") from exc
    return Response(content, media_type="text/csv; charset=utf-8")


@router.get("/exports/project-master.csv")
def export_project_master_csv(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> Response:
    _require(user, "export")
    records = _project_export_records(session)
    return Response(project_master_csv(records), media_type="text/csv; charset=utf-8")


@router.get("/exports/tranche-register.csv")
def export_tranche_register_csv(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> Response:
    _require(user, "export")
    return Response(tranche_register_csv(_tranche_export_records(session)), media_type="text/csv; charset=utf-8")


@router.get("/exports/project-master.xlsx")
def export_project_master_workbook(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> Response:
    _require(user, "export")
    return Response(project_master_xlsx(_project_export_records(session)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/exports/tranche-register.xlsx")
def export_tranche_register_workbook(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> Response:
    _require(user, "export")
    return Response(tranche_register_xlsx(_tranche_export_records(session)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _require(user: UserModel, action: str) -> None:
    role = Role(user.role)
    allowed = {
        "read": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER},
        "write": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR},
        "approve": {Role.ADMINISTRATOR, Role.FUND_REVIEWER},
        "audit_read": {Role.ADMINISTRATOR, Role.AUDITOR},
        "export": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER},
    }
    if role not in allowed[action]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {user.role} cannot {action}.")


def _commit_payload(session: Session, payload_factory, integrity_status: int = status.HTTP_409_CONFLICT):
    try:
        session.flush()
        payload = payload_factory()
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=integrity_status, detail="Database constraint rejected this operation.") from exc
    return payload


def _project_or_404(session: Session, project_id: str) -> ProjectModel:
    project = session.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _sanction_or_404(session: Session, sanction_id: str) -> FundingSanctionModel:
    sanction = session.get(FundingSanctionModel, sanction_id)
    if sanction is None:
        raise HTTPException(status_code=404, detail="Funding sanction not found.")
    return sanction


def _revision_or_404(session: Session, revision_id: str) -> FundingRevisionModel:
    revision = session.get(FundingRevisionModel, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Funding revision not found.")
    return revision


def _tranche_or_404(session: Session, tranche_id: str) -> TrancheModel:
    tranche = session.get(TrancheModel, tranche_id)
    if tranche is None:
        raise HTTPException(status_code=404, detail="Tranche not found.")
    return tranche


def _project_payload(session: Session, project: ProjectModel) -> dict[str, object]:
    _, sanctions, revisions, tranches = project_records(session, project.id)
    summary = calculate_project_financials(sanctions, revisions, tranches)
    return {
        "id": project.id,
        "projectCode": project.project_code,
        "project_code": project.project_code,
        "title": project.title,
        "institution": project.institution,
        "school": project.school,
        "department": project.department,
        "academicYear": project.academic_year,
        "academic_year": project.academic_year,
        "cohort": project.cohort,
        "status": project.project_status,
        "fundingStatus": project.funding_status,
        "version": project.version,
        "summary": _summary_payload(summary),
    }


def _summary_payload(summary) -> dict[str, object]:
    payload = asdict(summary)
    return {**{key: str(value) if isinstance(value, Decimal) else value for key, value in payload.items()}, **_camel_summary(payload)}


def _camel_summary(payload: dict[str, object]) -> dict[str, object]:
    return {
        "initialSanctionedAmount": str(payload["initial_sanctioned_amount"]),
        "approvedFundingIncreases": str(payload["approved_funding_increases"]),
        "approvedFundingReductions": str(payload["approved_funding_reductions"]),
        "totalSanctionedAmount": str(payload["total_sanctioned_amount"]),
        "totalRequestedAmount": str(payload["total_requested_amount"]),
        "totalApprovedTrancheAmount": str(payload["total_approved_tranche_amount"]),
        "grossDisbursedAmount": str(payload["gross_disbursed_amount"]),
        "totalRefundedAmount": str(payload["total_refunded_amount"]),
        "netDisbursedAmount": str(payload["net_disbursed_amount"]),
        "totalUtilizedAmount": str(payload["total_utilized_amount"]),
        "availableSanctionedBalance": str(payload["available_sanctioned_balance"]),
        "unutilizedDisbursedBalance": str(payload["unutilized_disbursed_balance"]),
        "pendingApprovedAmount": str(payload["pending_approved_amount"]),
        "trancheCount": payload["tranche_count"],
        "latestDisbursementDate": str(payload["latest_disbursement_date"]) if payload["latest_disbursement_date"] else None,
        "reconciliationStatus": payload["reconciliation_status"],
    }


def _sanction_payload(item: FundingSanctionModel) -> dict[str, object]:
    return {"id": item.id, "projectId": item.project_id, "sanctionReference": item.sanction_reference, "sanctionDate": item.sanction_date, "amount": str(item.amount), "status": item.status, "approvedBy": item.approved_by, "approvedAt": item.approved_at, "version": item.version}


def _revision_payload(item: FundingRevisionModel) -> dict[str, object]:
    return {"id": item.id, "projectId": item.project_id, "revisionNumber": item.revision_number, "revisionType": item.revision_type, "revisionDate": item.revision_date, "amount": str(item.amount), "status": item.status, "version": item.version}


def _tranche_payload(item: TrancheModel) -> dict[str, object]:
    return {"id": item.id, "projectId": item.project_id, "sequenceNumber": item.sequence_number, "transactionType": item.transaction_type, "requestedAmount": str(item.requested_amount), "approvedAmount": str(item.approved_amount), "disbursedAmount": str(item.disbursed_amount), "refundAmount": str(item.refund_amount), "utilizedAmount": str(item.utilized_amount), "paymentReference": item.payment_reference, "actualDisbursementDate": item.actual_disbursement_date, "status": item.status, "remarks": item.remarks, "version": item.version}


def _audit_payload(item: AuditEventModel) -> dict[str, object]:
    return {"id": item.id, "entityType": item.entity_type, "entityId": item.entity_id, "action": item.action, "actorId": item.actor_id, "timestamp": item.timestamp, "previousValues": item.previous_values, "newValues": item.new_values, "reason": item.reason}


def _user_payload(user: UserModel) -> dict[str, str]:
    return {"id": user.id, "email": user.email, "fullName": user.full_name, "role": user.role}


def _project_export_records(session: Session) -> list[ProjectExportRecord]:
    records = []
    for project in session.scalars(select(ProjectModel).order_by(ProjectModel.project_code)):
        _, sanctions, revisions, tranches = project_records(session, project.id)
        records.append(ProjectExportRecord(project, calculate_project_financials(sanctions, revisions, tranches)))
    return records


def _tranche_export_records(session: Session) -> list[TrancheExportRecord]:
    records = []
    for project in session.scalars(select(ProjectModel).order_by(ProjectModel.project_code)):
        _, sanctions, revisions, tranches = project_records(session, project.id)
        records.append(TrancheExportRecord(project, calculate_project_financials(sanctions, revisions, tranches), tranches))
    return records
