from __future__ import annotations

from typing import Any, Iterable

import requests


def response_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise AssertionError(f"Expected JSON response, got: {response.text[:500]}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"Expected JSON object, got: {type(data).__name__}")
    return data


def assert_http_status(response: requests.Response, expected: int = 200) -> dict[str, Any]:
    assert response.status_code == expected, (
        f"HTTP status mismatch: expected={expected}, actual={response.status_code}, body={response.text[:500]}"
    )
    return response_json(response)


def assert_business_code(response: requests.Response, expected_code: int = 0) -> dict[str, Any]:
    data = response_json(response)
    actual_code = data.get("code")
    assert actual_code == expected_code, (
        f"Business code mismatch: expected={expected_code}, actual={actual_code}, body={data}"
    )
    return data


def assert_success_response(response: requests.Response, max_seconds: float | None = 2) -> dict[str, Any]:
    assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}: {response.text[:500]}"
    data = assert_business_code(response, 0)
    assert "data" in data, f"Response should contain data field: {data}"
    if max_seconds is not None:
        assert response.elapsed.total_seconds() <= max_seconds, (
            f"Response too slow: {response.elapsed.total_seconds():.3f}s > {max_seconds}s"
        )
    return data


def assert_error_response(
    response: requests.Response,
    *,
    expected_code: int,
    allowed_http_status: Iterable[int] = (200, 400, 401, 403, 404),
) -> dict[str, Any]:
    assert response.status_code in allowed_http_status, (
        f"Unexpected HTTP status: {response.status_code}, body={response.text[:500]}"
    )
    return assert_business_code(response, expected_code)


def assert_required_keys(data: dict[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in data]
    assert not missing, f"Missing keys: {missing}, actual keys={list(data.keys())}"


def assert_page_result(data: dict[str, Any]) -> None:
    assert_required_keys(data, ["list", "page", "size", "total"])
    assert isinstance(data["list"], list), "data.list must be a list"
    assert isinstance(data["page"], int), "data.page must be int"
    assert isinstance(data["size"], int), "data.size must be int"
    assert isinstance(data["total"], int), "data.total must be int"


def extract_data(response: requests.Response) -> Any:
    return assert_success_response(response)["data"]

