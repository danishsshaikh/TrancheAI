# Imports

Status: CSV preview implemented.

Implemented:

- Canonical CSV templates for projects, funding sanctions, funding revisions and tranches.
- Strict header validation.
- Row normalization for whitespace, dates, currency, null markers and controlled values.
- Stable file and row fingerprints.
- Duplicate row detection.
- Preview does not commit records.

Remaining work:

- Transaction-safe commit to PostgreSQL.
- Import history tables and conflict resolution UI.
- XLSX import after CSV commit flow is stable.

