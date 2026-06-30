from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import requests

from common import allure_utils
from common.api_client import ApiClient
from common.config_loader import PROJECT_ROOT, load_data_file, load_env_config
from common.db_utils import DBUtils
from common.logger import get_logger
from services.auth_service import AuthService
from services.mock_device_service import MockDeviceService


LOGGER = get_logger("pytest")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--env", action="store", default="test", help="Environment name under config/*.yaml")
    parser.addoption("--run-ui", action="store_true", default=False, help="Run Playwright UI cases")
    parser.addoption("--no-auto-mock", action="store_true", default=False, help="Do not auto-start local mock services")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "requires_db: test needs a configured database")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-ui"):
        return
    skip_ui = pytest.mark.skip(reason="UI tests are skipped by default. Re-run with --run-ui.")
    for item in items:
        if "ui" in item.keywords:
            item.add_marker(skip_ui)


@pytest.fixture(scope="session")
def config(pytestconfig: pytest.Config) -> dict[str, Any]:
    env_name = pytestconfig.getoption("--env")
    loaded = load_env_config(env_name)
    LOGGER.info("Loaded environment config: %s", loaded["_config_path"])
    return loaded


def _health_ok(url: str) -> bool:
    try:
        response = requests.get(url, timeout=1)
        return response.status_code == 200 and response.json().get("code") == 0
    except Exception:
        return False


def _wait_for_health(url: str, timeout: int = 15) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _health_ok(url):
            return
        time.sleep(0.3)
    raise RuntimeError(f"Service did not become healthy: {url}")


def _start_uvicorn(module_app: str, host: str, port: int, env: dict[str, str]) -> subprocess.Popen:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        module_app,
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    LOGGER.info("Starting mock service: %s", " ".join(command))
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


@pytest.fixture(scope="session", autouse=True)
def managed_mock_services(config: dict[str, Any], pytestconfig: pytest.Config):
    if pytestconfig.getoption("--no-auto-mock"):
        yield
        return

    started: list[subprocess.Popen] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["ADMIN_API"] = config["base_url"]
    env["MOCK_DEVICE_CALLBACK_TOKEN"] = config.get("mock_device", {}).get("callback_token", "mock-device-secret")

    if config.get("auto_start_mock_backend"):
        backend = config.get("mock_backend", {})
        host = backend.get("host", "127.0.0.1")
        port = int(backend.get("port", 9000))
        health_url = f"http://{host}:{port}{backend.get('health_path', '/health')}"
        if not _health_ok(health_url):
            started.append(_start_uvicorn("mock_server.demo_admin_backend:app", host, port, env))
            _wait_for_health(health_url)
        LOGGER.info("Mock admin backend is healthy: %s", health_url)

    if config.get("auto_start_mock_device"):
        device = config.get("mock_device", {})
        host = device.get("host", "127.0.0.1")
        port = int(device.get("port", 8001))
        health_url = f"http://{host}:{port}/health"
        if not _health_ok(health_url):
            started.append(_start_uvicorn("mock_server.mock_device_server:app", host, port, env))
            _wait_for_health(health_url)
        LOGGER.info("Mock device server is healthy: %s", health_url)

    yield

    for process in started:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(autouse=True)
def reset_demo_backend(config: dict[str, Any], pytestconfig: pytest.Config):
    if config.get("auto_start_mock_backend") and not pytestconfig.getoption("--no-auto-mock"):
        try:
            requests.post(f"{config['base_url'].rstrip('/')}/api/test/reset", timeout=2)
        except requests.RequestException as exc:
            LOGGER.warning("Could not reset demo backend: %s", exc)
    yield


@pytest.fixture(scope="session")
def users_data() -> dict[str, Any]:
    return load_data_file("users.yaml")


@pytest.fixture(scope="session")
def device_cases() -> dict[str, Any]:
    return load_data_file("device_cases.yaml")


@pytest.fixture(scope="session")
def ota_cases() -> dict[str, Any]:
    return load_data_file("ota_cases.yaml")


@pytest.fixture(scope="session")
def permission_matrix() -> dict[str, Any]:
    return load_data_file("permission_matrix.yaml")


@pytest.fixture
def raw_client(config: dict[str, Any]) -> ApiClient:
    return ApiClient(
        base_url=config["base_url"],
        timeout=config.get("api_timeout", 5),
        verify_ssl=config.get("verify_ssl", True),
        name="raw",
    )


@pytest.fixture
def client_by_role(config: dict[str, Any]):
    def _factory(role: str) -> ApiClient:
        account = config["accounts"][role]
        client = ApiClient(
            base_url=config["base_url"],
            timeout=config.get("api_timeout", 5),
            verify_ssl=config.get("verify_ssl", True),
            name=role,
        )
        token = AuthService(client).login(account["username"], account["password"])
        client.set_token(token)
        return client

    return _factory


@pytest.fixture
def admin_client(client_by_role) -> ApiClient:
    return client_by_role("admin")


@pytest.fixture
def operator_client(client_by_role) -> ApiClient:
    return client_by_role("operator")


@pytest.fixture
def viewer_client(client_by_role) -> ApiClient:
    return client_by_role("viewer")


@pytest.fixture
def guest_client(client_by_role) -> ApiClient:
    return client_by_role("guest")


@pytest.fixture
def expired_client(config: dict[str, Any]) -> ApiClient:
    return ApiClient(
        base_url=config["base_url"],
        token="expired-or-invalid-token",
        timeout=config.get("api_timeout", 5),
        verify_ssl=config.get("verify_ssl", True),
        name="expired-token",
    )


@pytest.fixture
def db(config: dict[str, Any]):
    db_client = DBUtils(config.get("mysql", {}))
    yield db_client
    db_client.close()


@pytest.fixture
def mock_device(config: dict[str, Any]) -> MockDeviceService:
    return MockDeviceService(
        base_url=config["mock_device"]["base_url"],
        timeout=config.get("api_timeout", 5),
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    try:
        screenshot = page.screenshot(full_page=True)
    except Exception as exc:
        LOGGER.warning("Could not capture Playwright screenshot: %s", exc)
        return

    attachment_type = None
    if allure_utils.allure is not None:
        attachment_type = allure_utils.allure.attachment_type.PNG
    allure_utils.attach_bytes("ui-failure-screenshot", screenshot, attachment_type)

