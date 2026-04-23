# Kamernet Radar dashboard

The optional Next.js dashboard for [Kamernet Radar](../README.md). Visualizes listings, analytics, and listing history from the scraper's Postgres database.

## Run locally

```bash
cp .env.example .env.local   # set DATABASE_URL (and optionally DASHBOARD_PASSWORD)
npm install
npm run dev                  # → http://localhost:3000
```

## Run with Docker

From the repo root:

```bash
docker compose --profile dashboard up
```

This brings up `db + scraper + dashboard`. The dashboard binds to `127.0.0.1:3000`.

## Environment

| Variable             | Required | Description                                                        |
| -------------------- | -------- | ------------------------------------------------------------------ |
| `DATABASE_URL`       | yes      | Postgres connection string.                                        |
| `DASHBOARD_PASSWORD` | no       | If set, each route requires login. If unset, the dashboard is open. |

See the main [project README](../README.md) and [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for full details.
