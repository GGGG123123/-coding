from __future__ import annotations

from common.api_client import ApiClient
from common.assert_utils import assert_success_response


class MockDeviceService:
    def __init__(self, base_url: str, timeout: int | float = 5) -> None:
        self.client = ApiClient(base_url=base_url, timeout=timeout, name="mock-device")

    def health(self):
        return self.client.get("/health")

    def online(self, device_id: str):
        response = self.client.post("/mock/device/online", json_body={"device_id": device_id})
        return assert_success_response(response)["data"]

    def offline(self, device_id: str):
        response = self.client.post("/mock/device/offline", json_body={"device_id": device_id})
        return assert_success_response(response)["data"]

    def report_status(self, device_id: str, status: str, firmware_version: str | None = None):
        body = {"device_id": device_id, "status": status}
        if firmware_version:
            body["firmware_version"] = firmware_version
        response = self.client.post("/mock/device/report_status", json_body=body)
        return assert_success_response(response)["data"]

    def ota_success(self, task_id: str, device_id: str, version: str):
        response = self.client.post(
            "/mock/device/ota_success",
            json_body={"task_id": task_id, "device_id": device_id, "version": version},
        )
        return assert_success_response(response)["data"]

    def ota_failed(self, task_id: str, device_id: str, reason: str):
        response = self.client.post(
            "/mock/device/ota_failed",
            json_body={"task_id": task_id, "device_id": device_id, "reason": reason},
        )
        return assert_success_response(response)["data"]

    def report_log(self, device_id: str, level: str, message: str):
        response = self.client.post(
            "/mock/device/report_log",
            json_body={"device_id": device_id, "level": level, "message": message},
        )
        return assert_success_response(response)["data"]

