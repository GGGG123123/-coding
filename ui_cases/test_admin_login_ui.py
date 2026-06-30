from __future__ import annotations

import pytest


pytestmark = pytest.mark.ui


def _skip_demo_backend(config):
    if config.get("auto_start_mock_backend"):
        pytest.skip("The local demo backend has no real admin web UI. Use --env=dev/pre with a real admin_url.")


def test_admin_login_ui(page, config):
    _skip_demo_backend(config)
    selectors = config.get("ui_selectors", {})
    account = config["accounts"]["admin"]

    page.goto(config["admin_url"].rstrip("/") + "/login")
    page.fill(selectors.get("username", "input[name='username']"), account["username"])
    page.fill(selectors.get("password", "input[name='password']"), account["password"])
    page.click(selectors.get("submit", "button[type='submit']"))

    page.get_by_text(selectors.get("device_menu_text", "设备管理")).wait_for(timeout=config.get("ui_timeout", 10000))

