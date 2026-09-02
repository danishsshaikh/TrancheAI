# Frontend

Status: implemented source for server validation.

Implemented screens:

- Dashboard.
- Projects list.
- Project detail workspace.
- Tranche register.
- Reconciliation page.
- Imports and exports.
- AI assistant with persisted conversation history.
- Settings, profile and user administration.

The current UI uses `apps/web/src/api/client.ts` to call the FastAPI server directly. Authentication state is held in a Vue composable, and protected pages require a bearer token from `/api/v1/auth/login`.

Design approach:

- Administrative layout with left navigation and top search.
- Dense tables for project and reconciliation work.
- Frappe UI components for buttons, dialogs, dropdowns, badges and form controls.
- Clear empty, error and loading states for API-connected screens.
- Restrained color with project-first workflow density.
