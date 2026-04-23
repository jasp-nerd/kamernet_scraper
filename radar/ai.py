"""AI scoring via OpenRouter. Rubric comes from the active profile."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from radar.profile import Profile

log = logging.getLogger(__name__)

ENERGY_LABELS = {1: "A++", 2: "A+", 3: "A", 4: "B", 5: "C", 6: "D", 7: "E", 8: "F", 9: "G"}
TYPE_LABELS = {1: "Room (shared house)", 2: "Apartment", 3: "Studio", 4: "Studio"}
FURNISHING_LABELS = {1: "Unfurnished", 2: "Unfurnished", 3: "Semi-furnished", 4: "Furnished"}


def _listing_data_block(listing: dict) -> str:
    type_text = TYPE_LABELS.get(listing.get("listingType", 0), "Unknown")
    furnish_text = FURNISHING_LABELS.get(listing.get("furnishingId", 0), "Unknown")
    energy_text = ENERGY_LABELS.get(listing.get("energy_label_id"), "Unknown")
    avail_start = listing.get("availabilityStartDate") or listing.get("availability_start") or "Unknown"
    avail_end = listing.get("availabilityEndDate") or listing.get("availability_end") or "Indefinite"
    return (
        f"- Title: {listing.get('detailed_title', 'N/A')}\n"
        f"- Price: EUR {listing.get('totalRentalPrice', 'N/A')}/month\n"
        f"- Deposit: EUR {listing.get('deposit', 'N/A')}\n"
        f"- Utilities included: {listing.get('utilitiesIncluded', 'Unknown')}\n"
        f"- Surface area: {listing.get('surfaceArea', 'N/A')} m2\n"
        f"- City: {listing.get('city', 'N/A')}, Postal code: {listing.get('postal_code', 'N/A')}\n"
        f"- Street: {listing.get('street', 'N/A')} {listing.get('house_number', '')}\n"
        f"- Type: {type_text} (listingType id={listing.get('listingType')}; "
        "1=Room in shared house, 2=Apartment self-contained, 3/4=Studio self-contained)\n"
        f"- Furnishing: {furnish_text}\n"
        f"- Rooms: {listing.get('num_rooms', 'N/A')}, Bedrooms: {listing.get('num_bedrooms', 'N/A')}\n"
        f"- Energy label: {energy_text}\n"
        f"- Pets allowed: {listing.get('pets_allowed', 'Unknown')}\n"
        f"- Smoking allowed: {listing.get('smoking_allowed', 'Unknown')}\n"
        f"- Registration allowed: {listing.get('registration_allowed', 'Unknown')}\n"
        f"- Age range: {listing.get('min_age', 'N/A')}-{listing.get('max_age', 'N/A')}\n"
        f"- Suitable for: {listing.get('suitable_for_persons', 'N/A')} person(s) "
        "[NOTE: this field is unreliable on Kamernet — cross-check with surface and description]\n"
        f"- Available from: {avail_start}\n"
        f"- Available until: {avail_end}\n"
        f"- Description: {listing.get('detailed_description', '') or ''}"
    )


def _build_prompt(profile: Profile, listing: dict) -> str:
    data_block = _listing_data_block(listing)
    rubric = profile.scoring_prompt
    if "{listing_data}" in rubric:
        return rubric.format(listing_data=data_block)
    return f'{rubric}\n\n## Listing Data\n{data_block}\n\n## Response\nRespond with ONLY valid JSON: {{"score": <int 0-100>, "reasoning": "<1-2 sentences>"}}'


def _call_openrouter(prompt: str, model: str, api_key: str) -> dict[str, Any] | None:
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.2,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        log.warning("openrouter request failed (%s): %s", model, exc)
        return None

    if resp.status_code != 200:
        log.warning("openrouter %s returned %s", model, resp.status_code)
        return None

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        log.warning("openrouter %s: malformed response envelope", model)
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        score_match = re.search(r'"score"\s*:\s*(\d+)', content)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', content)
        if score_match:
            return {
                "score": int(score_match.group(1)),
                "reasoning": reasoning_match.group(1) if reasoning_match else "(unstructured response)",
            }
        log.warning("openrouter %s: failed to parse response", model)
        return None


def score_listing(
    listing: dict,
    profile: Profile,
    api_key: str,
    model: str,
    fallback_model: str,
) -> tuple[int | None, str | None]:
    """Score a listing against the profile's rubric. Returns (score, reasoning) or (None, None)."""
    prompt = _build_prompt(profile, listing)

    result = _call_openrouter(prompt, model, api_key)
    if result is None:
        log.info("falling back to %s", fallback_model)
        result = _call_openrouter(prompt, fallback_model, api_key)

    if not result or "score" not in result:
        return (None, None)

    score = max(0, min(100, int(result["score"])))
    reasoning = str(result.get("reasoning", ""))[:500]
    return (score, reasoning)
