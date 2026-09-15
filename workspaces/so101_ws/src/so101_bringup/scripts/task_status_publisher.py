#!/usr/bin/env python3
"""Status payload formatting for task executor."""

import json
import time
from typing import Callable, Dict, Optional


def build_status_payload(
    request_id: str,
    state: str,
    code: str,
    message: str,
    *,
    ts_ms: Optional[int] = None,
) -> Dict[str, object]:
    return {
        "requestId": request_id,
        "state": state,
        "code": code,
        "message": message,
        "ts": int(time.time() * 1000) if ts_ms is None else int(ts_ms),
    }


class TaskStatusPublisher:
    def __init__(
        self,
        *,
        publish_text: Callable[[str], None],
        log_info: Callable[[str], None],
        now_ms: Optional[Callable[[], int]] = None,
    ) -> None:
        self._publish_text = publish_text
        self._log_info = log_info
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))

    def emit(self, request_id: str, state: str, code: str, message: str) -> Dict[str, object]:
        payload = build_status_payload(
            request_id,
            state,
            code,
            message,
            ts_ms=self._now_ms(),
        )
        self._publish_text(json.dumps(payload, ensure_ascii=False))
        self._log_info(f"[{request_id}] {state} {code} - {message}")
        return payload
