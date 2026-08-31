from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChatMessage:
    user_id: int
    username: str
    text: str
    sent_at: datetime
