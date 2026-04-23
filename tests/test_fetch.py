from radar.fetch import build_search_url
from radar.profile import SearchConfig


def test_build_search_url_uses_city_slug_and_radius():
    sc = SearchConfig(
        city_slug="huurwoningen-utrecht", radius_km=15, max_rent=2500, min_size=50, sort="newest"
    )
    url = build_search_url(sc)
    assert url.startswith("https://kamernet.nl/huren/huurwoningen-utrecht?")
    assert "radius=15" in url
    assert "maxRent=2500" in url
    assert "minSize=50" in url
    assert "sort=1" in url


def test_build_search_url_price_asc_sort():
    sc = SearchConfig(city_slug="huurwoningen-amsterdam", sort="price_asc")
    assert "sort=2" in build_search_url(sc)


def test_build_search_url_unknown_sort_defaults_to_newest():
    sc = SearchConfig(city_slug="huurwoningen-amsterdam", sort="bogus")
    assert "sort=1" in build_search_url(sc)
