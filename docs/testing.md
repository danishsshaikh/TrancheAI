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

- UI formatting utilities for money, empty fields and human labels.
- Server-side frontend typecheck, unit tests and production build are still required after dependency install.

Server verification required:

- PostgreSQL migration.
- API persistence.
- AI proposal persistence, ownership checks, expiry handling and domain-service execution.
- Live OpenAI-compatible model endpoint through the server-configured `AI_BASE_URL`.
- Full frontend build.
- Browser and Playwright workflows.
