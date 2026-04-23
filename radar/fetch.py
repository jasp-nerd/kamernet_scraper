"""HTTP scraping of Kamernet's public search and listing detail pages.

Respects robots.txt: uses only allowed HTML pages, never the disallowed API endpoints.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlencode

import requests

from radar.profile import SearchConfig

log = logging.getLogger(__name__)

BASE_URL = "https://kamernet.nl"

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)

_SORT_MAP = {
    "newest": 1,
    "price_asc": 2,
    "price_desc": 3,
}


def build_search_url(search: SearchConfig) -> str:
    """Build a Kamernet search URL from profile search config."""
    params: dict[str, Any] = {
        "pageNo": 1,
        "radius": search.radius_km,
        "minSize": search.min_size,
        "maxRent": search.max_rent,
        "searchView": 1,
        "sort": _SORT_MAP.get(search.sort, 1),
    }
    return f"{BASE_URL}/huren/{search.city_slug}?{urlencode(params)}"


def make_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.7,nl;q=0.5",
            "Connection": "keep-alive",
        }
    )
    return session


def _extract_next_data(html: str) -> dict | None:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def fetch_listings(search: SearchConfig, session: requests.Session) -> list[dict]:
    """Fetch the search results page and return the raw listing dicts."""
    url = build_search_url(search)
    log.info("fetching %s", url)
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("search fetch failed: %s", exc)
        return []

    data = _extract_next_data(resp.text)
    if not data:
        log.warning("no __NEXT_DATA__ in search response")
        return []

    target = data.get("props", {}).get("pageProps", {}).get("targetPageProps", {})
    response_block = target.get("findListingsResponse", {})
    listings = response_block.get("listings", []) or []
    top = response_block.get("topAdListings", []) or []
    result = listings + top

    if search.listing_types:
        allowed = set(search.listing_types)
        result = [item for item in result if item.get("listingType") in allowed]

    log.info("found %d listings", len(result))
    return result


def fetch_listing_details(listing: dict, session: requests.Session) -> dict:
    """Fetch the detail page for a listing and merge enriched fields in."""
    listing_id = listing.get("listingId")
    city_slug = listing.get("citySlug", "")
    street_slug = listing.get("streetSlug", "")

    if not listing_id or not street_slug:
        return listing

    url = f"{BASE_URL}/huren/{city_slug}/{street_slug}/{listing_id}"

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("detail fetch failed for %s: %s", listing_id, exc)
        return listing

    data = _extract_next_data(resp.text)
    if not data:
        return listing

    details_block = (
        data.get("props", {}).get("pageProps", {}).get("targetPageProps", {}).get("listingDetails", {})
    )
    if not details_block:
        return listing

    enriched = {
        **listing,
        "detailed_description": details_block.get("dutchDescription")
        or details_block.get("englishDescription", ""),
        "detailed_title": details_block.get("dutchTitle") or details_block.get("englishTitle", ""),
        "deposit": details_block.get("deposit"),
        "rental_price": details_block.get("rentalPrice"),
        "num_bedrooms": details_block.get("numOfBedrooms"),
        "num_rooms": details_block.get("numOfRooms"),
        "postal_code": details_block.get("postalCode"),
        "house_number": details_block.get("houseNumber"),
        "house_number_addition": details_block.get("houseNumberAddition"),
        "energy_label_id": details_block.get("energyId"),
        "pets_allowed": details_block.get("candidatePetsAllowed"),
        "smoking_allowed": details_block.get("candidateSmokingAllowed"),
        "min_age": details_block.get("candidateMinAgeId"),
        "max_age": details_block.get("candidateMaxAgeId"),
        "suitable_for_persons": details_block.get("suitableForNumberOfPersons"),
        "registration_allowed": details_block.get("isRegistrationAllowed"),
        "landlord_name": details_block.get("landlordDisplayName"),
        "landlord_member_since": details_block.get("landlordMemberSince"),
        "landlord_last_seen": details_block.get("landlordLastLoggedOn"),
        "landlord_response_rate": details_block.get("responseRate"),
        "landlord_response_time": details_block.get("responseTime"),
        "landlord_verified": details_block.get("isLandlordOBPBankVerified", False),
        "landlord_active_listings": details_block.get("activeListingsCount", 0),
        "create_date": details_block.get("createDate"),
        "publish_date": details_block.get("publishDate"),
    }

    image_list = details_block.get("imageList") or []
    if image_list:
        enriched["additional_images"] = [
            f"https://resources.kamernet.nl/image/{img_id}" for img_id in image_list[:3]
        ]

    time.sleep(1)  # respectful rate limit between detail fetches
    return enriched
