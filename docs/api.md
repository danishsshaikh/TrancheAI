# API

Status: partially implemented.

Implemented route module: `apps/api/app/api/v1/routes.py`.

Current endpoints:

- `GET /api/v1/health`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}/summary`
- `GET /api/v1/projects/{project_id}/reconciliation`
- `GET /api/v1/reports/project-master`
- `GET /api/v1/exports/project-master.csv`
- `GET /api/v1/exports/project-master.xlsx`
- `GET /api/v1/exports/tranche-register.csv`
- `GET /api/v1/exports/tranche-register.xlsx`

Remaining work:

- Replace the in-memory route store with SQLAlchemy repositories.
- Add authentication dependencies on every route.
- Add full CRUD for participants, sanctions, revisions and tranches.
- Add pagination metadata and complete report filters.

