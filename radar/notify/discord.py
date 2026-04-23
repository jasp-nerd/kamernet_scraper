"""Discord notifier — rich embeds with smart batching."""

from __future__ import annotations

import logging
import time
from datetime import datetime

from discord_webhook import DiscordEmbed, DiscordWebhook

from radar.ai import FURNISHING_LABELS, TYPE_LABELS

log = logging.getLogger(__name__)

BASE_URL = "https://kamernet.nl"
BATCH_SIZE = 10  # Discord hard limit on embeds per webhook message


def _embed_color(listing: dict) -> int:
    price = listing.get("totalRentalPrice", 0) or 0
    if listing.get("isNewAdvert"):
        return 0xFF6B35  # orange
    if listing.get("isTopAdvert"):
        return 0xFFD700  # gold
    if price > 2000:
        return 0xFF4444  # red
    if price and price < 800:
        return 0x44FF44  # green
    return 0x0099FF  # blue


def _title(listing: dict) -> str:
    listing_type = listing.get("listingType", 0)
    emoji = {1: "🏠", 2: "🏢"}.get(listing_type, "🏡")
    detailed_title = (listing.get("detailed_title") or "").strip()
    if detailed_title and len(detailed_title) < 100:
        return f"{emoji} {detailed_title}"
    type_text = TYPE_LABELS.get(listing_type, "Property")
    return f"{emoji} {type_text}: {listing.get('street', 'Unknown')}, {listing.get('city', 'Unknown')}"


def _add_availability(embed: DiscordEmbed, listing: dict) -> None:
    start = listing.get("availabilityStartDate")
    end = listing.get("availabilityEndDate")

    if start:
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            embed.add_embed_field(name="📅 Available", value=f"From {dt.strftime('%b %d, %Y')}", inline=True)
        except (ValueError, TypeError):
            embed.add_embed_field(name="📅 Available", value=f"From {start[:10]}", inline=True)

    if end:
        try:
            dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            embed.add_embed_field(name="📅 Until", value=dt.strftime("%b %d, %Y"), inline=True)
        except (ValueError, TypeError):
            embed.add_embed_field(name="📅 Until", value=end[:10], inline=True)
    else:
        embed.add_embed_field(name="⏰ Duration", value="Long-term", inline=True)


def _add_landlord_and_prefs(embed: DiscordEmbed, listing: dict) -> None:
    landlord = listing.get("landlord_name")
    if landlord:
        parts = [f"👤 {landlord}"]
        if listing.get("landlord_verified"):
            parts.append("✅")
        rate = listing.get("landlord_response_rate")
        if rate is not None:
            parts.append(f"({rate}% response)")
        embed.add_embed_field(name="🏠 Landlord", value=" ".join(parts), inline=False)

    prefs: list[str] = []
    min_age, max_age = listing.get("min_age"), listing.get("max_age")
    if min_age and max_age:
        prefs.append(f"Age: {min_age}-{max_age}" if min_age != max_age else f"Age: {min_age}")
    if (v := listing.get("pets_allowed")) is not None:
        prefs.append("🐕 Pets OK" if v else "🚫 No pets")
    if (v := listing.get("smoking_allowed")) is not None:
        prefs.append("🚬 Smoking OK" if v else "🚭 No smoking")
    if prefs:
        embed.add_embed_field(name="👥 Preferences", value=" • ".join(prefs), inline=False)

    desc = listing.get("detailed_description") or ""
    if len(desc) > 50:
        excerpt = desc[:150]
        if len(desc) > 150:
            last_sentence = max(excerpt.rfind("."), excerpt.rfind("!"))
            excerpt = excerpt[: last_sentence + 1] if last_sentence > 80 else excerpt + "..."
        embed.add_embed_field(name="📝 Description", value=excerpt, inline=False)


def format_listing(listing: dict) -> DiscordEmbed:
    price = listing.get("totalRentalPrice", 0) or 0
    surface = listing.get("surfaceArea", 0) or 0
    listing_type = listing.get("listingType", 0)
    furnishing_text = FURNISHING_LABELS.get(listing.get("furnishingId", 0), "Unknown")
    type_text = TYPE_LABELS.get(listing_type, "Property")

    listing_id = listing.get("listingId")
    city_slug = listing.get("citySlug") or (listing.get("city") or "").lower()
    street_slug = listing.get("streetSlug") or (listing.get("street") or "").lower().replace(" ", "-")
    url = f"{BASE_URL}/huren/{city_slug}/{street_slug}/{listing_id}"

    desc_parts = [f"**€{price}/month** • **{surface}m²**"]
    if furnishing_text != "Unknown":
        desc_parts.append(f"• {furnishing_text}")

    embed = DiscordEmbed(
        title=_title(listing),
        description=" ".join(desc_parts),
        url=url,
        color=_embed_color(listing),
    )

    embed.add_embed_field(name="💰 Rent", value=f"€{price}/month", inline=True)
    embed.add_embed_field(name="📐 Size", value=f"{surface}m²", inline=True)
    embed.add_embed_field(name="🏠 Type", value=type_text, inline=True)

    bedrooms = listing.get("num_bedrooms")
    rooms = listing.get("num_rooms")
    if bedrooms or rooms:
        rinfo = []
        if bedrooms:
            rinfo.append(f"{bedrooms} bed")
        if rooms and rooms != bedrooms:
            rinfo.append(f"{rooms} rooms")
        if rinfo:
            embed.add_embed_field(name="🛏️ Rooms", value=" • ".join(rinfo), inline=True)

    if listing.get("deposit"):
        embed.add_embed_field(name="💳 Deposit", value=f"€{listing['deposit']}", inline=True)

    _add_availability(embed, listing)

    utilities_text = "✅ Included" if listing.get("utilitiesIncluded") else "❌ Extra cost"
    embed.add_embed_field(name="⚡ Utilities", value=utilities_text, inline=True)

    _add_landlord_and_prefs(embed, listing)

    ai_score = listing.get("ai_score")
    if ai_score is not None:
        score_emoji = "🟢" if ai_score >= 70 else "🟡" if ai_score >= 40 else "🔴"
        score_text = f"{score_emoji} **{ai_score}/100**"
        reasoning = (listing.get("ai_score_reasoning") or "")[:200]
        if reasoning:
            score_text += f"\n{reasoning}"
        embed.add_embed_field(name="🤖 AI Score", value=score_text, inline=False)

    badges = []
    if listing.get("isNewAdvert"):
        badges.append("🆕 **NEW**")
    if listing.get("isTopAdvert"):
        badges.append("⭐ **FEATURED**")
    if badges:
        embed.add_embed_field(name="🏷️ Special", value=" • ".join(badges), inline=False)

    if listing.get("thumbnailUrl"):
        embed.set_thumbnail(url=listing["thumbnailUrl"])
    image_url = listing.get("resizedFullPreviewImageUrl") or listing.get("fullPreviewImageUrl")
    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(
        text=f"ID: {listing_id} • Kamernet.nl • Click title for full details",
        icon_url="https://kamernet.nl/favicon.ico",
    )
    embed.set_timestamp()
    return embed


def _summary_header(listings: list[dict], total_batches: int) -> DiscordEmbed:
    n = len(listings)
    s = "listing" if n == 1 else "listings"
    new_count = sum(1 for item in listings if item.get("isNewAdvert"))
    top_count = sum(1 for item in listings if item.get("isTopAdvert"))

    parts = [f"**{n} new {s}** found!"]
    if new_count:
        parts.append(f"🆕 {new_count} brand-new")
    if top_count:
        parts.append(f"⭐ {top_count} featured")

    prices = [item.get("totalRentalPrice", 0) for item in listings if (item.get("totalRentalPrice") or 0) > 0]
    if prices:
        parts.append(f"💰 €{min(prices)}-€{max(prices)}/month")

    header = DiscordEmbed(title="🔔 Kamernet Radar", description="\n".join(parts), color=0xFF6B35)
    footer = "Kamernet Radar • Respects robots.txt"
    if total_batches > 1:
        footer += f" • Batch 1 of {total_batches}"
    header.set_footer(text=footer, icon_url="https://kamernet.nl/favicon.ico")
    header.set_timestamp()
    return header


class DiscordNotifier:
    name = "discord"

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send_listings(self, listings: list[dict]) -> None:
        if not listings:
            return

        sorted_listings = sorted(
            listings,
            key=lambda item: (
                not item.get("isNewAdvert", False),
                not item.get("isTopAdvert", False),
                item.get("totalRentalPrice", 0) or 0,
            ),
        )

        total_batches = (len(sorted_listings) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_num in range(total_batches):
            start = batch_num * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(sorted_listings))
            batch = sorted_listings[start:end]
            webhook = DiscordWebhook(url=self.webhook_url)

            if batch_num == 0:
                webhook.add_embed(_summary_header(sorted_listings, total_batches))
            else:
                hdr = DiscordEmbed(
                    title=f"📋 Batch {batch_num + 1} of {total_batches}",
                    description=f"Listings {start + 1}-{end} of {len(sorted_listings)}",
                    color=0x0099FF,
                )
                hdr.set_footer(text="Kamernet Radar • Continued…")
                webhook.add_embed(hdr)

            # Header uses 1 of the 10-embed slots, so 9 listings per batch
            for listing in batch[:9]:
                webhook.add_embed(format_listing(listing))

            resp = webhook.execute()
            if resp.status_code in (200, 204):
                log.info(
                    "discord batch %s/%s sent (%d listings)",
                    batch_num + 1,
                    total_batches,
                    min(len(batch), 9),
                )
            else:
                log.warning("discord webhook failed with status %s", resp.status_code)

            if batch_num < total_batches - 1:
                time.sleep(3)  # hand-rolled rate limit
