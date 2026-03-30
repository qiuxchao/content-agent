# Content Agent

AI 内容生产 Agent，基于 LangGraph + LangChain，输入主题自动生成多平台文章（微信公众号 / 小红书 / 知乎）。

## 技术栈

- **Agent**: Python 3.11+, LangGraph, LangChain
- **LLM**: OpenAI 兼容（DeepSeek/Kimi/通义等）+ Anthropic Claude
- **搜索**: Tavily
- **向量库**: Chroma（本地持久化 `data/vectorstore/`）
- **数据库**: SQLite（`data/content-agent.db`，WAL 模式）
- **API**: FastAPI + SSE 流式输出
- **前端**: Next.js + React 19 + Ant Design + Tailwind CSS
- **包管理**: Python 用 `uv`，前端用 `bun`

## 启动方式

```bash
# API 服务
uv run uvicorn api.server:app --reload --port 8917

# 前端（另一个终端）
cd web && bun dev
# 访问 http://localhost:3917
```

## 项目结构

```
agent/
  graph.py          # LangGraph 主图定义
  state.py          # AgentState 共享状态
  llm.py            # LLM 工厂（OpenAI/Anthropic）
  config.py         # 配置读取（env > SQLite > default）
  db.py             # SQLite 数据库
  memory.py         # Chroma 向量库（RAG）
  nodes/            # 图节点
    pre_researcher   → planner → researcher → writer → critic
                       ↑ (retry ≤2, score <7)  ↓ (pass)
                       └── increment_retry ←───┘
                                          image_fetcher → save_memory → END
  prompts/templates.py   # 平台 Prompt 模板 + 方向预设
  publish/               # 微信发布（MD→HTML、API、封面）
  tools/                 # 搜索、生图、截图、Unsplash
api/server.py            # FastAPI 路由
web/                     # Next.js 前端
```

## 配图系统

Writer 在初稿中插入占位符，ImageFetcher 节点替换为真实图片。两种占位符：

- `[IMAGE: 详细英文绘图提示词]` — AI 生图或 Unsplash 搜图
- `[SCREENSHOT: url, 中文描述]` — Playwright 截取网页

通过 `IMAGE_PROVIDER` 配置控制模式：
- `prompt` — 仅生成提示词，用户手动上传
- `screenshot` — 纯截图模式
- `mixed` — 混合模式（Writer 自行选择截图或生图）
- `unsplash` / `openai` / `gemini` 等 — AI 生图

## 开发约定

- 配置优先级：环境变量 > SQLite settings 表 > 默认值
- LLM 实例通过 `@lru_cache` 缓存，配置变更需重启
- 前端设置修改写入 SQLite，无需重启即生效（热更新）
- 图片保存到 `data/images/`，通过 `/api/images/{filename}` 访问
- SSE 流式事件格式：`{node, data, active}`，`active` 字段标记当前执行节点
- 中文正文，英文专有名词保留原文
- 修改代码时，要考虑是否需要同步全局注释/文档
