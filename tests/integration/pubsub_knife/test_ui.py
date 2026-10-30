import pytest
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
            assert f"pk tail -t {constants.TEST_TOPIC}" in notification.message

    async def test_reload_shows_new_resources(self, app, cli_runner, cli_app):
        async with app.run_test() as pilot:
            await settle(app, pilot)
            utils.invoke_command(
                cli_runner, cli_app, "topic", ["create", constants.TEST_TOPIC]
            )
            await pilot.press("r")
            await settle(app, pilot)
            assert tree_labels(app) == {constants.TEST_TOPIC: []}
