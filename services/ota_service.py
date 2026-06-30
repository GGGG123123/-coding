from __future__ import annotations

from common.api_client import ApiClient


class OtaService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def list_firmwares(self):
        return self.client.get("/api/firmwares")

    def create_task(self, device_ids: list[str], firmware_id: str, target_version: str):
        return self.client.post(
            "/api/ota/tasks",
            json_body={
                "device_ids": device_ids,
                "firmware_id": firmware_id,
                "target_version": target_version,
            },
        )

    def get_task_detail(self, task_id: str):
        return self.client.get(f"/api/ota/tasks/{task_id}")

    def list_tasks(self, page: int = 1, size: int = 10, device_id: str | None = None):
        params = {"page": page, "size": size}
        if device_id:
            params["device_id"] = device_id
        return self.client.get("/api/ota/tasks", params=params)

    def cancel_task(self, task_id: str):
        return self.client.post(f"/api/ota/tasks/{task_id}/cancel")

