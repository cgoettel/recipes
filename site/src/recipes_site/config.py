from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# In a checkout, the recipes live two levels above site/src/recipes_site.
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RECIPES_",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://recipes:recipes@localhost:5432/recipes",
    )
    log_level: str = "INFO"
    # Where README.md and the recipe folders live. The image copies them to
    # /app/content; a checkout reads them from the repo root.
    content_dir: Path = _REPO_ROOT
    # Short git SHA baked in at build time; /health reports it.
    asset_version: str = "dev"

    # --- Cloudflare Access, for the owner's private pages only --------------
    # The site is public. Paths under PRIVATE_PREFIX are gated twice: by a
    # Cloudflare Access app at the edge, and by the JWT check in cf_access.py.
    # Without these (and without auth_disabled) the app still starts, since the
    # public site shouldn't go down over private-page config, but every private
    # path answers 403 and startup logs auth.private_pages_closed.
    cf_access_team_domain: str | None = None
    cf_access_audience: str | None = None
    cf_access_allowed_emails: str = ""

    # Tests and local dev only. Never set in prod.
    auth_disabled: bool = False

    def missing_auth_settings(self) -> list[str]:
        missing = []
        if not self.cf_access_team_domain:
            missing.append("RECIPES_CF_ACCESS_TEAM_DOMAIN")
        if not self.cf_access_audience:
            missing.append("RECIPES_CF_ACCESS_AUDIENCE")
        if not self.cf_access_allowed_emails_set:
            missing.append("RECIPES_CF_ACCESS_ALLOWED_EMAILS")
        return missing

    @property
    def cf_access_allowed_emails_set(self) -> set[str]:
        return {e.strip() for e in self.cf_access_allowed_emails.split(",") if e.strip()}


def get_settings() -> Settings:
    return Settings()
