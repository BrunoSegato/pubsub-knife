import os
import socket

from google.api_core.retry import Retry
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmulatorUnavailableError(Exception):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pubsub_project_id: str = Field(default="dummy-project")
    pubsub_emulator_host: str = Field(default="localhost:8085")

    pubsub_timeout: float = Field(default=10.0)
    pubsub_retry_initial: float = Field(default=0.1)
    pubsub_retry_maximum: float = Field(default=5.0)
    pubsub_retry_deadline: float = Field(default=30.0)
    pubsub_retry_multiplier: float = Field(default=1.3)
    pubsub_connect_timeout: float = Field(default=2.0)

    def pubsub_retry(self) -> Retry:
        return Retry(
            initial=self.pubsub_retry_initial,
            maximum=self.pubsub_retry_maximum,
            multiplier=self.pubsub_retry_multiplier,
            deadline=self.pubsub_retry_deadline
        )

    def configure_emulator(self) -> None:
        """
        A lib do Google só enxerga o emulador via os.environ. Sem isso, um valor
        lido do .env seria ignorado e o client tentaria falar com o GCP real.
        """
        os.environ["PUBSUB_EMULATOR_HOST"] = self.pubsub_emulator_host

    def check_emulator(self) -> None:
        host, _, port = self.pubsub_emulator_host.rpartition(":")
        try:
            with socket.create_connection(
                (host or "localhost", int(port)),
                timeout=self.pubsub_connect_timeout
            ):
                pass
        except (OSError, ValueError) as e:
            raise EmulatorUnavailableError(self.pubsub_emulator_host) from e
