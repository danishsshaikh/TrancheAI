# Local Development

The user intends to code and run automated tests locally, with full manual runtime testing on the server.

Backend service tests:

```bash
scripts/run-local-backend-tests.sh
```

Backend install when network access is available:

```bash
cd apps/api
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
mypy app
```

Frontend install when network access is available:

```bash
cd apps/web
npm install
npm test
npm run build
```

Do not use real institutional spreadsheets for local tests. Use the synthetic fixtures in tests.

