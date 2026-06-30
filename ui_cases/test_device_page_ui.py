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


def test_device_page_can_open_and_search(page, config, device_cases):
    if config.get("auto_start_mock_backend"):
        pytest.skip("The local demo backend has no real admin web UI. Use --env=dev/pre with a real admin_url.")

    _login(page, config)
    page.get_by_text(config.get("ui_selectors", {}).get("device_menu_text", "设备管理")).click()
    page.get_by_placeholder("请输入设备ID").fill(device_cases["online_device"]["device_id"])
    page.get_by_role("button", name="查询").click()

    page.get_by_text(device_cases["online_device"]["device_id"]).wait_for(timeout=config.get("ui_timeout", 10000))

