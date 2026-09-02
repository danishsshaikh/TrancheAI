# TrancheAI

TrancheAI is a standalone open-source fund-disbursement and project-funding management platform. A project is created once, and all sanctions, funding revisions, tranches, refunds, utilization updates and payment references attach to that canonical project record.

## Status

First working vertical slice implemented locally.

Implemented:

- FastAPI backend with SQLAlchemy models, Alembic migration and DB-backed API routes.
- Token-based login/logout/current-user endpoints with role checks.
- Project, sanction, funding-revision and tranche CRUD/workflow endpoints.
- Canonical Decimal-based financial calculation service.
- Validation and deterministic reconciliation services.
- CSV import preview with normalization and row fingerprints.
- CSV exports and structural XLSX workbook generation.
- AI assistant routes backed by an OpenAI-compatible provider, allowlisted actions, persisted conversations and confirmation proposals.
- Speech-to-text boundary preserving Marathi transcripts.
- Vue 3/Vite administrative shell using Frappe UI for login, dashboard, project workspaces, tranches, reconciliation, imports, exports, AI history and settings.
- Docker Compose server setup.
- Backend service tests plus PostgreSQL API integration tests.
- Frontend typecheck, tests and production build.

Server verification required:

- Live Gemma provider through the configured OpenAI-compatible endpoint.
- Live STT provider.
- Manual browser workflow on the deployment server.

## Stack

- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL.
- Frontend: Vue 3, TypeScript, Vite, Vue Router, Frappe UI and Tailwind CSS.
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
npm run typecheck
npm test
npm run build
```

## Server Run

Copy `.env.example` to `.env`, set real secrets, then run:

```bash
docker compose up --build -d db
docker compose run --rm api alembic upgrade head
docker compose up --build -d api web
```

See [docs/server-runbook.md](docs/server-runbook.md).

## AI Configuration

The assistant is disabled by default for safe local development. On the server, configure the OpenAI-compatible Gemma endpoint through environment variables:

```bash
AI_ENABLED=true
AI_BASE_URL=<openai-compatible-base-url>
AI_MODEL=<server-configured-model>
AI_API_KEY=
AI_TIMEOUT_SECONDS=60
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.1
```

The code does not call replica ports directly and does not hardcode a model name or provider URL.

## Project Structure

- `apps/api`: backend app, domain services, imports, exports, AI, speech, migrations and tests.
- `apps/web`: Vue/Frappe UI admin interface.
- `docs`: architecture, operations and security documentation.
- `scripts`: local and server helper scripts.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

TrancheAI is released under the Apache License 2.0. See [LICENSE](LICENSE) and [docs/licensing-decision.md](docs/licensing-decision.md).
