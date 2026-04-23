"""Profile: search criteria + AI scoring rubric, loaded from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


@dataclass
class SearchConfig:
    """What the scraper searches for on Kamernet."""

    city_slug: str = "huurwoningen-amsterdam"
    radius_km: int = 5
    min_size: int = 0
    max_rent: int = 0
    sort: str = "newest"
    listing_types: list[int] = field(default_factory=lambda: [1, 2, 3, 4])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchConfig:
        return cls(
            city_slug=data.get("city_slug", cls.city_slug),
            radius_km=int(data.get("radius_km", cls.radius_km)),
            min_size=int(data.get("min_size", cls.min_size)),
            max_rent=int(data.get("max_rent", cls.max_rent)),
            sort=str(data.get("sort", cls.sort)),
            listing_types=list(data.get("listing_types") or [1, 2, 3, 4]),
        )


@dataclass
class Profile:
    """A search + scoring configuration. Load one per run."""

    name: str
    description: str
    search: SearchConfig
    scoring_prompt: str
    source_path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: Path | None = None) -> Profile:
        missing = [k for k in ("name", "search", "scoring_prompt") if k not in data]
        if missing:
            raise ValueError(f"Profile YAML missing required keys: {missing}")
        return cls(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            search=SearchConfig.from_dict(data["search"] or {}),
            scoring_prompt=str(data["scoring_prompt"]),
            source_path=source_path,
        )


def load_profile(name_or_path: str) -> Profile:
    """Load a profile by name (looks up profiles/<name>.yaml) or by absolute/relative path."""
    candidate = Path(name_or_path)
    if candidate.suffix in (".yaml", ".yml") and candidate.exists():
        path = candidate
    else:
        path = PROFILES_DIR / f"{name_or_path}.yaml"
        if not path.exists():
            available = sorted(p.stem for p in PROFILES_DIR.glob("*.yaml"))
            raise FileNotFoundError(
                f"Profile not found: {name_or_path!r}. "
                f"Looked for {path}. Available built-in profiles: {available}"
            )
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Profile.from_dict(data, source_path=path)
