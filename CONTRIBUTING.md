# Contributing to Kamernet Radar

Thanks for thinking about contributing. This project welcomes help, especially with broadening the user base: new city profiles, notification recipes, multi-site scraping.

## Dev setup

```bash
git clone https://github.com/YOUR_USERNAME/kamernet-radar
cd kamernet-radar

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install ruff pytest  # dev tools not in requirements.txt

cp .env.example .env     # set DATABASE_URL for any DB-touching work
```

For the dashboard:

```bash
cd dashboard
npm install
cp .env.example .env.local
npm run dev
```

Running the scraper against a throwaway local Postgres:

```bash
docker compose up -d db
python -m radar init-db
python -m radar run --once --dry-run --profile generic
```

## Ways to help

### 🌱 New profiles

The easiest first PR. Copy `profiles/generic.yaml` to `profiles/your-use-case.yaml`, tune the `search` block and `scoring_prompt`, add a row to the README's profile table.

Good starter profiles we want:

- `profiles/amsterdam-expat.yaml`: English-speaking professional, budget flexible, prefers furnished
- `profiles/rotterdam-student.yaml`: student at EUR / TU Delft, tight budget
- `profiles/the-hague-government.yaml`: government worker, commute to central The Hague
- `profiles/groningen-student.yaml`: student at RUG, cheap rooms acceptable
- your own situation

### 🔔 Notification recipes

Document new Apprise URLs in `docs/NOTIFICATIONS.md`. Useful additions: corporate Slack, Mattermost, Home Assistant, self-hosted ntfy, webhook-to-custom-service.

### 🐛 Bug reports

Use the bug template. Include:
- your profile
- a sanitized `.env` (blank out keys)
- the scraper's log output

### 🏗️ Bigger wishes

- **Multi-site support.** Abstract the scraper behind a `Provider` interface so it can target Pararius, Funda, HousingAnywhere. Biggest unlock for the project.
- **Map view on the dashboard.** Leaflet + OpenStreetMap. Pin each listing, color by score.
- **Live updates on the dashboard.** WebSocket or SSE. A new listing pops in as a toast.
- **iCal/ICS feed.** Subscribe your calendar to new listings.
- **Browser extension.** "Save to Radar" button on any Kamernet listing page.
- **Profile editor UI.** A form on the dashboard that writes YAML so non-devs can tweak their rubric.
- **Scoring comparison mode.** Run two rubrics on the same listing set and diff the scores.

## Code style

- **Python**: `ruff format .` and `ruff check .`. CI runs this.
- **TypeScript**: `npm run lint` in `dashboard/`.
- Keep modules small and single-purpose. If a file creeps past 300 lines, split it.
- Skip comments explaining *what* the code does. Let names do that. Add comments for *why*: hidden constraints, workarounds, subtle invariants.

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] `ruff check .` clean
- [ ] README / docs updated if behavior changed
- [ ] New env vars added to `.env.example`
- [ ] Commit message describes the change clearly
- [ ] No secrets or personal data committed (re-check `.env` and any test fixtures)
- [ ] If adding a notification channel, include a recipe in `docs/NOTIFICATIONS.md`
- [ ] If adding a profile, include a row in the README's profile table

## Non-negotiables

- **robots.txt compliance.** Any change that scrapes the disallowed API endpoints (`/SearchRooms/GetRooms`, `/ajax/`, etc.) gets rejected. No exceptions. The scraper reads the public HTML search pages only.
- **No scraper-stealth hacks.** No residential proxy rotation, no headless browsers to bypass rate limits, no detection evasion. If Kamernet asks us to stop, we stop.
- **No PII harvesting.** We don't store landlord emails or phone numbers beyond what's on the public search page.

## Code of conduct

See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). TL;DR: be kind, assume good faith.

## License

By contributing, you agree your contributions ship under the [MIT License](./LICENSE).
