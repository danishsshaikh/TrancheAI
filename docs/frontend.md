# Frontend

Status: partially implemented.

Implemented screens:

- Dashboard.
- Projects list.
- Project detail shell.
- Tranche creation form.
- Reconciliation page.
- AI Assistant preview surface.

The current UI uses a mock adapter in `apps/web/src/api/client.ts` so the interface can be developed before the server is running. Server wiring remains required.

Design approach:

- Administrative layout with left navigation and top search.
- Dense tables for project and reconciliation work.
- Clear empty, error and loading states planned for API-connected screens.
- Standard form controls and restrained color.

