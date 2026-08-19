from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import BaseModel, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.provider import AIAssistantProvider, AIProviderError
from app.ai.schemas import (
    AIAssistantResponse,
    AIProviderEnvelope,
    CreateProjectArguments,
    CreateTrancheArguments,
    ExportArguments,
    FundingRevisionArguments,
    ProjectLookupArguments,
    ReconciliationArguments,
    SearchProjectsArguments,
    TrancheActionArguments,
    UpdateProjectArguments,
)
from app.core.enums import ProjectStatus, Role, TransactionType
from app.core.money import ZERO, format_inr, money
from app.models.domain import (
    AIProposalModel,
    AuditEventModel,
    FundingRevisionModel,
    ProjectModel,
    TrancheModel,
    UserModel,
)
from app.services.financials import calculate_project_financials
from app.services.permissions import Actor, can
from app.services.reconciliation import reconcile_project
from app.services.workflow import (
    WorkflowError,
    approve_tranche,
    audit,
    create_funding_revision_record,
    create_project_record,
    create_tranche_record,
    project_records,
    record_disbursement,
    record_refund,
    record_utilization,
    update_project_fields,
    uuid,
)

PROPOSAL_TTL_MINUTES = 15
FORBIDDEN_KEYS = {"sql", "raw_sql", "query_sql", "method", "function", "python", "filesystem_path", "doctype", "import_path"}
PROJECT_UPDATE_FIELDS = {"title", "institution", "school", "department", "academic_year", "cohort", "expected_completion_date", "project_status", "remarks"}
TRANSACTION_TYPES = {item.value for item in TransactionType}
PROJECT_STATUSES = {item.value for item in ProjectStatus}
ResponseKind = Literal["answer", "proposal", "clarification", "error", "result", "export"]


class AIAssistantError(ValueError):
    pass


class ClarificationRequired(AIAssistantError):
    pass


@dataclass(frozen=True)
class ActionSpec:
    schema: type[BaseModel]
    permission: str
    write: bool = False


ACTION_REGISTRY: dict[str, ActionSpec] = {
    "search_projects": ActionSpec(SearchProjectsArguments, "read"),
    "get_project": ActionSpec(ProjectLookupArguments, "read"),
    "get_project_financial_summary": ActionSpec(ProjectLookupArguments, "read"),
    "summarize_project": ActionSpec(ProjectLookupArguments, "read"),
    "list_reconciliation_issues": ActionSpec(ReconciliationArguments, "read"),
    "generate_project_master_export": ActionSpec(ExportArguments, "export"),
    "generate_tranche_register_export": ActionSpec(ExportArguments, "export"),
    "create_project": ActionSpec(CreateProjectArguments, "write", write=True),
    "update_project": ActionSpec(UpdateProjectArguments, "write", write=True),
    "create_tranche": ActionSpec(CreateTrancheArguments, "write", write=True),
    "create_funding_revision": ActionSpec(FundingRevisionArguments, "write", write=True),
    "record_refund": ActionSpec(TrancheActionArguments, "write", write=True),
    "record_utilization": ActionSpec(TrancheActionArguments, "write", write=True),
    "record_disbursement": ActionSpec(TrancheActionArguments, "write", write=True),
    "approve_tranche": ActionSpec(TrancheActionArguments, "approve", write=True),
}


class AIAssistantService:
    def __init__(
        self,
        *,
        session: Session,
        provider: AIAssistantProvider,
        ai_enabled: bool,
        provider_base_url: str,
        provider_model: str,
    ) -> None:
        self.session = session
        self.provider = provider
        self.ai_enabled = ai_enabled
        self.provider_base_url = provider_base_url
        self.provider_model = provider_model

    def request(self, *, actor: UserModel, text: str, current_project_id: str | None = None, current_project_code: str | None = None, language: str | None = None) -> dict[str, object]:
        if not self.ai_enabled:
            return _response("error", "AI assistant is disabled. Set AI_ENABLED=true on the server to use it.")
        actor_permissions = _actor(actor)
        if not can(actor_permissions, "read"):
            return _response("error", "You do not have permission to use the assistant.")
        try:
            envelope = self.provider.complete(
                system_prompt=_system_prompt(),
                user_text=text,
                context={"current_project_id": current_project_id, "current_project_code": current_project_code, "language": language},
            )
        except AIProviderError as exc:
            return _response("error", str(exc))
        except Exception:
            return _response("error", "AI provider is unavailable.")
        try:
            return self._handle_envelope(actor, text, envelope, current_project_id, current_project_code)
        except ClarificationRequired as exc:
            return _response("clarification", str(exc))
        except AIAssistantError as exc:
            return _response("error", str(exc))

    def get_proposal(self, *, proposal_id: str, actor: UserModel) -> dict[str, object]:
        proposal = self._proposal_for_user(proposal_id, actor)
        return _response("proposal", proposal.message or "Proposal is pending confirmation.", proposal=_proposal_payload(proposal))

    def cancel(self, *, proposal_id: str, actor: UserModel) -> dict[str, object]:
        proposal = self._proposal_for_user(proposal_id, actor)
        if proposal.status != "pending_confirmation":
            return _response("result", f"Proposal is already {proposal.status}.", proposal=_proposal_payload(proposal))
        proposal.status = "cancelled"
        proposal.result = {"status": "cancelled"}
        audit(self.session, actor=actor, entity_type="ai_proposal", entity_id=proposal.id, action="cancel_ai_proposal", new={"action": proposal.action})
        self.session.commit()
        return _response("result", "Proposal cancelled.", proposal=_proposal_payload(proposal))

    def confirm(self, *, proposal_id: str, actor: UserModel) -> dict[str, object]:
        proposal = self._proposal_for_user(proposal_id, actor)
        if proposal.status != "pending_confirmation":
            return _response("error", f"Proposal is {proposal.status} and cannot be confirmed.", proposal=_proposal_payload(proposal))
        if proposal.expires_at <= datetime.now(UTC):
            proposal.status = "expired"
            proposal.result = {"status": "expired"}
            audit(self.session, actor=actor, entity_type="ai_proposal", entity_id=proposal.id, action="expire_ai_proposal", new={"action": proposal.action})
            self.session.commit()
            return _response("error", "Proposal expired. Ask the assistant to prepare it again.", proposal=_proposal_payload(proposal))
        spec = _action_spec(proposal.action)
        if not can(_actor(actor), spec.permission):
            return _response("error", "You do not have permission to confirm this proposal.", proposal=_proposal_payload(proposal))
        try:
            args = self._validated_arguments(proposal.action, proposal.arguments)
            result = self._execute_action(actor, proposal.action, args, proposal)
        except (AIAssistantError, WorkflowError, ValueError) as exc:
            proposal.status = "failed"
            proposal.result = {"status": "failed", "error": str(exc)}
            audit(self.session, actor=actor, entity_type="ai_proposal", entity_id=proposal.id, action="fail_ai_proposal", new={"action": proposal.action, "error": str(exc)})
            self.session.commit()
            return _response("error", str(exc), proposal=_proposal_payload(proposal))
        proposal.status = "executed"
        proposal.confirmed_at = proposal.confirmed_at or datetime.now(UTC)
        proposal.executed_at = datetime.now(UTC)
        proposal.result = _jsonable(result)
        audit(self.session, actor=actor, entity_type="ai_proposal", entity_id=proposal.id, action="confirm_ai_proposal", new={"action": proposal.action, "result": proposal.result})
        self.session.commit()
        return _response("result", "AI proposal executed.", proposal=_proposal_payload(proposal), data=proposal.result)

    def _handle_envelope(self, actor: UserModel, original_request: str, envelope: AIProviderEnvelope, current_project_id: str | None, current_project_code: str | None) -> dict[str, object]:
        if envelope.kind in {"error", "clarification"} and not envelope.action:
            return _response(envelope.kind, envelope.message)
        if not envelope.action:
            return _response("answer", envelope.message)
        spec = _action_spec(envelope.action)
        _assert_no_forbidden(envelope.arguments)
        if not can(_actor(actor), spec.permission):
            raise AIAssistantError("This action is not allowed for your role.")
        args = self._validated_arguments(envelope.action, envelope.arguments)
        if spec.write:
            proposal = self._create_proposal(actor, original_request, envelope, args, current_project_id, current_project_code)
            return _response("proposal", proposal.message or envelope.message, proposal=_proposal_payload(proposal))
        return self._execute_read_action(actor, envelope.action, args, current_project_id, current_project_code, envelope.message)

    def _validated_arguments(self, action: str, arguments: dict[str, Any]) -> BaseModel:
        try:
            return _action_spec(action).schema.model_validate(arguments)
        except ValidationError as exc:
            raise AIAssistantError(f"Invalid arguments for {action}: {exc.errors()}") from exc

    def _create_proposal(self, actor: UserModel, original_request: str, envelope: AIProviderEnvelope, args: BaseModel, current_project_id: str | None, current_project_code: str | None) -> AIProposalModel:
        current_values, proposed_values, target_type, target_id, message = self._preview_write_action(actor, envelope.action or "", args, current_project_id, current_project_code)
        proposal = AIProposalModel(
            id=uuid(),
            user_id=actor.id,
            action=envelope.action or "",
            arguments=_jsonable(args.model_dump(mode="json")),
            target_entity_type=target_type,
            target_entity_id=target_id,
            current_values=current_values,
            proposed_values=proposed_values,
            validation_result={"valid": True, "warnings": []},
            status="pending_confirmation",
            provider=self.provider.provider_name,
            model=self.provider.model,
            original_request=original_request,
            message=message or envelope.message,
            expires_at=datetime.now(UTC) + timedelta(minutes=PROPOSAL_TTL_MINUTES),
        )
        self.session.add(proposal)
        audit(self.session, actor=actor, entity_type="ai_proposal", entity_id=proposal.id, action="preview_ai_proposal", new={"action": proposal.action, "target": target_id})
        self.session.commit()
        return proposal

    def _execute_read_action(self, actor: UserModel, action: str, args: BaseModel, current_project_id: str | None, current_project_code: str | None, provider_message: str) -> dict[str, object]:
        if action == "search_projects":
            assert isinstance(args, SearchProjectsArguments)
            projects = _search_projects(self.session, args.query, args.limit)
            return _response("answer", f"Found {len(projects)} matching project(s).", data=[_project_brief(project) for project in projects])
        if action == "get_project":
            project = self._resolve_project(args, current_project_id, current_project_code)
            return _response("answer", f"{project.project_code}: {project.title}", data=_project_brief(project))
        if action == "get_project_financial_summary":
            project = self._resolve_project(args, current_project_id, current_project_code)
            return _response("answer", f"Financial summary for {project.project_code}.", data=self._project_summary(project))
        if action == "summarize_project":
            project = self._resolve_project(args, current_project_id, current_project_code)
            data = self._project_summary(project)
            data["project"] = _project_brief(project)
            data["recentActivity"] = self._recent_activity(project.id)
            return _response("answer", f"{project.project_code} summary.", data=data)
        if action == "list_reconciliation_issues":
            assert isinstance(args, ReconciliationArguments)
            reconciliation_project: ProjectModel | None = None
            if args.project_code or current_project_id or current_project_code:
                reconciliation_project = self._resolve_project(ProjectLookupArguments(project_code=args.project_code), current_project_id, current_project_code)
            issues = self._reconciliation_for(reconciliation_project)
            return _response("answer", f"Found {len(issues)} reconciliation issue(s).", data=issues)
        if action in {"generate_project_master_export", "generate_tranche_register_export"}:
            assert isinstance(args, ExportArguments)
            if action == "generate_project_master_export":
                path = f"/api/v1/exports/project-master.{args.file_format}"
                label = "project master"
            else:
                path = f"/api/v1/exports/tranche-register.{args.file_format}"
                label = "tranche register"
            return _response("export", f"Generated {label} export link.", download_url=path, data={"exportType": args.export_type, "format": args.file_format})
        return _response("answer", provider_message)

    def _preview_write_action(self, actor: UserModel, action: str, args: BaseModel, current_project_id: str | None, current_project_code: str | None) -> tuple[dict[str, Any], dict[str, Any], str | None, str | None, str]:
        if action == "create_project":
            assert isinstance(args, CreateProjectArguments)
            if self.session.scalar(select(ProjectModel).where(ProjectModel.project_code == args.project_code.strip().upper())) is not None:
                raise AIAssistantError(f"Project code {args.project_code} already exists.")
            proposed = _project_create_values(args)
            return {}, proposed, "project", None, "Create project proposal ready."
        if action == "update_project":
            assert isinstance(args, UpdateProjectArguments)
            project = self._resolve_project(args, current_project_id, current_project_code)
            updates = _project_updates(args.updates)
            current = {"version": project.version, **{key: _jsonable(getattr(project, key)) for key in updates}}
            return current, updates, "project", project.id, "Project update proposal ready."
        if action == "create_tranche":
            assert isinstance(args, CreateTrancheArguments)
            project = self._resolve_project(args, current_project_id, current_project_code)
            proposed = self._tranche_values(project, args)
            return self._project_financial_context(project), proposed, "project", project.id, "Create draft tranche proposal ready."
        if action == "create_funding_revision":
            assert isinstance(args, FundingRevisionArguments)
            project = self._resolve_project(args, current_project_id, current_project_code)
            proposed = self._funding_revision_values(project, args)
            return self._project_financial_context(project), proposed, "project", project.id, "Create draft funding revision proposal ready."
        if action in {"record_refund", "record_utilization", "record_disbursement", "approve_tranche"}:
            assert isinstance(args, TrancheActionArguments)
            tranche = self._resolve_tranche(args, current_project_id, current_project_code)
            current = _tranche_current_values(tranche)
            proposed = self._tranche_action_values(action, tranche, args)
            return current, proposed, "tranche", tranche.id, f"{action.replace('_', ' ').title()} proposal ready."
        raise AIAssistantError(f"Unsupported write action: {action}.")

    def _execute_action(self, actor: UserModel, action: str, args: BaseModel, proposal: AIProposalModel) -> dict[str, object]:
        if action == "create_project":
            assert isinstance(args, CreateProjectArguments)
            if self.session.scalar(select(ProjectModel).where(ProjectModel.project_code == args.project_code.strip().upper())) is not None:
                raise AIAssistantError(f"Project code {args.project_code} already exists.")
            project = create_project_record(self.session, actor, _project_create_values(args))
            return {"entityType": "project", "entityId": project.id, "projectCode": project.project_code}
        if action == "update_project":
            assert isinstance(args, UpdateProjectArguments)
            project = self._resolve_project(args, None, None)
            expected_version = int(proposal.current_values.get("version", -1))
            update_project_fields(self.session, project, actor, _project_updates(args.updates), expected_version)
            return {"entityType": "project", "entityId": project.id, "projectCode": project.project_code, "version": project.version}
        if action == "create_tranche":
            assert isinstance(args, CreateTrancheArguments)
            project = self._resolve_project(args, None, None)
            tranche = create_tranche_record(self.session, project, actor, self._tranche_values(project, args))
            return {"entityType": "tranche", "entityId": tranche.id, "projectCode": project.project_code, "sequenceNumber": tranche.sequence_number}
        if action == "create_funding_revision":
            assert isinstance(args, FundingRevisionArguments)
            project = self._resolve_project(args, None, None)
            revision = create_funding_revision_record(self.session, project, actor, self._funding_revision_values(project, args))
            return {"entityType": "funding_revision", "entityId": revision.id, "projectCode": project.project_code, "revisionNumber": revision.revision_number}
        if action in {"record_refund", "record_utilization", "record_disbursement", "approve_tranche"}:
            assert isinstance(args, TrancheActionArguments)
            tranche = self._resolve_tranche(args, None, None)
            if action == "record_refund":
                amount = _amount(args.amount)
                record_refund(self.session, tranche, actor, amount)
            elif action == "record_utilization":
                amount = _amount(args.amount)
                record_utilization(self.session, tranche, actor, amount)
            elif action == "record_disbursement":
                if not args.payment_reference or not args.payment_date:
                    raise AIAssistantError("payment_reference and payment_date are required for disbursement.")
                amount = _amount(args.amount)
                record_disbursement(self.session, tranche, actor, amount, args.payment_reference, args.payment_date, args.payment_mode)
            elif action == "approve_tranche":
                approve_tranche(self.session, tranche, actor)
            return {"entityType": "tranche", "entityId": tranche.id, "status": tranche.status}
        raise AIAssistantError(f"Unsupported action: {action}.")

    def _resolve_project(self, args: BaseModel, current_project_id: str | None, current_project_code: str | None) -> ProjectModel:
        project_code = getattr(args, "project_code", None) or current_project_code
        query = getattr(args, "query", None)
        if project_code:
            project = self.session.scalar(select(ProjectModel).where(ProjectModel.project_code == str(project_code).strip().upper()))
            if project is None:
                raise AIAssistantError(f"Project {project_code} was not found.")
            return project
        if current_project_id:
            project = self.session.get(ProjectModel, current_project_id)
            if project is None:
                raise AIAssistantError("Current project context was not found.")
            return project
        if query:
            matches = _search_projects(self.session, str(query), 5)
            if not matches:
                raise AIAssistantError(f"No project matched {query!r}.")
            if len(matches) > 1:
                raise ClarificationRequired("Multiple projects match that request. Use the exact project code.")
            return matches[0]
        raise ClarificationRequired("Specify a project code or open the assistant from a project page.")

    def _resolve_tranche(self, args: TrancheActionArguments, current_project_id: str | None, current_project_code: str | None) -> TrancheModel:
        if args.tranche_id:
            tranche = self.session.get(TrancheModel, args.tranche_id)
            if tranche is None:
                raise AIAssistantError("Tranche was not found.")
            return tranche
        if args.tranche_sequence is None:
            raise ClarificationRequired("Specify the tranche sequence.")
        project = self._resolve_project(args, current_project_id, current_project_code)
        tranche = self.session.scalar(select(TrancheModel).where(TrancheModel.project_id == project.id, TrancheModel.sequence_number == args.tranche_sequence))
        if tranche is None:
            raise AIAssistantError(f"Tranche {args.tranche_sequence} was not found for {project.project_code}.")
        return tranche

    def _project_summary(self, project: ProjectModel) -> dict[str, Any]:
        _, sanctions, revisions, tranches = project_records(self.session, project.id)
        return _summary_payload(calculate_project_financials(sanctions, revisions, tranches))

    def _project_financial_context(self, project: ProjectModel) -> dict[str, Any]:
        summary = self._project_summary(project)
        return {
            "projectCode": project.project_code,
            "projectTitle": project.title,
            "totalSanctionedAmount": summary["totalSanctionedAmount"],
            "netDisbursedAmount": summary["netDisbursedAmount"],
            "pendingApprovedAmount": summary["pendingApprovedAmount"],
            "approvalCapacity": summary["approvalCapacity"],
            "reconciliationStatus": summary["reconciliationStatus"],
        }

    def _tranche_values(self, project: ProjectModel, args: CreateTrancheArguments) -> dict[str, Any]:
        requested = _amount(args.requested_amount)
        approved = _amount(args.approved_amount if args.approved_amount is not None else args.requested_amount)
        if approved > requested:
            raise AIAssistantError("Approved amount cannot exceed requested amount.")
        if args.transaction_type not in TRANSACTION_TYPES:
            raise AIAssistantError(f"transaction_type must be one of: {', '.join(sorted(TRANSACTION_TYPES))}.")
        capacity = _approval_capacity(self.session, project)
        if approved > capacity:
            raise AIAssistantError(f"Proposed tranche exceeds available approval capacity by {format_inr(approved - capacity)}.")
        sequence = args.sequence_number or _next_tranche_sequence(self.session, project)
        if self.session.scalar(select(TrancheModel).where(TrancheModel.project_id == project.id, TrancheModel.sequence_number == sequence)) is not None:
            raise AIAssistantError(f"Tranche {sequence} already exists for {project.project_code}.")
        return {
            "sequence_number": sequence,
            "transaction_type": args.transaction_type,
            "requested_amount": approved if requested == ZERO else requested,
            "approved_amount": approved,
            "request_date": args.request_date,
            "remarks": args.remarks,
        }

    def _funding_revision_values(self, project: ProjectModel, args: FundingRevisionArguments) -> dict[str, Any]:
        amount = _amount(args.amount)
        if amount <= ZERO:
            raise AIAssistantError("Funding revision amount must be greater than zero.")
        return {
            "revision_number": _next_revision_number(self.session, project),
            "revision_type": args.revision_type,
            "revision_date": args.revision_date,
            "amount": amount,
            "approval_reference": args.approval_reference,
            "reason": args.reason,
        }

    def _tranche_action_values(self, action: str, tranche: TrancheModel, args: TrancheActionArguments) -> dict[str, Any]:
        if action == "record_refund":
            amount = _amount(args.amount)
            if amount > tranche.disbursed_amount:
                raise AIAssistantError("Refund amount cannot exceed this tranche's disbursed amount.")
            return {"refundAmount": str(amount)}
        if action == "record_utilization":
            amount = _amount(args.amount)
            if amount > tranche.disbursed_amount - tranche.refund_amount:
                raise AIAssistantError("Utilization cannot exceed this tranche's net disbursed amount.")
            return {"utilizedAmount": str(amount)}
        if action == "record_disbursement":
            amount = _amount(args.amount)
            if amount > tranche.approved_amount:
                raise AIAssistantError("Disbursed amount cannot exceed approved amount.")
            if not args.payment_reference or not args.payment_date:
                raise AIAssistantError("payment_reference and payment_date are required for disbursement.")
            return {"disbursedAmount": str(amount), "paymentReference": args.payment_reference, "paymentDate": args.payment_date.isoformat()}
        if action == "approve_tranche":
            project = self.session.get(ProjectModel, tranche.project_id)
            if project is None:
                raise AIAssistantError("Project was not found for tranche.")
            capacity = _approval_capacity(self.session, project, excluding_tranche_id=tranche.id)
            if tranche.approved_amount > capacity:
                raise AIAssistantError(f"This tranche exceeds available approval capacity by {format_inr(tranche.approved_amount - capacity)}.")
            return {"status": "approved", "approvedAmount": str(tranche.approved_amount), "approvalCapacity": str(capacity)}
        raise AIAssistantError(f"Unsupported tranche action: {action}.")

    def _reconciliation_for(self, project: ProjectModel | None) -> list[dict[str, Any]]:
        if project is not None:
            _, sanctions, revisions, tranches = project_records(self.session, project.id)
            return [_reconciliation_payload(issue, project) for issue in reconcile_project(project, sanctions, revisions, tranches)]
        rows: list[dict[str, Any]] = []
        for item in self.session.scalars(select(ProjectModel).order_by(ProjectModel.project_code)):
            _, sanctions, revisions, tranches = project_records(self.session, item.id)
            rows.extend(_reconciliation_payload(issue, item) for issue in reconcile_project(item, sanctions, revisions, tranches))
        return rows

    def _recent_activity(self, project_id: str) -> list[dict[str, Any]]:
        _, sanctions, revisions, tranches = project_records(self.session, project_id)
        entity_ids = [project_id, *[item.id for item in sanctions], *[item.id for item in revisions], *[item.id for item in tranches]]
        events = self.session.scalars(select(AuditEventModel).where(AuditEventModel.entity_id.in_(entity_ids)).order_by(AuditEventModel.timestamp.desc()).limit(5))
        return [{"action": event.action, "entityType": event.entity_type, "timestamp": event.timestamp.isoformat() if event.timestamp else None} for event in events]

    def _proposal_for_user(self, proposal_id: str, actor: UserModel) -> AIProposalModel:
        proposal = self.session.get(AIProposalModel, proposal_id)
        if proposal is None:
            raise AIAssistantError("AI proposal not found.")
        if proposal.user_id != actor.id:
            raise AIAssistantError("You cannot access another user's AI proposal.")
        return proposal


def _system_prompt() -> str:
    return (
        "You are TrancheAI's administrative assistant. Return only JSON with keys kind, message, action and arguments. "
        "Use only supported action names. Do not invent project identifiers, financial values or database fields. "
        "Mark missing information as clarification. Never request SQL, Python methods, filesystem paths or workflow bypasses. "
        "Financial balances are calculated by TrancheAI after your structured response."
    )


def _action_spec(action: str) -> ActionSpec:
    spec = ACTION_REGISTRY.get(action)
    if spec is None:
        raise AIAssistantError(f"Unsupported AI action: {action}.")
    return spec


def _actor(user: UserModel) -> Actor:
    return Actor(user.id, {Role(user.role)})


def _assert_no_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise AIAssistantError(f"AI action contains forbidden field: {key}.")
            _assert_no_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_forbidden(item)


def _search_projects(session: Session, query: str, limit: int) -> list[ProjectModel]:
    needle = f"%{query.strip()}%"
    return list(
        session.scalars(
            select(ProjectModel)
            .where(or_(ProjectModel.project_code.ilike(needle), ProjectModel.title.ilike(needle), ProjectModel.department.ilike(needle)))
            .order_by(ProjectModel.project_code)
            .limit(limit)
        )
    )


def _project_brief(project: ProjectModel) -> dict[str, Any]:
    return {
        "id": project.id,
        "projectCode": project.project_code,
        "title": project.title,
        "school": project.school,
        "department": project.department,
        "academicYear": project.academic_year,
        "status": project.project_status,
        "createdAt": project.created_at.isoformat() if project.created_at else None,
    }


def _project_create_values(args: CreateProjectArguments) -> dict[str, Any]:
    code = args.project_code.strip().upper()
    if not code:
        raise AIAssistantError("project_code is required.")
    if args.project_status not in PROJECT_STATUSES:
        raise AIAssistantError(f"project_status must be one of: {', '.join(sorted(PROJECT_STATUSES))}.")
    return {
        "project_code": code,
        "title": args.title.strip(),
        "institution": args.institution,
        "school": args.school,
        "department": args.department,
        "academic_year": args.academic_year,
        "cohort": args.cohort,
        "project_status": args.project_status,
        "funding_status": "not_sanctioned",
        "expected_completion_date": args.expected_completion_date,
        "remarks": args.remarks,
    }


def _project_updates(updates: dict[str, Any]) -> dict[str, Any]:
    unknown = set(updates) - PROJECT_UPDATE_FIELDS
    if unknown:
        raise AIAssistantError(f"AI cannot update project field(s): {', '.join(sorted(unknown))}.")
    if not updates:
        raise AIAssistantError("No project fields were provided for update.")
    if "project_status" in updates and updates["project_status"] not in PROJECT_STATUSES:
        raise AIAssistantError(f"project_status must be one of: {', '.join(sorted(PROJECT_STATUSES))}.")
    return updates


def _next_tranche_sequence(session: Session, project: ProjectModel) -> int:
    sequences = list(session.scalars(select(TrancheModel.sequence_number).where(TrancheModel.project_id == project.id)))
    return max(sequences, default=0) + 1


def _next_revision_number(session: Session, project: ProjectModel) -> int:
    numbers = list(session.scalars(select(FundingRevisionModel.revision_number).where(FundingRevisionModel.project_id == project.id)))
    return max(numbers, default=0) + 1


def _approval_capacity(session: Session, project: ProjectModel, excluding_tranche_id: str | None = None) -> Decimal:
    _, sanctions, revisions, tranches = project_records(session, project.id)
    if excluding_tranche_id:
        tranches = [item for item in tranches if item.id != excluding_tranche_id]
    summary = calculate_project_financials(sanctions, revisions, tranches)
    return summary.available_sanctioned_balance - summary.pending_approved_amount


def _summary_payload(summary) -> dict[str, Any]:
    return {
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
        "approvalCapacity": str(summary.available_sanctioned_balance - summary.pending_approved_amount),
        "trancheCount": summary.tranche_count,
        "latestDisbursementDate": summary.latest_disbursement_date.isoformat() if summary.latest_disbursement_date else None,
        "reconciliationStatus": summary.reconciliation_status,
    }


def _tranche_current_values(tranche: TrancheModel) -> dict[str, Any]:
    return {
        "status": tranche.status,
        "sequenceNumber": tranche.sequence_number,
        "requestedAmount": str(tranche.requested_amount),
        "approvedAmount": str(tranche.approved_amount),
        "disbursedAmount": str(tranche.disbursed_amount),
        "refundAmount": str(tranche.refund_amount),
        "utilizedAmount": str(tranche.utilized_amount),
        "paymentReference": tranche.payment_reference,
        "actualDisbursementDate": tranche.actual_disbursement_date.isoformat() if tranche.actual_disbursement_date else None,
    }


def _reconciliation_payload(issue, project: ProjectModel) -> dict[str, Any]:
    return {
        "issueType": issue.issue_type,
        "severity": issue.severity,
        "projectId": project.id,
        "projectCode": project.project_code,
        "projectTitle": project.title,
        "description": issue.description,
        "financialImpact": str(issue.financial_impact),
        "suggestedAction": issue.suggested_action,
    }


def _proposal_payload(proposal: AIProposalModel) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "action": proposal.action,
        "status": proposal.status,
        "targetEntityType": proposal.target_entity_type,
        "targetEntityId": proposal.target_entity_id,
        "currentValues": proposal.current_values,
        "proposedValues": proposal.proposed_values,
        "validationResult": proposal.validation_result,
        "message": proposal.message,
        "expiresAt": proposal.expires_at.isoformat() if proposal.expires_at else None,
        "result": proposal.result,
    }


def _response(kind: ResponseKind, message: str, *, proposal: dict[str, Any] | None = None, data: dict[str, Any] | list[dict[str, Any]] | None = None, download_url: str | None = None) -> dict[str, object]:
    return AIAssistantResponse(kind=kind, message=message, proposal=proposal, data=data, download_url=download_url).model_dump(mode="json", exclude_none=True)


def _amount(value: Any) -> Decimal:
    if value is None:
        raise AIAssistantError("Amount is required.")
    if isinstance(value, int | Decimal):
        return money(value)
    text = str(value).strip().lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()
    multiplier = Decimal("1")
    for marker, factor in [("crore", "10000000"), ("cr", "10000000"), ("lakh", "100000"), ("lac", "100000"), ("k", "1000")]:
        if text.endswith(marker):
            text = text[: -len(marker)].strip()
            multiplier = Decimal(factor)
            break
    try:
        return money(Decimal(text) * multiplier)
    except (InvalidOperation, ValueError) as exc:
        raise AIAssistantError(f"Invalid amount: {value!r}.") from exc


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
