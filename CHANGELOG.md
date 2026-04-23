# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — Open-source relaunch

First public release under the **Kamernet Radar** name.

### Added
- **`radar/` Python package** replacing the single monolithic `kamernet_scraper.py`. Modules: `config`, `profile`, `fetch`, `db`, `ai`, `scheduler`, `cli`, `notify/{discord,telegram,apprise}`.
- **Apprise notifier** (`APPRISE_URLS`). One env var for Slack, ntfy, email, Pushover, Matrix, WhatsApp via Twilio, and 100+ other channels.
- **Profile system.** Search criteria and scoring rubric live in `profiles/*.yaml`. Four shipped: `generic`, `student-amsterdam`, `young-professional-randstad`, `family-utrecht`.
- **CLI.** `python -m radar run`, `init-db`, `list-profiles`, plus `--once`, `--dry-run`, `--profile` flags.
- **docker-compose.yml.** db + scraper + optional dashboard profile.
- **Dashboard Dockerfile** with Next.js standalone output.
- **Optional dashboard password gate** via `DASHBOARD_PASSWORD` env var (Next.js 16 proxy).
- **`.env.example`** documenting each env var.
- **LICENSE** (MIT), **CONTRIBUTING.md**, **CODE_OF_CONDUCT.md**, **SECURITY.md**, **docs/PROFILES.md**, **docs/NOTIFICATIONS.md**, **docs/DEPLOYMENT.md**.
- **Pydantic-settings** for env validation. Loud errors on misconfiguration.
- **psycopg3** replaces `psycopg2-binary`.
- **GitHub issue / PR templates**, **CI** via GitHub Actions (ruff + pytest).

### Changed
- Schema: `ai_score` and `ai_score_reasoning` columns inlined (were commented-out migrations).
- Dockerfile: non-root user, health check, no Heroku or Coolify assumptions.
- README: full rewrite. Quick-start in three flavors, legal disclaimer, contributing call-to-action.
- Repo name: `kamernet_scraper` → `kamernet-radar`.

### Removed
- **Heroku artifacts** (`Procfile`, `HEROKU_DEPLOYMENT.md`).
- **Legacy helper scripts** (`get_telegram_chat_id.py`, superseded by the subscriber flow).
- **Personal data leakage**: Telegram password default, Amsterdam-specific hardcoded search URL, VU-specific scoring rubric embedded in Python.
- **`seen_listings.json`** file fallback. The database is now the single source of truth.

### Security
- The Telegram notifier refuses to start without `TELEGRAM_PASSWORD` set. No more open public subscription bots.
- The dashboard supports `DASHBOARD_PASSWORD` for a password gate.
