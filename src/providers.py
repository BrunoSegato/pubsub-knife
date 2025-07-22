from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import BatchSettings, PublishFlowControl, PublisherOptions, LimitExceededBehavior

from src.config import settings


def get_publisher_client() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def get_publisher_with_batch_settings() -> pubsub_v1.PublisherClient:
    batch_size = 100

    batch_settings = BatchSettings(
        max_messages=batch_size,
        max_bytes=5 * 1024 * 1024,  # 5 MB
        max_latency=1.0,  # 1 segundo
    )
    publisher_options = PublisherOptions(
        flow_control=PublishFlowControl(
            message_limit=batch_size * 2,
            byte_limit=10 * 1024 * 1024,
            limit_exceeded_behavior=LimitExceededBehavior.BLOCK
        )
    )
    return pubsub_v1.PublisherClient(batch_settings=batch_settings, publisher_options=publisher_options)


def get_subscriber_client() -> pubsub_v1.SubscriberClient:
    return pubsub_v1.SubscriberClient()


def get_topic_path(topic: str) -> str:
    client = get_publisher_client()
    return client.topic_path(settings.pubsub_project_id, topic)
