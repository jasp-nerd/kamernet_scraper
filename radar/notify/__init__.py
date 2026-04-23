"""Notification layer. Ships with three notifiers; any, all, or none can be active.

- Discord (native rich embeds): set DISCORD_WEBHOOK_URL
- Telegram (native subscriber flow with password gate): set TELEGRAM_BOT_TOKEN + TELEGRAM_PASSWORD
- Apprise (100+ channels via one URL): set APPRISE_URLS

Each notifier fans out a batch of listings independently. If none are configured,
the scraper still writes to the DB — notifications are purely optional.
"""

from __future__ import annotations

import logging
from typing import Protocol

from radar.config import Settings
from radar.db import Database

log = logging.getLogger(__name__)


class Notifier(Protocol):
    name: str

    def send_listings(self, listings: list[dict]) -> None: ...


class NotifierBundle:
    """Fan-out to all active notifiers."""

    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = notifiers

    @property
    def active(self) -> bool:
        return bool(self.notifiers)

    @property
    def active_names(self) -> list[str]:
        return [n.name for n in self.notifiers]

    def send_listings(self, listings: list[dict]) -> None:
        if not listings:
            return
        for notifier in self.notifiers:
            try:
                notifier.send_listings(listings)
            except Exception as exc:
                log.error("%s notifier failed: %s", notifier.name, exc)

    def process_commands(self) -> None:
        """Give each notifier a chance to process inbound commands (e.g. Telegram /start)."""
        for notifier in self.notifiers:
            handler = getattr(notifier, "process_commands", None)
            if callable(handler):
                try:
                    handler()
                except Exception as exc:
                    log.error("%s command processing failed: %s", notifier.name, exc)


def build_notifiers(settings: Settings, db: Database | None) -> NotifierBundle:
    """Inspect settings and return a bundle of enabled notifiers."""
    notifiers: list[Notifier] = []

    if settings.discord_webhook_url:
        from radar.notify.discord import DiscordNotifier

        notifiers.append(DiscordNotifier(settings.discord_webhook_url))

    if settings.telegram_bot_token:
        if db is None:
            log.warning(
                "TELEGRAM_BOT_TOKEN is set but DATABASE_URL is not; "
                "telegram subscribers cannot be persisted. Disabling telegram."
            )
        elif not settings.telegram_password:
            log.warning(
                "TELEGRAM_BOT_TOKEN is set but TELEGRAM_PASSWORD is not. "
                "Refusing to run an open subscription bot. Disabling telegram."
            )
        else:
            from radar.notify.telegram import TelegramNotifier

            notifiers.append(
                TelegramNotifier(
                    bot_token=settings.telegram_bot_token,
                    password=settings.telegram_password,
                    score_threshold=settings.telegram_score_threshold,
                    db=db,
                )
            )

    if settings.apprise_urls:
        from radar.notify.apprise import AppriseNotifier

        notifiers.append(
            AppriseNotifier(
                urls=settings.apprise_urls,
                score_threshold=settings.apprise_score_threshold,
            )
        )

    return NotifierBundle(notifiers)
