"""Postgres persistence layer (psycopg3)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

try:
    import psycopg
    from psycopg import Connection

    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False
    Connection = Any  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)


def _parse_dt(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _listing_to_params(listing: dict) -> dict:
    return {
        "listing_id": listing.get("listingId"),
        "street": listing.get("street"),
        "city": listing.get("city"),
        "city_slug": listing.get("citySlug"),
        "street_slug": listing.get("streetSlug"),
        "postal_code": listing.get("postal_code"),
        "house_number": listing.get("house_number"),
        "house_number_addition": listing.get("house_number_addition"),
        "listing_type": listing.get("listingType"),
        "furnishing_id": listing.get("furnishingId"),
        "total_rental_price": listing.get("totalRentalPrice"),
        "surface_area": listing.get("surfaceArea"),
        "deposit": listing.get("deposit"),
        "utilities_included": listing.get("utilitiesIncluded"),
        "num_bedrooms": listing.get("num_bedrooms"),
        "num_rooms": listing.get("num_rooms"),
        "energy_label_id": listing.get("energy_label_id"),
        "pets_allowed": listing.get("pets_allowed"),
        "smoking_allowed": listing.get("smoking_allowed"),
        "registration_allowed": listing.get("registration_allowed"),
        "min_age": listing.get("min_age"),
        "max_age": listing.get("max_age"),
        "suitable_for_persons": listing.get("suitable_for_persons"),
        "availability_start": _parse_date(listing.get("availabilityStartDate")),
        "availability_end": _parse_date(listing.get("availabilityEndDate")),
        "detailed_title": listing.get("detailed_title"),
        "detailed_description": listing.get("detailed_description"),
        "thumbnail_url": listing.get("thumbnailUrl"),
        "full_preview_image_url": listing.get("resizedFullPreviewImageUrl")
        or listing.get("fullPreviewImageUrl"),
        "additional_images": json.dumps(listing.get("additional_images") or []),
        "landlord_name": listing.get("landlord_name"),
        "landlord_verified": bool(listing.get("landlord_verified", False)),
        "landlord_response_rate": listing.get("landlord_response_rate"),
        "landlord_response_time": listing.get("landlord_response_time"),
        "landlord_member_since": _parse_dt(listing.get("landlord_member_since")),
        "landlord_last_seen": _parse_dt(listing.get("landlord_last_seen")),
        "landlord_active_listings": listing.get("landlord_active_listings"),
        "create_date": _parse_dt(listing.get("create_date") or listing.get("createDate")),
        "publish_date": _parse_dt(listing.get("publish_date") or listing.get("publishDate")),
        "is_new_advert": bool(listing.get("isNewAdvert", False)),
        "is_top_advert": bool(listing.get("isTopAdvert", False)),
    }


UPSERT_SQL = """
INSERT INTO listings (
    listing_id, street, city, city_slug, street_slug,
    postal_code, house_number, house_number_addition,
    listing_type, furnishing_id,
    total_rental_price, surface_area, deposit, utilities_included,
    num_bedrooms, num_rooms, energy_label_id,
    pets_allowed, smoking_allowed, registration_allowed,
    min_age, max_age, suitable_for_persons,
    availability_start, availability_end,
    detailed_title, detailed_description,
    thumbnail_url, full_preview_image_url, additional_images,
    landlord_name, landlord_verified, landlord_response_rate,
    landlord_response_time, landlord_member_since, landlord_last_seen,
    landlord_active_listings,
    create_date, publish_date,
    is_new_advert, is_top_advert,
    first_seen_at, last_seen_at
) VALUES (
    %(listing_id)s, %(street)s, %(city)s, %(city_slug)s, %(street_slug)s,
    %(postal_code)s, %(house_number)s, %(house_number_addition)s,
    %(listing_type)s, %(furnishing_id)s,
    %(total_rental_price)s, %(surface_area)s, %(deposit)s, %(utilities_included)s,
    %(num_bedrooms)s, %(num_rooms)s, %(energy_label_id)s,
    %(pets_allowed)s, %(smoking_allowed)s, %(registration_allowed)s,
    %(min_age)s, %(max_age)s, %(suitable_for_persons)s,
    %(availability_start)s, %(availability_end)s,
    %(detailed_title)s, %(detailed_description)s,
    %(thumbnail_url)s, %(full_preview_image_url)s, %(additional_images)s,
    %(landlord_name)s, %(landlord_verified)s, %(landlord_response_rate)s,
    %(landlord_response_time)s, %(landlord_member_since)s, %(landlord_last_seen)s,
    %(landlord_active_listings)s,
    %(create_date)s, %(publish_date)s,
    %(is_new_advert)s, %(is_top_advert)s,
    NOW(), NOW()
)
ON CONFLICT (listing_id) DO UPDATE SET
    total_rental_price = EXCLUDED.total_rental_price,
    surface_area = EXCLUDED.surface_area,
    last_seen_at = NOW(),
    disappeared_at = NULL,
    updated_at = NOW(),
    is_new_advert = EXCLUDED.is_new_advert,
    is_top_advert = EXCLUDED.is_top_advert
"""


class Database:
    """Thin wrapper around a psycopg3 connection with the queries we use."""

    def __init__(self, url: str | None) -> None:
        if not HAS_PSYCOPG:
            raise RuntimeError("psycopg (v3) is not installed. Run `pip install 'psycopg[binary]'`.")
        if not url:
            raise ValueError("DATABASE_URL is required to use Database.")
        self.url = url
        self._conn: Connection | None = None
        self._connect()

    def _connect(self) -> None:
        try:
            self._conn = psycopg.connect(self.url, autocommit=True, connect_timeout=10)
            log.info("connected to postgres")
        except Exception as exc:
            log.error("db connect failed: %s", exc)
            self._conn = None

    def _cursor(self):
        if self._conn is None or self._conn.closed:
            self._connect()
        if self._conn is None:
            raise RuntimeError("no database connection available")
        return self._conn.cursor()

    # ── Listings ──

    def load_seen_listing_ids(self) -> set[int]:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT listing_id FROM listings")
                return {row[0] for row in cur.fetchall()}
        except Exception as exc:
            log.warning("load seen listings failed: %s", exc)
            return set()

    def upsert_listing(self, listing: dict) -> None:
        try:
            with self._cursor() as cur:
                cur.execute(UPSERT_SQL, _listing_to_params(listing))
        except Exception as exc:
            log.warning("upsert failed for %s: %s", listing.get("listingId"), exc)

    def touch_listings(self, listing_ids: list[int]) -> None:
        if not listing_ids:
            return
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE listings SET last_seen_at = NOW(), disappeared_at = NULL "
                    "WHERE listing_id = ANY(%s)",
                    (listing_ids,),
                )
        except Exception as exc:
            log.warning("touch failed: %s", exc)

    def mark_disappeared(self, minutes: int = 30) -> int:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE listings SET disappeared_at = NOW() "
                    "WHERE disappeared_at IS NULL "
                    "  AND last_seen_at < NOW() - make_interval(mins => %s)",
                    (int(minutes),),
                )
                return cur.rowcount or 0
        except Exception as exc:
            log.warning("mark disappeared failed: %s", exc)
            return 0

    def update_ai_score(self, listing_id: int, score: int, reasoning: str) -> None:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE listings SET ai_score = %s, ai_score_reasoning = %s WHERE listing_id = %s",
                    (score, reasoning, listing_id),
                )
        except Exception as exc:
            log.warning("ai_score update failed for %s: %s", listing_id, exc)

    # ── Scrape runs ──

    def log_scrape_run(self, total_found: int, new_found: int, error: str | None = None) -> None:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO scrape_runs (started_at, finished_at, total_found, new_found, errors) "
                    "VALUES (NOW(), NOW(), %s, %s, %s)",
                    (total_found, new_found, error),
                )
        except Exception as exc:
            log.warning("scrape run log failed: %s", exc)

    # ── Telegram subscribers ──

    def get_telegram_subscribers(self) -> list[int]:
        try:
            with self._cursor() as cur:
                cur.execute("SELECT chat_id FROM telegram_subscribers")
                return [row[0] for row in cur.fetchall()]
        except Exception as exc:
            log.warning("load subscribers failed: %s", exc)
            return []

    def add_telegram_subscriber(self, chat_id: int, username: str, first_name: str) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO telegram_subscribers (chat_id, username, first_name) "
                    "VALUES (%s, %s, %s) ON CONFLICT (chat_id) DO NOTHING",
                    (chat_id, username, first_name),
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:
            log.warning("add subscriber failed: %s", exc)
            return False

    def remove_telegram_subscriber(self, chat_id: int) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM telegram_subscribers WHERE chat_id = %s",
                    (chat_id,),
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:
            log.warning("remove subscriber failed: %s", exc)
            return False

    # ── Schema init ──

    def init_schema(self, schema_sql: str) -> None:
        """Execute the schema SQL. Use for first-run bootstrap."""
        with self._cursor() as cur:
            cur.execute(schema_sql)

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
