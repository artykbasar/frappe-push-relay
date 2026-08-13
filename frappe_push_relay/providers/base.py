from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    permanent_token_failure: bool = False


class PushProvider:
    def send_token(self, token: str, title: str, body: str, data: dict[str, Any] | None = None) -> SendResult:
        raise NotImplementedError
