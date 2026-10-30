MESSAGE_NO_RESULT = "No results."

MESSAGE_EMULATOR_UNAVAILABLE = (
    "Pub/Sub emulator is not reachable at {}. "
    "Start it with `docker compose up -d` or set --emulator-host."
)

MESSAGE_TOPIC_IS_ALREADY_EXISTS = "Topic already exists."
MESSAGE_TOPIC_CREATED = "Topic {} successfully created."
MESSAGE_TOPIC_NOT_FOUND = "Topic not found."
MESSAGE_TOPIC_DELETED = "Topic {} successfully deleted."

MESSAGE_SUBSCRIPTION_DELETED = "Subscription {} successfully deleted."
MESSAGE_SUBSCRIPTION_CREATED = "Subscription {} successfully created."
MESSAGE_SUBSCRIPTION_NOT_FOUND = "Subscription not found."
MESSAGE_SUBSCRIPTION_IS_ALREADY_EXISTS = "Subscription already exists."

MESSAGE_PUBLISHING = "Publishing to {}..."
MESSAGE_PUBLISHED = "Message published with ID: {} ({}s)"
MESSAGE_PUBLISHED_ERROR = "Failed to publish message: {}"
MESSAGE_PUBLISHED_INTERVAL = "Waiting {}s before publishing another message..."
MESSAGE_PUBLISH_MISSING_MESSAGE = (
    "Provide a message as argument, @file or '-' to read from stdin."
)
MESSAGE_PUBLISH_FILE_NOT_FOUND = "File not found: {}"
MESSAGE_PUBLISH_INVALID_JSON = "Invalid JSON message."

MESSAGE_CONSUMER_ALL_ACK = "All messages were acknowledged."

MESSAGE_APPLY_FILE_NOT_FOUND = "File not found: {}"
MESSAGE_APPLY_INVALID_FILE = "Invalid file {}:\n{}"
MESSAGE_APPLY_EMPTY = "No topics declared in {}."
MESSAGE_APPLY_EXISTS_HINT = (
    "[dim]Existing resources were not changed. "
    "Use --recreate to apply changes to them.[/dim]"
)

MESSAGE_TAIL_TARGET = "Provide a subscription or --topic (but not both)."
MESSAGE_TAIL_LISTENING = "[dim]Listening on {} (Ctrl+C to stop)...[/dim]"
MESSAGE_TAIL_STOPPED = "[dim]Stopped after {} message(s).[/dim]"
MESSAGE_TAIL_ERROR = "Streaming pull failed: {}"
