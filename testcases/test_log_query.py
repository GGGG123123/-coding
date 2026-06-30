from __future__ import annotations

import pytest

from common.assert_utils import assert_error_response, assert_page_result, assert_success_response
from common.reporting import case_meta, report_step
from services.log_service import LogService


@pytest.mark.log
@pytest.mark.smoke
@pytest.mark.p1
def test_query_logs_by_device_id(admin_client, mock_device, device_cases):
    case_meta("日志管理模块", "按设备查询日志", "根据设备 ID 查询日志成功", "normal")

    with report_step("Mock 设备上报一条日志"):
        device_id = device_cases["online_device"]["device_id"]
        mock_device.report_log(device_id=device_id, level="INFO", message="OTA readiness check")

    with report_step("按设备 ID 查询日志"):
        response = LogService(admin_client).query_logs(device_id=device_id, page=1, size=10)

    with report_step("校验日志分页结构和设备 ID"):
        data = assert_success_response(response)["data"]
        assert_page_result(data)
        assert data["total"] >= 1
        assert all(item["device_id"] == device_id for item in data["list"])


@pytest.mark.log
@pytest.mark.p1
def test_query_logs_by_keyword(admin_client, mock_device, device_cases):
    case_meta("日志管理模块", "按关键字查询日志", "根据 battery 关键字查询日志成功", "normal")

    with report_step("Mock 设备上报包含 battery 的日志"):
        device_id = device_cases["online_device"]["device_id"]
        mock_device.report_log(device_id=device_id, level="WARN", message="OTA battery level low")

    with report_step("按 battery 关键字查询日志"):
        response = LogService(admin_client).query_logs(keyword="battery", page=1, size=10)

    with report_step("校验返回日志包含 battery"):
        data = assert_success_response(response)["data"]
        assert any("battery" in item["message"].lower() for item in data["list"])


@pytest.mark.log
@pytest.mark.p1
def test_query_logs_for_unknown_device_returns_empty_list(admin_client):
    case_meta("日志管理模块", "空结果查询", "查询不存在设备日志返回空列表", "normal")

    with report_step("查询不存在设备的日志"):
        response = LogService(admin_client).query_logs(device_id="UNKNOWN_DEVICE", page=1, size=10)

    with report_step("校验返回空分页列表"):
        data = assert_success_response(response)["data"]
        assert_page_result(data)
        assert data["total"] == 0


@pytest.mark.log
@pytest.mark.p1
def test_export_logs(admin_client, mock_device, device_cases):
    case_meta("日志管理模块", "日志导出", "按设备导出日志成功", "normal")

    with report_step("准备可导出的日志"):
        device_id = device_cases["online_device"]["device_id"]
        mock_device.report_log(device_id=device_id, level="INFO", message="export smoke log")

    with report_step("调用日志导出接口"):
        response = LogService(admin_client).export_logs(device_id=device_id)

    with report_step("校验导出文件名"):
        data = assert_success_response(response)["data"]
        assert data["file_name"].endswith(".csv")


@pytest.mark.log
@pytest.mark.permission
@pytest.mark.p0
def test_guest_cannot_query_logs(guest_client):
    case_meta("日志管理模块", "日志权限控制", "guest 角色不能查询日志", "critical")

    with report_step("guest 调用日志查询接口"):
        response = LogService(guest_client).query_logs(page=1, size=10)

    with report_step("校验返回 403"):
        assert_error_response(response, expected_code=403, allowed_http_status=(403,))
