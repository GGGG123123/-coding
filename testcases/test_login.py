from __future__ import annotations

import pytest

from common.assert_utils import assert_error_response, assert_success_response
from common.reporting import case_meta, report_step
from services.auth_service import AuthService


@pytest.mark.smoke
@pytest.mark.p0
@pytest.mark.parametrize("role", ["admin", "operator", "viewer", "guest"])
def test_login_success_for_all_roles(raw_client, config, role):
    case_meta("登录鉴权模块", "登录成功", f"使用 {role} 角色账号登录成功", "blocker")

    with report_step("读取角色账号"):
        account = config["accounts"][role]
        auth_service = AuthService(raw_client)

    with report_step("输入正确用户名和密码"):
        response = auth_service.login_raw(account["username"], account["password"])

    with report_step("校验返回 token 和角色"):
        data = assert_success_response(response)["data"]
        assert data["token"]
        assert data["role"] == role


@pytest.mark.p0
def test_login_rejects_wrong_password(raw_client, config):
    case_meta("登录鉴权模块", "登录失败", "使用错误密码登录失败", "blocker")

    with report_step("输入正确用户名和错误密码"):
        account = config["accounts"]["admin"]
        response = AuthService(raw_client).login_raw(account["username"], "wrong-password")

    with report_step("校验系统拒绝登录"):
        assert_error_response(response, expected_code=401)


@pytest.mark.p0
def test_missing_token_cannot_visit_me(raw_client):
    case_meta("登录鉴权模块", "Token 校验", "缺少 Token 访问用户信息失败", "blocker")

    with report_step("不携带 Token 访问 /api/auth/me"):
        response = raw_client.get("/api/auth/me")

    with report_step("校验返回 401"):
        assert_error_response(response, expected_code=401, allowed_http_status=(401,))


@pytest.mark.smoke
@pytest.mark.p0
def test_admin_token_can_query_current_user(admin_client):
    case_meta("登录鉴权模块", "Token 校验", "admin Token 可以查询当前用户", "blocker")

    with report_step("携带 admin Token 查询当前用户"):
        response = admin_client.get("/api/auth/me")

    with report_step("校验当前用户角色和用户名"):
        data = assert_success_response(response)["data"]
        assert data["role"] == "admin"
        assert data["username"]
