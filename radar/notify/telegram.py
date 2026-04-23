"""Telegram notifier with password-gated /start subscription flow."""

from __future__ import annotations

import logging

import requests

from radar.db import Database

log = logging.getLogger(__name__)


class TelegramNotifier:
    name = "telegram"

    def __init__(
        self,
        bot_token: str,
        password: str,
        score_threshold: int,
        db: Database,
    ) -> None:
        self.bot_token = bot_token
        self.password = password
        self.score_threshold = score_threshold
        self.db = db
        self._last_update_id = 0

    # ── Low-level ──

    def _send(self, chat_id: int, text: str) -> bool:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
                timeout=10,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    # ── Subscriber management ──

    def process_commands(self) -> None:
        """Poll getUpdates and handle /start <password> and /stop commands."""
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                params={"offset": self._last_update_id + 1, "timeout": 0},
                timeout=10,
            )
        except requests.RequestException as exc:
            log.warning("telegram getUpdates failed: %s", exc)
            return

        data = resp.json() if resp.ok else {}
        if not data.get("ok") or not data.get("result"):
            return

        for update in data["result"]:
            self._last_update_id = update["update_id"]
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if not chat_id or not text:
                continue

            first_name = chat.get("first_name") or ""
            username = (message.get("from") or {}).get("username") or ""

            if text.startswith("/start"):
                parts = text.split(maxsplit=1)
                given = parts[1] if len(parts) > 1 else ""
                if given != self.password:
                    self._send(
                        chat_id,
                        "🔒 Password required.\n\nSend: <code>/start yourpassword</code>",
                    )
                    continue
                is_new = self.db.add_telegram_subscriber(chat_id, username, first_name)
                if is_new:
                    self._send(
                        chat_id,
                        "✅ <b>Subscribed!</b>\n\n"
                        f"You'll receive notifications for listings scoring ≥ {self.score_threshold}/100.\n\n"
                        "Send /stop to unsubscribe.",
                    )
                    log.info("new telegram subscriber: %s (%s)", first_name, chat_id)
                else:
                    self._send(chat_id, "You're already subscribed! 👍")

            elif text == "/stop":
                removed = self.db.remove_telegram_subscriber(chat_id)
                if removed:
                    self._send(
                        chat_id,
                        "👋 Unsubscribed. Send <code>/start yourpassword</code> to resubscribe.",
                    )
                    log.info("telegram unsubscribe: %s (%s)", first_name, chat_id)
                else:
                    self._send(chat_id, "You weren't subscribed.")

    # ── Outbound ──

    def send_listings(self, listings: list[dict]) -> None:
        subscribers = self.db.get_telegram_subscribers()
        if not subscribers:
            return

        for listing in listings:
            score = listing.get("ai_score")
            if score is None or score < self.score_threshold:
                continue

            listing_id = listing.get("listingId")
            city_slug = listing.get("citySlug", "")
            street_slug = listing.get("streetSlug", "")
            url = f"https://kamernet.nl/huren/{city_slug}/{street_slug}/{listing_id}"

            price = listing.get("totalRentalPrice", 0) or 0
            area = listing.get("surfaceArea", 0) or 0
            city = listing.get("city", "Unknown")
            title = listing.get("detailed_title") or listing.get("street") or "Unknown"
            reasoning = listing.get("ai_score_reasoning") or ""

            text = (
                f"🏠 <b>High-scoring listing: {score}/100</b>\n\n"
                f"<b>{title}</b>\n"
                f"💰 €{price}/mo  |  📐 {area}m²  |  📍 {city}\n\n"
                f"💡 <i>{reasoning}</i>\n\n"
                f'🔗 <a href="{url}">View on Kamernet</a>'
            )

            sent = sum(1 for chat_id in subscribers if self._send(chat_id, text))
            log.info(
                "telegram: listing %s (score %s) → %s/%s subscribers",
                listing_id,
                score,
                sent,
                len(subscribers),
            )
