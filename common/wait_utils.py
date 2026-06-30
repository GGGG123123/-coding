from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


def wait_until(
    predicate: Callable[[], Any],
    *,
    timeout: int | float = 30,
    interval: int | float = 1,
    message: str = "condition was not satisfied",
) -> Any:
    deadline = time.time() + timeout
    last_value: Any = None
    while time.time() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval)
    raise AssertionError(f"Timed out after {timeout}s: {message}. Last value: {last_value!r}")


def wait_until_task_status(ota_service: Any, task_id: str, expected_status: str, timeout: int = 30) -> dict[str, Any]:
    def _query() -> dict[str, Any] | None:
        response = ota_service.get_task_detail(task_id)
        if response.status_code != 200:
            return None
        data = response.json().get("data", {})
        return data if data.get("status") == expected_status else None

    return wait_until(
        _query,
        timeout=timeout,
        interval=1,
        message=f"OTA task {task_id} did not become {expected_status}",
    )

