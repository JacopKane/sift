"""Settings, read once from the environment.

Only the classify layer reads this. The scanner and catalog never do — that is
what keeps them portable to a CLI or a native shell.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sift_provider: str = "google_genai"
    sift_model: str = "gemini-3.1-flash-lite"

    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    @property
    def provider(self) -> str:
        return self.sift_provider

    @property
    def model(self) -> str:
        return self.sift_model

    @property
    def api_key(self) -> str | None:
        """The key for whichever provider is selected, or None if it isn't set."""
        return {
            "google_genai": self.google_api_key,
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
        }.get(self.sift_provider)


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
