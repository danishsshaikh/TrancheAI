# Ports and Networking

Defaults:

- Web: `WEB_PORT=3100`
- API: `API_PORT=8100`
- PostgreSQL host mapping: `POSTGRES_PORT=5433`
- PostgreSQL container port: `5432`
- Local AI endpoint: `AI_BASE_URL=http://host.docker.internal:11434/v1`
- STT endpoint: `STT_BASE_URL`

Production guidance:

- Do not expose PostgreSQL to the internet.
- Put API and web behind a reverse proxy with HTTPS.
- Limit firewall ingress to HTTP/HTTPS and SSH from trusted networks.
- Keep AI and STT endpoints private.
- On Linux, add Docker host gateway support if `host.docker.internal` is not available.

