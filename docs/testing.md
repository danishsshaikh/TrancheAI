# Testing

Implemented local backend tests:

- Financial calculations.
- Validation failures.
- Reconciliation issue detection.
- CSV import preview and duplicate fingerprints.
- CSV exports and Unicode preservation.
- XLSX workbook structure.
- AI provider structured-output validation.
- AI disabled, malformed response and malicious action handling.
- AI proposal confirmation boundary.
- Speech transcript preservation and audio validation.

Frontend tests:

- Project table rendering.
- Empty state.
- AI assistant answers, proposal confirm/cancel states and disabled-provider handling.
- Project-detail launch into the assistant with project context.

Server verification required:

- PostgreSQL migration.
- API persistence.
- AI proposal persistence, ownership checks, expiry handling and domain-service execution.
- Live Gemma endpoint at `AI_BASE_URL=http://127.0.0.1:3001/v1`.
- Full frontend build.
- Browser and Playwright workflows.
