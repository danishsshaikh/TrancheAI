# API

Status: first working administrative vertical slice.

Implemented route module: `apps/api/app/api/v1/routes.py`.

Current endpoints:

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/ai/requests`
- `GET /api/v1/ai/proposals/{proposal_id}`
- `POST /api/v1/ai/proposals/{proposal_id}/confirm`
- `POST /api/v1/ai/proposals/{proposal_id}/cancel`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `GET /api/v1/projects/{project_id}/summary`
- `GET /api/v1/projects/{project_id}/audit`
- `GET /api/v1/projects/{project_id}/timeline`
- `GET /api/v1/projects/{project_id}/sanctions`
- `POST /api/v1/projects/{project_id}/sanctions`
- `POST /api/v1/sanctions/{sanction_id}/submit`
- `POST /api/v1/sanctions/{sanction_id}/approve`
- `GET /api/v1/projects/{project_id}/funding-revisions`
- `POST /api/v1/projects/{project_id}/funding-revisions`
- `POST /api/v1/funding-revisions/{revision_id}/submit`
- `POST /api/v1/funding-revisions/{revision_id}/approve`
- `GET /api/v1/projects/{project_id}/tranches`
- `POST /api/v1/projects/{project_id}/tranches`
- `GET /api/v1/tranches`
- `GET /api/v1/tranches/{tranche_id}`
- `POST /api/v1/tranches/{tranche_id}/submit`
- `POST /api/v1/tranches/{tranche_id}/approve`
- `POST /api/v1/tranches/{tranche_id}/reject`
- `POST /api/v1/tranches/{tranche_id}/disburse`
- `POST /api/v1/tranches/{tranche_id}/record-refund`
- `POST /api/v1/tranches/{tranche_id}/record-utilization`
- `POST /api/v1/tranches/{tranche_id}/cancel`
- `GET /api/v1/reports/project-master`
- `GET /api/v1/reports/tranche-register`
- `GET /api/v1/reports/reconciliation`
- `GET /api/v1/imports/templates/{import_type}.csv`
- `POST /api/v1/imports/preview`
- `GET /api/v1/imports/{batch_id}`
- `GET /api/v1/imports/{batch_id}/rows`
- `POST /api/v1/imports/{batch_id}/commit`
- `GET /api/v1/exports/project-master.csv`
- `GET /api/v1/exports/project-master.xlsx`
- `GET /api/v1/exports/tranche-register.csv`
- `GET /api/v1/exports/tranche-register.xlsx`

Remaining work:

- Add pagination metadata and complete report filters.
- Add bulk import update support after review rules are specified.
- Validate live Gemma and STT providers on the deployment server.

AI response shapes:

- Assistant requests return `{ kind, message }` plus optional `data`, `download_url` or `proposal`.
- Write proposals are persisted and must be confirmed through `/api/v1/ai/proposals/{proposal_id}/confirm`.
- Confirmation responses use the same workflow validation as manual project, tranche and funding routes.
