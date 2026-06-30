# X-SENSE IoT 后台服务端自动化测试项目

本项目根据 `X-SENSE_backend_server_autotest_plan.md` 落地了一套可执行的后台和服务端自动化测试工程。核心路线是：接口自动化为主，数据库一致性和 Mock 设备联动兜底，Playwright UI 自动化只覆盖后台核心链路。

## 目录说明

```text
iot-admin-autotest/
├── common/          # HTTP、断言、DB、等待、Allure 附件等公共能力
├── services/        # 登录、设备、OTA、日志、Mock 设备等业务接口封装
├── testcases/       # pytest 接口、权限、OTA、日志、设备用例
├── ui_cases/        # Playwright UI 核心链路用例
├── mock_server/     # Mock 设备服务 + 本地 Demo 后台服务
├── ai_assistant/    # AI 辅助分析 Allure/pytest 结果
├── config/          # dev/test/pre 多环境配置
├── data/            # 角色、设备、OTA、权限矩阵测试数据
├── docs/            # 具体测试路线、流程图和交付说明
└── scripts/         # 常用运行脚本
```

## 快速运行

```bash
cd outputs/iot-admin-autotest
python -m pip install -r requirements.txt
pytest testcases/ --env=test
```

`config/test.yaml` 默认会自动启动本地 Demo 后台和 Mock 设备服务，方便没有真实 X-SENSE 环境时直接验证框架。接入真实环境时，把 `base_url`、账号、数据库和 `auto_start_mock_backend` 修改为真实配置即可。

## 常用命令

```bash
# 冒烟测试
pytest testcases/ -m smoke --env=test

# OTA 全链路测试
pytest testcases/test_ota.py --env=test --alluredir=reports/allure-results

# 权限矩阵测试
pytest testcases/test_permission.py --env=test

# 日志查询测试
pytest testcases/test_log_query.py --env=test

# UI 测试，默认跳过，需要显式打开；如需有头模式，再追加 --headed
pytest ui_cases/ --env=pre --run-ui

# 生成 Allure 报告
allure serve reports/allure-results
```

## 查看类似截图的 Allure 页面

先生成 Allure 原始结果：

```bash
pytest testcases/ --env=test --alluredir=reports/allure-results
```

如果已经安装 Allure 命令行，直接打开网页：

```bash
allure serve reports/allure-results
```

如果没有安装 `allure`，但电脑有 Node/npm，可以用：

```bash
npx allure-commandline serve reports/allure-results
```

Windows PowerShell 也可以一键运行：

```powershell
.\scripts\run_allure_report.ps1 -EnvName test
```

打开网页后，左侧点击 `Behaviors`，可以看到按中文模块分组的结果，例如 `登录鉴权模块`、`设备管理模块`、`OTA 固件升级模块`、`日志管理模块`、`权限管理模块`。点击单条用例后，右侧会展示中文步骤、请求/响应附件、stdout 和失败堆栈。

## AI 辅助测试分析

项目提供了一个可选 AI 分析链路，会读取 Allure 结果并生成失败原因分析、排查路径和补充用例建议。

不配置 API Key 时，会生成规则版分析报告：

```powershell
.\scripts\run_ai_analysis.ps1 -EnvName test
```

生成报告：

```text
reports/ai-analysis-report.md
```

如果需要真正调用 AI，推荐使用和 `super_biz_agent_py` 一样的 `.env` 配置方式。

先复制模板：

```text
.env.example -> .env
```

然后在 `.env` 中填自己的 API Key：

```dotenv
DASHSCOPE_API_KEY=你的 DashScope API Key
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen3.7-plus

MODEL_API_KEY=${DASHSCOPE_API_KEY}
MODEL_API_BASE=${DASHSCOPE_API_BASE}
MODEL_NAME=${DASHSCOPE_MODEL}
MODEL_API_PATH=/chat/completions
```

这几个变量名和参考项目保持一致：`MODEL_API_KEY`、`MODEL_API_BASE`、`MODEL_NAME`。代码会按 OpenAI-compatible 的 `/chat/completions` 请求格式调用模型。

也可以继续用 `config/ai.yaml` 作为可选兜底配置：

```yaml
model: "qwen3.7-plus"
api_key: "你的 DashScope API Key"
```

或者临时设置环境变量：

```powershell
$env:MODEL_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:MODEL_API_PATH="/chat/completions"
$env:MODEL_NAME="qwen3.7-plus"
$env:MODEL_API_KEY="你的 DashScope API Key"
.\scripts\run_ai_analysis.ps1 -EnvName test
```

如果你习惯使用 DashScope 官方变量名，也可以配置：

```powershell
$env:DASHSCOPE_API_KEY="你的 DashScope API Key"
$env:DASHSCOPE_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:DASHSCOPE_MODEL="qwen3.7-plus"
.\scripts\run_ai_analysis.ps1 -EnvName test
```

配置优先级：环境变量优先，其次读取 `.env`，再读取 `config/ai.yaml`。如果都没有 API Key，则自动生成规则版分析报告。

AI 分析模块位置：

```text
ai_assistant/analyze_results.py
```

## 接入真实项目时需要替换

1. `config/*.yaml` 中的域名、账号、数据库配置。
2. `services/*.py` 中的接口路径和字段名。
3. `data/*.yaml` 中的测试设备、固件包、权限矩阵。
4. `ui_cases/*.py` 中的页面地址和元素定位。
5. 如果真实环境已有设备回调机制，可保留 `mock_server/mock_device_server.py` 作为异常场景模拟工具。

## 交付文档

详细测试路线、流程图、执行分层、OTA 全链路设计见：

```text
docs/测试流程文档.md
```
