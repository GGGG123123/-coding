from __future__ import annotations

from typing import Any

from common.api_client import ApiClient


class LogService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def query_logs(
        self,
        *,
        device_id: str | None = None,
        keyword: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        page: int = 1,
        size: int = 10,
    ):
        params: dict[str, Any] = {"page": page, "size": size}
        if device_id:
            params["device_id"] = device_id
        if keyword:
            params["keyword"] = keyword
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        return self.client.get("/api/logs", params=params)

    def export_logs(self, *, device_id: str | None = None, keyword: str | None = None):
        params: dict[str, Any] = {}
        if device_id:
            params["device_id"] = device_id
        if keyword:
            params["keyword"] = keyword
        return self.client.get("/api/logs/export", params=params)

