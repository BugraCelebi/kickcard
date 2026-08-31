import json
from dataclasses import fields
from datetime import datetime

from kickcard.ingest.pusher_client import parse_chat_message


def test_parse_chat_message_extracts_message_from_chat_event() -> None:
    event = {
        "event": "App\\Events\\ChatMessageEvent",
        "data": json.dumps(
            {
                "id": "abc-123",
                "chatroom_id": 42,
                "content": "!paket",
                "type": "message",
                "created_at": "2026-08-31T17:33:27+00:00",
                "sender": {
                    "id": 999,
                    "username": "izleyici1",
                    "slug": "izleyici1",
                    "identity": {
                        "color": "#FBCFD8",
                        "badges": [
                            {"type": "broadcaster", "text": "Broadcaster", "sort_order": 13}
                        ],
                    },
                },
                "metadata": {"message_ref": "1788197606621"},
            }
        ),
        "channel": "chatrooms.42.v2",
    }

    message = parse_chat_message(event)

    assert message is not None
    assert message.user_id == 999
    assert message.username == "izleyici1"
    assert message.text == "!paket"
    assert message.sent_at == datetime.fromisoformat("2026-08-31T17:33:27+00:00")
    assert {f.name for f in fields(message)} == {"user_id", "username", "text", "sent_at"}


def test_parse_chat_message_ignores_non_chat_events() -> None:
    event = {
        "event": "pusher_internal:subscription_succeeded",
        "data": "{}",
        "channel": "chatrooms.42.v2",
    }

    assert parse_chat_message(event) is None
