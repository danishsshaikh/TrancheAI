from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.enums import Role
from app.db.session import SessionLocal
from app.main import app
from app.models.domain import (
    AuditEventModel,
    AuthSessionModel,
    FundingRevisionModel,
    FundingSanctionModel,
    ProjectModel,
    TrancheModel,
    UserModel,
)
from app.services.security import hash_password
from app.services.workflow import uuid


@pytest.fixture(autouse=True)
def clean_database():
    with SessionLocal() as session:
        for model in [AuditEventModel, TrancheModel, FundingRevisionModel, FundingSanctionModel, ProjectModel, AuthSessionModel, UserModel]:
            session.execute(delete(model))
        session.commit()
    yield
    with SessionLocal() as session:
        for model in [AuditEventModel, TrancheModel, FundingRevisionModel, FundingSanctionModel, ProjectModel, AuthSessionModel, UserModel]:
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
            "school": "Engineering",
            "department": "Mechanical",
            "academic_year": "2026-27",
            "project_status": "active",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]

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
        json={"sequence_number": 1, "transaction_type": "advance", "requested_amount": "60000.00", "approved_amount": "60000.00"},
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


def test_readonly_roles_cannot_modify_records(client: TestClient) -> None:
    create_user("viewer@example.test", Role.VIEWER)
    create_user("auditor@example.test", Role.AUDITOR)
    viewer_headers = login(client, "viewer@example.test")
    auditor_headers = login(client, "auditor@example.test")
    assert client.post("/api/v1/projects", headers=viewer_headers, json={"project_code": "NOPE", "title": "Nope"}).status_code == 403
    assert client.post("/api/v1/projects", headers=auditor_headers, json={"project_code": "NOPE2", "title": "Nope"}).status_code == 403


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
