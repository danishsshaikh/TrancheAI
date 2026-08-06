# TrancheAI

TrancheAI is a standalone open-source fund-disbursement and project-funding management platform. A project is created once, and all sanctions, funding revisions, tranches, refunds, utilization updates and payment references attach to that canonical project record.

## Status

Partially implemented.

Implemented:

- FastAPI backend structure with SQLAlchemy models and Alembic migration.
- Canonical Decimal-based financial calculation service.
- Validation and deterministic reconciliation services.
- CSV import preview with normalization and row fingerprints.
- CSV exports and structural XLSX workbook generation.
- AI proposal boundary with allowlisted actions and confirmation flow.
- Speech-to-text boundary preserving Marathi transcripts.
- React/Vite administrative shell with dashboard, projects, tranche form, reconciliation and AI pages.
- Docker Compose server setup.
- Local backend service tests that do not require Docker or PostgreSQL.

Server verification required:

- PostgreSQL migrations against a live database.
- Full API persistence wiring.
- Frontend build and browser workflows after dependencies are installed.
- Live AI and STT providers.

## Stack

- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL.
- Frontend: React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS, React Hook Form, Zod.
- Tests: Python `unittest`/pytest-compatible backend tests, Vitest frontend tests.
- Infrastructure: Docker Compose with PostgreSQL, API and web services.

## Local Tests

```bash
scripts/run-local-backend-tests.sh
```

Frontend tests require installed npm dependencies:

```bash
cd apps/web
npm install
npm test
```

## Server Run

Copy `.env.example` to `.env`, set real secrets, then run:

```bash
docker compose up --build -d db
docker compose run --rm api alembic upgrade head
docker compose up --build -d api web
```

See [docs/server-runbook.md](docs/server-runbook.md).

## Project Structure

- `apps/api`: backend app, domain services, imports, exports, AI, speech, migrations and tests.
- `apps/web`: React admin interface.
- `docs`: architecture, operations and security documentation.
- `scripts`: local and server helper scripts.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A final project license has not been chosen; see [docs/licensing-decision.md](docs/licensing-decision.md).

