from __future__ import annotations

import pytest

from common.assert_utils import assert_business_code, assert_error_response, assert_page_result, assert_success_response
from common.reporting import case_meta, report_step
from services.device_service import DeviceService


@pytest.mark.smoke
@pytest.mark.device
@pytest.mark.p0
def test_device_list_smoke(admin_client):
    case_meta("设备管理模块", "设备列表查询", "管理员查询设备列表成功", "critical")

    with report_step("查询第一页设备列表"):
        response = DeviceService(admin_client).list_devices(page=1, size=10)

    with report_step("校验分页结构和设备数量"):
        data = assert_success_response(response)["data"]
        assert_page_result(data)
        assert data["total"] >= 1


@pytest.mark.contract
@pytest.mark.device
@pytest.mark.p0
def test_device_detail_contract(admin_client, device_cases):
    case_meta("设备管理模块", "设备详情契约", "设备详情字段完整且类型正确", "critical")

    with report_step("读取测试设备 ID 并查询详情"):
        device_id = device_cases["online_device"]["device_id"]
        response = DeviceService(admin_client).get_device_detail(device_id)

    with report_step("校验设备详情核心字段"):
        data = assert_success_response(response)["data"]
        assert data["device_id"] == device_id
        assert isinstance(data["status"], str)
        assert isinstance(data["firmware_version"], str)
        assert "org_id" in data


@pytest.mark.device
@pytest.mark.p1
@pytest.mark.parametrize("case", ["online_device", "offline_device"])
def test_device_status_filter(admin_client, device_cases, case):
    expected_status = device_cases[case]["expected_status"]
    case_meta("设备管理模块", "设备状态筛选", f"按 {expected_status} 状态筛选设备", "normal")

    with report_step(f"查询 {expected_status} 状态设备"):
        response = DeviceService(admin_client).list_devices(page=1, size=10, status=expected_status)

    with report_step("校验返回设备状态均符合筛选条件"):
        data = assert_success_response(response)["data"]
        assert_page_result(data)
        assert all(device["status"] == expected_status for device in data["list"])


@pytest.mark.contract
@pytest.mark.device
@pytest.mark.parametrize("case", [0, 1, 2, 3])
def test_device_pagination_validation(admin_client, device_cases, case):
    params = device_cases["pagination_cases"][case]
    case_meta("设备管理模块", "分页参数校验", f"设备列表分页参数校验 page={params['page']} size={params['size']}", "normal")

    with report_step("使用指定分页参数查询设备列表"):
        response = DeviceService(admin_client).list_devices(page=params["page"], size=params["size"])

    with report_step("校验业务 code 符合预期"):
        assert_business_code(response, params["expected_code"])


@pytest.mark.data_consistency
@pytest.mark.device
@pytest.mark.p0
def test_device_status_consistency_after_mock_callback(admin_client, mock_device, device_cases):
    case_meta("设备管理模块", "设备状态一致性", "Mock 设备上下线后后台状态同步正确", "critical")

    with report_step("准备测试设备并模拟离线"):
        device_id = device_cases["online_device"]["device_id"]
        device_service = DeviceService(admin_client)
        mock_device.offline(device_id)

    with report_step("校验后台设备详情变为 offline"):
        offline_detail = assert_success_response(device_service.get_device_detail(device_id))["data"]
        assert offline_detail["status"] == "offline"

    with report_step("模拟设备重新上线"):
        mock_device.online(device_id)

    with report_step("校验后台设备详情恢复 online"):
        online_detail = assert_success_response(device_service.get_device_detail(device_id))["data"]
        assert online_detail["status"] == "online"


@pytest.mark.permission
@pytest.mark.device
@pytest.mark.p0
def test_guest_cannot_query_devices(guest_client):
    case_meta("设备管理模块", "设备权限控制", "guest 角色不能查询设备列表", "critical")

    with report_step("guest 调用设备列表接口"):
        response = DeviceService(guest_client).list_devices(page=1, size=10)

    with report_step("校验返回 403"):
        assert_error_response(response, expected_code=403, allowed_http_status=(403,))
