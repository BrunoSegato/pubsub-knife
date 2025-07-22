from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pubsub_project_id: str = Field(default="", description="")
    pubsub_emulator_host: str = Field(default="", description="")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
