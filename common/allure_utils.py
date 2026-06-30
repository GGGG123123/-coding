from __future__ import annotations

import json
from typing import Any


try:
    import allure
except Exception:  # pragma: no cover - allure is optional for local smoke runs
    allure = None


def attach_text(name: str, content: str) -> None:
    if allure is None:
        return
    allure.attach(content, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_json(name: str, content: Any) -> None:
    if allure is None:
        return
    text = json.dumps(content, ensure_ascii=False, indent=2, default=str)
    allure.attach(text, name=name, attachment_type=allure.attachment_type.JSON)


def attach_bytes(name: str, content: bytes, attachment_type: Any | None = None) -> None:
    if allure is None:
        return
    allure.attach(content, name=name, attachment_type=attachment_type)

