import pytest
from pydantic import ValidationError

from pubsub_knife.apply import PubSubSpec

pytestmark = [
    pytest.mark.unit,
    pytest.mark.apply,
]


class TestPubSubSpec:

    def test_minimal_topics(self):
        spec = PubSubSpec.model_validate({"topics": {"orders": None, "dlq": {}}})
        assert set(spec.topics) == {"orders", "dlq"}
        assert spec.topics["orders"].subscriptions == []

    def test_subscription_as_string_or_object(self):
        spec = PubSubSpec.model_validate({
            "topics": {
                "orders": {
                    "subscriptions": [
                        "orders-worker",
                        {"name": "orders-filtered", "filter": 'attributes.a = "1"'},
                    ]
                }
            }
        })
        subs = spec.topics["orders"].subscriptions
        assert [s.name for s in subs] == ["orders-worker", "orders-filtered"]
        assert subs[1].filter_ == 'attributes.a = "1"'

    def test_dead_letter_topic_must_be_declared(self):
        with pytest.raises(ValidationError, match="must be declared"):
            PubSubSpec.model_validate({
                "topics": {
                    "orders": {
                        "subscriptions": [
                            {"name": "orders-worker", "dead_letter_topic": "dlq"}
                        ]
                    }
                }
            })

    def test_duplicated_subscription(self):
        with pytest.raises(ValidationError, match="duplicated subscription"):
            PubSubSpec.model_validate({
                "topics": {
                    "a": {"subscriptions": ["same"]},
                    "b": {"subscriptions": ["same"]},
                }
            })

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError):
            PubSubSpec.model_validate({
                "topics": {"a": {"subscriptions": [{"name": "s", "ack": 10}]}}
            })

    def test_ack_deadline_range(self):
        with pytest.raises(ValidationError):
            PubSubSpec.model_validate({
                "topics": {"a": {"subscriptions": [{"name": "s", "ack_deadline": 5}]}}
            })
