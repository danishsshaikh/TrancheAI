from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypeVar

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.assistant_service import AIAssistantError, AIAssistantService
from app.ai.provider import OpenAICompatibleProvider
from app.ai.schemas import AIRequestPayload
from app.core.config import settings
from app.core.enums import Role
from app.db.session import get_session
from app.exports.csv_export import project_master_csv, tranche_register_csv
from app.exports.rows import ProjectExportRecord, TrancheExportRecord
from app.exports.xlsx_export import project_master_xlsx, tranche_register_xlsx
from app.imports.csv_importer import template_csv
from app.imports.workflow import commit_import_batch, create_import_preview, import_batch_payload, import_row_payload
from app.models.domain import (
    AIConversationModel,
    AIMessageModel,
    AuditEventModel,
    AuthSessionModel,
    FundingRevisionModel,
    FundingSanctionModel,
    ImportBatchModel,
    ProjectModel,
    ProjectParticipantModel,
    TrancheModel,
    UserModel,
)
from app.schemas.domain import (
    AIConversationCreate,
    AIConversationMessageCreate,
    AIConversationUpdate,
    AmountAction,
    DisbursementCreate,
    LoginRequest,
    LoginResponse,
    ProjectCreate,
    ProjectParticipantInput,
    ProjectUpdate,
    RevisionCreate,
    SanctionCreate,
    StatusAction,
    TrancheCreate,
    UserCreate,
    UserUpdate,
)
from app.services.financials import ProjectFinancialSummary, calculate_project_financials
from app.services.security import hash_password, hash_token, new_token, verify_password
from app.services.workflow import (
    WorkflowError,
    approve_revision,
    approve_sanction,
    approve_tranche,
    audit,
    cancel_tranche,
    create_funding_revision_record,
    create_project_record,
    create_tranche_record,
    project_records,
    reconciliation_rows,
    record_disbursement,
    record_refund,
    record_utilization,
    reject_tranche,
    submit_tranche,
    update_project_fields,
    uuid,
)
from app.services.workflow import (
    submit_revision as workflow_submit_revision,
)
from app.services.workflow import (
    submit_sanction as workflow_submit_sanction,
)

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)
PayloadT = TypeVar("PayloadT")


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
def me(user: UserModel = Depends(_current_user)) -> dict[str, object]:
    return _user_payload(user)


@router.get("/settings")
def settings_payload(user: UserModel = Depends(_current_user)) -> dict[str, object]:
    return {
        "profile": _user_payload(user),
        "roles": [{"value": role.value, "label": _label(role.value)} for role in Role],
        "ai": {
            "enabled": settings.ai_enabled,
            "baseUrlConfigured": bool(settings.ai_base_url),
            "modelConfigured": bool(settings.ai_model),
            "model": settings.ai_model or None,
            "timeoutSeconds": settings.ai_timeout_seconds,
            "maxTokens": settings.ai_max_tokens,
            "temperature": settings.ai_temperature,
        },
        "application": {"name": settings.app_name, "version": "0.1.0", "license": "Apache-2.0"},
    }


@router.get("/users")
def list_users(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "user_admin")
    return [_user_payload(item) for item in session.scalars(select(UserModel).order_by(UserModel.email))]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user_route(payload: UserCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "user_admin")
    role = _role_or_400(payload.role)
    created = UserModel(id=uuid(), email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password), role=role.value)
    session.add(created)
    audit(session, actor=user, entity_type="user", entity_id=created.id, action="create_user", new={"email": created.email, "role": created.role})
    return _commit_payload(session, lambda: _user_payload(created))


@router.patch("/users/{user_id}")
def update_user_route(user_id: str, payload: UserUpdate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "user_admin")
    target = session.get(UserModel, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    previous = {"full_name": target.full_name, "role": target.role, "is_active": target.is_active}
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.role is not None:
        target.role = _role_or_400(payload.role).value
    if payload.is_active is not None:
        if target.id == user.id and payload.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
        target.is_active = payload.is_active
    target.version += 1
    audit(session, actor=user, entity_type="user", entity_id=target.id, action="update_user", previous=previous, new={"full_name": target.full_name, "role": target.role, "is_active": target.is_active})
    return _commit_payload(session, lambda: _user_payload(target))


@router.get("/search")
def global_search(q: str = Query(min_length=1), session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    needle = f"%{q.strip()}%"
    results: list[dict[str, object]] = []
    for project in session.scalars(select(ProjectModel).where(or_(ProjectModel.project_code.ilike(needle), ProjectModel.title.ilike(needle), ProjectModel.department.ilike(needle))).order_by(ProjectModel.project_code).limit(8)):
        results.append({"type": "project", "label": f"{project.project_code} · {project.title}", "description": project.department or project.school, "to": f"/projects/{project.id}", "projectId": project.id})
    tranches = session.scalars(select(TrancheModel).where(TrancheModel.payment_reference.ilike(needle)).order_by(TrancheModel.created_at.desc()).limit(8))
    for tranche in tranches:
        project_for_tranche = session.get(ProjectModel, tranche.project_id)
        if project_for_tranche is None:
            continue
        results.append({"type": "tranche", "label": f"{project_for_tranche.project_code} · Tranche {tranche.sequence_number}", "description": tranche.payment_reference, "to": f"/projects/{project_for_tranche.id}/tranches", "projectId": project_for_tranche.id, "trancheId": tranche.id})
    return results[:12]


@router.post("/ai/requests")
def create_ai_request(payload: AIRequestPayload, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    if not settings.ai_enabled:
        return _ai_disabled_response()
    return _ai_service(session).request(
        actor=user,
        text=payload.text,
        current_project_id=payload.current_project_id,
        current_project_code=payload.current_project_code,
        language=payload.language,
    )


@router.get("/ai/conversations")
def list_ai_conversations(session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    return [
        _conversation_payload(session, conversation, include_messages=False)
        for conversation in session.scalars(
            select(AIConversationModel)
            .where(AIConversationModel.user_id == user.id, AIConversationModel.archived.is_(False))
            .order_by(AIConversationModel.updated_at.desc())
        )
    ]


@router.post("/ai/conversations", status_code=status.HTTP_201_CREATED)
def create_ai_conversation(payload: AIConversationCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    project = _project_from_context(session, payload.project_id, payload.project_code)
    conversation = AIConversationModel(
        id=uuid(),
        user_id=user.id,
        title=payload.title,
        project_id=project.id if project else None,
        project_code=project.project_code if project else payload.project_code,
    )
    session.add(conversation)
    session.commit()
    return _conversation_payload(session, conversation)


@router.get("/ai/conversations/{conversation_id}")
def get_ai_conversation(conversation_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    return _conversation_payload(session, _conversation_or_404(session, conversation_id, user), include_messages=True)


@router.patch("/ai/conversations/{conversation_id}")
def update_ai_conversation(conversation_id: str, payload: AIConversationUpdate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    conversation = _conversation_or_404(session, conversation_id, user)
    if payload.title is not None:
        conversation.title = payload.title.strip()[:255] or conversation.title
    if payload.archived is not None:
        conversation.archived = payload.archived
    conversation.version += 1
    session.commit()
    return _conversation_payload(session, conversation, include_messages=True)


@router.post("/ai/conversations/{conversation_id}/messages")
def create_ai_conversation_message(conversation_id: str, payload: AIConversationMessageCreate, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    if not settings.ai_enabled:
        return _ai_disabled_response()
    conversation = _conversation_or_404(session, conversation_id, user)
    user_message = AIMessageModel(id=uuid(), conversation_id=conversation.id, role="user", content=payload.text)
    session.add(user_message)
    if not conversation.title:
        conversation.title = _conversation_title(payload.text)
    response = _ai_service(session).request(
        actor=user,
        text=payload.text,
        current_project_id=conversation.project_id,
        current_project_code=conversation.project_code,
        language=payload.language,
    )
    proposal = response.get("proposal")
    proposal_id = proposal.get("id") if isinstance(proposal, dict) else None
    assistant_message = AIMessageModel(
        id=uuid(),
        conversation_id=conversation.id,
        role="assistant",
        content=str(response["message"]),
        response_kind=str(response["kind"]),
        action=str(proposal.get("action")) if isinstance(proposal, dict) and proposal.get("action") else None,
        metadata_=response,
        proposal_id=str(proposal_id) if proposal_id else None,
    )
    session.add(assistant_message)
    conversation.version += 1
    session.commit()
    return {"conversation": _conversation_payload(session, conversation, include_messages=True), "response": response}


@router.get("/ai/proposals/{proposal_id}")
def get_ai_proposal(proposal_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    try:
        return _ai_service(session).get_proposal(proposal_id=proposal_id, actor=user)
    except AIAssistantError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/proposals/{proposal_id}/confirm")
def confirm_ai_proposal(proposal_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    try:
        return _ai_service(session).confirm(proposal_id=proposal_id, actor=user)
    except AIAssistantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/proposals/{proposal_id}/cancel")
def cancel_ai_proposal(proposal_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    try:
        return _ai_service(session).cancel(proposal_id=proposal_id, actor=user)
    except AIAssistantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    project = create_project_record(session, user, _project_create_values(payload))
    _sync_project_participants(session, project, payload.participants, user)
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
    try:
        values = payload.model_dump(exclude_unset=True, exclude={"version", "participants"})
        update_project_fields(session, project, user, values, payload.version)
        if payload.participants is not None:
            _sync_project_participants(session, project, payload.participants, user)
    except WorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
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
    try:
        return _commit_payload(session, lambda: _sanction_payload(workflow_submit_sanction(session, _sanction_or_404(session, sanction_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    project = _project_or_404(session, project_id)
    revision = create_funding_revision_record(session, project, user, {"revision_number": payload.revision_number, "revision_type": payload.revision_type, "revision_date": payload.revision_date, "amount": payload.amount, "approval_reference": payload.approval_reference, "reason": payload.reason, "remarks": payload.remarks})
    return _commit_payload(session, lambda: _revision_payload(revision), status.HTTP_400_BAD_REQUEST)


@router.post("/funding-revisions/{revision_id}/submit")
def submit_revision(revision_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        return _commit_payload(session, lambda: _revision_payload(workflow_submit_revision(session, _revision_or_404(session, revision_id), user)), status.HTTP_400_BAD_REQUEST)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    project = _project_or_404(session, project_id)
    try:
        tranche = create_tranche_record(session, project, user, {"sequence_number": payload.sequence_number, "transaction_type": payload.transaction_type, "purchase_order_number": payload.purchase_order_number, "purchase_order_received_date": payload.purchase_order_received_date, "request_date": payload.request_date, "requested_amount": payload.requested_amount, "approved_amount": payload.approved_amount, "approval_date": payload.approval_date, "expected_disbursement_date": payload.expected_disbursement_date, "actual_disbursement_date": payload.actual_disbursement_date, "payment_mode": payload.payment_mode, "payment_reference": payload.payment_reference, "bill_status": payload.bill_status, "utilization_certificate_status": payload.utilization_certificate_status, "remarks": payload.remarks})
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _commit_payload(session, lambda: _tranche_payload(tranche), status.HTTP_400_BAD_REQUEST)


@router.get("/tranches")
def list_tranches(status_filter: str | None = Query(default=None, alias="status"), session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    statement = select(TrancheModel).order_by(TrancheModel.created_at.desc())
    if status_filter:
        statement = statement.where(TrancheModel.status == status_filter)
    rows: list[dict[str, object]] = []
    for tranche in session.scalars(statement):
        rows.append(_tranche_payload(tranche, session.get(ProjectModel, tranche.project_id)))
    return rows


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


@router.post("/imports/preview")
def preview_import(
    import_type: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: UserModel = Depends(_current_user),
) -> dict[str, object]:
    _require(user, "write")
    try:
        batch = create_import_preview(
            session,
            import_type=import_type,
            filename=file.filename or "import.csv",
            content_type=file.content_type,
            content=file.file.read(),
            actor=user,
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return import_batch_payload(batch)


@router.get("/imports/{batch_id}")
def get_import_batch(batch_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "read")
    batch = _import_batch_or_404(session, batch_id)
    return import_batch_payload(batch)


@router.get("/imports/{batch_id}/rows")
def get_import_rows(batch_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> list[dict[str, object]]:
    _require(user, "read")
    batch = _import_batch_or_404(session, batch_id)
    return [import_row_payload(row) for row in sorted(batch.rows, key=lambda item: item.row_number)]


@router.post("/imports/{batch_id}/commit")
def commit_import(batch_id: str, session: Session = Depends(get_session), user: UserModel = Depends(_current_user)) -> dict[str, object]:
    _require(user, "write")
    try:
        batch = commit_import_batch(session, batch_id, user)
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return import_batch_payload(batch)


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


def _ai_service(session: Session) -> AIAssistantService:
    provider = OpenAICompatibleProvider(
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        timeout_seconds=settings.ai_timeout_seconds,
        max_tokens=settings.ai_max_tokens,
        temperature=settings.ai_temperature,
    )
    return AIAssistantService(
        session=session,
        provider=provider,
        ai_enabled=settings.ai_enabled,
        provider_base_url=settings.ai_base_url,
        provider_model=settings.ai_model,
    )


def _ai_disabled_response() -> dict[str, object]:
    return {"kind": "error", "message": "AI assistant is disabled. Set AI_ENABLED=true on the server to use it."}


def _conversation_or_404(session: Session, conversation_id: str, user: UserModel) -> AIConversationModel:
    conversation = session.get(AIConversationModel, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="AI conversation not found.")
    return conversation


def _conversation_payload(session: Session, conversation: AIConversationModel, *, include_messages: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": conversation.id,
        "title": conversation.title or "New conversation",
        "projectId": conversation.project_id,
        "projectCode": conversation.project_code,
        "archived": conversation.archived,
        "createdAt": conversation.created_at,
        "updatedAt": conversation.updated_at,
    }
    if include_messages:
        messages = session.scalars(select(AIMessageModel).where(AIMessageModel.conversation_id == conversation.id).order_by(AIMessageModel.created_at))
        payload["messages"] = [_message_payload(message) for message in messages]
    return payload


def _message_payload(message: AIMessageModel) -> dict[str, object]:
    return {
        "id": message.id,
        "conversationId": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "responseKind": message.response_kind,
        "action": message.action,
        "metadata": message.metadata_,
        "proposalId": message.proposal_id,
        "createdAt": message.created_at,
    }


def _project_from_context(session: Session, project_id: str | None, project_code: str | None) -> ProjectModel | None:
    if project_id:
        project = session.get(ProjectModel, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project context not found.")
        return project
    if project_code:
        project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == project_code.strip().upper()))
        if project is None:
            raise HTTPException(status_code=404, detail="Project context not found.")
        return project
    return None


def _conversation_title(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= 72:
        return collapsed or "New conversation"
    return f"{collapsed[:69]}..."


def _require(user: UserModel, action: str) -> None:
    role = Role(user.role)
    allowed = {
        "read": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER},
        "write": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR},
        "approve": {Role.ADMINISTRATOR, Role.FUND_REVIEWER},
        "audit_read": {Role.ADMINISTRATOR, Role.AUDITOR},
        "export": {Role.ADMINISTRATOR, Role.FUND_ADMINISTRATOR, Role.FUND_REVIEWER, Role.AUDITOR, Role.VIEWER},
        "user_admin": {Role.ADMINISTRATOR},
    }
    if role not in allowed[action]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role {user.role} cannot {action}.")


def _commit_payload(session: Session, payload_factory: Callable[[], PayloadT], integrity_status: int = status.HTTP_409_CONFLICT) -> PayloadT:
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


def _import_batch_or_404(session: Session, batch_id: str) -> ImportBatchModel:
    batch = session.get(ImportBatchModel, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return batch


def _role_or_400(value: str) -> Role:
    try:
        return Role(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid role.") from exc


def _project_create_values(payload: ProjectCreate) -> dict[str, object]:
    return payload.model_dump(exclude={"participants"}, exclude_none=True) | {"project_code": payload.project_code.strip().upper()}


def _sync_project_participants(session: Session, project: ProjectModel, participants: list[ProjectParticipantInput], actor: UserModel) -> None:
    existing = list(session.scalars(select(ProjectParticipantModel).where(ProjectParticipantModel.project_id == project.id)))
    previous = [_participant_payload(item) for item in existing]
    for item in existing:
        session.delete(item)
    for participant in participants:
        session.add(
            ProjectParticipantModel(
                id=uuid(),
                project_id=project.id,
                role=participant.role,
                full_name=participant.full_name,
                email=participant.email,
                phone=participant.phone,
                department=participant.department,
                organization=participant.organization,
                is_primary=participant.is_primary,
                start_date=participant.start_date,
                end_date=participant.end_date,
                notes=participant.notes,
            )
        )
    audit(session, actor=actor, entity_type="project", entity_id=project.id, action="sync_participants", previous={"participants": previous}, new={"participants": [item.model_dump(mode="json") for item in participants]})


def _project_payload(session: Session, project: ProjectModel) -> dict[str, object]:
    _, sanctions, revisions, tranches = project_records(session, project.id)
    summary = calculate_project_financials(sanctions, revisions, tranches)
    return {
        "id": project.id,
        "projectCode": project.project_code,
        "project_code": project.project_code,
        "title": project.title,
        "shortTitle": project.short_title,
        "short_title": project.short_title,
        "description": project.description,
        "institution": project.institution,
        "school": project.school,
        "department": project.department,
        "academicYear": project.academic_year,
        "academic_year": project.academic_year,
        "cohort": project.cohort,
        "category": project.category,
        "domain": project.domain,
        "technologyReadinessLevel": project.technology_readiness_level,
        "technology_readiness_level": project.technology_readiness_level,
        "prototypeStatus": project.prototype_status,
        "prototype_status": project.prototype_status,
        "publicationStatus": project.publication_status,
        "publication_status": project.publication_status,
        "patentStatus": project.patent_status,
        "patent_status": project.patent_status,
        "startupStatus": project.startup_status,
        "startup_status": project.startup_status,
        "status": project.project_status,
        "projectStatus": project.project_status,
        "project_status": project.project_status,
        "fundingStatus": project.funding_status,
        "funding_status": project.funding_status,
        "startDate": project.start_date,
        "start_date": project.start_date,
        "expectedCompletionDate": project.expected_completion_date,
        "expected_completion_date": project.expected_completion_date,
        "actualCompletionDate": project.actual_completion_date,
        "actual_completion_date": project.actual_completion_date,
        "closureNotes": project.closure_notes,
        "closure_notes": project.closure_notes,
        "remarks": project.remarks,
        "version": project.version,
        "participants": [_participant_payload(item) for item in sorted(project.participants, key=lambda participant: (not participant.is_primary, participant.full_name))],
        "summary": _summary_payload(summary),
    }


def _summary_payload(summary: ProjectFinancialSummary) -> dict[str, object]:
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


def _participant_payload(item: ProjectParticipantModel) -> dict[str, object]:
    return {
        "id": item.id,
        "projectId": item.project_id,
        "role": item.role,
        "roleLabel": _label(item.role),
        "fullName": item.full_name,
        "email": item.email,
        "phone": item.phone,
        "department": item.department,
        "organization": item.organization,
        "isPrimary": item.is_primary,
        "startDate": item.start_date,
        "endDate": item.end_date,
        "notes": item.notes,
    }


def _sanction_payload(item: FundingSanctionModel) -> dict[str, object]:
    return {
        "id": item.id,
        "projectId": item.project_id,
        "sanctionReference": item.sanction_reference,
        "sanctionDate": item.sanction_date,
        "amount": str(item.amount),
        "fundingSource": item.funding_source,
        "financialYear": item.financial_year,
        "status": item.status,
        "statusLabel": _label(item.status),
        "approvedBy": item.approved_by,
        "approvedAt": item.approved_at,
        "remarks": item.remarks,
        "version": item.version,
    }


def _revision_payload(item: FundingRevisionModel) -> dict[str, object]:
    return {
        "id": item.id,
        "projectId": item.project_id,
        "revisionNumber": item.revision_number,
        "revisionType": item.revision_type,
        "revisionTypeLabel": _label(item.revision_type),
        "revisionDate": item.revision_date,
        "amount": str(item.amount),
        "approvalReference": item.approval_reference,
        "reason": item.reason,
        "status": item.status,
        "statusLabel": _label(item.status),
        "approvedBy": item.approved_by,
        "approvedAt": item.approved_at,
        "remarks": item.remarks,
        "version": item.version,
    }


def _tranche_payload(item: TrancheModel, project: ProjectModel | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": item.id,
        "projectId": item.project_id,
        "sequenceNumber": item.sequence_number,
        "transactionType": item.transaction_type,
        "transactionTypeLabel": _label(item.transaction_type),
        "purchaseOrderNumber": item.purchase_order_number,
        "purchaseOrderReceivedDate": item.purchase_order_received_date,
        "requestDate": item.request_date,
        "requestedAmount": str(item.requested_amount),
        "approvedAmount": str(item.approved_amount),
        "approvalDate": item.approval_date,
        "expectedDisbursementDate": item.expected_disbursement_date,
        "actualDisbursementDate": item.actual_disbursement_date,
        "disbursedAmount": str(item.disbursed_amount),
        "refundAmount": str(item.refund_amount),
        "utilizedAmount": str(item.utilized_amount),
        "paymentMode": item.payment_mode,
        "paymentReference": item.payment_reference,
        "billStatus": item.bill_status,
        "utilizationCertificateStatus": item.utilization_certificate_status,
        "status": item.status,
        "statusLabel": _label(item.status),
        "remarks": item.remarks,
        "version": item.version,
    }
    if project is not None:
        payload["projectCode"] = project.project_code
        payload["projectTitle"] = project.title
    return payload


def _audit_payload(item: AuditEventModel) -> dict[str, object]:
    return {"id": item.id, "entityType": item.entity_type, "entityId": item.entity_id, "action": item.action, "actorId": item.actor_id, "timestamp": item.timestamp, "previousValues": item.previous_values, "newValues": item.new_values, "reason": item.reason}


def _user_payload(user: UserModel) -> dict[str, object]:
    return {"id": user.id, "email": user.email, "fullName": user.full_name, "role": user.role, "roleLabel": _label(user.role), "isActive": user.is_active}


def _label(value: object) -> str:
    return str(getattr(value, "value", value) or "").replace("_", " ").title()


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
