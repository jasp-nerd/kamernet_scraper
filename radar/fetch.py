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

# Kamernet's rent/size/radius URL params are indexes into fixed ladders, not
# real-world values — raw euros/m²/km silently disable or distort the filter
# (e.g. maxRent=2300 is out of range and dropped; minSize=25 means "90 m²").
# Ladders ported from the kamernet-mcp project and verified against the live
# site (July 2026).
MAX_RENT_LADDER: list[int] = [*range(0, 1600, 100), 1750, *range(2000, 6250, 250)]
MIN_SIZE_LADDER: list[int] = [0, 6, *range(8, 42, 2), 45, 50, 60, 70, 80, 90, 100]
RADIUS_KM_TO_ID: dict[int, int] = {0: 1, 1: 2, 2: 3, 5: 4, 10: 5, 20: 6}


def _max_rent_param(euros: int) -> int | None:
    """euros → maxRent ladder index; rounds UP so no affordable listing is excluded.

    Returns None when the budget exceeds the ladder (no server-side filtering).
    """
    for index, step in enumerate(MAX_RENT_LADDER):
        if step >= euros:
            return index
    return None


def _min_size_param(m2: int) -> int | None:
    """m² → minSize id (ladder index + 1); rounds DOWN so no matching listing is excluded."""
    candidates = [i for i, step in enumerate(MIN_SIZE_LADDER) if step <= m2]
    if not candidates:
        return None
    return candidates[-1] + 1


def _radius_param(km: int) -> int:
    """km → radius id; rounds UP to the nearest radius Kamernet supports (max 20 km)."""
    for supported in sorted(RADIUS_KM_TO_ID):
        if supported >= km:
            return RADIUS_KM_TO_ID[supported]
    return RADIUS_KM_TO_ID[20]


def build_search_url(search: SearchConfig) -> str:
    """Build a Kamernet search URL from profile search config (real-world units)."""
    params: dict[str, Any] = {
        "pageNo": 1,
        "radius": _radius_param(search.radius_km),
        "searchView": 1,
        "sort": _SORT_MAP.get(search.sort, 1),
    }
    if search.max_rent > 0:
        rent_index = _max_rent_param(search.max_rent)
        if rent_index is not None:
            params["maxRent"] = rent_index
    if search.min_size > 0:
        size_id = _min_size_param(search.min_size)
        if size_id is not None and size_id > 1:  # id 1 = 0 m² = no filter
            params["minSize"] = size_id
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
    result = _apply_profile_filters(listings + top, search)

    log.info("found %d listings", len(result))
    return result


def _apply_profile_filters(listings: list[dict], search: SearchConfig) -> list[dict]:
    """Enforce the profile's exact criteria client-side.

    The server-side ladder params round inclusively (rent up, size down) and
    sponsored top ads ignore filters entirely, so listings just outside the
    profile's bounds can still come back. Items missing a field are kept.
    """
    result = listings
    if search.listing_types:
        allowed = set(search.listing_types)
        result = [item for item in result if item.get("listingType") in allowed]
    if search.max_rent > 0:
        result = [
            item
            for item in result
            if not item.get("totalRentalPrice") or item["totalRentalPrice"] <= search.max_rent
        ]
    if search.min_size > 0:
        result = [
            item for item in result if not item.get("surfaceArea") or item["surfaceArea"] >= search.min_size
        ]
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
