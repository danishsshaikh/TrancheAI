# Frontend

Status: partially implemented.

Implemented screens:

- Dashboard.
- Projects list.
- Project detail shell.
- Tranche creation form.
- Reconciliation page.
- AI Assistant preview surface.

The current UI uses `apps/web/src/api/client.ts` to call the FastAPI server directly. Authentication state is held in `AuthContext`, and protected pages require a bearer token from `/api/v1/auth/login`.

Design approach:

- Administrative layout with left navigation and top search.
- Dense tables for project and reconciliation work.
- Clear empty, error and loading states planned for API-connected screens.
- Standard form controls and restrained color.
