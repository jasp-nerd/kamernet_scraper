"""Main scraping loop: fetch → enrich → score → notify → persist."""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime

import requests

from radar import ai, fetch
from radar.config import Settings
from radar.db import Database
from radar.notify import NotifierBundle
from radar.profile import Profile

log = logging.getLogger(__name__)


class Radar:
    """Stateful scraper. One instance per process."""

    def __init__(
        self,
        settings: Settings,
        profile: Profile,
        db: Database | None,
        notifiers: NotifierBundle,
        dry_run: bool = False,
    ) -> None:
        self.settings = settings
        self.profile = profile
        self.db = db
        self.notifiers = notifiers
        self.dry_run = dry_run
        self.session = fetch.make_session(settings.user_agent)
        self.seen_ids: set[int] = db.load_seen_listing_ids() if db else set()

    # ── Single tick ──

    def check_once(self) -> None:
        log.info("=" * 60)
        log.info("check at %s — profile=%s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.profile.name)

        # Process inbound commands (Telegram /start etc.)
        self.notifiers.process_commands()

        listings = fetch.fetch_listings(self.profile.search, self.session)
        if not listings:
            log.info("no listings returned")
            if self.db and not self.dry_run:
                self.db.log_scrape_run(0, 0, "no listings")
            return

        all_ids = [item["listingId"] for item in listings if item.get("listingId")]
        if self.db and not self.dry_run:
            self.db.touch_listings(all_ids)

        new_listings = [
            item for item in listings if item.get("listingId") and item["listingId"] not in self.seen_ids
        ]
        for item in new_listings:
            self.seen_ids.add(item["listingId"])

        log.info("total=%d new=%d", len(listings), len(new_listings))

        if not new_listings:
            if self.db and not self.dry_run:
                self.db.mark_disappeared()
                self.db.log_scrape_run(len(listings), 0)
            return

        for listing in new_listings:
            log.info(
                "  · %s, %s — €%s (id=%s)",
                listing.get("street", "Unknown"),
                listing.get("city", "Unknown"),
                listing.get("totalRentalPrice", 0),
                listing.get("listingId"),
            )

        log.info("enriching %d listings", len(new_listings))
        enriched = [fetch.fetch_listing_details(item, self.session) for item in new_listings]

        if self.db and not self.dry_run:
            for listing in enriched:
                self.db.upsert_listing(listing)

        if self.settings.openrouter_api_key:
            log.info("scoring %d listings via OpenRouter", len(enriched))
            for listing in enriched:
                score, reasoning = ai.score_listing(
                    listing,
                    self.profile,
                    self.settings.openrouter_api_key,
                    self.settings.openrouter_model,
                    self.settings.openrouter_fallback_model,
                )
                if score is not None:
                    listing["ai_score"] = score
                    listing["ai_score_reasoning"] = reasoning
                    if self.db and not self.dry_run:
                        self.db.update_ai_score(listing["listingId"], score, reasoning or "")
                    log.info("  · %s → %s/100", listing.get("listingId"), score)
                time.sleep(1)  # free-tier rate limit cushion

        if self.dry_run:
            log.info("dry-run: skipping notifications")
        else:
            self.notifiers.send_listings(enriched)

        if self.db and not self.dry_run:
            self.db.mark_disappeared()
            self.db.log_scrape_run(len(listings), len(new_listings))

    # ── Loop ──

    def run_forever(self) -> None:
        self._print_banner()
        while True:
            try:
                self.check_once()
            except requests.RequestException as exc:
                log.error("network error in main loop: %s", exc)
            except Exception as exc:
                log.exception("unhandled error in main loop: %s", exc)

            wait = random.randint(self.settings.check_interval_min, self.settings.check_interval_max)
            log.info("sleeping %ds until next check", wait)
            try:
                time.sleep(wait)
            except KeyboardInterrupt:
                log.info("interrupted — exiting")
                break

    def _print_banner(self) -> None:
        log.info("Kamernet Radar starting")
        log.info("  profile:      %s (%s)", self.profile.name, self.profile.source_path)
        log.info(
            "  interval:     %d-%ds (randomized)",
            self.settings.check_interval_min,
            self.settings.check_interval_max,
        )
        log.info("  database:     %s", "yes" if self.db else "no (DB writes skipped)")
        log.info(
            "  notifiers:    %s",
            ", ".join(self.notifiers.active_names) if self.notifiers.active else "none (DB-only mode)",
        )
        log.info(
            "  ai scoring:   %s",
            f"yes ({self.settings.openrouter_model})" if self.settings.openrouter_api_key else "no",
        )
        log.info("  dry-run:      %s", "yes" if self.dry_run else "no")
