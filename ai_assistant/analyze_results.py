from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "reports" / "allure-results"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "ai-analysis-report.md"
DEFAULT_AI_CONFIG = PROJECT_ROOT / "config" / "ai.yaml"
DEFAULT_DOTENV = PROJECT_ROOT / ".env"
DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_API_PATH = "/chat/completions"
DEFAULT_MODEL = "qwen3.7-plus"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def load_ai_config() -> dict[str, Any]:
    config_path = Path(os.getenv("AI_CONFIG_FILE", str(DEFAULT_AI_CONFIG)))
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except OSError:
        return {}

    if not isinstance(data, dict):
        return {}

    llm_config = data.get("llm")
    if isinstance(llm_config, dict):
        return llm_config
    return data


def _resolve_dotenv_value(name: str, values: dict[str, str], seen: set[str] | None = None) -> str:
    seen = seen or set()
    if name in seen:
        return values.get(name, "")
    seen.add(name)

    value = values.get(name, "")

    def replace_var(match: re.Match[str]) -> str:
        ref_name = match.group(1)
        if ref_name in os.environ:
            return os.environ[ref_name]
        return _resolve_dotenv_value(ref_name, values, seen.copy())

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", replace_var, value)


def load_dotenv_config() -> dict[str, str]:
    dotenv_path = Path(os.getenv("AI_DOTENV_FILE", str(DEFAULT_DOTENV)))
    if not dotenv_path.exists():
        return {}

    raw_values: dict[str, str] = {}
    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        raw_values[name.strip()] = value.strip().strip('"').strip("'")

    return {name: _resolve_dotenv_value(name, raw_values) for name in raw_values}


def config_value(config: dict[str, Any], key: str, default: str = "") -> str:
    value = config.get(key)
    return str(value).strip() if value is not None else default


def first_config_value(*values: str | None, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        value = str(value).strip()
        if value:
            return value
    return default


def load_allure_results(results_dir: Path) -> list[dict[str, Any]]:
    if not results_dir.exists():
        return []

    all_cases: list[dict[str, Any]] = []
    for file_path in results_dir.glob("*-result.json"):
        data = _load_json(file_path)
        if not data:
            continue
        labels = {item.get("name"): item.get("value") for item in data.get("labels", []) if isinstance(item, dict)}
        steps = [step.get("name", "") for step in data.get("steps", []) if isinstance(step, dict)]
        all_cases.append(
            {
                "history_id": data.get("historyId") or data.get("uuid") or str(file_path),
                "start": data.get("start", 0),
                "name": data.get("name", ""),
                "status": data.get("status", "unknown"),
                "feature": labels.get("feature", ""),
                "story": labels.get("story", ""),
                "severity": labels.get("severity", ""),
                "full_name": data.get("fullName", ""),
                "message": (data.get("statusDetails") or {}).get("message", ""),
                "trace": (data.get("statusDetails") or {}).get("trace", ""),
                "steps": steps,
            }
        )

    latest_by_case: dict[str, dict[str, Any]] = {}
    for case in all_cases:
        history_id = str(case["history_id"])
        previous = latest_by_case.get(history_id)
        if previous is None or int(case.get("start") or 0) >= int(previous.get("start") or 0):
            latest_by_case[history_id] = case
    return list(latest_by_case.values())


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counter = Counter(case["status"] for case in cases)
    feature_counter: dict[str, Counter] = defaultdict(Counter)
    for case in cases:
        feature_counter[case.get("feature") or "未标注模块"][case["status"]] += 1

    failed = [case for case in cases if case["status"] in {"failed", "broken"}]
    skipped = [case for case in cases if case["status"] == "skipped"]
    return {
        "total": len(cases),
        "status": dict(status_counter),
        "by_feature": {feature: dict(counter) for feature, counter in feature_counter.items()},
        "failed": failed,
        "skipped": skipped,
    }


def build_prompt(summary: dict[str, Any]) -> str:
    compact_failed = []
    for case in summary["failed"][:10]:
        compact_failed.append(
            {
                "name": case["name"],
                "feature": case["feature"],
                "story": case["story"],
                "severity": case["severity"],
                "message": case["message"][:1000],
                "steps": case["steps"][:8],
            }
        )

    payload = {
        "total": summary["total"],
        "status": summary["status"],
        "by_feature": summary["by_feature"],
        "failed_cases": compact_failed,
        "skipped_count": len(summary["skipped"]),
    }
    return (
        "你是资深测试开发工程师，请基于以下 pytest/Allure 自动化测试结果，"
        "输出中文分析报告。报告要包含：1. 本次结果摘要；2. 失败原因分类；"
        "3. 优先排查路径；4. 建议补充的回归用例；5. 对测试框架维护的建议。"
        "如果没有失败用例，请重点分析覆盖情况和下一步可增强点。\n\n"
        f"测试结果 JSON：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def extract_response_text(data: dict[str, Any]) -> str:
    output = data.get("output")
    if isinstance(output, dict):
        native_choices = output.get("choices")
        if isinstance(native_choices, list):
            chunks: list[str] = []
            for choice in native_choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") or {}
                content = message.get("content")
                if isinstance(content, str):
                    chunks.append(content)
            if chunks:
                return "\n".join(chunks).strip()
        if isinstance(output.get("text"), str):
            return output["text"]

    choices = data.get("choices")
    if isinstance(choices, list):
        chunks: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        chunks.append(item["text"])
        if chunks:
            return "\n".join(chunks).strip()

    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    chunks: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def _build_chat_completions_url(base_url: str, api_path: str) -> str:
    base = base_url.rstrip("/")
    path = api_path.strip() or "/chat/completions"
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _raise_for_ai_response(response: requests.Response) -> None:
    if response.ok:
        return
    body = response.text[:800].replace("\n", " ")
    raise requests.HTTPError(
        f"{response.status_code} Client Error for url: {response.url}; response: {body}",
        response=response,
    )


def _post_chat_completions(endpoint: str, api_key: str, model: str, prompt: str) -> str:
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是测试开发专家，擅长分析接口自动化、权限、OTA、日志和数据一致性问题。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "stream": False,
            "enable_thinking": False,
        },
        timeout=120,
    )
    _raise_for_ai_response(response)
    return extract_response_text(response.json())


def call_llm(prompt: str) -> str | None:
    yaml_config = load_ai_config()
    dotenv_config = load_dotenv_config()

    api_key = first_config_value(
        dotenv_config.get("MODEL_API_KEY"),
        dotenv_config.get("DASHSCOPE_API_KEY"),
        os.getenv("MODEL_API_KEY"),
        os.getenv("DASHSCOPE_API_KEY"),
        os.getenv("LLM_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        config_value(yaml_config, "api_key"),
    )
    if not api_key:
        return None

    base_url = first_config_value(
        dotenv_config.get("MODEL_API_BASE"),
        dotenv_config.get("DASHSCOPE_API_BASE"),
        os.getenv("MODEL_API_BASE"),
        os.getenv("DASHSCOPE_API_BASE"),
        os.getenv("LLM_API_BASE"),
        config_value(yaml_config, "base_url"),
        default=DEFAULT_API_BASE,
    )
    api_path = first_config_value(
        dotenv_config.get("MODEL_API_PATH"),
        os.getenv("MODEL_API_PATH"),
        os.getenv("LLM_API_PATH"),
        config_value(yaml_config, "path"),
        default=DEFAULT_API_PATH,
    )
    model = first_config_value(
        dotenv_config.get("MODEL_NAME"),
        dotenv_config.get("DASHSCOPE_MODEL"),
        os.getenv("MODEL_NAME"),
        os.getenv("DASHSCOPE_MODEL"),
        os.getenv("LLM_API_MODEL"),
        os.getenv("OPENAI_MODEL"),
        config_value(yaml_config, "model"),
        default=DEFAULT_MODEL,
    )
    endpoint = _build_chat_completions_url(base_url, api_path)

    return _post_chat_completions(endpoint, api_key, model, prompt)


def rule_based_report(summary: dict[str, Any]) -> str:
    lines = [
        "# AI 辅助测试分析报告",
        "",
        "> 未检测到 `MODEL_API_KEY` / `DASHSCOPE_API_KEY`，本报告使用规则分析生成。配置后会调用 DashScope/OpenAI 兼容接口生成更完整的原因归类和补充用例建议。",
        "",
        "## 1. 结果摘要",
        "",
        f"- 用例总数：{summary['total']}",
    ]
    for status, count in sorted(summary["status"].items()):
        lines.append(f"- {status}：{count}")

    lines.extend(["", "## 2. 模块分布", ""])
    for feature, counter in sorted(summary["by_feature"].items()):
        status_text = "，".join(f"{status}={count}" for status, count in sorted(counter.items()))
        lines.append(f"- {feature}：{status_text}")

    lines.extend(["", "## 3. 失败分析", ""])
    if summary["failed"]:
        for case in summary["failed"]:
            lines.append(f"- `{case['name']}`：{case.get('message') or '未提供错误信息'}")
        lines.extend(
            [
                "",
                "建议优先按以下顺序排查：环境配置、账号权限、测试数据、接口响应、异步状态、日志和数据库记录。",
            ]
        )
    else:
        lines.append("- 本次未发现失败用例。建议继续补充超时、并发、跨组织越权和异常回调场景，提高缺陷发现能力。")

    lines.extend(
        [
            "",
            "## 4. 建议补充用例",
            "",
            "- OTA 超时无回调后任务状态是否变为 timeout。",
            "- 批量 OTA 中部分设备失败时，其他设备任务状态是否独立。",
            "- A 组织账号是否不能查询或操作 B 组织设备。",
            "- 日志导出在大时间范围和空结果时是否稳定。",
            "- Token 过期后刷新或重新登录流程是否符合预期。",
            "",
            "## 5. 维护建议",
            "",
            "- 将历史缺陷补充为固定回归用例。",
            "- 权限矩阵跟随后端角色权限变更同步维护。",
            "- OTA 相关用例保留 task_id、device_id、firmware_id，便于失败复现。",
            "- UI 自动化只保留核心链路，避免维护成本过高。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(summary: dict[str, Any]) -> str:
    prompt = build_prompt(summary)
    try:
        ai_text = call_llm(prompt)
    except requests.RequestException as exc:
        fallback = rule_based_report(summary)
        return fallback + f"\n> AI 调用失败：{exc}\n"

    if not ai_text:
        return rule_based_report(summary)

    return "# AI 辅助测试分析报告\n\n" + ai_text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze pytest Allure results with optional AI assistance.")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS_DIR), help="Allure results directory")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown report output path")
    args = parser.parse_args()

    results_dir = Path(args.results)
    output_path = Path(args.output)
    cases = load_allure_results(results_dir)
    summary = summarize_cases(cases)
    report = build_report(summary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"AI analysis report generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
