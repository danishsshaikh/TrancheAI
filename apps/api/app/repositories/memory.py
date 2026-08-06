from __future__ import annotations

from dataclasses import dataclass, field

from app.services.domain import FundingRevision, FundingSanction, Project, Tranche


@dataclass
class InMemoryStore:
    projects: dict[str, Project] = field(default_factory=dict)
    sanctions: dict[str, FundingSanction] = field(default_factory=dict)
    revisions: dict[str, FundingRevision] = field(default_factory=dict)
    tranches: dict[str, Tranche] = field(default_factory=dict)
    row_fingerprints: set[str] = field(default_factory=set)

    def add_project(self, project: Project) -> Project:
        self.projects[project.id] = project
        return project

    def project_by_code(self, code: str) -> Project | None:
        return next((p for p in self.projects.values() if p.project_code == code), None)

    def project_financial_records(self, project_id: str) -> tuple[list[FundingSanction], list[FundingRevision], list[Tranche]]:
        sanctions = [s for s in self.sanctions.values() if s.project_id == project_id]
        revisions = [r for r in self.revisions.values() if r.project_id == project_id]
        tranches = [t for t in self.tranches.values() if t.project_id == project_id]
        return sanctions, revisions, tranches
