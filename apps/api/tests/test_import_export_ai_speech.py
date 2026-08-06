from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from zipfile import ZipFile

from app.ai.provider import FakeAIProvider
from app.ai.proposal_service import AIProposalService
from app.ai.schemas import AIProposal
from app.core.enums import Role, SanctionStatus, TrancheStatus
from app.exports.csv_export import project_master_csv, tranche_register_csv
from app.exports.rows import ProjectExportRecord, TrancheExportRecord
from app.exports.xlsx_export import project_master_xlsx, tranche_register_xlsx
from app.imports.csv_importer import PROJECT_HEADERS, TRANCHE_HEADERS, preview_csv
from app.services.audit import AuditRecorder
from app.services.domain import FundingSanction, Project, Tranche
from app.services.financials import calculate_project_financials
from app.services.permissions import Actor
from app.speech.provider import FakeSTTProvider
from app.speech.schemas import SpeechTranscript
from app.speech.stt_service import SpeechService


class ImportTests(unittest.TestCase):
    def test_import_preview_normalizes_values_and_does_not_commit(self) -> None:
        csv_content = ",".join(PROJECT_HEADERS) + "\n" + " trai-syn-001 ,Synthetic Marathi प्रकल्प,Institute,School,Dept,2026-27,A,Active,01/08/2026,31-12-2026,Dr Test,Asha; Vivek,Robotics,4,Prototype,N/A\n"
        preview = preview_csv("projects", csv_content)
        self.assertTrue(preview.valid)
        self.assertEqual(preview.rows[0].normalized_values["project_code"], "TRAI-SYN-001")
        self.assertEqual(preview.rows[0].normalized_values["project_status"], "active")
        self.assertEqual(preview.rows[0].normalized_values["remarks"], None)

    def test_duplicate_import_fingerprint_is_flagged(self) -> None:
        csv_content = ",".join(TRANCHE_HEADERS) + "\n" + "TRAI-SYN-001,1,Advance,PO-1,2026-08-01,\"₹50,000\",50000,0,0,0,2026-08-01,,,,UTR-1,draft,pending,pending,\n"
        first = preview_csv("tranches", csv_content)
        second = preview_csv("tranches", csv_content, {first.rows[0].row_fingerprint})
        self.assertTrue(second.rows[0].duplicate)
        self.assertIn("already imported", second.rows[0].warnings[0])


class ExportTests(unittest.TestCase):
    def _records(self) -> tuple[list[ProjectExportRecord], list[TrancheExportRecord]]:
        project = Project(id="p1", project_code="TRAI-SYN-001", title="Synthetic Marathi प्रकल्प", school="School", department="Dept")
        sanctions = [FundingSanction(project_id="p1", amount="100000", status=SanctionStatus.APPROVED)]
        tranches = [
            Tranche(project_id="p1", sequence_number=2, requested_amount="25000", approved_amount="25000", disbursed_amount="0", status=TrancheStatus.APPROVED),
            Tranche(project_id="p1", sequence_number=1, requested_amount="50000", approved_amount="50000", disbursed_amount="50000", status=TrancheStatus.DISBURSED, payment_reference="UTR-1", actual_disbursement_date=date(2026, 8, 1)),
        ]
        summary = calculate_project_financials(sanctions, [], tranches)
        return [ProjectExportRecord(project, summary, "Dr Synthetic")], [TrancheExportRecord(project, summary, tranches, "Dr Synthetic")]

    def test_csv_column_order_and_unicode(self) -> None:
        project_records, tranche_records = self._records()
        project_csv = project_master_csv(project_records)
        self.assertTrue(project_csv.startswith("Project Code,Project Title,Institution"))
        self.assertIn("Synthetic Marathi प्रकल्प", project_csv)
        tranche_csv = tranche_register_csv(tranche_records)
        self.assertTrue(tranche_csv.splitlines()[0].startswith("Serial Number,Project Code,Project Title"))

    def test_xlsx_xml_contains_expected_structure(self) -> None:
        project_records, tranche_records = self._records()
        data = tranche_register_xlsx(tranche_records)
        import io

        with ZipFile(io.BytesIO(data)) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            styles_xml = archive.read("xl/styles.xml").decode("utf-8")
        self.assertIn('name="Tranche Register"', workbook_xml)
        self.assertIn('mergeCell ref="A1:U1"', sheet_xml)
        self.assertIn('topLeftCell="A5"', sheet_xml)
        self.assertIn("₹#,##0.00", styles_xml)
        self.assertIn("<v>1</v>", sheet_xml)
        self.assertIn("<v>2</v>", sheet_xml)


class AIAndSpeechTests(unittest.TestCase):
    def test_ai_proposal_does_not_execute_before_confirmation(self) -> None:
        audit = AuditRecorder()
        provider = FakeAIProvider(AIProposal(action="propose_tranche_creation", payload={"project_code": "TRAI-SYN-001", "approved_amount": "50000"}, confidence=0.9))
        service = AIProposalService(provider, audit)
        actor = Actor("admin", {Role.ADMINISTRATOR})
        preview = service.preview("Add tranche", actor)
        self.assertTrue(preview.allowed)
        self.assertEqual(len(audit.events), 1)
        result = service.confirm(preview, actor)
        self.assertEqual(result["status"], "accepted_for_domain_service")
        self.assertEqual(len(audit.events), 2)

    def test_ai_rejects_arbitrary_action_and_viewer_write(self) -> None:
        provider = FakeAIProvider(AIProposal(action="drop_database", payload={"sql": "select * from users"}, confidence=1.0, requires_confirmation=False))
        service = AIProposalService(provider, AuditRecorder())
        preview = service.preview("bad", Actor("viewer", {Role.VIEWER}))
        self.assertFalse(preview.allowed)
        self.assertTrue(any("Unknown AI action" in error for error in preview.errors))

    def test_speech_preserves_marathi_transcript(self) -> None:
        transcript = SpeechTranscript(original_transcript="माझा प्रकल्प दाखवा", detected_language="mr-IN", translated_text="Show my project")
        result = SpeechService(FakeSTTProvider(transcript)).transcribe(b"audio", "audio/wav")
        self.assertEqual(result.original_transcript, "माझा प्रकल्प दाखवा")
        self.assertEqual(result.detected_language, "mr-IN")
        self.assertEqual(result.translated_text, "Show my project")

    def test_speech_rejects_invalid_audio_type(self) -> None:
        with self.assertRaises(ValueError):
            SpeechService(FakeSTTProvider()).transcribe(b"audio", "text/plain")


if __name__ == "__main__":
    unittest.main()
