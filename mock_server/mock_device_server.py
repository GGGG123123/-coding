from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


ADMIN_API = os.getenv("ADMIN_API", "http://127.0.0.1:9000").rstrip("/")
CALLBACK_TOKEN = os.getenv("MOCK_DEVICE_CALLBACK_TOKEN", "mock-device-secret")

app = FastAPI(title="X-SENSE Mock Device Server", version="1.0.0")


class DeviceStatusBody(BaseModel):
    device_id: str
    status: str = Field(pattern="^(online|offline)$")
    firmware_version: str | None = None


class DeviceIdBody(BaseModel):
    device_id: str


class OtaSuccessBody(BaseModel):
    task_id: str
    device_id: str
    version: str


class OtaFailedBody(BaseModel):
    task_id: str
    device_id: str
    reason: str


class DeviceLogBody(BaseModel):
    device_id: str
    level: str = "INFO"
    message: str


def ok(data: Any | None = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data if data is not None else {}}


def post_admin(path: str, payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    try:
        response = requests.post(
            f"{ADMIN_API}{path}",
            json=payload,
            headers={"X-Mock-Device-Token": CALLBACK_TOKEN},
            timeout=5,
        )
    except requests.RequestException as exc:
        return JSONResponse(status_code=502, content={"code": 502, "message": str(exc), "data": {}})

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    if response.status_code >= 400 or body.get("code") not in (0, None):
        return JSONResponse(
            status_code=response.status_code,
            content={"code": body.get("code", response.status_code), "message": body.get("message", "upstream error"), "data": body},
        )
    return ok({"admin_status_code": response.status_code, "admin_response": body})


@app.get("/health", response_model=None)
def health() -> dict[str, Any]:
    return ok({"service": "mock-device", "status": "ok", "admin_api": ADMIN_API})


@app.post("/mock/device/online", response_model=None)
def device_online(body: DeviceIdBody) -> dict[str, Any] | JSONResponse:
    return post_admin("/api/device/status/callback", {"device_id": body.device_id, "status": "online"})


@app.post("/mock/device/offline", response_model=None)
def device_offline(body: DeviceIdBody) -> dict[str, Any] | JSONResponse:
    return post_admin("/api/device/status/callback", {"device_id": body.device_id, "status": "offline"})


@app.post("/mock/device/report_status", response_model=None)
def report_status(body: DeviceStatusBody) -> dict[str, Any] | JSONResponse:
    payload = {"device_id": body.device_id, "status": body.status}
    if body.firmware_version:
        payload["firmware_version"] = body.firmware_version
    return post_admin("/api/device/status/callback", payload)


@app.post("/mock/device/ota_success", response_model=None)
def ota_success(body: OtaSuccessBody) -> dict[str, Any] | JSONResponse:
    return post_admin(
        "/api/device/ota/callback",
        {
            "task_id": body.task_id,
            "device_id": body.device_id,
            "status": "success",
            "firmware_version": body.version,
            "message": "mock ota success",
        },
    )


@app.post("/mock/device/ota_failed", response_model=None)
def ota_failed(body: OtaFailedBody) -> dict[str, Any] | JSONResponse:
    return post_admin(
        "/api/device/ota/callback",
        {
            "task_id": body.task_id,
            "device_id": body.device_id,
            "status": "failed",
            "message": body.reason,
        },
    )


@app.post("/mock/device/report_log", response_model=None)
def report_log(body: DeviceLogBody) -> dict[str, Any] | JSONResponse:
    return post_admin(
        "/api/device/log/callback",
        {"device_id": body.device_id, "level": body.level, "message": body.message},
    )
