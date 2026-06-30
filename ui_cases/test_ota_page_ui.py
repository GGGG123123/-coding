from __future__ import annotations

import pytest


pytestmark = pytest.mark.ui


def _login(page, config, role="admin"):
    selectors = config.get("ui_selectors", {})
    account = config["accounts"][role]
    page.goto(config["admin_url"].rstrip("/") + "/login")
    page.fill(selectors.get("username", "input[name='username']"), account["username"])
    page.fill(selectors.get("password", "input[name='password']"), account["password"])
    page.click(selectors.get("submit", "button[type='submit']"))


def test_create_ota_task_by_ui(page, config, ota_cases):
    if config.get("auto_start_mock_backend"):
        pytest.skip("The local demo backend has no real admin web UI. Use --env=dev/pre with a real admin_url.")

    case = ota_cases["normal_ota"]
    _login(page, config)
    page.get_by_text(config.get("ui_selectors", {}).get("ota_menu_text", "OTA管理")).click()
    page.get_by_role("button", name="创建任务").click()
    page.locator("select[name='device']").select_option(case["device_id"])
    page.locator("select[name='firmware']").select_option(case["firmware_id"])
    page.get_by_role("button", name="确认创建").click()

    page.get_by_text("创建成功").wait_for(timeout=config.get("ui_timeout", 10000))

