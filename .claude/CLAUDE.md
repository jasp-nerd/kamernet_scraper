# Kamernet Scraper

## Architecture
- **Scraper**: `kamernet_scraper.py` — Python, runs as a Coolify app on a Hetzner VPS (`kamernet-scraper` app inside `kamernet` project, Coolify UI at https://coolify.jaspnerd.dev). Built from `Dockerfile`.
- **Dashboard**: `dashboard/` — Next.js 16, deployed on Vercel.
- **Database**: PostgreSQL 15 in Coolify on Hetzner. Publicly reachable with TLS at `db.jaspnerd.dev:5432`. Connection string lives in `dashboard/.env.local` as `DATABASE_URL`.
- **DB driver**: Dashboard uses `postgres` (porsager/postgres) — tagged-template API, supports `sql\`...\`` and `sql.unsafe(text, params)` for dynamic queries. Self-signed cert, so `ssl: { rejectUnauthorized: false }` in `src/lib/db.ts`.

## Parked legacy
- **Heroku** app `kamernet-monitor-jasp` is scaled to 0 (kept for rollback). No active scraping from Heroku.
- **Neon** project (`ep-icy-sea-a2no7wkr`, via Vercel integration) is parked with its last data intact. Compute is quota-gated so it's unreadable until quota resets — don't delete; use if you ever want to import historical listings.

## Database Access
```bash
export DATABASE_URL=$(grep '^DATABASE_URL=' dashboard/.env.local | cut -d'"' -f2) && python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT ...')
conn.close()
"
```

## Schema (4 tables)

### `listings` — core rental listings
Key columns: `listing_id` (PK), street, city, city_slug, street_slug, postal_code, total_rental_price, surface_area, listing_type, furnishing_id, detailed_title, detailed_description, ai_score (INTEGER), ai_score_reasoning (TEXT), first_seen_at, last_seen_at, disappeared_at

### `listing_snapshots` — price/surface tracking
- id, listing_id (FK), total_rental_price, surface_area, captured_at

### `scrape_runs` — scraper execution logs
- id, started_at, finished_at, total_found, new_found, errors

### `telegram_subscribers` — Telegram notification subscribers
- chat_id (PK), username, first_name, subscribed_at

## Key Features
- **AI Scoring**: OpenRouter API scores listings 0-100 via structured rubric. Primary model: `openai/gpt-oss-120b:free`, fallback: `deepseek/deepseek-v3.2`
- **Telegram**: Password-protected subscriber system. Users send `/start <password>` to subscribe, `/stop` to unsubscribe. Notifications sent for listings scoring >= threshold (default 80)
- **Discord**: Webhook notifications for all new listings. `DISCORD_WEBHOOK_URL` is optional — if unset, the scraper runs silently without Discord (still writes to DB).

## Coolify Env Vars
Set on the `kamernet-scraper` app in Coolify:
`DISCORD_WEBHOOK_URL` (optional), `DATABASE_URL`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PASSWORD` (defaults to a literal in code), `TELEGRAM_SCORE_THRESHOLD` (default 80), `CHECK_INTERVAL_MIN` (default 50), `CHECK_INTERVAL_MAX` (default 70), `TELEGRAM_CHAT_ID` (legacy single-user fallback).

`DATABASE_URL` for the scraper uses the internal Docker hostname (container-to-container). The dashboard's `DATABASE_URL` uses `db.jaspnerd.dev:5432` (public TLS endpoint).

## Kamernet Listing URLs
```
https://kamernet.nl/huren/{city_slug}/{street_slug}/{listing_id}
```

## Deployment
- **Scraper (Coolify)**: `git push origin main`. Coolify watches the GitHub repo and auto-deploys on new commits. To force a deploy: hit `GET https://coolify.jaspnerd.dev/api/v1/deploy?uuid=<app_uuid>&force=true` with the API token, or use the Coolify UI.
- **Dashboard (Vercel)**: `cd dashboard && vercel --prod` — Git auto-deploy does NOT work for this project, always deploy manually via CLI.
- **NEVER run `vercel` from the project root** — only from `dashboard/`. The Vercel project is "dashboard", not "kamernet_scraper".

## Important Notes
- The "Gone/disappeared" status is unreliable — listings that scroll off page 1 get marked gone but are still live on Kamernet. The status column was removed from the UI but `disappeared_at` remains in the DB for stats.
- Scraper only checks page 1 of results (sorted by newest).
- `requests` library is used for both OpenRouter and Telegram APIs (no extra dependencies).
