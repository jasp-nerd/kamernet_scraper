from __future__ import annotations

import pytest

from radar.profile import PROFILES_DIR, Profile, SearchConfig, load_profile

BUILTIN_PROFILES = ["generic", "student-amsterdam", "young-professional-randstad", "family-utrecht"]


@pytest.mark.parametrize("name", BUILTIN_PROFILES)
def test_builtin_profile_loads(name):
    profile = load_profile(name)
    assert profile.name
    assert profile.description
    assert profile.scoring_prompt
    assert "{listing_data}" in profile.scoring_prompt
    assert isinstance(profile.search, SearchConfig)
    assert profile.search.city_slug.startswith(("huurwoningen-", "kamers-"))
    assert profile.search.radius_km >= 0
    assert profile.search.sort in {"newest", "price_asc", "price_desc"}


def test_all_profiles_are_discoverable():
    discovered = sorted(p.stem for p in PROFILES_DIR.glob("*.yaml") if ".local" not in p.stem)
    for name in BUILTIN_PROFILES:
        assert name in discovered, f"Missing {name} in {discovered}"


def test_profile_from_path():
    path = PROFILES_DIR / "generic.yaml"
    profile = load_profile(str(path))
    assert profile.name == "generic"


def test_missing_profile_raises():
    with pytest.raises(FileNotFoundError):
        load_profile("definitely-does-not-exist")


def test_profile_from_dict_requires_keys():
    with pytest.raises(ValueError):
        Profile.from_dict({"name": "x"})  # missing search + scoring_prompt


def test_search_config_defaults():
    sc = SearchConfig.from_dict({})
    assert sc.city_slug == "huurwoningen-amsterdam"
    assert sc.radius_km == 5
    assert sc.listing_types == [1, 2, 3, 4]
