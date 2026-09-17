from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://docmind:docmind@localhost:5432/docmind"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
