from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator


try:
    import allure
except Exception:  # pragma: no cover - report labels are optional outside Allure runs
    allure = None


SEVERITY_MAP = {
    "blocker": "BLOCKER",
    "critical": "CRITICAL",
    "normal": "NORMAL",
    "minor": "MINOR",
    "trivial": "TRIVIAL",
}


def case_meta(feature: str, story: str, title: str, severity: str = "normal") -> None:
    if allure is None:
        return
    allure.dynamic.epic("X-SENSE 后台和服务端自动化测试")
    allure.dynamic.feature(feature)
    allure.dynamic.story(story)
    allure.dynamic.title(title)
    severity_name = SEVERITY_MAP.get(severity.lower(), "NORMAL")
    allure.dynamic.severity(getattr(allure.severity_level, severity_name))


@contextmanager
def report_step(name: str) -> Iterator[None]:
    if allure is None:
        yield
        return
    with allure.step(name):
        yield

