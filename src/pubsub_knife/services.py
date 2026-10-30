"""
Operações no emulador sem nenhuma saída no terminal: usadas pelo CLI e pela UI.
Erros da API (NotFound, AlreadyExists...) sobem para quem chamou decidir o que mostrar.
"""
import gzip
import uuid
from contextlib import suppress
from typing import Any

from google.cloud.pubsub_v1.subscriber.message import Message
from google.pubsub_v1.types import PubsubMessage, Subscription, Topic

from pubsub_knife.providers import KnifeContext


def decode_message(message: PubsubMessage | Message) -> dict[str, Any]:
    data = message.data
    attributes = dict(message.attributes)
    if attributes.get("encoding") == "gzip":
        # se o conteúdo não for gzip de verdade, mostra como veio
        with suppress(OSError):
            data = gzip.decompress(data)
    try:
        content: str = data.decode()
    except UnicodeDecodeError:
        content = repr(data)
    decoded: dict[str, Any] = {
        "data": content,
        "id": message.message_id,
        "attributes": attributes,
        "publish_time": (
            message.publish_time.isoformat() if message.publish_time else None
        ),
    }
    if message.ordering_key:
        decoded["ordering_key"] = message.ordering_key
    return decoded


def topic_to_dict(topic: Topic) -> dict[str, Any]:
    return {"name": topic.name, "labels": dict(topic.labels)}


def subscription_to_dict(subscription: Subscription) -> dict[str, Any]:
    ttl = (
        subscription.expiration_policy.ttl
        if "ttl" in subscription.expiration_policy else None
    )
    return {
        "name": subscription.name,
        "topic": subscription.topic,
        "labels": dict(subscription.labels),
        "ack_deadline_seconds": subscription.ack_deadline_seconds,
        "push_endpoint": subscription.push_config.push_endpoint or None,
        "filter": subscription.filter or None,
        "dead_letter_topic": (
            subscription.dead_letter_policy.dead_letter_topic or None
        ),
        "max_delivery_attempts": (
            subscription.dead_letter_policy.max_delivery_attempts or None
        ),
        "delivery_exactly_once": subscription.enable_exactly_once_delivery,
        "ordering": subscription.enable_message_ordering,
        # sem ttl a assinatura nunca expira
        "expiration_ttl_seconds": int(ttl.total_seconds()) if ttl else None,
        "retention_seconds": int(
            subscription.message_retention_duration.total_seconds()
        ),
    }


def list_topics(knife: KnifeContext) -> list[dict[str, Any]]:
    topics = knife.publisher.list_topics(project=knife.project_path)
    return [topic_to_dict(topic) for topic in topics]


def get_topic(knife: KnifeContext, name: str) -> dict[str, Any]:
    return topic_to_dict(knife.publisher.get_topic(topic=knife.topic_path(name)))


def list_subscriptions(knife: KnifeContext) -> list[dict[str, Any]]:
    subscriptions = knife.subscriber.list_subscriptions(project=knife.project_path)
    return [subscription_to_dict(s) for s in subscriptions]


def get_subscription(knife: KnifeContext, name: str) -> dict[str, Any]:
    return subscription_to_dict(
        knife.subscriber.get_subscription(subscription=knife.subscription_path(name))
    )


def pull(
    knife: KnifeContext,
    subscription: str,
    max_messages: int,
    *,
    ack: bool = False,
    release: bool = False
) -> list[dict[str, Any]]:
    """
    Busca até max_messages. Com ack as mensagens são consumidas; com release voltam
    na hora para a assinatura (ack deadline 0). Sem nenhum dos dois, reaparecem
    quando o ack deadline vencer. Toda entrega conta como tentativa para a DLQ.
    """
    path = knife.subscription_path(subscription)
    response = knife.subscriber.pull(
        subscription=path,
        max_messages=max_messages,
        retry=knife.settings.pubsub_retry(),
        timeout=knife.settings.pubsub_timeout
    )
    received = response.received_messages
    ack_ids = [m.ack_id for m in received]
    if ack_ids and ack:
        knife.subscriber.acknowledge(subscription=path, ack_ids=ack_ids)
    elif ack_ids and release:
        knife.subscriber.modify_ack_deadline(
            subscription=path, ack_ids=ack_ids, ack_deadline_seconds=0
        )
    return [decode_message(m.message) for m in received]


def create_topic(knife: KnifeContext, name: str) -> str:
    path = knife.topic_path(name)
    knife.publisher.create_topic(name=path)
    return path


def delete_topic(knife: KnifeContext, name: str) -> str:
    path = knife.topic_path(name)
    knife.publisher.delete_topic(topic=path)
    return path


def create_subscription(knife: KnifeContext, name: str, topic: str) -> str:
    path = knife.subscription_path(name)
    knife.subscriber.create_subscription(name=path, topic=knife.topic_path(topic))
    return path


def delete_subscription(knife: KnifeContext, name: str) -> str:
    path = knife.subscription_path(name)
    knife.subscriber.delete_subscription(subscription=path)
    return path


def create_temporary_subscription(knife: KnifeContext, topic: str) -> str:
    """Assinatura descartável para acompanhar um tópico. Quem cria, remove."""
    return create_subscription(
        knife, f"pk-tail-{topic}-{uuid.uuid4().hex[:8]}", topic
    )


def publish(
    knife: KnifeContext,
    topic: str,
    data: bytes,
    attributes: dict[str, str] | None = None,
    ordering_key: str = ""
) -> str:
    """Publica uma mensagem e espera o id."""
    future = knife.publisher.publish(
        knife.topic_path(topic), data, ordering_key=ordering_key,
        **(attributes or {})
    )
    message_id: str = future.result(timeout=knife.settings.pubsub_timeout)
    return message_id
