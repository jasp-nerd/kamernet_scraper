<div align="center">

# 📡 Kamernet Radar

**Real-time Kamernet rental listing scraper with LLM-powered scoring and notifications anywhere.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![Docker ready](https://img.shields.io/badge/docker-ready-2496ED.svg)](./Dockerfile)
[![Apprise-powered](https://img.shields.io/badge/apprise-100%2B_channels-ff6600.svg)](https://github.com/caronc/apprise)

<sub>Self-hostable. Not affiliated with Kamernet B.V. Educational / personal use.</sub>

</div>

---

Finding a place to rent on [Kamernet.nl](https://kamernet.nl) is brutal. Good listings vanish in minutes. **Kamernet Radar** watches the site for you, scores each new listing against your preferences with a local or free LLM, and pings you the moment something good drops. Choose Discord, Telegram, WhatsApp, ntfy, email, Slack, or any of 100+ other channels.

## What it does

- 🔍 **Polite, robots.txt-compliant scraping.** Public HTML pages only, rate-limited, with a transparent User-Agent.
- 🤖 **LLM scoring 0–100** via [OpenRouter](https://openrouter.ai) (free models work). Rubrics live in editable YAML.
- 📬 **Notify anywhere.** Native Discord rich embeds, Telegram with a password-gated subscriber flow, or Apprise for 100+ channels.
- 🎯 **Preset profiles.** `student-amsterdam`, `young-professional-randstad`, `family-utrecht`, `generic`. Copy and tweak.
- 📊 **Optional Next.js dashboard.** Filter, sort, chart, and drill into listings. Runs locally.
- 🐳 **Docker-first.** `docker compose up` and you're running.
- 🗃️ **Postgres-backed.** Full listing history, price snapshots, scrape audit log.

## Quick start

<details open>
<summary><b>Option A: Docker (recommended)</b></summary>

```bash
git clone https://github.com/YOUR_USERNAME/kamernet-radar
cd kamernet-radar
cp .env.example .env               # edit at least APPRISE_URLS or DISCORD_WEBHOOK_URL
docker compose up -d db            # start Postgres
docker compose run --rm scraper init-db   # one-time schema bootstrap
docker compose up scraper          # start scraping
```

Want the dashboard too?

```bash
docker compose --profile dashboard up
# → http://127.0.0.1:3000
```

</details>

<details>
<summary><b>Option B: Terminal only (no Docker)</b></summary>

Requires Python 3.10+ and access to a Postgres instance.

```bash
git clone https://github.com/YOUR_USERNAME/kamernet-radar
cd kamernet-radar

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # edit DATABASE_URL + one notification channel
python -m radar init-db            # run schema.sql
python -m radar run                # scrape forever
```

One-shot dry-run (skips notifications and DB writes, handy for tuning your profile):

```bash
python -m radar run --once --dry-run --profile student-amsterdam
```

</details>

<details>
<summary><b>Option C: No notifications, database only</b></summary>

Leave every notifier env var blank. The scraper writes to Postgres silently. Pair it with the dashboard for a private searchable archive.

</details>

## Configuration

Environment variables (or `.env`) control behavior. Full list with comments: **[`.env.example`](./.env.example)**.

| Variable                                    | Required | Purpose                                                         |
| ------------------------------------------- | :------: | --------------------------------------------------------------- |
| `DATABASE_URL`                              |    ✖️    | Postgres connection. Without it, no persistence.                |
| `PROFILE`                                   |    ✖️    | Profile name (default: `generic`).                              |
| `OPENROUTER_API_KEY`                        |    ✖️    | Enables AI scoring. Free tier works fine.                       |
| `DISCORD_WEBHOOK_URL`                       |    ✖️    | Native Discord rich-embed notifications.                        |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_PASSWORD`  |    ✖️    | Telegram bot with `/start <password>` subscription.             |
| `APPRISE_URLS`                              |    ✖️    | Any of 100+ channels (Slack, ntfy, WhatsApp, email, Pushover).  |
| `CHECK_INTERVAL_MIN/MAX`                    |    ✖️    | Seconds between checks (randomized, default 50-70).             |

Configure at least one notification channel, otherwise listings go to the database silently. None are required.

## Scoring profiles

A profile controls two things: what gets scraped (city, radius, price cap) and how the LLM scores listings. Four ship out of the box:

| Profile                        | Who it's for                                                    |
| ------------------------------ | --------------------------------------------------------------- |
| `generic`                      | Neutral universal defaults. Start here.                         |
| `student-amsterdam`            | Two students/young adults near VU Amsterdam, budget ~€2000/mo.  |
| `young-professional-randstad`  | Solo professional, €1800–2500, Randstad-wide.                   |
| `family-utrecht`               | Family of 4, Utrecht + suburbs, 2+ bedrooms, long-term only.    |

Writing your own takes two minutes of YAML. See **[`docs/PROFILES.md`](./docs/PROFILES.md)**.

## Notifications

Pick any channel. The scraper fans out to all configured notifiers:

- 🔵 **Discord.** Rich embeds with images, price, availability, AI score. Set `DISCORD_WEBHOOK_URL`.
- ✈️ **Telegram.** Personal bot with password-gated subscriptions. Users send `/start <password>`. Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_PASSWORD`.
- 🌈 **Apprise.** One env var, 100+ channels: Slack, ntfy, email, WhatsApp (via Twilio), Pushover, Matrix, Home Assistant, and more. Set `APPRISE_URLS`.

All three can coexist. A high-scoring listing fans out to each configured channel. Channel recipes live in **[`docs/NOTIFICATIONS.md`](./docs/NOTIFICATIONS.md)**.

## Dashboard

The optional Next.js dashboard shows listing history, trends, top-scored picks, and landlord leaderboards. Run it locally with `npm run dev` or `docker compose --profile dashboard up`. See **[`dashboard/README.md`](./dashboard/README.md)**.

<!-- TODO(community): add a screenshot here. See issue #1 for contribution notes. -->

## Deployment

Local use needs nothing beyond the quick-start. To run Radar 24/7 on a tiny VPS (€4/mo is plenty), read **[`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md)**. It covers `docker compose` on a plain VPS, Coolify, Railway, and fly.io.

## Contributing

Pull requests welcome. Especially valuable:

- 📝 **New preset profiles.** Your city or situation isn't covered? Copy `profiles/generic.yaml` and send a PR.
- 🌐 **Notification recipes.** Add Apprise recipes for channels we haven't covered.
- 🧭 **Provider plugins.** Abstract the scraper to target Pararius, Funda, or HousingAnywhere.
- 🎨 **Dashboard polish.** Map view, websocket live updates, browser extension.

See **[`CONTRIBUTING.md`](./CONTRIBUTING.md)** for dev setup and the roadmap.

## Legal & ethical notice

This project is **not affiliated with Kamernet B.V.** Use it for personal, educational, non-commercial purposes.

- The scraper respects [Kamernet's `robots.txt`](https://kamernet.nl/robots.txt). It hits the public HTML search pages and avoids the disallowed API endpoints (`/SearchRooms/GetRooms`, `/ajax/`, etc.). Pull requests that weaken this get rejected.
- The scraper rate-limits requests with jittered intervals (default 50–70s).
- You are responsible for complying with Kamernet's Terms of Service and applicable law (including EU GDPR if you process personal data).
- Use a transparent User-Agent with a link back to this repo (default template in `.env.example`).

If you're on the Kamernet operations team and this causes trouble, open an issue and let's talk. One HTML fetch per minute per user puts less pressure on your servers than a motivated human refreshing the site.

## License

[MIT](./LICENSE). Do whatever you want, no warranty.
