from __future__ import annotations

from typing import Any

from common.api_client import ApiClient
from common.assert_utils import assert_success_response


class AuthService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        response = self.client.post(
            "/api/auth/login",
            json_body={"username": username, "password": password},
        )
        data = assert_success_response(response)["data"]
        token = data.get("token")
        assert token, f"Login response does not contain token: {data}"
        return str(token)

    def login_raw(self, username: str, password: str):
        return self.client.post(
            "/api/auth/login",
            json_body={"username": username, "password": password},
        )

    def me(self) -> dict[str, Any]:
        response = self.client.get("/api/auth/me")
        return assert_success_response(response)["data"]

