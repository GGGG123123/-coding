from __future__ import annotations

import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field

from mock_server.mock_data import DEVICES, FIRMWARES, ROLE_PERMISSIONS, USERS


app = FastAPI(title="X-SENSE Demo Admin Backend", version="1.0.0")
CALLBACK_TOKEN = os.getenv("MOCK_DEVICE_CALLBACK_TOKEN", "mock-device-secret")

STATE: dict[str, Any] = {}
TOKENS: dict[str, dict[str, Any]] = {}


class LoginBody(BaseModel):
    username: str
    password: str


class DeviceStatusBody(BaseModel):
    status: str = Field(pattern="^(online|offline)$")
    firmware_version: str | None = None


class StatusCallbackBody(BaseModel):
    device_id: str
    status: str = Field(pattern="^(online|offline)$")
    firmware_version: str | None = None


class CreateOtaTaskBody(BaseModel):
    device_ids: list[str]
    firmware_id: str
    target_version: str


class OtaCallbackBody(BaseModel):
    task_id: str
    device_id: str
    status: str = Field(pattern="^(success|failed)$")
    firmware_version: str | None = None
    message: str | None = None


class DeviceLogBody(BaseModel):
    device_id: str
    level: str = "INFO"
    message: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ok(data: Any | None = None, message: str = "ok") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data if data is not None else {}}


def error(code: int, message: str, http_status: int = 200, data: Any | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": data if data is not None else {}},
    )


def reset_state() -> None:
    STATE["devices"] = deepcopy(DEVICES)
    STATE["firmwares"] = deepcopy(FIRMWARES)
    STATE["tasks"] = {}
    STATE["logs"] = []
    STATE["task_seq"] = 0
    TOKENS.clear()
    add_log("SYSTEM", "INFO", "demo backend reset", biz_id="RESET")


def add_log(device_id: str, level: str, message: str, biz_id: str | None = None) -> dict[str, Any]:
    record = {
        "log_id": f"LOG_{uuid4().hex[:12]}",
        "device_id": device_id,
        "level": level,
        "message": message,
        "biz_id": biz_id,
        "created_at": now_iso(),
    }
    STATE.setdefault("logs", []).append(record)
    return record


def user_from_token(authorization: str | None) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "", 1).strip()
    return TOKENS.get(token)


def require_user(authorization: str | None) -> dict[str, Any] | JSONResponse:
    user = user_from_token(authorization)
    if not user:
        return error(401, "missing or invalid token", http_status=401)
    return user


def require_permission(authorization: str | None, permission: str) -> dict[str, Any] | JSONResponse:
    user_or_error = require_user(authorization)
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    role = user_or_error["role"]
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        return error(403, f"role {role} has no permission {permission}", http_status=403)
    return user_or_error


def can_access_device(user: dict[str, Any], device: dict[str, Any]) -> bool:
    return user["role"] == "admin" or user["org_id"] == device.get("org_id")


def visible_devices(user: dict[str, Any]) -> list[dict[str, Any]]:
    devices = list(STATE["devices"].values())
    return [device for device in devices if can_access_device(user, device)]


def page_response(items: list[dict[str, Any]], page: int, size: int) -> dict[str, Any] | JSONResponse:
    if page < 1 or size < 1 or size > 100:
        return error(400, "invalid page or size")
    start = (page - 1) * size
    end = start + size
    return ok({"list": items[start:end], "page": page, "size": size, "total": len(items)})


def compare_version(target: str, current: str) -> int:
    try:
        target_v = Version(target)
        current_v = Version(current)
    except InvalidVersion:
        target_v = Version("0")
        current_v = Version("0")
    return (target_v > current_v) - (target_v < current_v)


@app.on_event("startup")
def startup() -> None:
    reset_state()


@app.get("/health", response_model=None)
def health() -> dict[str, Any]:
    return ok({"service": "demo-admin-backend", "status": "ok"})


@app.post("/api/test/reset", response_model=None)
def api_test_reset() -> dict[str, Any]:
    reset_state()
    return ok({"reset": True})


@app.post("/api/auth/login", response_model=None)
def login(body: LoginBody) -> dict[str, Any] | JSONResponse:
    user = USERS.get(body.username)
    if not user or user["password"] != body.password:
        return error(401, "invalid username or password")
    token = f"token-{user['role']}-{uuid4().hex}"
    token_user = {
        "username": body.username,
        "role": user["role"],
        "org_id": user["org_id"],
        "token": token,
    }
    TOKENS[token] = token_user
    return ok({"token": token, "role": user["role"], "username": body.username})


@app.get("/api/auth/me", response_model=None)
def me(authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_user(authorization)
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    return ok({k: v for k, v in user_or_error.items() if k != "token"})


@app.get("/api/devices", response_model=None)
def list_devices(
    page: int = Query(default=1),
    size: int = Query(default=10),
    status: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "device:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    items = visible_devices(user_or_error)
    if status:
        items = [device for device in items if device["status"] == status]
    return page_response(items, page, size)


@app.get("/api/devices/{device_id}", response_model=None)
def device_detail(device_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "device:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    device = STATE["devices"].get(device_id)
    if not device:
        return error(404, f"device not found: {device_id}", http_status=404)
    if not can_access_device(user_or_error, device):
        return error(403, "device is outside current organization", http_status=403)
    return ok(device)


@app.post("/api/devices/{device_id}/status", response_model=None)
def update_device_status(
    device_id: str,
    body: DeviceStatusBody,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "device:write")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    device = STATE["devices"].get(device_id)
    if not device:
        return error(404, f"device not found: {device_id}", http_status=404)
    device["status"] = body.status
    if body.firmware_version:
        device["firmware_version"] = body.firmware_version
    add_log(device_id, "INFO", f"manual status update: {body.status}")
    return ok(device)


@app.delete("/api/devices/{device_id}", response_model=None)
def delete_device(device_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "device:write")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    if not device_id.startswith("TEST_"):
        return error(400, "only TEST_ devices can be deleted in demo backend")
    removed = STATE["devices"].pop(device_id, None)
    if not removed:
        return error(404, f"device not found: {device_id}", http_status=404)
    add_log(device_id, "WARN", "device deleted by automation")
    return ok({"deleted": device_id})


@app.get("/api/firmwares", response_model=None)
def list_firmwares(authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "ota:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    return ok({"list": list(STATE["firmwares"].values()), "total": len(STATE["firmwares"])})


@app.get("/api/ota/tasks", response_model=None)
def list_ota_tasks(
    page: int = Query(default=1),
    size: int = Query(default=10),
    device_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "ota:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    tasks = list(STATE["tasks"].values())
    visible_device_ids = {device["device_id"] for device in visible_devices(user_or_error)}
    tasks = [task for task in tasks if task["device_id"] in visible_device_ids]
    if device_id:
        tasks = [task for task in tasks if task["device_id"] == device_id]
    return page_response(tasks, page, size)


@app.post("/api/ota/tasks", response_model=None)
def create_ota_task(body: CreateOtaTaskBody, authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "ota:write")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    if not body.device_ids:
        return error(400, "device_ids cannot be empty")
    firmware = STATE["firmwares"].get(body.firmware_id)
    if not firmware:
        return error(400, f"firmware not found: {body.firmware_id}")
    if firmware["version"] != body.target_version:
        return error(400, "target_version does not match firmware version")

    task_ids: list[str] = []
    for device_id in body.device_ids:
        device = STATE["devices"].get(device_id)
        if not device:
            return error(400, f"device not found: {device_id}")
        if not can_access_device(user_or_error, device):
            return error(403, f"device is outside current organization: {device_id}", http_status=403)
        if device["status"] != "online":
            return error(400, f"device is not online: {device_id}")
        if compare_version(body.target_version, device["firmware_version"]) <= 0:
            return error(400, f"target version must be newer than current version: {device_id}")

    for device_id in body.device_ids:
        STATE["task_seq"] += 1
        task_id = f"OTA_{STATE['task_seq']:06d}"
        task = {
            "task_id": task_id,
            "device_id": device_id,
            "firmware_id": body.firmware_id,
            "target_version": body.target_version,
            "status": "waiting",
            "created_by": user_or_error["username"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "message": "task created",
        }
        STATE["tasks"][task_id] = task
        task_ids.append(task_id)
        add_log(device_id, "INFO", f"OTA task created: {task_id} -> {body.target_version}", biz_id=task_id)

    return ok({"task_id": task_ids[0], "task_ids": task_ids})


@app.get("/api/ota/tasks/{task_id}", response_model=None)
def ota_task_detail(task_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "ota:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    task = STATE["tasks"].get(task_id)
    if not task:
        return error(404, f"OTA task not found: {task_id}", http_status=404)
    device = STATE["devices"].get(task["device_id"])
    if device and not can_access_device(user_or_error, device):
        return error(403, "task is outside current organization", http_status=403)
    return ok(task)


@app.post("/api/ota/tasks/{task_id}/cancel", response_model=None)
def cancel_ota_task(task_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "ota:write")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    task = STATE["tasks"].get(task_id)
    if not task:
        return error(404, f"OTA task not found: {task_id}", http_status=404)
    if task["status"] in {"success", "failed", "cancelled"}:
        return error(400, f"task is already finished: {task['status']}")
    task["status"] = "cancelled"
    task["updated_at"] = now_iso()
    task["message"] = "task cancelled"
    add_log(task["device_id"], "WARN", f"OTA task cancelled: {task_id}", biz_id=task_id)
    return ok(task)


@app.get("/api/logs", response_model=None)
def query_logs(
    page: int = Query(default=1),
    size: int = Query(default=10),
    device_id: str | None = None,
    keyword: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "log:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    visible_device_ids = {device["device_id"] for device in visible_devices(user_or_error)}
    items = [log for log in STATE["logs"] if log["device_id"] in visible_device_ids or log["device_id"] == "SYSTEM"]
    if device_id:
        items = [log for log in items if log["device_id"] == device_id]
    if keyword:
        items = [log for log in items if keyword.lower() in log["message"].lower()]
    return page_response(items, page, size)


@app.get("/api/logs/export", response_model=None)
def export_logs(
    device_id: str | None = None,
    keyword: str | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    user_or_error = require_permission(authorization, "log:read")
    if isinstance(user_or_error, JSONResponse):
        return user_or_error
    return ok({"file_name": "logs-demo.csv", "device_id": device_id, "keyword": keyword})


@app.post("/api/device/status/callback", response_model=None)
def device_status_callback(
    body: StatusCallbackBody,
    x_mock_device_token: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    if CALLBACK_TOKEN and x_mock_device_token != CALLBACK_TOKEN:
        return error(403, "invalid mock device callback token", http_status=403)
    device = STATE["devices"].get(body.device_id)
    if not device:
        return error(404, f"device not found: {body.device_id}", http_status=404)
    device["status"] = body.status
    if body.firmware_version:
        device["firmware_version"] = body.firmware_version
    add_log(body.device_id, "INFO", f"device status callback: {body.status}")
    return ok(device)


@app.post("/api/device/ota/callback", response_model=None)
def ota_callback(
    body: OtaCallbackBody,
    x_mock_device_token: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    if CALLBACK_TOKEN and x_mock_device_token != CALLBACK_TOKEN:
        return error(403, "invalid mock device callback token", http_status=403)
    task = STATE["tasks"].get(body.task_id)
    if not task:
        return error(404, f"OTA task not found: {body.task_id}", http_status=404)
    if task["device_id"] != body.device_id:
        return error(400, "callback device_id does not match task")
    task["status"] = body.status
    task["message"] = body.message or f"mock OTA {body.status}"
    task["updated_at"] = now_iso()
    if body.status == "success":
        device = STATE["devices"][body.device_id]
        device["firmware_version"] = body.firmware_version or task["target_version"]
        add_log(body.device_id, "INFO", f"OTA success: {body.task_id}", biz_id=body.task_id)
    else:
        add_log(body.device_id, "ERROR", f"OTA failed: {body.task_id}; {task['message']}", biz_id=body.task_id)
    return ok(task)


@app.post("/api/device/log/callback", response_model=None)
def log_callback(
    body: DeviceLogBody,
    x_mock_device_token: str | None = Header(default=None),
) -> dict[str, Any] | JSONResponse:
    if CALLBACK_TOKEN and x_mock_device_token != CALLBACK_TOKEN:
        return error(403, "invalid mock device callback token", http_status=403)
    if body.device_id not in STATE["devices"]:
        return error(404, f"device not found: {body.device_id}", http_status=404)
    return ok(add_log(body.device_id, body.level, body.message))
