import asyncio
import uuid

import pytest
from google.api_core.exceptions import NotFound
from rich.console import Console
from textual.widgets import RichLog, Static, Tree

from pubsub_knife.config import Settings
from pubsub_knife.providers import KnifeContext
from pubsub_knife.tui import KnifeApp
from tests import constants, utils

pytestmark = [
    pytest.mark.integration,
]


@pytest.fixture
def app() -> KnifeApp:
    # Settings lê o PUBSUB_PROJECT_ID do projeto isolado do teste
    return KnifeApp(KnifeContext(Settings()))


async def settle(app: KnifeApp, pilot) -> None:
    await app.workers.wait_for_complete()
    await pilot.pause()


def tree_labels(app: KnifeApp) -> dict[str, list[str]]:
    tree = app.query_one(Tree)
    return {
        str(node.label): [str(child.label) for child in node.children]
        for node in tree.root.children
    }


def select(app: KnifeApp, label: str) -> None:
    tree = app.query_one(Tree)
    for node in tree.root.children:
        for candidate in (node, *node.children):
            if str(candidate.label) == label:
                tree.move_cursor(candidate)
                return
    raise AssertionError(f"{label} not in tree")


def details_text(app: KnifeApp) -> str:
    console = Console(width=200)
    with console.capture() as capture:
        console.print(app.query_one("#details", Static).content)
    return capture.get()


def log_text(app: KnifeApp) -> str:
    return "\n".join(line.text for line in app.query_one(RichLog).lines)


def notifications(app: KnifeApp) -> list[str]:
    return [n.message for n in app._notifications]


async def wait_for(condition, timeout: float = 10) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.1)


async def fill(pilot, app: KnifeApp, values: dict[str, str]) -> None:
    """Preenche o formulário aberto e confirma com ctrl+s."""
    for name, value in values.items():
        widget = app.screen.query_one(f"#{name}")
        if hasattr(widget, "load_text"):
            widget.load_text(value)
        else:
            widget.value = value
    await pilot.press("ctrl+s")
    await settle(app, pilot)


class TestUi:

    async def test_lists_topics_with_their_subscriptions(self, app, ready_subscription):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            assert tree_labels(app) == {
                constants.TEST_TOPIC: [constants.TEST_SUBSCRIPTION]
            }

    async def test_empty_project(self, app):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            assert tree_labels(app) == {"nenhum tópico": []}

    async def test_shows_subscription_details(self, app, ready_subscription):
        topic_path, _ = ready_subscription
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_SUBSCRIPTION)
            await pilot.pause()
            assert topic_path in details_text(app)

    async def test_peek_does_not_consume(
        self,
        app,
        ready_subscription,
        publisher_client,
        subscriber_client
    ):
        topic_path, subscription_path = ready_subscription
        publisher_client.publish(topic_path, b'{"id": 42}').result()

        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_SUBSCRIPTION)
            await pilot.press("p")
            await settle(app, pilot)
            assert '"id": 42' in log_text(app)

        # a mensagem voltou para a assinatura na hora
        response = subscriber_client.pull(
            subscription=subscription_path, max_messages=10, timeout=5
        )
        assert [m.message.data for m in response.received_messages] == [b'{"id": 42}']

    async def test_peek_on_topic_only_warns(self, app, ready_subscription):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_TOPIC)
            await pilot.press("p")
            await settle(app, pilot)
            assert [n.message for n in app._notifications] == [
                "Selecione uma assinatura."
            ]

    async def test_peek_on_push_subscription_only_warns(
        self,
        app,
        cli_runner,
        cli_app,
        tmp_path
    ):
        spec = tmp_path / "pubsub.yaml"
        spec.write_text(
            f"topics:\n  {constants.TEST_TOPIC}:\n    subscriptions:\n"
            f"      - name: {constants.TEST_SUBSCRIPTION}\n"
            "        push_endpoint: http://localhost:9/push\n"
        )
        utils.invoke_command(cli_runner, cli_app, "apply", [spec])

        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_SUBSCRIPTION)
            await pilot.press("p")
            await settle(app, pilot)
            [notification] = app._notifications
            assert "Assinatura push" in notification.message
            assert "t (ao vivo)" in notification.message

    async def test_reload_shows_new_resources(self, app, cli_runner, cli_app):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            utils.invoke_command(
                cli_runner, cli_app, "topic", ["create", constants.TEST_TOPIC]
            )
            await pilot.press("r")
            await settle(app, pilot)
            assert tree_labels(app) == {constants.TEST_TOPIC: []}


class TestUiActions:

    async def test_create_topic(self, app, publisher_client):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            await pilot.press("c")
            await fill(pilot, app, {"name": constants.TEST_TOPIC})
            await settle(app, pilot)
            assert tree_labels(app) == {constants.TEST_TOPIC: []}
        utils.get_topic(publisher_client, utils.get_topic_path(publisher_client))

    async def test_create_form_requires_name(self, app):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            await pilot.press("c")
            await fill(pilot, app, {"name": ""})
            # o formulário continua aberto com o erro
            assert "Preencha: Nome." in str(app.screen.query_one("#error").content)
            await pilot.press("escape")
            assert tree_labels(app) == {"nenhum tópico": []}

    async def test_create_subscription_for_selected_topic(
        self,
        app,
        ready_topic,
        subscriber_client
    ):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_TOPIC)
            await pilot.press("s")
            # o tópico vem preenchido com o selecionado
            assert app.screen.query_one("#topic").value == constants.TEST_TOPIC
            await fill(pilot, app, {"name": constants.TEST_SUBSCRIPTION})
            await settle(app, pilot)
            assert tree_labels(app) == {
                constants.TEST_TOPIC: [constants.TEST_SUBSCRIPTION]
            }
        subscription = utils.get_subscription(
            subscriber_client, utils.get_subscription_path(subscriber_client)
        )
        assert subscription.topic == ready_topic

    async def test_delete_subscription_after_confirmation(
        self,
        app,
        ready_subscription,
        subscriber_client
    ):
        _, subscription_path = ready_subscription
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_SUBSCRIPTION)
            await pilot.press("d")
            await pilot.press("n")
            await settle(app, pilot)
            utils.get_subscription(subscriber_client, subscription_path)

            await pilot.press("d")
            await pilot.press("y")
            await settle(app, pilot)
            assert tree_labels(app) == {constants.TEST_TOPIC: []}
        with pytest.raises(NotFound):
            utils.get_subscription(subscriber_client, subscription_path)

    async def test_publish_to_selected_topic(self, app, ready_subscription):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_SUBSCRIPTION)
            await pilot.press("m")
            await fill(pilot, app, {
                "data": '{"id": 7}',
                "attributes": "type=created, source=ui",
                "ordering_key": "k1",
            })
            assert any("Mensagem publicada" in n for n in notifications(app))

            await pilot.press("p")
            await settle(app, pilot)
            text = log_text(app)
            assert '"id": 7' in text
            assert "'source': 'ui'" in text
            assert "ordering_key: k1" in text

    async def test_publish_rejects_invalid_attribute(self, app, ready_topic):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_TOPIC)
            await pilot.press("m")
            await fill(pilot, app, {"data": "x", "attributes": "semvalor"})
            assert "Atributo inválido 'semvalor'" in str(
                app.screen.query_one("#error").content
            )

    async def test_live_tail_follows_topic_and_cleans_up(
        self,
        app,
        ready_topic,
        publisher_client,
        subscriber_client
    ):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_TOPIC)
            await pilot.press("t")
            await settle(app, pilot)
            assert app.live
            assert app.live.future

            publisher_client.publish(ready_topic, b"ao vivo!").result()
            await wait_for(lambda: "ao vivo!" in log_text(app))

            await pilot.press("t")
            await settle(app, pilot)
            assert app.live is None

        subscriptions = subscriber_client.list_subscriptions(
            project=f"projects/{utils.current_project()}"
        )
        assert not [s for s in subscriptions if "pk-tail-" in s.name]

    async def test_quitting_while_live_cleans_up(
        self,
        app,
        ready_topic,
        subscriber_client
    ):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            select(app, constants.TEST_TOPIC)
            await pilot.press("t")
            await settle(app, pilot)
            await pilot.press("q")

        subscriptions = subscriber_client.list_subscriptions(
            project=f"projects/{utils.current_project()}"
        )
        assert not [s for s in subscriptions if "pk-tail-" in s.name]

    async def test_apply_spec_file(self, cli_app, subscriber_client, tmp_path):
        spec = tmp_path / "pubsub.yaml"
        spec.write_text(
            f"topics:\n  {constants.TEST_TOPIC}:\n"
            f"    subscriptions: [{constants.TEST_SUBSCRIPTION}]\n"
        )
        app = KnifeApp(KnifeContext(Settings()), spec_file=spec)
        async with app.run_test() as pilot:
            await settle(app, pilot)
            await pilot.press("a")
            await settle(app, pilot)
            assert tree_labels(app) == {
                constants.TEST_TOPIC: [constants.TEST_SUBSCRIPTION]
            }
            assert any("2 criados" in n for n in notifications(app))

    async def test_apply_missing_file(self, tmp_path):
        app = KnifeApp(KnifeContext(Settings()), spec_file=tmp_path / "nope.yaml")
        async with app.run_test() as pilot:
            await settle(app, pilot)
            await pilot.press("a")
            await settle(app, pilot)
            assert any("File not found" in n for n in notifications(app))

    async def test_switch_project(self, app, publisher_client, subscriber_client):
        other = f"{constants.PROJECT_PREFIX}-{uuid.uuid4().hex[:12]}"
        publisher_client.create_topic(name=f"projects/{other}/topics/elsewhere")
        try:
            async with app.run_test() as pilot:
                await settle(app, pilot)
                await pilot.press("g")
                await fill(pilot, app, {"project": other})
                await settle(app, pilot)
                assert tree_labels(app) == {"elsewhere": []}
                assert other in app.sub_title
                assert app.knife.project_overridden
        finally:
            utils.cleanup_project(publisher_client, subscriber_client, other)
