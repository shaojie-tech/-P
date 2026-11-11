# 面试官小P 🎤

> **DeepSeek 驱动的 Python/后端 AI 面试助手** —— 模拟面试、实时题库、语音通话，帮你为真实面试做足准备。

基于 DeepSeek 大模型 + Vue3 前端 + FastAPI 后端，支持多用户账号与会话持久化，提供**模拟面试**与**辅导答疑**两种模式，另有定制面试与像打电话一样的语音通话。

**目录**：[功能特性](#-功能特性) · [快速开始](#-快速开始) · [使用指南](#-使用指南) · [题库与更新](#-题库与更新) · [运行测试](#-运行测试) · [配置项](#️-配置项) · [常见问题](#-常见问题) · [贡献指南](#-贡献指南) · [License](#-license)

## ✨ 功能特性

**面试模式**
- **模拟面试** —— 自我介绍 → 六阶段递进出题 → 每题点评 + 追问深挖 → 结束时输出 0-100 评分报告。
- **辅导答疑** —— 直接提问即获得"标准参考回答 + 加分点 + 变式题"，自动检索本地题库辅助作答。
- **定制面试** —— 输入目标岗位 + JD，生成专属递进式面试题后开始面试。

**题库与工程**
- **实时题库** —— 自动爬取面试鸭 + JavaGuide，SQLite 本地增量去重，定时自动更新。
- **多用户账号** —— 会话 / 收藏 / 定制面试按账号隔离并持久化，换设备不丢失。
- **流式输出 & 健壮性** —— SSE 逐字渲染；LLM 重试、上下文压缩、题库降级、SQLite WAL，稳。

**语音通话**
- **像打电话一样** —— 边说边答、开口即打断、edge-tts 边生成边播报。

## 🧱 项目结构

```
智能面试/
├── app/                  # 后端（统一 FastAPI 服务）
│   ├── main.py            # 入口：挂载 REST/WS，托管前端 dist
│   ├── voice_ws.py       # 语音 WebSocket 协议处理
│   ├── routers/          # REST 路由层：auth / session / questions / custom
│   ├── agent/            # 领域层：会话状态机 + LLM 封装
│   ├── crawler/          # 采集层：题库爬虫适配器
│   ├── core/             # 基础设施：config / db / ratelimit / scheduler
│   ├── services/         # 业务服务：tts / asr_client / prompts / importer
│   ├── stores/           # 数据访问层：session / voice / auth 持久化
│   └── ui/assets/        # 静态资源（虚拟人物头像，运行时 /assets 挂载源）
├── frontend/     # Vue3 前端工程（Vite + Element Plus；public/assets 供构建期引用）
├── tests/        # 单元测试（数据层、爬虫、LLM、状态机、语音、多用户）
├── scripts/      # start.bat（Windows）/ start.sh（macOS·Linux）
├── docs/         # 设计文档
└── deploy/       # Dockerfile + docker-compose.yml
```

## 🚀 快速开始

**环境要求**：Python 3.10+；一个 [DeepSeek API Key](https://platform.deepseek.com)。

```bash
# 1. 安装依赖（仅运行可去掉 [dev]）
pip install -e ".[dev]"

# 2. 配置密钥
copy .env.example .env     # 编辑 .env，填入 DEEPSEEK_API_KEY=sk-你的key
```

> ⚠️ `.env` 已被 `.gitignore` 排除，请勿提交真实密钥。

**启动**（三选一）：

- **Windows（推荐）**：双击 `scripts/start.bat` —— 自动装依赖、构建前端、开浏览器。
- **命令行**：

  ```bash
  cd frontend && npm install && npm run build && cd ..
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
  ```

- **Docker**：`cd deploy && docker compose up -d`

访问 <http://localhost:8765>，注册即用（聊天 `/`、语音 `/voice`）。

## 📖 使用指南

- **模拟面试**：点「开始面试」，小P 按六阶段递进：Python 基础 → 算法 → 数据库/SQL → 网络并发 → 项目深挖 → 场景设计。每题点评 + 追问深挖，结束输出评分报告与改进清单。
- **辅导答疑**：直接输入问题（如"Redis 缓存穿透怎么答"），得到标准回答 + 加分点 + 同类变式题。
- **定制面试**：输入目标岗位 + JD（可不填），生成专属题目后进入模拟面试。
- **语音通话**：右下角 📞 进入 `/voice`。点「接通」即可边说边答、开口即打断；说"开始面试"自动切模拟面试；按钮变「挂断」即停播断开。需登录并配置 `DASHSCOPE_API_KEY`，浏览器用 Chrome / Edge。

## 🗂 题库与更新

```bash
python -m app.crawler.run              # 手动全量抓取（面试鸭 + JavaGuide）
python -m app.crawler.run --limit 50   # 调试：每源最多 N 条
```

启动自动抓一次，之后每日 `CRAWL_TIME` 与按间隔 `CRAWL_INTERVAL_HOURS` 更新，按内容哈希增量去重、单实例锁防重复。默认源为面试鸭 + JavaGuide；LeetCode 需 `CRAWL_LEETCODE=1` 开启。新增源继承 `app/crawler/base.py` 的 `SourceAdapter` 并登记到 `run.py`。

## 🧪 运行测试

```bash
python -m pytest   # 全量测试（LLM / 网络均已 mock，不触网不耗额度）
ruff check .       # 静态检查
```

## ⚙️ 配置项

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DEEPSEEK_API_KEY` | 无 | DeepSeek 密钥（**必填**） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名 |
| `LLM_TIMEOUT_SECONDS` / `LLM_MAX_RETRIES` | `120` / `3` | LLM 超时与重试 |
| `CRAWL_TIME` / `CRAWL_INTERVAL_HOURS` | `02:00` / `24` | 定时抓取 |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8765` | 服务地址 / 端口 |
| `TOKEN_TTL_DAYS` | `30` | 登录令牌有效期 |
| `VOICE_TTS` | `edge` | 语音引擎：`edge` / `cosyvoice` / `local` |
| `DASHSCOPE_API_KEY` | 无 | 语音识别 / CosyVoice 用 |
| `DISABLE_SCHEDULER` | 未设置 | `1` 禁用后台爬取 |

> 完整参数（音色、语速、CosyVoice、VAD 阈值等）见 [.env.example](.env.example)。

## ❓ 常见问题

1. **题库为空？** 先运行 `python -m app.crawler.run`，或查 `data/scheduler.log`。
2. **语音输入不工作？** 用 Chrome / Edge 并登录；`/health` 应返回 `{"status":"ok"}`；确认已配 `DASHSCOPE_API_KEY`。
3. **多实例会重复抓取吗？** 不会，`data/scheduler.lock` 单实例锁保证只跑一次调度。

## 🤝 贡献指南

欢迎提交 Issue 与 PR。开发约定请先读 [AGENTS.md](AGENTS.md)；提交规范 `type(scope): 中文描述`、一个需求一个提交；`pytest` 全量离线通过 + `ruff` 干净后再提交，经 PR 合入 `main`（受保护需通过 CI）。基于 WorkBuddy 平台的多人协作流程（职责边界 / 任务流转 / 资产库存放清单 / 成员准入）见 [docs/TEAM_COLLABORATION.md](docs/TEAM_COLLABORATION.md)。

## 📄 License

[MIT](LICENSE) © 2026 MianShiGuanXiaoP Contributors