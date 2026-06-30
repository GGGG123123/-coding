from __future__ import annotations

from typing import Any

from common.api_client import ApiClient


class PermissionService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def request_by_definition(self, definition: dict[str, Any]):
        method = definition["method"].upper()
        path = definition["path"]
        params = definition.get("params")
        body = definition.get("body")
        return self.client.request(method, path, params=params, json_body=body)

