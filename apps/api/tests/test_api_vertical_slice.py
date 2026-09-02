from __future__ import annotations

import csv
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.assistant_service import AIAssistantService
from app.ai.provider import FakeAIAssistantProvider
from app.ai.schemas import AIProviderEnvelope
from app.api.v1 import routes as api_routes
from app.core.enums import Role
from app.db.session import SessionLocal
from app.imports.csv_importer import PROJECT_HEADERS, REVISION_HEADERS, SANCTION_HEADERS, TRANCHE_HEADERS
from app.main import app
from app.models.domain import (
    AIConversationModel,
    AIMessageModel,
    AIProposalModel,
    AuditEventModel,
    AuthSessionModel,
    FundingRevisionModel,
    FundingSanctionModel,
    ImportBatchModel,
    ImportRowModel,
    ProjectModel,
    ProjectParticipantModel,
    TrancheModel,
    UserModel,
)
from app.services.security import hash_password
from app.services.workflow import uuid


@pytest.fixture(autouse=True)
def clean_database(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api_routes, "_effective_ai_enabled", lambda: False)
    with SessionLocal() as session:
        for model in [AuditEventModel, AIMessageModel, AIConversationModel, AIProposalModel, ImportRowModel, ImportBatchModel, TrancheModel, FundingRevisionModel, FundingSanctionModel, ProjectParticipantModel, ProjectModel, AuthSessionModel, UserModel]:
            session.execute(delete(model))
        session.commit()
    yield
    with SessionLocal() as session:
        for model in [AuditEventModel, AIMessageModel, AIConversationModel, AIProposalModel, ImportRowModel, ImportBatchModel, TrancheModel, FundingRevisionModel, FundingSanctionModel, ProjectParticipantModel, ProjectModel, AuthSessionModel, UserModel]:
            session.execute(delete(model))
        session.commit()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_user(email: str, role: Role) -> None:
    with SessionLocal() as session:
        session.add(
            UserModel(
                id=uuid(),
                email=email,
                full_name=email.split("@")[0],
                password_hash=hash_password("Password123!"),
                role=role.value,
            )
        )
        session.commit()


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def csv_content(headers: list[str], rows: list[list[object]]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def preview_import(client: TestClient, headers: dict[str, str], import_type: str, filename: str, content: str):
    return client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": import_type},
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )


def fake_ai_service(envelope: AIProviderEnvelope) -> Callable[[Session], AIAssistantService]:
    def factory(session: Session) -> AIAssistantService:
        return AIAssistantService(
            session=session,
            provider=FakeAIAssistantProvider(envelope),
            ai_enabled=True,
            provider_base_url="http://ai-provider.test/v1",
            provider_model="server-configured-model",
        )

    return factory


def test_authenticated_database_backed_fund_workflow(client: TestClient) -> None:
    create_user("admin@example.test", Role.ADMINISTRATOR)
    create_user("fund@example.test", Role.FUND_ADMINISTRATOR)
    create_user("reviewer@example.test", Role.FUND_REVIEWER)
    create_user("viewer@example.test", Role.VIEWER)

    admin_headers = login(client, "admin@example.test")
    fund_headers = login(client, "fund@example.test")
    reviewer_headers = login(client, "reviewer@example.test")
    viewer_headers = login(client, "viewer@example.test")

    anonymous = client.post("/api/v1/projects", json={"project_code": "TRAI-DB-001", "title": "Blocked"})
    assert anonymous.status_code == 401

    project_response = client.post(
        "/api/v1/projects",
        headers=fund_headers,
        json={
            "project_code": "TRAI-DB-001",
            "title": "Database Vertical Slice प्रकल्प",
            "short_title": "Vertical Slice",
            "description": "Project metadata should survive edits and detail payloads.",
            "school": "Engineering",
            "department": "Mechanical",
            "academic_year": "2026-27",
            "domain": "Robotics",
            "project_status": "active",
            "participants": [{"role": "principal_investigator", "full_name": "Dr Vertical", "email": "pi@example.test", "is_primary": True}],
        },
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]
    assert project_response.json()["shortTitle"] == "Vertical Slice"
    assert project_response.json()["participants"][0]["fullName"] == "Dr Vertical"

    duplicate_response = client.post(
        "/api/v1/projects",
        headers=fund_headers,
        json={"project_code": "TRAI-DB-001", "title": "Duplicate"},
    )
    assert duplicate_response.status_code == 409

    sanction = client.post(
        f"/api/v1/projects/{project_id}/sanctions",
        headers=fund_headers,
        json={"sanction_reference": "SAN-001", "amount": "100000.00"},
    )
    assert sanction.status_code == 201, sanction.text
    sanction_id = sanction.json()["id"]
    assert client.post(f"/api/v1/sanctions/{sanction_id}/approve", headers=fund_headers).status_code == 403
    assert client.post(f"/api/v1/sanctions/{sanction_id}/submit", headers=fund_headers).status_code == 200
    assert client.post(f"/api/v1/sanctions/{sanction_id}/approve", headers=reviewer_headers).status_code == 200

    revision = client.post(
        f"/api/v1/projects/{project_id}/funding-revisions",
        headers=fund_headers,
        json={"revision_number": 1, "revision_type": "increase", "amount": "25000.00"},
    )
    assert revision.status_code == 201, revision.text
    revision_id = revision.json()["id"]
    assert client.post(f"/api/v1/funding-revisions/{revision_id}/submit", headers=fund_headers).status_code == 200
    assert client.post(f"/api/v1/funding-revisions/{revision_id}/approve", headers=reviewer_headers).status_code == 200

    tranche_1 = client.post(
        f"/api/v1/projects/{project_id}/tranches",
        headers=fund_headers,
        json={"sequence_number": 1, "transaction_type": "advance", "requested_amount": "60000.00", "approved_amount": "60000.00", "purchase_order_number": "PO-001", "bill_status": "received"},
    )
    assert tranche_1.status_code == 201, tranche_1.text
    tranche_1_id = tranche_1.json()["id"]
    assert client.post(f"/api/v1/tranches/{tranche_1_id}/submit", headers=fund_headers).status_code == 200
    assert client.post(f"/api/v1/tranches/{tranche_1_id}/approve", headers=reviewer_headers).status_code == 200
    assert client.post(
        f"/api/v1/tranches/{tranche_1_id}/disburse",
        headers=fund_headers,
        json={"amount": "60000.00", "payment_reference": "UTR-DB-001", "payment_date": "2026-08-06"},
    ).status_code == 200
    assert client.post(f"/api/v1/tranches/{tranche_1_id}/record-refund", headers=fund_headers, json={"amount": "5000.00"}).status_code == 200
    assert client.post(f"/api/v1/tranches/{tranche_1_id}/record-utilization", headers=fund_headers, json={"amount": "40000.00"}).status_code == 200

    tranche_2 = client.post(
        f"/api/v1/projects/{project_id}/tranches",
        headers=fund_headers,
        json={"sequence_number": 2, "transaction_type": "reimbursement", "requested_amount": "70000.00", "approved_amount": "70000.00"},
    )
    assert tranche_2.status_code == 201, tranche_2.text
    tranche_2_id = tranche_2.json()["id"]
    assert client.post(f"/api/v1/tranches/{tranche_2_id}/submit", headers=fund_headers).status_code == 200
    assert client.post(f"/api/v1/tranches/{tranche_2_id}/approve", headers=reviewer_headers).status_code == 200

    excessive = client.post(
        f"/api/v1/projects/{project_id}/tranches",
        headers=fund_headers,
        json={"sequence_number": 3, "transaction_type": "advance", "requested_amount": "100000.00", "approved_amount": "100000.00"},
    )
    assert excessive.status_code == 201
    assert client.post(f"/api/v1/tranches/{excessive.json()['id']}/submit", headers=fund_headers).status_code == 200
    blocked = client.post(f"/api/v1/tranches/{excessive.json()['id']}/approve", headers=reviewer_headers)
    assert blocked.status_code == 400
    assert "available sanctioned balance" in blocked.text

    summary = client.get(f"/api/v1/projects/{project_id}/summary", headers=viewer_headers)
    assert summary.status_code == 200
    body = summary.json()
    assert Decimal(body["total_sanctioned_amount"]) == Decimal("125000.00")
    assert Decimal(body["total_approved_tranche_amount"]) == Decimal("130000.00")
    assert Decimal(body["gross_disbursed_amount"]) == Decimal("60000.00")
    assert Decimal(body["total_refunded_amount"]) == Decimal("5000.00")
    assert Decimal(body["net_disbursed_amount"]) == Decimal("55000.00")
    assert Decimal(body["total_utilized_amount"]) == Decimal("40000.00")
    assert Decimal(body["available_sanctioned_balance"]) == Decimal("70000.00")
    assert Decimal(body["pending_approved_amount"]) == Decimal("70000.00")

    with SessionLocal() as session:
        assert session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-DB-001")) is not None
        assert session.scalar(select(AuditEventModel).where(AuditEventModel.action == "record_disbursement")) is not None

    search = client.get("/api/v1/search?q=UTR-DB-001", headers=viewer_headers)
    assert search.status_code == 200
    assert search.json()[0]["type"] == "tranche"

    audit_response = client.get(f"/api/v1/projects/{project_id}/audit", headers=admin_headers)
    assert audit_response.status_code == 200
    assert {event["action"] for event in audit_response.json()} >= {"create", "approve", "record_disbursement"}
    assert "password" not in str(audit_response.json()).lower()

    project_csv = client.get("/api/v1/exports/project-master.csv", headers=viewer_headers)
    assert project_csv.status_code == 200
    assert "TRAI-DB-001" in project_csv.text
    assert "Database Vertical Slice प्रकल्प" in project_csv.text
    assert "125000.00" in project_csv.text

    tranche_csv = client.get("/api/v1/exports/tranche-register.csv", headers=viewer_headers)
    assert tranche_csv.status_code == 200
    rows = tranche_csv.text.splitlines()
    assert rows[1].startswith("1,TRAI-DB-001")
    assert rows[2].startswith(",,,,,,,,,2,")

    workbook = client.get("/api/v1/exports/tranche-register.xlsx", headers=viewer_headers)
    assert workbook.status_code == 200
    with ZipFile(BytesIO(workbook.content)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        styles_xml = archive.read("xl/styles.xml").decode("utf-8")
    assert 'mergeCell ref="A1:U1"' in sheet_xml
    assert "TRAI-DB-001" in sheet_xml
    assert "₹#,##0.00" in styles_xml


def test_settings_and_user_admin_routes(client: TestClient) -> None:
    create_user("admin@example.test", Role.ADMINISTRATOR)
    create_user("viewer@example.test", Role.VIEWER)
    admin_headers = login(client, "admin@example.test")
    viewer_headers = login(client, "viewer@example.test")

    settings_response = client.get("/api/v1/settings", headers=viewer_headers)
    assert settings_response.status_code == 200
    body = settings_response.json()
    assert body["application"]["license"] == "Apache-2.0"
    assert "baseUrl" not in body["ai"]
    assert "apiKey" not in body["ai"]

    assert client.get("/api/v1/users", headers=viewer_headers).status_code == 403
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"email": "fund-new@example.test", "full_name": "Fund New", "password": "Password123!", "role": "fund_administrator"},
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    updated = client.patch(f"/api/v1/users/{user_id}", headers=admin_headers, json={"is_active": False})
    assert updated.status_code == 200
    assert updated.json()["isActive"] is False


def test_readonly_roles_cannot_modify_records(client: TestClient) -> None:
    create_user("viewer@example.test", Role.VIEWER)
    create_user("auditor@example.test", Role.AUDITOR)
    viewer_headers = login(client, "viewer@example.test")
    auditor_headers = login(client, "auditor@example.test")
    assert client.post("/api/v1/projects", headers=viewer_headers, json={"project_code": "NOPE", "title": "Nope"}).status_code == 403
    assert client.post("/api/v1/projects", headers=auditor_headers, json={"project_code": "NOPE2", "title": "Nope"}).status_code == 403


def test_ai_disabled_endpoint_returns_controlled_error(client: TestClient) -> None:
    create_user("viewer@example.test", Role.VIEWER)
    headers = login(client, "viewer@example.test")
    response = client.post("/api/v1/ai/requests", headers=headers, json={"text": "माझा प्रकल्प दाखवा"})
    assert response.status_code == 200
    assert response.json()["kind"] == "error"
    assert "disabled" in response.json()["message"]


def test_ai_create_project_proposal_persists_until_confirmation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    create_user("fund@example.test", Role.FUND_ADMINISTRATOR)
    headers = login(client, "fund@example.test")
    envelope = AIProviderEnvelope(
        kind="proposal",
        message="Create project proposal ready.",
        action="create_project",
        arguments={"project_code": "TRAI-AI-001", "title": "AI Marathi प्रकल्प", "project_status": "active", "department": "Robotics"},
    )
    monkeypatch.setattr(api_routes, "_ai_service", fake_ai_service(envelope))

    response = client.post("/api/v1/ai/requests", headers=headers, json={"text": "Create TRAI-AI-001"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "proposal"
    proposal_id = body["proposal"]["id"]

    with SessionLocal() as session:
        assert session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-AI-001")) is None
        proposal = session.get(AIProposalModel, proposal_id)
        assert proposal is not None
        assert proposal.status == "pending_confirmation"
        assert session.scalar(select(AuditEventModel).where(AuditEventModel.action == "preview_ai_proposal")) is not None

    confirm = client.post(f"/api/v1/ai/proposals/{proposal_id}/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["kind"] == "result"

    with SessionLocal() as session:
        project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-AI-001"))
        assert project is not None
        assert project.title == "AI Marathi प्रकल्प"
        proposal = session.get(AIProposalModel, proposal_id)
        assert proposal is not None
        assert proposal.status == "executed"
        assert session.scalar(select(AuditEventModel).where(AuditEventModel.action == "confirm_ai_proposal")) is not None


def test_ai_conversation_messages_are_persisted(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    create_user("fund@example.test", Role.FUND_ADMINISTRATOR)
    headers = login(client, "fund@example.test")
    project = client.post("/api/v1/projects", headers=headers, json={"project_code": "TRAI-CHAT-001", "title": "Chat context"})
    assert project.status_code == 201, project.text

    envelope = AIProviderEnvelope(kind="answer", message="The project is in draft funding workflow.")
    monkeypatch.setattr(api_routes, "_ai_service", fake_ai_service(envelope))

    conversation = client.post(
        "/api/v1/ai/conversations",
        headers=headers,
        json={"project_id": project.json()["id"]},
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["id"]

    response = client.post(
        f"/api/v1/ai/conversations/{conversation_id}/messages",
        headers=headers,
        json={"text": "What is the next fund action?"},
    )
    assert response.status_code == 200, response.text
    messages = response.json()["conversation"]["messages"]
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "The project is in draft funding workflow."

    history = client.get(f"/api/v1/ai/conversations/{conversation_id}", headers=headers)
    assert history.status_code == 200
    assert len(history.json()["messages"]) == 2

    with SessionLocal() as session:
        assert session.scalar(select(AIConversationModel).where(AIConversationModel.id == conversation_id)) is not None
        assert len(list(session.scalars(select(AIMessageModel).where(AIMessageModel.conversation_id == conversation_id)))) == 2


def test_ai_rejects_forbidden_update_fields_and_viewer_writes(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    create_user("fund@example.test", Role.FUND_ADMINISTRATOR)
    create_user("viewer@example.test", Role.VIEWER)
    fund_headers = login(client, "fund@example.test")
    viewer_headers = login(client, "viewer@example.test")
    project = client.post("/api/v1/projects", headers=fund_headers, json={"project_code": "TRAI-AI-GUARD", "title": "Guarded"})
    assert project.status_code == 201, project.text

    forbidden_update = AIProviderEnvelope(
        kind="proposal",
        message="Bad update.",
        action="update_project",
        arguments={"project_code": "TRAI-AI-GUARD", "updates": {"created_by": "attacker"}},
    )
    monkeypatch.setattr(api_routes, "_ai_service", fake_ai_service(forbidden_update))
    rejected = client.post("/api/v1/ai/requests", headers=fund_headers, json={"text": "change internal field"})
    assert rejected.status_code == 200
    assert rejected.json()["kind"] == "error"
    assert "cannot update" in rejected.json()["message"]

    write_attempt = AIProviderEnvelope(
        kind="proposal",
        message="Create project.",
        action="create_project",
        arguments={"project_code": "TRAI-AI-VIEW", "title": "Viewer write"},
    )
    monkeypatch.setattr(api_routes, "_ai_service", fake_ai_service(write_attempt))
    viewer_response = client.post("/api/v1/ai/requests", headers=viewer_headers, json={"text": "create project"})
    assert viewer_response.status_code == 200
    assert viewer_response.json()["kind"] == "error"
    assert "not allowed" in viewer_response.json()["message"]


def test_ai_expired_and_cross_user_proposals_cannot_execute(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    create_user("fund-a@example.test", Role.FUND_ADMINISTRATOR)
    create_user("fund-b@example.test", Role.FUND_ADMINISTRATOR)
    headers_a = login(client, "fund-a@example.test")
    headers_b = login(client, "fund-b@example.test")
    envelope = AIProviderEnvelope(
        kind="proposal",
        message="Create project proposal ready.",
        action="create_project",
        arguments={"project_code": "TRAI-AI-EXPIRED", "title": "Expired"},
    )
    monkeypatch.setattr(api_routes, "_ai_service", fake_ai_service(envelope))

    response = client.post("/api/v1/ai/requests", headers=headers_a, json={"text": "create project"})
    proposal_id = response.json()["proposal"]["id"]

    other_user = client.post(f"/api/v1/ai/proposals/{proposal_id}/confirm", headers=headers_b)
    assert other_user.status_code == 400

    with SessionLocal() as session:
        proposal = session.get(AIProposalModel, proposal_id)
        assert proposal is not None
        proposal.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

    expired = client.post(f"/api/v1/ai/proposals/{proposal_id}/confirm", headers=headers_a)
    assert expired.status_code == 200
    assert expired.json()["kind"] == "error"
    assert "expired" in expired.json()["message"]

    with SessionLocal() as session:
        assert session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-AI-EXPIRED")) is None


def test_project_import_preview_commit_and_repeat_duplicate_protection(client: TestClient) -> None:
    create_user("admin@example.test", Role.ADMINISTRATOR)
    admin_headers = login(client, "admin@example.test")
    content = csv_content(
        PROJECT_HEADERS,
        [[" trai-imp-001 ", "Imported Marathi प्रकल्प", "MIT ADT", "Engineering", "Mechanical", "2026-27", "A", "Active", "01/08/2026", "31-12-2026", "Dr Import", "Asha; Vivek", "Robotics", "4", "Prototype", "N/A"]],
    )

    preview = preview_import(client, admin_headers, "projects", "projects.csv", content)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["rowsDetected"] == 1
    assert body["validRows"] == 1
    assert body["proposedCreates"] == 1
    assert body["rows"][0]["normalizedValues"]["project_code"] == "TRAI-IMP-001"

    with SessionLocal() as session:
        assert session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-IMP-001")) is None
        assert session.scalar(select(ImportBatchModel).where(ImportBatchModel.id == body["id"])) is not None

    commit = client.post(f"/api/v1/imports/{body['id']}/commit", headers=admin_headers)
    assert commit.status_code == 200, commit.text
    committed = commit.json()
    assert committed["status"] == "committed"
    assert committed["committedRows"] == 1

    with SessionLocal() as session:
        project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-IMP-001"))
        assert project is not None
        assert project.title == "Imported Marathi प्रकल्प"
        assert session.scalar(select(ProjectParticipantModel).where(ProjectParticipantModel.project_id == project.id, ProjectParticipantModel.is_primary.is_(True))) is not None
        assert session.scalar(select(AuditEventModel).where(AuditEventModel.action == "commit_import")) is not None

    repeat = preview_import(client, admin_headers, "projects", "projects.csv", content)
    assert repeat.status_code == 200, repeat.text
    repeated = repeat.json()
    assert repeated["duplicateRows"] == 1
    assert repeated["proposedCreates"] == 0
    assert repeated["rows"][0]["status"] == "duplicate"


def test_import_preview_validation_for_sanctions_revisions_and_tranches(client: TestClient) -> None:
    create_user("admin@example.test", Role.ADMINISTRATOR)
    admin_headers = login(client, "admin@example.test")
    with SessionLocal() as session:
        project = ProjectModel(id=uuid(), project_code="TRAI-IMP-BASE", title="Import base", project_status="active")
        session.add(project)
        session.add(TrancheModel(id=uuid(), project_id=project.id, sequence_number=1, transaction_type="advance", requested_amount=Decimal("1000.00"), approved_amount=Decimal("1000.00")))
        session.commit()

    bad_header = preview_import(client, admin_headers, "projects", "bad.csv", "wrong,headers\n1,2\n")
    assert bad_header.status_code == 400
    assert "Invalid headers" in bad_header.text

    sanctions = preview_import(
        client,
        admin_headers,
        "funding_sanctions",
        "sanctions.csv",
        csv_content(
            SANCTION_HEADERS,
            [
                ["TRAI-IMP-BASE", "SAN-VALID", "01/08/2026", "₹1,00,000", "N/A", "2026-27", "submitted", "N/A"],
                ["TRAI-IMP-BASE", "SAN-EMPTY", "2026-08-01", "", "", "", "draft", ""],
                ["UNKNOWN", "SAN-UNKNOWN", "2026-08-01", "1000", "", "", "draft", ""],
                ["TRAI-IMP-BASE", "SAN-DATE", "not-a-date", "1000", "", "", "draft", ""],
            ],
        ),
    )
    assert sanctions.status_code == 200, sanctions.text
    sanction_body = sanctions.json()
    assert sanction_body["validRows"] == 1
    assert sanction_body["invalidRows"] == 3
    messages = " ".join(" ".join(row["errors"]) for row in sanction_body["rows"])
    assert "sanction_amount is required" in messages
    assert "Unknown project_code UNKNOWN" in messages
    assert "Invalid date" in messages
    assert sanction_body["rows"][0]["normalizedValues"]["sanction_amount"] == "100000.00"

    revisions = preview_import(
        client,
        admin_headers,
        "funding_revisions",
        "revisions.csv",
        csv_content(
            REVISION_HEADERS,
            [
                ["TRAI-IMP-BASE", 1, "Increase", "01-Aug-2026", "50,000", "REV-1", "More funding", "draft", ""],
                ["TRAI-IMP-BASE", 2, "Reduction", "2026-08-02", "25000", "REV-2", "Scope change", "draft", ""],
            ],
        ),
    )
    assert revisions.status_code == 200, revisions.text
    assert revisions.json()["validRows"] == 2

    tranches = preview_import(
        client,
        admin_headers,
        "tranches",
        "tranches.csv",
        csv_content(
            TRANCHE_HEADERS,
            [
                ["TRAI-IMP-BASE", 1, "Advance", "", "", "1000", "1000", "0", "0", "0", "2026-08-01", "", "", "", "", "draft", "", "", ""],
                ["TRAI-IMP-BASE", 2, "Advance", "", "", "₹5,000", "5000", "0", "0", "0", "2026-08-01", "", "", "", "", "draft", "", "", ""],
                ["TRAI-IMP-BASE", 2, "Advance", "", "", "₹5,000", "5000", "0", "0", "0", "2026-08-01", "", "", "", "", "draft", "", "", ""],
                ["TRAI-IMP-BASE", 3, "Advance", "", "", "1000", "2000", "0", "0", "0", "2026-08-01", "", "", "", "", "draft", "", "", ""],
            ],
        ),
    )
    assert tranches.status_code == 200, tranches.text
    tranche_body = tranches.json()
    assert tranche_body["validRows"] == 1
    assert tranche_body["duplicateRows"] == 2
    assert tranche_body["invalidRows"] == 1
    assert "approved_amount cannot exceed requested_amount" in str(tranche_body["rows"])


def test_import_commit_uses_financial_validation_and_reports_partial_failure(client: TestClient) -> None:
    create_user("admin@example.test", Role.ADMINISTRATOR)
    admin_headers = login(client, "admin@example.test")
    with SessionLocal() as session:
        project = ProjectModel(id=uuid(), project_code="TRAI-IMP-LIMIT", title="Import limit", project_status="active")
        session.add(project)
        session.add(FundingSanctionModel(id=uuid(), project_id=project.id, sanction_reference="SAN-LIMIT", amount=Decimal("100000.00"), status="approved"))
        session.commit()

    preview = preview_import(
        client,
        admin_headers,
        "tranches",
        "limit-tranches.csv",
        csv_content(
            TRANCHE_HEADERS,
            [
                ["TRAI-IMP-LIMIT", 1, "Advance", "", "", "70000", "70000", "0", "0", "0", "2026-08-01", "", "", "", "", "approved", "", "", ""],
                ["TRAI-IMP-LIMIT", 2, "Advance", "", "", "70000", "70000", "0", "0", "0", "2026-08-01", "", "", "", "", "approved", "", "", ""],
            ],
        ),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["validRows"] == 2

    commit = client.post(f"/api/v1/imports/{preview.json()['id']}/commit", headers=admin_headers)
    assert commit.status_code == 200, commit.text
    body = commit.json()
    assert body["status"] == "partial_failed"
    assert body["committedRows"] == 1
    assert body["failedRows"] == 1
    assert "available sanctioned balance" in str(body["rows"])

    with SessionLocal() as session:
        persisted_project = session.scalar(select(ProjectModel).where(ProjectModel.project_code == "TRAI-IMP-LIMIT"))
        assert persisted_project is not None
        tranches = list(session.scalars(select(TrancheModel).where(TrancheModel.project_id == persisted_project.id)))
        assert len(tranches) == 1
        assert tranches[0].status == "approved"
        assert tranches[0].approved_amount == Decimal("70000.00")
        assert session.scalar(select(AuditEventModel).where(AuditEventModel.action == "commit_import")) is not None


def test_competing_tranche_approvals_cannot_overrun_sanctioned_balance(client: TestClient) -> None:
    create_user("fund@example.test", Role.FUND_ADMINISTRATOR)
    create_user("reviewer@example.test", Role.FUND_REVIEWER)
    fund_headers = login(client, "fund@example.test")
    reviewer_headers = login(client, "reviewer@example.test")

    project = client.post("/api/v1/projects", headers=fund_headers, json={"project_code": "TRAI-RACE-001", "title": "Approval race"})
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    sanction = client.post(f"/api/v1/projects/{project_id}/sanctions", headers=fund_headers, json={"sanction_reference": "SAN-RACE-001", "amount": "100000.00"})
    assert sanction.status_code == 201
    assert client.post(f"/api/v1/sanctions/{sanction.json()['id']}/approve", headers=reviewer_headers).status_code == 200

    tranche_ids = []
    for sequence in [1, 2]:
        tranche = client.post(
            f"/api/v1/projects/{project_id}/tranches",
            headers=fund_headers,
            json={"sequence_number": sequence, "transaction_type": "advance", "requested_amount": "70000.00", "approved_amount": "70000.00"},
        )
        assert tranche.status_code == 201, tranche.text
        tranche_ids.append(tranche.json()["id"])
        assert client.post(f"/api/v1/tranches/{tranche.json()['id']}/submit", headers=fund_headers).status_code == 200

    def approve(tranche_id: str) -> int:
        return TestClient(app).post(f"/api/v1/tranches/{tranche_id}/approve", headers=reviewer_headers).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(approve, tranche_ids))

    assert statuses == [200, 400]
