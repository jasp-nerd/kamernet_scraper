from radar.ai import _build_prompt, _listing_data_block
from radar.profile import Profile, SearchConfig

SAMPLE_LISTING = {
    "detailed_title": "Cozy studio near Vondelpark",
    "totalRentalPrice": 1450,
    "deposit": 1500,
    "utilitiesIncluded": True,
    "surfaceArea": 32,
    "city": "Amsterdam",
    "postal_code": "1071 AB",
    "street": "Willemsparkweg",
    "house_number": "12",
    "listingType": 2,
    "furnishingId": 4,
    "num_rooms": 2,
    "num_bedrooms": 1,
    "energy_label_id": 4,  # B
    "pets_allowed": False,
    "smoking_allowed": False,
    "registration_allowed": True,
    "min_age": 22,
    "max_age": 40,
    "suitable_for_persons": 2,
    "availability_start": "2026-05-01",
    "availability_end": None,
    "detailed_description": "Fully furnished studio, suitable for a couple.",
}


def test_listing_data_block_contains_core_fields():
    block = _listing_data_block(SAMPLE_LISTING)
    assert "Cozy studio near Vondelpark" in block
    assert "EUR 1450" in block
    assert "Willemsparkweg" in block
    assert "1071 AB" in block
    assert "32 m2" in block


def test_build_prompt_substitutes_listing_data_placeholder():
    profile = Profile(
        name="t",
        description="",
        search=SearchConfig(),
        scoring_prompt="Evaluate:\n\n{listing_data}\n\nRespond JSON.",
    )
    rendered = _build_prompt(profile, SAMPLE_LISTING)
    assert "{listing_data}" not in rendered
    assert "EUR 1450" in rendered
    assert "Respond JSON." in rendered


def test_build_prompt_appends_listing_data_when_no_placeholder():
    profile = Profile(
        name="t",
        description="",
        search=SearchConfig(),
        scoring_prompt="Freeform rubric with no placeholder",
    )
    rendered = _build_prompt(profile, SAMPLE_LISTING)
    assert "Freeform rubric with no placeholder" in rendered
    assert "EUR 1450" in rendered
