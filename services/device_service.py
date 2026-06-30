from __future__ import annotations

from typing import Any

from common.api_client import ApiClient


class DeviceService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def list_devices(self, page: int = 1, size: int = 10, status: str | None = None):
        params: dict[str, Any] = {"page": page, "size": size}
        if status:
            params["status"] = status
        return self.client.get("/api/devices", params=params)

    def get_device_detail(self, device_id: str):
        return self.client.get(f"/api/devices/{device_id}")

    def update_device_status(self, device_id: str, status: str):
        return self.client.post(
            f"/api/devices/{device_id}/status",
            json_body={"status": status},
        )

    def delete_device(self, device_id: str):
        return self.client.delete(f"/api/devices/{device_id}")

