from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urljoin

import requests

from common.allure_utils import attach_json
from common.logger import get_logger


class ApiClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: int | float = 5,
        name: str = "anonymous",
        verify_ssl: bool = True,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self.timeout = timeout
        self.name = name
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.default_headers = default_headers or {}
        self.logger = get_logger(f"api.{name}")

    def set_token(self, token: str | None) -> None:
        self.token = token

    def clone(self, *, token: str | None = None, name: str | None = None) -> "ApiClient":
        return ApiClient(
            base_url=self.base_url,
            token=self.token if token is None else token,
            timeout=self.timeout,
            name=name or self.name,
            verify_ssl=self.verify_ssl,
            default_headers=dict(self.default_headers),
        )

    def _build_url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def _headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        result = {"Content-Type": "application/json", **self.default_headers}
        if self.token:
            result["Authorization"] = f"Bearer {self.token}"
        if headers:
            result.update(headers)
        return result

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | float | None = None,
    ) -> requests.Response:
        url = self._build_url(path)
        request_meta = {
            "client": self.name,
            "method": method.upper(),
            "url": url,
            "params": params,
            "json": json_body,
        }
        start = time.perf_counter()
        response = self.session.request(
            method=method.upper(),
            url=url,
            headers=self._headers(headers),
            params=params,
            json=json_body,
            data=data,
            timeout=timeout or self.timeout,
            verify=self.verify_ssl,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text

        response_meta = {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "body": response_body,
        }
        self.logger.info("%s %s -> %s %.2fms", method.upper(), path, response.status_code, elapsed_ms)
        attach_json(f"request-{method.upper()}-{path}", request_meta)
        attach_json(f"response-{method.upper()}-{path}", response_meta)
        return response

    def get(self, path: str, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, json_body: Any | None = None, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, json_body=json_body, **kwargs)

    def put(self, path: str, json_body: Any | None = None, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, json_body=json_body, **kwargs)

    def patch(self, path: str, json_body: Any | None = None, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, json_body=json_body, **kwargs)

    def delete(self, path: str, json_body: Any | None = None, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, json_body=json_body, **kwargs)

    @staticmethod
    def safe_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise AssertionError(
                f"Response is not valid JSON: status={response.status_code}, body={response.text[:500]}"
            ) from exc

    @staticmethod
    def pretty(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return json.dumps(
            {"status_code": response.status_code, "body": body},
            ensure_ascii=False,
            indent=2,
            default=str,
        )

