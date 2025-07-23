from functools import lru_cache

from google.api_core.retry import Retry
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pubsub_project_id: str = Field(default="", description="")
    pubsub_emulator_host: str = Field(default="", description="")

    pubsub_timeout: float = Field(default=30.0)
    pubsub_retry_initial: float = Field(default=0.1)
    pubsub_retry_maximum: float = Field(default=60.0)
    pubsub_retry_deadline: float = Field(default=600.0)
    pubsub_retry_multiplier: float = Field(default=1.3)

    def pubsub_retry(self) -> Retry:
        return Retry(
            initial=self.pubsub_retry_initial,
            maximum=self.pubsub_retry_maximum,
            multiplier=self.pubsub_retry_multiplier,
            deadline=self.pubsub_retry_deadline
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
