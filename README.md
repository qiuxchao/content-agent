# Content Agent

基于 LangGraph + LangChain 构建的 AI 内容生产 Agent，输入主题，自动搜集资讯、生成文章，支持公众号、小红书、知乎三个平台，并自动配插图。

![Content Agent 预览](assets/preview.png)

## 功能

- **多平台写作**：根据平台风格差异自动调整文章结构、字数、语气、emoji 用法
- **自动搜索素材**：调用 Tavily 搜索最新资讯，LLM 提炼整理
- **质量自检**：Critic 节点给初稿打分，不达标自动重写（最多 2 次）
- **RAG 素材库**：历史素材存入向量库，写相关主题时自动关联复用
- **自动配图**：解析文章中的图片占位符，调用 Unsplash 获取真实配图
- **Web UI**：Next.js 前端，实时显示 Agent 状态、搜索关键词、质量评分
- **可观测**：接入 LangSmith，每个节点的输入输出一目了然，方便调试 Prompt

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph (Python) |
| LLM | 兼容 OpenAI / Anthropic 规范的任意模型 |
| 搜索 | Tavily Search API |
| 配图 | Unsplash API |
| RAG | Chroma (本地向量库) |
| API 层 | FastAPI + SSE |
| 前端 | Next.js + Tailwind CSS |
| 可观测 | LangSmith |
| 包管理 | uv (Python) / npm (前端) |

## 项目结构

```
content-agent/
├── agent/                       # Agent 核心
│   ├── graph.py                 # LangGraph 主图，定义节点和执行顺序
│   ├── state.py                 # 共享状态定义（AgentState）
│   ├── llm.py                   # LLM 工厂，统一管理模型配置
│   ├── memory.py                # RAG 向量库读写（Chroma）
│   ├── nodes/
│   │   ├── planner.py           # 把主题拆解成搜索关键词
│   │   ├── researcher.py        # 搜索 + 检索历史素材 + 提炼
│   │   ├── writer.py            # 按平台 Prompt 生成初稿
│   │   ├── critic.py            # 给初稿打分，提出修改建议
│   │   └── image_fetcher.py     # 解析占位符，获取 Unsplash 图片
│   ├── prompts/
│   │   └── templates.py         # 三个平台的写作 Prompt 模板
│   └── tools/
│       ├── search.py            # Tavily 搜索工具
│       └── unsplash.py          # Unsplash 图片搜索工具
├── api/                         # FastAPI 后端
│   └── server.py                # SSE 流式接口
├── web/                         # Next.js 前端
│   └── app/
│       ├── page.tsx             # 主页面
│       └── components/
│           ├── InputPanel.tsx    # 左侧：主题输入 + 平台选择
│           ├── ArticlePanel.tsx  # 中间：文章渲染
│           └── StatusPanel.tsx   # 右侧：Agent 状态面板
├── data/                        # 本地数据（git 忽略）
│   └── vectorstore/             # Chroma 向量库
├── run.py                       # CLI 入口
├── inspect_memory.py            # 查看向量库内容
├── pyproject.toml
└── .env.example
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)（Python 包管理）

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/content-agent.git
cd content-agent
```

### 2. 安装依赖

```bash
# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 Python 依赖
uv sync

# 安装前端依赖
cd web && bun install && cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入以下配置：

**LLM 配置（支持任意兼容 OpenAI 规范的服务）**

| 变量 | 说明 |
|---|---|
| `LLM_PROVIDER` | `openai`（默认）或 `anthropic` |
| `LLM_API_KEY` | 对应服务的 API Key |
| `LLM_BASE_URL` | API 地址，使用 OpenAI 官方可留空 |
| `LLM_MODEL` | 模型名称 |

常用服务配置示例：

```bash
# Kimi
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# DeepSeek
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# OpenAI 官方
LLM_PROVIDER=openai
LLM_BASE_URL=    # 留空
LLM_MODEL=gpt-4o-mini

# Anthropic Claude（需额外安装：uv add langchain-anthropic）
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-haiku-20241022
```

**Embedding 配置（RAG 素材库）**

Embedding 模型用于向量化素材。如果你的 LLM 服务不提供 Embedding API（如 Kimi），需要单独配置：

| 变量 | 说明 |
|---|---|
| `EMBEDDING_MODEL` | 向量化模型名称 |
| `EMBEDDING_BASE_URL` | Embedding API 地址，留空则跟 `LLM_BASE_URL` 一致 |
| `EMBEDDING_API_KEY` | Embedding API Key，留空则复用 `LLM_API_KEY` |

```bash
# 推荐：硅基流动（免费，中文效果好）
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_API_KEY=你的硅基流动key

# 或者：OpenAI 官方
EMBEDDING_MODEL=text-embedding-ada-002
```

**其他 Key**

| 变量 | 获取地址 | 是否必填 |
|---|---|---|
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com)（免费 1000次/月） | 必填 |
| `UNSPLASH_ACCESS_KEY` | [unsplash.com/developers](https://unsplash.com/developers)（免费） | 必填 |
| `LANGCHAIN_API_KEY` | [smith.langchain.com](https://smith.langchain.com)（免费） | 可选，用于调试 |

### 4. 启动

有两种使用方式：

#### 方式一：命令行（CLI）

编辑 `run.py` 顶部的两个变量：

```python
TOPIC    = "OpenAI o3 模型发布"
PLATFORM = "xiaohongshu"   # wechat | xiaohongshu | zhihu
```

运行：

```bash
uv run run.py
```

生成的文章会打印到终端，同时保存为 `output_<平台>_<时间戳>.md`。

#### 方式二：Web UI（推荐）

需要同时启动后端 API 和前端，打开两个终端窗口：

**终端 1 — 启动 Python API：**

```bash
uv run uvicorn api.server:app --reload --port 8917
```

**终端 2 — 启动 Next.js 前端：**

```bash
cd web
bun dev
```

打开浏览器访问 http://localhost:3917

## Agent 执行流程

```
用户输入主题
    │
    ▼
[Planner]        把主题拆解成 2~4 个搜索关键词
    │
    ▼
[Researcher]     ① 从向量库检索历史相关素材
                 ② 对每个关键词调用 Tavily 搜索
                 ③ LLM 整理去重，输出素材摘要
    │
    ▼
[Writer]         调用平台对应的 Prompt 模板
                 生成含 [IMAGE: 关键词] 占位符的初稿
    │
    ▼
[Critic]         给初稿打分（满分 10 分）
                 ≥ 7 分 → 继续
                 < 7 分 → 带修改建议回到 Researcher 重写（最多 2 次）
    │
    ▼
[ImageFetcher]   解析所有占位符
                 调用 Unsplash 获取图片
                 替换为 Markdown 图片格式
    │
    ▼
[SaveMemory]     把本次素材存入向量库，供未来检索
    │
    ▼
最终文章（Markdown 格式）
```

## 三平台风格说明

| | 公众号 | 小红书 | 知乎 |
|---|---|---|---|
| 字数 | 1500~2500 | 400~600 | 1000~2000 |
| 标题风格 | 数字/悬念感 | emoji + 口语化 | 问题式/观点式 |
| 结构 | H2 分节，有逻辑层次 | 分点列举 | 先结论后论据 |
| 语气 | 有温度，有观点 | 闺蜜感，接地气 | 理性克制 |
| 插图位置 | 每个段落前 | 文章首行 | 关键段落前 |

## 自定义

### 修改 Prompt 模板

编辑 `agent/prompts/templates.py` 中对应平台的模板。

约定：在需要插图的位置写 `[IMAGE: 英文关键词]`，ImageFetcher 节点会自动替换。

### 查看向量库内容

```bash
uv run inspect_memory.py
```

### 添加新平台

1. 在 `agent/state.py` 的 `Platform` 类型中添加新值
2. 在 `agent/prompts/templates.py` 中添加对应的 Prompt 模板

## 调试

接入 LangSmith 后，访问 [smith.langchain.com](https://smith.langchain.com) 可以看到每次运行的完整 Trace，包括每个节点的输入、输出、耗时和 Token 用量。

`.env` 中配置：

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=你的key
LANGCHAIN_PROJECT=content-agent
```

## 参考

- 写作 Prompt 中的标题公式参考了 [baoyu-skills](https://github.com/JimLiu/baoyu-skills)

## License

MIT
