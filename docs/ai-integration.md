# AI Integration

Status: implementation complete in code; live provider validation pending server execution.

TrancheAI uses an OpenAI-compatible chat completions provider configured entirely through environment variables. The application does not call model replica ports directly and does not hardcode a provider URL or model name.

Environment:

- `AI_ENABLED=false`
- `AI_BASE_URL=`
- `AI_MODEL=`
- `AI_API_KEY=`
- `AI_TIMEOUT_SECONDS=60`
- `AI_MAX_TOKENS=2048`
- `AI_TEMPERATURE=0.1`

Implemented backend flow:

- `POST /api/v1/ai/requests` accepts authenticated assistant requests with optional project context.
- Provider output must be strict JSON with `kind`, `message`, `action` and `arguments`.
- Actions are validated against a server-side registry.
- AI conversations and messages are persisted in `ai_conversations` and `ai_messages`.
- Forbidden keys such as SQL, Python, dynamic methods and filesystem paths are rejected recursively.
- Read actions execute immediately when the role has permission.
- Write actions create rows in `ai_proposals` and do not mutate project data until confirmed.
- Confirmation re-checks proposal ownership, expiry, role permissions, current database state and domain workflow validation.
- Confirmed writes call the same domain services as manual API actions.
- Preview, cancel, failure and confirmation actions are audited.

Implemented actions:

- Read: `search_projects`, `get_project`, `get_project_financial_summary`, `summarize_project`, `list_reconciliation_issues`.
- Export links: `generate_project_master_export`, `generate_tranche_register_export`.
- Proposed writes: `create_project`, `update_project`, `create_tranche`, `create_funding_revision`, `record_refund`, `record_utilization`, `record_disbursement`, `approve_tranche`.

Frontend:

- `/ai` provides the assistant thread, structured result rendering and proposal confirm/cancel controls.
- Project detail pages link to `/ai` with `projectId` and `projectCode` context.

Validation still required on the deployment server:

- Start the real API/web stack and PostgreSQL.
- Set `AI_ENABLED=true`, `AI_BASE_URL` and the actual `AI_MODEL`.
- Send read, export and write-proposal requests through the configured endpoint.
- Confirm that Marathi and mixed English/Marathi prompts return valid JSON envelopes.
