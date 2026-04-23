"""Apprise notifier — one env var, 100+ channels.

See https://github.com/caronc/apprise/wiki for URL syntax. Examples:
- ntfy://mytopic
- slack://TokenA/TokenB/TokenC
- mailto://user:pass@smtp.gmail.com?to=you@example.com
- pover://user@token
- twilio://AccountSID:AuthToken@FromNumber/ToNumber (for WhatsApp, prefix ToNumber with "whatsapp:")
"""

from __future__ import annotations

import logging

try:
    import apprise

    HAS_APPRISE = True
except ImportError:
    HAS_APPRISE = False

log = logging.getLogger(__name__)


class AppriseNotifier:
    name = "apprise"

    def __init__(self, urls: str, score_threshold: int = 0) -> None:
        if not HAS_APPRISE:
            raise RuntimeError("apprise is not installed. Run `pip install apprise`.")

        self.score_threshold = score_threshold
        self._apobj = apprise.Apprise()
        for url in (u.strip() for u in urls.split(",") if u.strip()):
            if not self._apobj.add(url):
                log.warning("apprise: could not register URL (bad format?): %s", url)

        if len(self._apobj) == 0:
            raise ValueError("APPRISE_URLS is set but no valid URLs were registered.")

    def send_listings(self, listings: list[dict]) -> None:
        for listing in listings:
            score = listing.get("ai_score")
            if score is not None and score < self.score_threshold:
                continue

            listing_id = listing.get("listingId")
            city_slug = listing.get("citySlug", "")
            street_slug = listing.get("streetSlug", "")
            url = f"https://kamernet.nl/huren/{city_slug}/{street_slug}/{listing_id}"

            price = listing.get("totalRentalPrice", 0) or 0
            area = listing.get("surfaceArea", 0) or 0
            city = listing.get("city", "Unknown")
            title = listing.get("detailed_title") or listing.get("street") or "Kamernet listing"

            score_suffix = f" — score {score}/100" if score is not None else ""
            body_lines = [
                f"{title}",
                f"€{price}/mo · {area}m² · {city}{score_suffix}",
            ]
            reasoning = (listing.get("ai_score_reasoning") or "").strip()
            if reasoning:
                body_lines.append("")
                body_lines.append(reasoning)
            body_lines.append("")
            body_lines.append(url)

            title_line = f"🏠 New listing: {title}"[:250]
            self._apobj.notify(title=title_line, body="\n".join(body_lines))
