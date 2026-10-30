from functools import cached_property

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import PublisherOptions

from pubsub_knife import constants
from pubsub_knife.config import EmulatorUnavailableError, Settings
from pubsub_knife.utils import fail


class KnifeContext:
    """
    Cria os clients sob demanda: comandos como --help não pagam o custo de
    abrir conexões gRPC e só falham se o emulador for realmente necessário.
    """

    def __init__(self, settings: Settings, project_overridden: bool = False) -> None:
        self.settings = settings
        self.project_overridden = project_overridden

    @property
    def project_id(self) -> str:
        return self.settings.pubsub_project_id

    @property
    def project_path(self) -> str:
        return f"projects/{self.project_id}"

    def _ensure_emulator(self) -> None:
        self.settings.configure_emulator()
        try:
            self.settings.check_emulator()
        except EmulatorUnavailableError:
            fail(constants.MESSAGE_EMULATOR_UNAVAILABLE.format(
                self.settings.pubsub_emulator_host
            ))

    @cached_property
    def publisher(self) -> pubsub_v1.PublisherClient:
        self._ensure_emulator()
        # sem ordering key as mensagens se comportam como antes
        return pubsub_v1.PublisherClient(
            publisher_options=PublisherOptions(enable_message_ordering=True)
        )

    @cached_property
    def subscriber(self) -> pubsub_v1.SubscriberClient:
        self._ensure_emulator()
        return pubsub_v1.SubscriberClient()

    def topic_path(self, topic: str) -> str:
        return f"{self.project_path}/topics/{topic}"

    def subscription_path(self, subscription: str) -> str:
        return f"{self.project_path}/subscriptions/{subscription}"
