# Server Runbook

1. Copy `.env.example` to `.env`.
2. Replace every `change-me` value with server-only secrets.
3. Start PostgreSQL:

```bash
docker compose up --build -d db
```

4. Run migrations:

```bash
docker compose run --rm api alembic upgrade head
```

5. Start API and web:

```bash
docker compose up --build -d api web
```

6. Check health:

```bash
curl http://localhost:${API_PORT:-8100}/api/v1/health
```

7. Run backend tests in the API container:

```bash
docker compose run --rm api pytest
```

8. Run frontend tests and build in the web source directory before image build:

```bash
cd apps/web
npm install
npm test
npm run build
```

Manual scenarios:

- Create a project.
- Add an approved sanction.
- Add a funding increase.
- Add two tranches.
- Disburse one tranche.
- Record a refund and utilization.
- Verify the project summary.
- Reject an over-disbursement.
- Generate project master CSV and XLSX.
- Generate tranche register CSV and XLSX.
- Verify protected routes reject anonymous requests.
- Verify read-only users cannot modify projects or funding records.
- Verify Marathi speech transcripts remain editable before AI submission when that provider is enabled.
