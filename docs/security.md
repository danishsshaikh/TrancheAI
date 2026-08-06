# Security

Status: foundation implemented.

Threat model:

- Unauthorized financial changes: backend permissions and AI confirmation are required; frontend hiding is not enough.
- Malicious spreadsheet uploads: import preview validates headers and normalizes rows; commit flow must keep file-size and type checks.
- Duplicate imports: row fingerprints detect repeated rows.
- Prompt injection: AI actions are allowlisted and forbidden keys are rejected.
- Model hallucination: write proposals require user confirmation and domain validation.
- Compromised local AI endpoint: secrets are configured server-side and model output is treated as untrusted.
- Insecure server exposure: database and model endpoints must remain private.
- Leaked backups: backups must include encryption-key handling and restricted storage.
- Malicious public contribution: review dependencies, migrations and export code carefully.

Do not commit secrets, real spreadsheets, production exports, backup files or private financial data.

