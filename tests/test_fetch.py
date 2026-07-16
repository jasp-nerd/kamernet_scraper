from radar.fetch import (
    _apply_profile_filters,
    _max_rent_param,
    _min_size_param,
    _radius_param,
    build_search_url,
)
from radar.profile import SearchConfig


def test_build_search_url_converts_units_to_kamernet_ladder_ids():
    sc = SearchConfig(
        city_slug="huurwoningen-utrecht", radius_km=15, max_rent=2500, min_size=50, sort="newest"
    )
    url = build_search_url(sc)
    assert url.startswith("https://kamernet.nl/huren/huurwoningen-utrecht?")
    assert "radius=6" in url  # 15 km rounds up to 20 km (id 6)
    assert "maxRent=19" in url  # €2500 is ladder index 19
    assert "minSize=21" in url  # 50 m² is ladder id 21
    assert "sort=1" in url


def test_build_search_url_omits_disabled_filters():
    sc = SearchConfig(city_slug="huurwoningen-amsterdam", max_rent=0, min_size=0)
    url = build_search_url(sc)
    assert "maxRent" not in url
    assert "minSize" not in url


def test_build_search_url_price_asc_sort():
    sc = SearchConfig(city_slug="huurwoningen-amsterdam", sort="price_asc")
    assert "sort=2" in build_search_url(sc)


def test_build_search_url_unknown_sort_defaults_to_newest():
    sc = SearchConfig(city_slug="huurwoningen-amsterdam", sort="bogus")
    assert "sort=1" in build_search_url(sc)


def test_max_rent_rounds_up_to_next_ladder_step():
    assert _max_rent_param(500) == 5
    assert _max_rent_param(2300) == 19  # next step is €2500
    assert _max_rent_param(9000) is None  # above the ladder: no server filter


def test_min_size_rounds_down_to_previous_ladder_step():
    assert _min_size_param(25) == 11  # previous step is 24 m² (id 11)
    assert _min_size_param(90) == 25
    assert _min_size_param(500) == 26  # clamps to the 100 m² top step


def test_radius_rounds_up_to_supported_radius():
    assert _radius_param(5) == 4
    assert _radius_param(7) == 5  # rounds up to 10 km
    assert _radius_param(50) == 6  # clamps to 20 km


def test_apply_profile_filters_enforces_exact_bounds():
    listings = [
        {"listingType": 1, "totalRentalPrice": 900, "surfaceArea": 20},
        {"listingType": 2, "totalRentalPrice": 2400, "surfaceArea": 60},
        {"listingType": 2, "totalRentalPrice": 1800, "surfaceArea": 12},
        {"listingType": 8, "totalRentalPrice": 800, "surfaceArea": 30},
    ]
    sc = SearchConfig(listing_types=[1, 2], max_rent=2300, min_size=15)
    result = _apply_profile_filters(listings, sc)
    assert result == [{"listingType": 1, "totalRentalPrice": 900, "surfaceArea": 20}]


def test_apply_profile_filters_keeps_items_missing_fields():
    listings = [{"listingType": 2, "totalRentalPrice": None, "surfaceArea": None}]
    sc = SearchConfig(listing_types=[2], max_rent=1000, min_size=30)
    assert _apply_profile_filters(listings, sc) == listings
