#!/usr/bin/env python3
"""Re-score all listings in the database using the current profile's rubric.

Useful after changing a profile's scoring_prompt — pulls every row, feeds it through
OpenRouter, and updates ai_score + ai_score_reasoning.

Usage:
    python -m scripts.rescore [--profile NAME] [--limit N] [--only-unscored]
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Make the project root importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

from radar import ai  # noqa: E402
from radar.config import load_settings  # noqa: E402
from radar.profile import load_profile  # noqa: E402

log = logging.getLogger("rescore")


def _row_to_listing(row: dict) -> dict:
    """Map a DB row to the listing shape the AI module expects."""
    return {
        "listingId": row["listing_id"],
        "detailed_title": row.get("detailed_title"),
        "totalRentalPrice": row.get("total_rental_price"),
        "deposit": row.get("deposit"),
        "utilitiesIncluded": row.get("utilities_included"),
        "surfaceArea": row.get("surface_area"),
        "city": row.get("city"),
        "postal_code": row.get("postal_code"),
        "street": row.get("street"),
        "house_number": row.get("house_number"),
        "listingType": row.get("listing_type"),
        "furnishingId": row.get("furnishing_id"),
        "num_rooms": row.get("num_rooms"),
        "num_bedrooms": row.get("num_bedrooms"),
        "energy_label_id": row.get("energy_label_id"),
        "pets_allowed": row.get("pets_allowed"),
        "smoking_allowed": row.get("smoking_allowed"),
        "registration_allowed": row.get("registration_allowed"),
        "min_age": row.get("min_age"),
        "max_age": row.get("max_age"),
        "suitable_for_persons": row.get("suitable_for_persons"),
        "availability_start": row.get("availability_start"),
        "availability_end": row.get("availability_end"),
        "detailed_description": row.get("detailed_description"),
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S"
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="profile name (overrides PROFILE env)")
    parser.add_argument("--limit", type=int, help="stop after N listings")
    parser.add_argument(
        "--only-unscored",
        action="store_true",
        help="only score rows where ai_score IS NULL",
    )
    args = parser.parse_args()

    settings = load_settings()
    if args.profile:
        settings.profile = args.profile

    if not settings.database_url:
        log.error("DATABASE_URL is not set")
        return 1
    if not settings.openrouter_api_key:
        log.error("OPENROUTER_API_KEY is not set")
        return 1

    profile = load_profile(settings.profile)
    log.info("using profile: %s", profile.name)
    log.info("primary model: %s", settings.openrouter_model)

    where = "WHERE ai_score IS NULL" if args.only_unscored else ""
    limit = f"LIMIT {int(args.limit)}" if args.limit else ""

    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                f"""
                SELECT listing_id, street, city, postal_code, house_number,
                       listing_type, furnishing_id, total_rental_price, surface_area,
                       deposit, utilities_included, num_bedrooms, num_rooms,
                       energy_label_id, pets_allowed, smoking_allowed, registration_allowed,
                       min_age, max_age, suitable_for_persons,
                       availability_start, availability_end,
                       detailed_title, detailed_description,
                       ai_score
                FROM listings
                {where}
                ORDER BY listing_id
                {limit}
                """
            )
            rows = cur.fetchall()

        log.info("rescoring %d listings", len(rows))
        scored = errors = 0

        with conn.cursor() as cur:
            for i, row in enumerate(rows, 1):
                listing = _row_to_listing(row)
                old_score = row.get("ai_score")
                title = (row.get("detailed_title") or "N/A")[:60]
                log.info("[%d/%d] id=%s | %s", i, len(rows), row["listing_id"], title)

                score, reasoning = ai.score_listing(
                    listing,
                    profile,
                    settings.openrouter_api_key,
                    settings.openrouter_model,
                    settings.openrouter_fallback_model,
                )
                if score is None:
                    errors += 1
                    log.warning("  → no score returned")
                    continue

                cur.execute(
                    "UPDATE listings SET ai_score = %s, ai_score_reasoning = %s WHERE listing_id = %s",
                    (score, reasoning, row["listing_id"]),
                )
                scored += 1
                delta = f" ({score - old_score:+d})" if old_score is not None else ""
                log.info("  → %s/100%s | %s", score, delta, (reasoning or "")[:100])
                time.sleep(1)  # gentle pacing

    log.info("done. scored=%d errors=%d total=%d", scored, errors, len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
