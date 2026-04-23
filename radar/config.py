"""Runtime settings loaded from environment / .env file."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ──
    database_url: str | None = Field(
        default=None,
        description="Postgres connection string. If unset, the scraper runs without persistence.",
    )

    # ── AI scoring (OpenRouter) ──
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openrouter_fallback_model: str = "deepseek/deepseek-v3.2"

    # ── Notifications: Discord (native rich embeds) ──
    discord_webhook_url: str | None = None

    # ── Notifications: Telegram (native subscriber flow) ──
    telegram_bot_token: str | None = None
    telegram_password: str | None = Field(
        default=None,
        description=(
            "Password users send with /start <password> to subscribe. "
            "Required if TELEGRAM_BOT_TOKEN is set, otherwise anyone who finds the bot can subscribe."
        ),
    )
    telegram_score_threshold: int = 80

    # ── Notifications: Apprise (100+ channels) ──
    apprise_urls: str | None = Field(
        default=None,
        description=(
            "Comma-separated Apprise URLs (e.g. 'ntfy://mytopic,slack://tokenA/tokenB/tokenC'). "
            "See https://github.com/caronc/apprise/wiki for syntax."
        ),
    )
    apprise_score_threshold: int = 0

    # ── Scraper scheduling ──
    check_interval_min: int = 50
    check_interval_max: int = 70

    # ── Profile ──
    profile: str = Field(
        default="generic",
        description="Profile name (looks up profiles/<name>.yaml) or absolute path to a YAML file.",
    )

    # ── User agent ──
    user_agent: str = "Mozilla/5.0 (compatible; KamernetRadar/1.0; +https://github.com/jasp/kamernet-radar)"


def load_settings() -> Settings:
    """Entry point for resolving settings from env/.env."""
    return Settings()
