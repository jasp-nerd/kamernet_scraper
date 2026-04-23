# Security

## Reporting a vulnerability

Please don't open a public GitHub issue for security problems.

Instead, open a [GitHub security advisory](https://github.com/YOUR_USERNAME/kamernet-radar/security/advisories/new) or email the maintainer at the address listed on the repo's homepage.

You can expect:

- An acknowledgment within 72 hours.
- A fix and advisory within 30 days for most issues.
- Credit in the changelog if you want it.

## Scope

In scope:

- The Python scraper (`radar/` package)
- The Next.js dashboard
- Docker images and deployment templates in this repo

Out of scope:

- Vulnerabilities in upstream dependencies (report those to the project)
- Issues in Kamernet.nl itself (report those to Kamernet B.V.)
- Social engineering of maintainers

## Good-faith research

Security research is welcome. Please:

- Don't exfiltrate data beyond what proves a vulnerability
- Don't degrade service for other users
- Test against your own deployment, not the maintainer's
