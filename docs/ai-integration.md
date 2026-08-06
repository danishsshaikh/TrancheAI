# AI Integration

Status: foundation implemented, live provider verification required.

Implemented:

- Provider protocol.
- Fake provider for tests.
- Allowlisted actions.
- Forbidden payload-key checks for SQL, arbitrary methods, filesystem paths and Python execution.
- Confirmation requirement for write proposals.
- Audit events for previews and confirmations.

The AI does not write directly to records. A confirmed proposal returns an accepted action for normal domain services.

Environment:

- `AI_ENABLED`
- `AI_BASE_URL`
- `AI_MODEL`
- `AI_API_KEY`
- `AI_TIMEOUT_SECONDS`
- `AI_MAX_TOKENS`

