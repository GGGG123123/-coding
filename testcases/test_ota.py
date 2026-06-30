from __future__ import annotations

import pytest

from common.assert_utils import assert_error_response, assert_success_response
from common.reporting import case_meta, report_step
from common.wait_utils import wait_until_task_status
from services.device_service import DeviceService
from services.log_service import LogService
from services.ota_service import OtaService


def _create_normal_ota(admin_client, ota_cases):
    case = ota_cases["normal_ota"]
    return OtaService(admin_client).create_task(
        device_ids=[case["device_id"]],
        firmware_id=case["firmware_id"],
        target_version=case["target_version"],
    )


@pytest.mark.smoke
@pytest.mark.ota
@pytest.mark.p0
def test_create_ota_task_success(admin_client, db, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 任务创建", "管理员创建 OTA 任务成功", "blocker")

    with report_step("准备在线设备和目标固件"):
        case = ota_cases["normal_ota"]
        ota_service = OtaService(admin_client)

    with report_step("调用创建 OTA 任务接口"):
        response = ota_service.create_task(
            device_ids=[case["device_id"]],
            firmware_id=case["firmware_id"],
            target_version=case["target_version"],
        )

    with report_step("校验任务创建成功并查询详情"):
        data = assert_success_response(response)["data"]
        task_id = data["task_id"]
        detail = assert_success_response(ota_service.get_task_detail(task_id))["data"]
        assert detail["device_id"] == case["device_id"]
        assert detail["target_version"] == case["target_version"]
        assert detail["status"] in {"created", "waiting", "upgrading"}

    if db.enabled:
        with report_step("校验数据库 OTA 任务记录"):
            task = db.query_one("select * from ota_task where task_id=%s", [task_id])
            assert task is not None
            assert task["target_version"] == case["target_version"]


@pytest.mark.ota
@pytest.mark.data_consistency
@pytest.mark.p0
def test_ota_callback_success_updates_task_device_and_log(admin_client, mock_device, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 成功回调", "设备回调成功后任务、版本和日志同步正确", "blocker")

    with report_step("创建 OTA 任务"):
        case = ota_cases["normal_ota"]
        ota_service = OtaService(admin_client)
        device_service = DeviceService(admin_client)
        log_service = LogService(admin_client)
        create_response = _create_normal_ota(admin_client, ota_cases)
        task_id = assert_success_response(create_response)["data"]["task_id"]

    with report_step("Mock 设备上报 OTA 成功回调"):
        mock_device.ota_success(task_id=task_id, device_id=case["device_id"], version=case["target_version"])

    with report_step("轮询任务直到 success"):
        task = wait_until_task_status(ota_service, task_id, "success", timeout=10)

    with report_step("校验设备版本更新和 OTA 成功日志"):
        device = assert_success_response(device_service.get_device_detail(case["device_id"]))["data"]
        logs = assert_success_response(log_service.query_logs(device_id=case["device_id"], keyword="OTA success"))["data"]
        assert task["status"] == "success"
        assert device["firmware_version"] == case["target_version"]
        assert any(task_id in item.get("biz_id", "") or task_id in item.get("message", "") for item in logs["list"])


@pytest.mark.ota
@pytest.mark.data_consistency
@pytest.mark.p0
def test_ota_callback_failed_keeps_device_version_and_records_reason(admin_client, mock_device, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 失败回调", "设备回调失败后记录失败原因且不更新版本", "blocker")

    with report_step("创建 OTA 任务并记录升级前版本"):
        case = ota_cases["normal_ota"]
        ota_service = OtaService(admin_client)
        device_service = DeviceService(admin_client)
        log_service = LogService(admin_client)
        create_response = _create_normal_ota(admin_client, ota_cases)
        task_id = assert_success_response(create_response)["data"]["task_id"]
        before_device = assert_success_response(device_service.get_device_detail(case["device_id"]))["data"]

    with report_step("Mock 设备上报 OTA 失败回调"):
        mock_device.ota_failed(task_id=task_id, device_id=case["device_id"], reason="mock network timeout")

    with report_step("轮询任务直到 failed"):
        task = wait_until_task_status(ota_service, task_id, "failed", timeout=10)

    with report_step("校验失败原因、设备版本和失败日志"):
        after_device = assert_success_response(device_service.get_device_detail(case["device_id"]))["data"]
        logs = assert_success_response(log_service.query_logs(device_id=case["device_id"], keyword="failed"))["data"]
        assert task["status"] == "failed"
        assert "mock network timeout" in task["message"]
        assert after_device["firmware_version"] == before_device["firmware_version"]
        assert logs["total"] >= 1


@pytest.mark.ota
@pytest.mark.p0
def test_create_ota_rejects_offline_device(admin_client, mock_device, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 异常参数", "离线设备不能创建 OTA 任务", "critical")

    with report_step("将测试设备置为 offline"):
        case = ota_cases["offline_device"]
        mock_device.offline(case["device_id"])

    with report_step("尝试对离线设备创建 OTA 任务"):
        response = OtaService(admin_client).create_task(
            device_ids=[case["device_id"]],
            firmware_id=case["firmware_id"],
            target_version=case["target_version"],
        )

    with report_step("校验创建失败"):
        assert_error_response(response, expected_code=case["expected_code"])


@pytest.mark.ota
@pytest.mark.p1
@pytest.mark.parametrize("case_name", ["same_version", "downgrade", "missing_firmware"])
def test_create_ota_rejects_invalid_version_or_firmware(admin_client, ota_cases, case_name):
    case_meta("OTA 固件升级模块", "OTA 异常参数", f"非法固件场景 {case_name} 创建 OTA 失败", "normal")

    with report_step("读取异常 OTA 测试数据"):
        case = ota_cases[case_name]

    with report_step("调用创建 OTA 任务接口"):
        response = OtaService(admin_client).create_task(
            device_ids=[case["device_id"]],
            firmware_id=case["firmware_id"],
            target_version=case["target_version"],
        )

    with report_step("校验系统拒绝非法固件或版本"):
        assert_error_response(response, expected_code=case["expected_code"])


@pytest.mark.ota
@pytest.mark.permission
@pytest.mark.p0
def test_expired_token_cannot_create_ota(expired_client, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 权限控制", "过期 Token 不能创建 OTA 任务", "blocker")

    with report_step("使用非法 Token 调用创建 OTA 任务接口"):
        case = ota_cases["normal_ota"]
        response = OtaService(expired_client).create_task(
            device_ids=[case["device_id"]],
            firmware_id=case["firmware_id"],
            target_version=case["target_version"],
        )

    with report_step("校验返回 401"):
        assert_error_response(response, expected_code=401, allowed_http_status=(401,))


@pytest.mark.ota
@pytest.mark.p1
def test_batch_ota_creates_independent_tasks(admin_client, ota_cases):
    case_meta("OTA 固件升级模块", "OTA 批量升级", "批量 OTA 为多个设备生成独立任务", "normal")

    with report_step("准备批量设备和固件"):
        case = ota_cases["batch_ota"]
        ota_service = OtaService(admin_client)

    with report_step("创建批量 OTA 任务"):
        response = ota_service.create_task(
            device_ids=case["device_ids"],
            firmware_id=case["firmware_id"],
            target_version=case["target_version"],
        )

    with report_step("校验每个设备都有独立任务"):
        data = assert_success_response(response)["data"]
        assert len(data["task_ids"]) == len(case["device_ids"])
        details = [assert_success_response(ota_service.get_task_detail(task_id))["data"] for task_id in data["task_ids"]]
        assert {item["device_id"] for item in details} == set(case["device_ids"])
