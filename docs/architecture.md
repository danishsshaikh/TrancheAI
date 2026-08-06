# Architecture

Status: partially implemented.

TrancheAI is a standalone monorepo.

- `apps/api/app/api`: versioned FastAPI routes.
- `apps/api/app/models`: SQLAlchemy persistence models.
- `apps/api/app/schemas`: Pydantic request and response schemas.
- `apps/api/app/services`: domain services for financial calculations, validation, reconciliation, permissions and audit.
- `apps/api/app/imports`: canonical import templates, normalization and preview.
- `apps/api/app/exports`: CSV and XLSX export generation.
- `apps/api/app/ai`: provider-neutral AI proposals and confirmation guardrails.
- `apps/api/app/speech`: STT provider boundary and transcript handling.
- `apps/web`: React administrative interface.

The financial calculation service is the canonical source for project totals. API routes, reports and exports must call it rather than reimplementing totals.

