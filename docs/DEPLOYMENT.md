# Deployment

Running Radar 24/7. Four options, from easiest to most flexible.

For local-only use, skip this doc. The quick start in the main README covers it.

---

## Option 1: Any VPS + docker compose (recommended)

Works on any VPS with Docker: Hetzner (€4/mo), DigitalOcean, Vultr, Linode, your home server, a Raspberry Pi 4+.

### 1. Provision

Spin up a VPS. 1 vCPU + 1 GB RAM is plenty. Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER   # re-login after this
```

### 2. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/kamernet-radar /opt/radar
cd /opt/radar
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD (for docker-compose), APPRISE_URLS or DISCORD_WEBHOOK_URL, OPENROUTER_API_KEY
```

Add these at the top of your `.env` so docker-compose picks them up:

```bash
POSTGRES_DB=radar
POSTGRES_USER=radar
POSTGRES_PASSWORD=<a-long-random-password>
```

### 3. Bootstrap schema and run

```bash
docker compose up -d db
docker compose run --rm scraper python -m radar init-db
docker compose up -d scraper
```

Watch logs:

```bash
docker compose logs -f scraper
```

### 4. Auto-update (optional)

Pull manually (`git pull && docker compose up -d --build`) or set up [watchtower](https://containrrr.dev/watchtower/) for the scraper image.

### 5. Dashboard on the same VPS (optional)

The compose file binds the dashboard to `127.0.0.1:3000`. The public internet can't reach it. Two ways to access:

**SSH tunnel** (simplest, works for solo use):

```bash
ssh -L 3000:127.0.0.1:3000 you@your-vps
# visit http://localhost:3000 in your browser
```

**Reverse proxy with auth** (for a small team):

Use [Caddy](https://caddyserver.com/) with a basic-auth block, or put it behind Cloudflare Access / Tailscale. Always combine with `DASHBOARD_PASSWORD` in `.env`.

```caddyfile
radar.example.com {
    basicauth {
        you <bcrypt-hash>
    }
    reverse_proxy 127.0.0.1:3000
}
```

Remember to expose the dashboard port on the docker-compose side. Change `"127.0.0.1:3000:3000"` to `"3000:3000"` if you front it with a proxy on the same host.

---

## Option 2: Coolify / Dokploy / Portainer

These panels wrap docker-compose with a nice UI. Point them at this repo, they read the `docker-compose.yml`, and you configure env vars through the panel.

Caveats:
- Some panels don't expose `profiles:` cleanly. You may need to merge the dashboard service into a separate compose file or start it manually.
- Mount a persistent volume for the `db` service.

---

## Option 3: Railway / fly.io (PaaS)

The scraper is a long-running worker. Most PaaS platforms charge for that like a regular container. It works, but `docker-compose up` on a €4/mo VPS beats the cheapest Railway worker on price.

If you want PaaS anyway:

- **Railway**: separate services for `scraper` (Dockerfile at root) and `dashboard` (Dockerfile at `dashboard/`). Attach a Railway Postgres to both.
- **fly.io**: two fly apps, a single Postgres volume app. Use `fly.toml` per service.

Both need a one-time manual `python -m radar init-db`.

---

## Option 4: Heroku / old-school PaaS

Possible but fiddly. The free tier is gone. The scraper-as-worker dyno restarts periodically and dyno-local files don't persist, so you must use Heroku Postgres (Radar 1.0 removed the local SQLite/JSON fallback anyway). Grab a €4/mo VPS instead.

---

## Production checklist

Before you consider a deployment done:

- [ ] `.env` is not in git and not world-readable on the server (`chmod 600 .env`).
- [ ] Postgres has a non-trivial password (don't leave it at `radar`).
- [ ] Dashboard is behind auth if exposed at all (`DASHBOARD_PASSWORD` + reverse proxy).
- [ ] Your User-Agent identifies you and points at your fork (don't impersonate the upstream).
- [ ] Daily Postgres backup (cron + `pg_dump | gzip > backup.sql.gz`).
- [ ] Alerting on the scraper container being down (uptime-kuma, healthchecks.io).
- [ ] Check logs occasionally. If Kamernet blocks you, you want to know.

## FAQ

**Why does the container keep restarting?**
Check logs first. The common cause is a malformed `.env` or a Postgres that isn't up yet. `docker compose logs scraper | tail -50` tells you.

**The scraper is silent. No notifications.**
Confirm with `docker compose exec scraper env | grep -E 'DISCORD|TELEGRAM|APPRISE'` that at least one is set. Then try `--dry-run` on your laptop against a test channel.

**Kamernet returned 403 / empty results.**
You might be rate-limited. Raise `CHECK_INTERVAL_MIN`/`MAX`, wait an hour, try again. If it persists, the site's HTML may have changed. Open an issue.

**How do I update?**
`cd /opt/radar && git pull && docker compose up -d --build`. If a migration is needed, the release notes will say so.
