#!/usr/bin/env python3
"""Pure command gate helpers for task_executor characterization tests."""

from typing import Any, Dict


def evaluate_command_request(
    *,
    request_id: str,
    template_id: str,
    params: Dict[str, Any],
    command_execution_enabled: bool,
    busy: bool,
) -> Dict[str, Any]:
    if not command_execution_enabled:
        return {
            "accepted": False,
            "requestId": request_id,
            "templateId": template_id,
            "params": params,
            "status": {
                "requestId": request_id,
                "state": "异常",
                "code": "COMMAND_LOCKED",
                "message": "Execution gate disabled for safe real bringup",
            },
        }

    if busy:
        return {
            "accepted": False,
            "requestId": request_id,
            "templateId": template_id,
            "params": params,
            "status": {
                "requestId": request_id,
                "state": "异常",
                "code": "BUSY",
                "message": "Executor is busy",
            },
        }

    return {
        "accepted": True,
        "requestId": request_id,
        "templateId": template_id,
        "params": params,
        "status": None,
    }
