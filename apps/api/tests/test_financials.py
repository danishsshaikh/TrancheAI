from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.core.enums import ProjectStatus, RevisionStatus, RevisionType, SanctionStatus, TrancheStatus
from app.services.financials import calculate_project_financials
from app.services.reconciliation import reconcile_project
from app.services.validation import DomainValidationError, validate_project_code_unique, validate_tranche


def project(**kwargs):
    values = {"id": "p1", "project_code": "TRAI-SYN-001", "title": "Synthetic", "project_status": "draft"}
    values.update(kwargs)
    return SimpleNamespace(**values)


def sanction(**kwargs):
    values = {"id": "s1", "project_id": "p1", "amount": Decimal("0.00"), "status": "draft"}
    values.update(kwargs)
    values["amount"] = Decimal(str(values["amount"])).quantize(Decimal("0.01"))
    return SimpleNamespace(**values)


def revision(**kwargs):
    values = {"id": "r1", "project_id": "p1", "amount": Decimal("0.00"), "revision_type": "increase", "status": "draft"}
    values.update(kwargs)
    values["amount"] = Decimal(str(values["amount"])).quantize(Decimal("0.01"))
    return SimpleNamespace(**values)


def tranche(**kwargs):
    values = {
        "id": "t1",
        "project_id": "p1",
        "sequence_number": 1,
        "requested_amount": Decimal("0.00"),
        "approved_amount": Decimal("0.00"),
        "disbursed_amount": Decimal("0.00"),
        "refund_amount": Decimal("0.00"),
        "utilized_amount": Decimal("0.00"),
        "status": "draft",
        "payment_reference": None,
        "payment_mode": None,
        "actual_disbursement_date": None,
    }
    values.update(kwargs)
    for key in ["requested_amount", "approved_amount", "disbursed_amount", "refund_amount", "utilized_amount"]:
        values[key] = Decimal(str(values[key])).quantize(Decimal("0.01"))
    return SimpleNamespace(**values)


class FinancialCalculationTests(unittest.TestCase):
    def test_approved_sanction_and_revisions_affect_totals(self) -> None:
        sanctions = [
            sanction(amount="100000", status=SanctionStatus.APPROVED),
            sanction(id="s2", amount="50000", status=SanctionStatus.DRAFT),
        ]
        revisions = [
            revision(amount="25000", revision_type=RevisionType.INCREASE, status=RevisionStatus.APPROVED),
            revision(id="r2", amount="10000", revision_type=RevisionType.REDUCTION, status=RevisionStatus.APPROVED),
            revision(id="r3", amount="9000", revision_type=RevisionType.INCREASE, status=RevisionStatus.DRAFT),
        ]
        summary = calculate_project_financials(sanctions, revisions, [])
        self.assertEqual(summary.initial_sanctioned_amount, Decimal("100000.00"))
        self.assertEqual(summary.approved_funding_increases, Decimal("25000.00"))
        self.assertEqual(summary.approved_funding_reductions, Decimal("10000.00"))
        self.assertEqual(summary.total_sanctioned_amount, Decimal("115000.00"))

    def test_multiple_tranches_refund_utilization_and_cancelled_exclusion(self) -> None:
        sanctions = [sanction(amount="300000", status=SanctionStatus.APPROVED)]
        tranches = [
            tranche(sequence_number=1, requested_amount="100000", approved_amount="100000", disbursed_amount="100000", refund_amount="5000", utilized_amount="40000", status=TrancheStatus.DISBURSED, actual_disbursement_date=date(2026, 1, 10)),
            tranche(id="t2", sequence_number=2, requested_amount="50000", approved_amount="50000", disbursed_amount="0", utilized_amount="0", status=TrancheStatus.APPROVED),
            tranche(id="t3", sequence_number=3, requested_amount="99999", approved_amount="99999", disbursed_amount="99999", status=TrancheStatus.CANCELLED),
        ]
        summary = calculate_project_financials(sanctions, [], tranches)
        self.assertEqual(summary.total_requested_amount, Decimal("150000.00"))
        self.assertEqual(summary.total_approved_tranche_amount, Decimal("150000.00"))
        self.assertEqual(summary.gross_disbursed_amount, Decimal("100000.00"))
        self.assertEqual(summary.total_refunded_amount, Decimal("5000.00"))
        self.assertEqual(summary.net_disbursed_amount, Decimal("95000.00"))
        self.assertEqual(summary.total_utilized_amount, Decimal("40000.00"))
        self.assertEqual(summary.available_sanctioned_balance, Decimal("205000.00"))
        self.assertEqual(summary.unutilized_disbursed_balance, Decimal("55000.00"))
        self.assertEqual(summary.pending_approved_amount, Decimal("50000.00"))
        self.assertEqual(summary.tranche_count, 2)

    def test_repeated_recalculation_is_stable(self) -> None:
        sanctions = [sanction(amount="100000", status=SanctionStatus.APPROVED)]
        tranches = [tranche(approved_amount="50000", disbursed_amount="50000", status=TrancheStatus.DISBURSED)]
        self.assertEqual(calculate_project_financials(sanctions, [], tranches), calculate_project_financials(sanctions, [], tranches))


class ValidationAndReconciliationTests(unittest.TestCase):
    def test_project_code_uniqueness(self) -> None:
        with self.assertRaises(DomainValidationError):
            validate_project_code_unique(project(project_code="TRAI-SYN-001"), {"TRAI-SYN-001"})

    def test_over_disbursement_and_duplicate_sequence_are_rejected(self) -> None:
        sanctions = [sanction(amount="100000", status=SanctionStatus.APPROVED)]
        existing = [tranche(id="existing", sequence_number=1, approved_amount="50000", status=TrancheStatus.APPROVED)]
        candidate = tranche(sequence_number=1, requested_amount="80000", approved_amount="120000", disbursed_amount="0", status=TrancheStatus.APPROVED)
        with self.assertRaises(DomainValidationError) as raised:
            validate_tranche(candidate, sanctions, [], existing, allow_approved_above_requested=True)
        codes = {issue.code for issue in raised.exception.issues}
        self.assertIn("duplicate_sequence", codes)
        self.assertIn("approval_exceeds_sanction", codes)

    def test_duplicate_payment_reference_is_rejected(self) -> None:
        sanctions = [sanction(amount="200000", status=SanctionStatus.APPROVED)]
        existing = [tranche(id="existing", sequence_number=1, approved_amount="50000", payment_reference="UTR-1", status=TrancheStatus.DISBURSED)]
        candidate = tranche(sequence_number=2, requested_amount="50000", approved_amount="50000", disbursed_amount="50000", payment_reference="UTR-1", actual_disbursement_date=date(2026, 2, 1), status=TrancheStatus.DISBURSED)
        with self.assertRaises(DomainValidationError) as raised:
            validate_tranche(candidate, sanctions, [], existing)
        self.assertIn("duplicate_payment_reference", {issue.code for issue in raised.exception.issues})

    def test_negative_reconciliation_state(self) -> None:
        project = globals()["project"](project_code="TRAI-SYN-002", project_status=ProjectStatus.ACTIVE)
        sanctions = [sanction(amount="100000", status=SanctionStatus.APPROVED)]
        revisions = [revision(amount="30000", revision_type=RevisionType.REDUCTION, status=RevisionStatus.APPROVED)]
        tranches = [tranche(approved_amount="90000", disbursed_amount="90000", status=TrancheStatus.DISBURSED)]
        issues = reconcile_project(project, sanctions, revisions, tranches)
        self.assertIn("over_disbursed", {issue.issue_type for issue in issues})


if __name__ == "__main__":
    unittest.main()
