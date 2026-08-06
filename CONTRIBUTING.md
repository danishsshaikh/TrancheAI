# Contributing

Use small, reviewed changes.

1. Open an issue or describe the behavior being changed.
2. Keep financial rules in backend services, not in UI components.
3. Add tests for new validation, calculation, import, export or permission behavior.
4. Do not commit real institutional spreadsheets, financial data, secrets or personal information.
5. Run local checks before sending a change:

```bash
scripts/run-local-backend-tests.sh
cd apps/web && npm test && npm run build
```

Server-only checks are documented in `docs/server-runbook.md`.

