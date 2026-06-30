from __future__ import annotations

from copy import deepcopy

import pytest

from common.assert_utils import assert_business_code, assert_success_response
from common.reporting import case_meta, report_step
from services.ota_service import OtaService
from services.permission_service import PermissionService


def _prepare_operation(definition, admin_client):
    prepared = deepcopy(definition)
    prepare = prepared.get("prepare")
    if not prepare:
        return prepared

    if prepare["type"] == "ota_task":
        response = OtaService(admin_client).create_task(
            device_ids=[prepare["device_id"]],
            firmware_id=prepare["firmware_id"],
            target_version=prepare["target_version"],
        )
        task_id = assert_success_response(response)["data"]["task_id"]
        prepared["path"] = prepared["path"].format(task_id=task_id)
        return prepared

    raise ValueError(f"Unsupported prepare type: {prepare['type']}")


def _matrix_cases(permission_matrix):
    for operation_name, definition in permission_matrix.items():
        for role, expected_code in definition["roles"].items():
            yield operation_name, role, expected_code


@pytest.mark.permission
@pytest.mark.p0
def test_permission_matrix_is_not_empty(permission_matrix):
    case_meta("权限管理模块", "权限矩阵配置", "权限矩阵 YAML 配置完整", "critical")

    with report_step("读取权限矩阵配置"):
        assert permission_matrix

    with report_step("校验每个权限场景包含 method、path、roles"):
        for operation, definition in permission_matrix.items():
            assert "method" in definition, operation
            assert "path" in definition, operation
            assert "roles" in definition and definition["roles"], operation


@pytest.mark.permission
@pytest.mark.p0
def test_create_ota_permission_quick_check(client_by_role, ota_cases):
    case_meta("权限管理模块", "OTA 创建权限", "不同角色创建 OTA 权限符合预期", "blocker")

    with report_step("准备 OTA 权限期望"):
        case = ota_cases["normal_ota"]
        expectations = {
            "admin": 0,
            "operator": 0,
            "viewer": 403,
            "guest": 403,
        }

    for role, expected_code in expectations.items():
        with report_step(f"{role} 角色调用创建 OTA 接口，预期 code={expected_code}"):
            response = OtaService(client_by_role(role)).create_task(
                device_ids=[case["device_id"]],
                firmware_id=case["firmware_id"],
                target_version=case["target_version"],
            )
            assert_business_code(response, expected_code)


@pytest.mark.permission
@pytest.mark.p0
def test_permission_matrix_by_yaml(permission_matrix, client_by_role, admin_client):
    case_meta("权限管理模块", "权限矩阵执行", "按 YAML 权限矩阵验证所有角色接口权限", "blocker")

    for operation_name, role, expected_code in _matrix_cases(permission_matrix):
        with report_step(f"执行 {operation_name} - {role}，预期 code={expected_code}"):
            definition = _prepare_operation(permission_matrix[operation_name], admin_client)
            response = PermissionService(client_by_role(role)).request_by_definition(definition)
            assert_business_code(response, expected_code)
