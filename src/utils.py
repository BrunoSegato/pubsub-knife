from google.cloud.pubsub_v1.futures import Future
from rich import print as rich_print


def callback(future: Future) -> None:
    try:
        msg_id = future.result()
        rich_print(f"🎯 Callback: Mensagem publicada com ID {msg_id}")
    except Exception as e:
        rich_print(f"❌ Callback: Falha ao publicar mensagem: {e}")
